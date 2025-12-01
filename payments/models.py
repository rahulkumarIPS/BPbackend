from django.db import models
from bookings.models import Booking

class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="payment")

    razorpay_order_id = models.CharField(max_length=200, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=200, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=200, null=True, blank=True)

    amount = models.IntegerField()
    status = models.CharField(max_length=20, default="CREATED")  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment - {self.booking.id}"
