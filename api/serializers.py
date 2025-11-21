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

class SiteSerializer(serializers.ModelSerializer):
    location = LocationSerializer()
    pricings = PricingSerializer(many=True)
    charges = serializers.SerializerMethodField()

    class Meta:
        model = Site
        fields = ['id','name','location','address','total_slots_car','total_slots_bike','pricings','charges']

    def get_charges(self, obj):
        return [{'id': c.id, 'name': c.name, 'amount': c.amount} for c in obj.charges.filter(is_active=True)]

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'
