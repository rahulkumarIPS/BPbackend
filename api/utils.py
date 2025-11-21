from datetime import timedelta
import math
from django.utils import timezone

# Input durations in minutes
def calculate_amount(site, vehicle_type, start_dt, end_dt, optional_charge_ids=[]):
    diff = end_dt - start_dt
    minutes = int(diff.total_seconds() // 60)
    hours = minutes / 60.0

    # fetch pricing for the site & vehicle
    pricings = {p.tier: float(p.price) for p in site.pricings.filter(vehicle_type=vehicle_type)}

    base = 0.0
    # Using your rules:
    # For car:
    # 0-2 hrs -> 60
    # 2-4 -> 120
    # full day ->160
    # monthly -> 3500
    # For bike:
    # 1-2 hrs -> 30
    # 2-4 -> 40
    # full day -> 70
    # monthly -> 1000
    # We'll choose tier according to hours.
    if hours <= 2:
        base = pricings.get('0_2') or pricings.get('0_2', 0)
    elif hours <= 4:
        base = pricings.get('2_4') or pricings.get('2_4', 0)
    elif hours < 24:
        base = pricings.get('full_day') or pricings.get('full_day', 0)
    else:
        # full days multiples
        days = math.ceil(hours / 24)
        base = (pricings.get('full_day') or 0) * days

    # Now optional charges
    option_total = 0.0
    if optional_charge_ids:
        from .models import OptionalCharge
        option_total = sum(c.amount for c in OptionalCharge.objects.filter(id__in=optional_charge_ids, is_active=True))

    total = float(base) + float(option_total)
    return {
        'duration_minutes': minutes,
        'base_amount': round(base, 2),
        'optional_amount': round(option_total, 2),
        'total_amount': round(total, 2)
    }
