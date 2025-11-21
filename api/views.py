from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import Site, Booking, OptionalCharge
from .serializers import SiteSerializer, BookingSerializer
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
