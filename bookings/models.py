from django.db import models
from django.contrib.auth.models import User
from parking.models import ParkingSite
from django.utils import timezone

class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parking_site = models.ForeignKey(ParkingSite, on_delete=models.CASCADE)
    vehicle_type = models.CharField(max_length=10, choices=(("CAR", "Car"), ("BIKE", "Bike")))

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    base_price = models.IntegerField(default=0)
    optional_price = models.IntegerField(default=0)
    total_price = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)

    payment_status = models.CharField(
        max_length=20,
        choices=(("PENDING", "Pending"), ("PAID", "Paid"), ("FAILED", "Failed")),
        default="PENDING"
    )

    def __str__(self):
        return f"Booking #{self.id} - {self.user.username}"
