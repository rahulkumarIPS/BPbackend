from rest_framework import serializers
from .models import Site, Location, Booking, Pricing, OptionalCharge

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class PricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = '__all__'

class OptionalChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionalCharge
        fields = '__all__'

class SiteSerializer(serializers.ModelSerializer):
    location = LocationSerializer()
    pricings = PricingSerializer(many=True)
    charges = serializers.SerializerMethodField()

    class Meta:
        model = Site
        fields = ['id','name','location','address','pincode','lat','lng','total_slots_car','total_slots_bike','pricings','charges','created_at']

    def get_charges(self, obj):
        return [{'id': c.id, 'name': c.name, 'amount': c.amount} for c in obj.charges.filter(is_active=True)]

class SiteCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a site with embedded location data.
    """
    site_name = serializers.CharField(max_length=255)
    address = serializers.CharField(required=False, allow_blank=True)
    pincode = serializers.CharField(max_length=20, required=False, allow_blank=True)
    lat = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    total_slots_car = serializers.IntegerField(default=0)
    total_slots_bike = serializers.IntegerField(default=0)
    location_name = serializers.CharField(max_length=255)

    def create(self, validated_data):
        # Extract location fields
        location_data = {
            'name': validated_data.pop('location_name'),
            'pincode': validated_data.pop('pincode', None),
            'lat': validated_data.pop('lat', None),
            'lng': validated_data.pop('lng', None),
        }
        
        # Create or get location
        location, _ = Location.objects.get_or_create(
            name=location_data['name'],
            defaults={
                'pincode': location_data['pincode'],
                'lat': location_data['lat'],
                'lng': location_data['lng'],
            }
        )
        
        # Create site with location and optional fields
        site = Site.objects.create(
            name=validated_data['site_name'],
            address=validated_data.get('address', ''),
            pincode=validated_data.get('pincode'),
            lat=validated_data.get('lat'),
            lng=validated_data.get('lng'),
            total_slots_car=validated_data.get('total_slots_car', 0),
            total_slots_bike=validated_data.get('total_slots_bike', 0),
            location=location
        )
        
        return site

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'
