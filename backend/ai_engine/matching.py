"""
AI-powered matching engine to connect donors with suitable acceptors.
"""
from django.db.models import Q
from geopy.distance import geodesic
from users.models import User, AcceptorProfile
from acceptors.models import CurrentNeed


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers."""
    if not all([lat1, lon1, lat2, lon2]):
        return None
    return geodesic((lat1, lon1), (lat2, lon2)).km


def get_matching_score(donation, acceptor_profile):
    """
    Calculate matching score based on multiple factors.
    Returns a score between 0-100.
    """
    score = 0
    
    # Factor 1: Distance (40 points max)
    if donation.pickup_latitude and acceptor_profile.latitude:
        distance = calculate_distance(
            donation.pickup_latitude,
            donation.pickup_longitude,
            acceptor_profile.latitude,
            acceptor_profile.longitude
        )
        if distance is not None:
            # Closer is better: 0-5km = 40pts, 5-10km = 30pts, 10-20km = 20pts, >20km = 10pts
            if distance <= 5:
                score += 40
            elif distance <= 10:
                score += 30
            elif distance <= 20:
                score += 20
            else:
                score += 10
    
    # Factor 2: Current needs match (30 points max)
    matching_needs = CurrentNeed.objects.filter(
        acceptor=acceptor_profile.user,
        category=donation.category,
        is_active=True
    )
    if matching_needs.exists():
        need = matching_needs.first()
        score += 20  # Base score for matching category
        
        # Urgency bonus
        urgency_scores = {'LOW': 0, 'MEDIUM': 5, 'HIGH': 8, 'CRITICAL': 10}
        score += urgency_scores.get(need.urgency, 0)
    
    # Factor 3: Storage capacity (10 points max)
    capacity_scores = {'Large': 10, 'Medium': 7, 'Small': 4}
    score += capacity_scores.get(acceptor_profile.storage_capacity, 5)
    
    # Factor 4: Past acceptance rate (10 points max)
    # Simplified: if they've received donations before, they're more reliable
    if acceptor_profile.total_received > 0:
        score += min(acceptor_profile.total_received, 10)
    
    # Factor 5: Rating bonus (10 points max)
    if acceptor_profile.average_rating > 0:
        score += int(acceptor_profile.average_rating * 2)
    
    # Apply priority multiplier
    if hasattr(donation, 'is_priority') and donation.is_priority:
        score = int(score * 1.3)

    return min(score, 100)


def find_best_matches(donation, limit=5):
    """
    Find the best matching acceptors for a donation.
    Returns a list of (acceptor_profile, score) tuples sorted by score.
    """
    # Get all verified acceptors
    verified_acceptors = AcceptorProfile.objects.filter(
        verification_status='VERIFIED'
    ).select_related('user')
    
    matches = []
    
    for acceptor_profile in verified_acceptors:
        score = get_matching_score(donation, acceptor_profile)
        matches.append((acceptor_profile, score))
    
    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return matches[:limit]


def get_ai_suggestion(donation):
    """
    Get the top AI-suggested acceptor for a donation.
    Returns (acceptor_user, score) or (None, 0) if no matches.
    """
    matches = find_best_matches(donation, limit=1)
    
    if matches:
        acceptor_profile, score = matches[0]
        return acceptor_profile.user, score
    
    return None, 0
