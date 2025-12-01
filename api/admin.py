from django.contrib import admin
from django import forms
from .models import Site, Pricing, OptionalCharge, Booking, Location

class SiteAdminForm(forms.ModelForm):
    """Custom form to include location fields inline"""
    location_name = forms.CharField(max_length=255, label="Location Name", required=True)
    location_pincode = forms.CharField(max_length=20, label="Pincode", required=False)
    location_lat = forms.DecimalField(max_digits=9, decimal_places=6, label="Latitude", required=False)
    location_lng = forms.DecimalField(max_digits=9, decimal_places=6, label="Longitude", required=False)

    class Meta:
        model = Site
        fields = ['name', 'address', 'total_slots_car', 'total_slots_bike']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Pre-fill location fields when editing
            self.fields['location_name'].initial = self.instance.location.name
            self.fields['location_pincode'].initial = self.instance.location.pincode
            self.fields['location_lat'].initial = self.instance.location.lat
            self.fields['location_lng'].initial = self.instance.location.lng

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Create or update location
        location, _ = Location.objects.get_or_create(
            name=self.cleaned_data['location_name'],
            defaults={
                'pincode': self.cleaned_data.get('location_pincode'),
                'lat': self.cleaned_data.get('location_lat'),
                'lng': self.cleaned_data.get('location_lng'),
            }
        )
        instance.location = location
        
        if commit:
            instance.save()
        return instance

class SiteAdmin(admin.ModelAdmin):
    """Custom Site admin with location fields embedded in site information"""
    form = SiteAdminForm
    list_display = ['name', 'get_location', 'address', 'total_slots_car', 'total_slots_bike', 'created_at']
    search_fields = ['name', 'address', 'location__name']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Site Information', {
            'fields': ('name', 'address', 'total_slots_car', 'total_slots_bike', 
                      'location_name', 'location_pincode', 'location_lat', 'location_lng', 'created_at'),
            'description': 'All site and location details in one section'
        }),
    )

    def get_location(self, obj):
        return obj.location.name if obj.location else '-'
    get_location.short_description = 'Location'

admin.site.register(Site, SiteAdmin)
admin.site.register(Pricing)
admin.site.register(OptionalCharge)
admin.site.register(Booking)
