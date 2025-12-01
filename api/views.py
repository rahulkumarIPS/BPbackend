from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authentication import TokenAuthentication
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import Site, Location, Booking, OptionalCharge
from .serializers import SiteSerializer, BookingSerializer, SiteCreateSerializer
from .utils import calculate_amount
from .razorpay_client import client
import razorpay
import datetime
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

@api_view(['GET'])
def search_sites(request):
    q = request.query_params.get('q', '')
    pincode = request.query_params.get('pincode', '')
    qs = Site.objects.select_related('location').all()
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(location__name__icontains=q)
    if pincode:
        qs = qs.filter(location__pincode__icontains=pincode)
    serializer = SiteSerializer(qs, many=True)
    return Response(serializer.data)

@authentication_classes([TokenAuthentication])
@permission_classes([IsAdminUser])
@api_view(['POST'])
def create_site(request):
    """
    Create a new parking site with location details embedded.
    body: {
        "site_name": "Site Name",
        "address": "Full address",
        "total_slots_car": 50,
        "total_slots_bike": 100,
        "location_name": "Andheri East",
        "pincode": "400069",
        "lat": 19.1136,
        "lng": 72.8697
    }
    """
    try:
        data = request.data
        # Check for duplicate site (location is a related object)
        location = Location.objects.filter(
            name=data.get('location_name'),
            pincode=data.get('pincode'),
            lat=data.get('lat'),
            lng=data.get('lng')
        ).first()
        if location:
            duplicate = Site.objects.filter(
                name=data.get('site_name'),
                address=data.get('address'),
                total_slots_car=data.get('total_slots_car'),
                total_slots_bike=data.get('total_slots_bike'),
                location=location
            ).first()
            if duplicate:
                return Response({'detail': 'Site with these details already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SiteCreateSerializer(data=data)
        if serializer.is_valid():
            site = serializer.save()
            response_serializer = SiteSerializer(site)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_sites(request):
    """
    List all sites for admin management.
    """
    sites = Site.objects.select_related('location').all()
    serializer = SiteSerializer(sites, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def calculate_price(request):
    """
    body: { site_id, vehicle_type, start_time, end_time, optional_charges: [ids] }
    """
    data = request.data
    site = get_object_or_404(Site, id=data['site_id'])
    start = datetime.datetime.fromisoformat(data['start_time'])
    end = datetime.datetime.fromisoformat(data['end_time'])
    result = calculate_amount(site, data['vehicle_type'], start, end, data.get('optional_charges', []))
    return Response(result)

@api_view(['POST'])
def book_create(request):
    """
    Create booking and create Razorpay order.
    """
    data = request.data
    site = get_object_or_404(Site, id=data['site_id'])
    start = datetime.datetime.fromisoformat(data['start_time'])
    end = datetime.datetime.fromisoformat(data['end_time'])
    calc = calculate_amount(site, data['vehicle_type'], start, end, data.get('optional_charges', []))
    amount_in_inr = Decimal(calc['total_amount'])
    amount_paise = int(amount_in_inr * 100)

    # Build razorpay order
    razorpay_order = client.order.create({
        'amount': amount_paise,
        'currency': 'INR',
        'payment_capture': '1'  # auto capture
    })

    with transaction.atomic():
        booking = Booking.objects.create(
            user=request.user if request.user.is_authenticated else None,
            site=site,
            vehicle_type=data['vehicle_type'],
            start_time=start,
            end_time=end,
            duration_minutes=calc['duration_minutes'],
            base_amount=Decimal(calc['base_amount']),
            total_amount=Decimal(calc['total_amount']),
            razorpay_order_id=razorpay_order['id'],
            status='pending'
        )
        if data.get('optional_charges'):
            booking.optional_charges.set(OptionalCharge.objects.filter(id__in=data['optional_charges']))

    return Response({
        'booking_id': str(booking.id),
        'razorpay_order_id': razorpay_order['id'],
        'amount': amount_paise,
        'razorpay_key': settings.RAZORPAY_KEY_ID
    }, status=201)

@api_view(['POST'])
def verify_payment(request):
    """
    After Razorpay checkout success, frontend posts:
    { booking_id, razorpay_payment_id, razorpay_order_id, razorpay_signature }
    """
    payload = request.data
    booking = get_object_or_404(Booking, id=payload['booking_id'])
    try:
        # Verify signature
        params_dict = {
            'razorpay_order_id': payload['razorpay_order_id'],
            'razorpay_payment_id': payload['razorpay_payment_id'],
            'razorpay_signature': payload['razorpay_signature']
        }
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        return Response({'detail': 'Signature verification failed'}, status=status.HTTP_400_BAD_REQUEST)

    # mark paid
    booking.razorpay_payment_id = payload['razorpay_payment_id']
    booking.razorpay_signature = payload['razorpay_signature']
    booking.status = 'paid'
    booking.save()

    # Trigger background tasks: send email, sms, generate pdf
    from .tasks import send_booking_notifications
    send_booking_notifications.delay(str(booking.id))

    return Response({'detail': 'Payment verified and booking confirmed.'})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_pricing(request):
    """
    Create pricing for a site.
    body: {
        "site_id": 1,
        "vehicle_type": "car",
        "tier": "0_2",
        "price": 60.00
    }
    """
    from .serializers import PricingSerializer
    try:
        data = request.data.copy()
        serializer = PricingSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_optional_charge(request):
    """
    Create an optional charge.
    body: {
        "site_id": 1,
        "name": "Valet Parking",
        "amount": 50.00,
        "is_active": true
    }
    """
    from .serializers import OptionalChargeSerializer
    try:
        data = request.data.copy()
        serializer = OptionalChargeSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
