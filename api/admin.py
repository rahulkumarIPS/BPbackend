from django.contrib import admin
from .models import Location, Site, Pricing, OptionalCharge, Booking

admin.site.register(Location)
admin.site.register(Site)
admin.site.register(Pricing)
admin.site.register(OptionalCharge)
admin.site.register(Booking)
