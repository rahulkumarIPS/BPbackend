from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()

VEHICLE_CHOICES = (
    ('car', 'Car'),
    ('bike', 'Bike'),
)

BOOKING_STATUS = (
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('cancelled', 'Cancelled'),
    ('expired', 'Expired'),
)

class Location(models.Model):
    name = models.CharField(max_length=255)     
    pincode = models.CharField(max_length=20, blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.pincode})"

class Site(models.Model):
    """A parking site (specific car park)"""
    name = models.CharField(max_length=255)  # site name
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='sites')
    address = models.TextField(blank=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    total_slots_car = models.IntegerField(default=0)
    total_slots_bike = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.location.name}"

class Pricing(models.Model):
    """
    Pricing per site, per vehicle type.
    We'll store named tiers like '0-2', '2-4', 'full-day', 'monthly'
    """
    TIER_CHOICES = (
        ('0_2', '0 to 2 hrs'),
        ('2_4', 'After 2 hrs to 4 hrs'),
        ('full_day', 'Full Day'),
        ('monthly', 'Monthly Pass'),
    )

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='pricings')
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES)
    tier = models.CharField(max_length=30, choices=TIER_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # currency INR

    class Meta:
        unique_together = ('site', 'vehicle_type', 'tier')

    def __str__(self):
        return f"{self.site} | {self.vehicle_type} | {self.tier} = {self.price}"

class OptionalCharge(models.Model):
    """Admin-only extra charges that may be applied per booking"""
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='charges', null=True, blank=True)
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.amount}"

class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='api_bookings')
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES)
    slot_number = models.CharField(max_length=50, blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.IntegerField()
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    optional_charges = models.ManyToManyField(OptionalCharge, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Booking {self.id} - {self.site.name} - {self.status}"
