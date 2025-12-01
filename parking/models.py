from django.db import models

class ParkingSite(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    def __str__(self):
        return self.name


class ParkingPrice(models.Model):
    VEHICLE_CHOICES = (
        ('CAR', 'Car'),
        ('BIKE', 'Bike'),
    )

    parking_site = models.ForeignKey(ParkingSite, on_delete=models.CASCADE, related_name="prices")
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_CHOICES)

    upto_2_hours = models.IntegerField()
    two_to_four_hours = models.IntegerField()
    full_day = models.IntegerField()
    monthly_pass = models.IntegerField()

    def __str__(self):
        return f"{self.parking_site.name} - {self.vehicle_type}"


class OptionalCharge(models.Model):
    parking_site = models.ForeignKey(ParkingSite, on_delete=models.CASCADE, related_name="optional_charges")
    name = models.CharField(max_length=200)
    amount = models.IntegerField()

    def __str__(self):
        return f"{self.name} - {self.amount}"
