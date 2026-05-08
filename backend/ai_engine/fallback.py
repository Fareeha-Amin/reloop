"""
Waste management fallback logic.
When no NGO accepts a donation and the deadline expires,
automatically match with nearest WasteCollector.
"""
from django.utils import timezone
from donations.models import Donation, WasteCollector
from ai_engine.matching import calculate_distance


def check_and_trigger_fallback(donation, force=False):
    """Check if a donation should fall back to waste collection.
    Called when: all NGOs reject, deadline expires, or donor requests.
    Set force=True to bypass status/deadline checks (for donor-initiated redirect).
    Returns dict with fallback info or None if not triggered."""

    if donation.status in ('COMPLETED', 'DELIVERED', 'WASTE_REDIRECTED', 'WASTE_COLLECTED', 'CANCELLED'):
        return None

    if not force:
        # Check if deadline has passed
        deadline_passed = donation.donation_deadline and timezone.now() > donation.donation_deadline
        is_escalated = donation.status == 'ESCALATED'
        all_rejected = donation.status == 'REJECTED'

        if not (deadline_passed or is_escalated or all_rejected):
            return None

    # Find nearest active waste collector
    collectors = WasteCollector.objects.filter(status='ACTIVE')

    if not collectors.exists():
        return None

    best_collector = None
    best_distance = None

    for collector in collectors:
        if donation.pickup_latitude and collector.latitude:
            dist = calculate_distance(
                float(donation.pickup_latitude),
                float(donation.pickup_longitude),
                float(collector.latitude),
                float(collector.longitude),
            )
            if dist is not None and (best_distance is None or dist < best_distance):
                best_distance = dist
                best_collector = collector

    if not best_collector:
        # If no collector has coordinates, just pick first one
        best_collector = collectors.first()
        best_distance = 0

    # Calculate compensation
    # Estimate weight: quantity * avg_weight_per_item
    category_weights = {'CLOTHES': 0.5, 'TOYS': 0.3, 'BOOKS': 0.8}
    weight_per_item = category_weights.get(donation.category, 0.5)
    estimated_weight_kg = donation.quantity * weight_per_item

    total_value = float(best_collector.fee_per_kg) * estimated_weight_kg
    donor_commission = total_value * float(best_collector.commission_to_donor_pct) / 100
    platform_fee = total_value * float(best_collector.platform_fee_pct) / 100

    # Update donation status
    donation.status = 'WASTE_REDIRECTED'
    donation.save()

    # Credit donor wallet
    try:
        donor_profile = donation.donor.donor_profile
        donor_profile.wallet_balance += round(donor_commission, 2)
        donor_profile.save()
    except Exception:
        pass

    return {
        'collector': best_collector.name,
        'estimated_weight_kg': round(estimated_weight_kg, 2),
        'total_value': round(total_value, 2),
        'donor_commission': round(donor_commission, 2),
        'platform_fee': round(platform_fee, 2),
        'distance_km': round(best_distance, 2) if best_distance else None,
    }
