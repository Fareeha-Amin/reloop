"""
Basic AI scheduling logic for pickup time suggestions.
"""
from datetime import datetime, timedelta
from django.utils import timezone


def suggest_pickup_time(donation):
    """
    Suggest an optimal pickup time based on:
    - Donor's preferred time window
    - Priority status
    - Time of day
    Returns a suggested datetime.
    """
    now = timezone.now()

    # If priority, suggest within 2 hours
    if donation.is_priority:
        suggested = now + timedelta(hours=2)
        # Round to next half hour
        minutes = suggested.minute
        if minutes < 30:
            suggested = suggested.replace(minute=30, second=0, microsecond=0)
        else:
            suggested = (suggested + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        return suggested

    # If donor has preferred window, use the start time
    if donation.preferred_pickup_start:
        return donation.preferred_pickup_start

    # Default: suggest next day at 10 AM
    tomorrow = now + timedelta(days=1)
    suggested = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)

    # If it's early enough today (before 4 PM), suggest today at 2 PM
    if now.hour < 14:
        suggested = now.replace(hour=14, minute=0, second=0, microsecond=0)

    return suggested


def get_optimal_pickup_time(donation, acceptor_profile=None):
    """Backward-compatible wrapper used by logistics.views."""
    return suggest_pickup_time(donation)
