"""
AI Engine views for NGO suggestions and matching.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions
from .matching import find_best_matches, calculate_distance, get_matching_score
from users.models import AcceptorProfile
from acceptors.models import CurrentNeed


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def suggest_ngos(request):
    """Get ranked NGO suggestions for a donation based on category, location, urgency."""
    category = request.query_params.get('category', '')
    lat = request.query_params.get('lat')
    lon = request.query_params.get('lon')

    # Fall back to donor profile location
    if (not lat or not lon) and hasattr(request.user, 'donor_profile'):
        profile = request.user.donor_profile
        lat = profile.latitude
        lon = profile.longitude

    # Get all verified (or all) acceptors
    acceptors = AcceptorProfile.objects.select_related('user').all()

    suggestions = []
    for ap in acceptors:
        score = 0
        distance = None

        # Distance scoring (40 pts max)
        if lat and lon and ap.latitude and ap.longitude:
            distance = calculate_distance(float(lat), float(lon), float(ap.latitude), float(ap.longitude))
            if distance is not None:
                if distance <= 5:
                    score += 40
                elif distance <= 10:
                    score += 30
                elif distance <= 20:
                    score += 20
                else:
                    score += 10

        # Category match scoring (30 pts max)
        matching_needs = CurrentNeed.objects.filter(
            acceptor=ap.user,
            category=category,
            is_active=True,
        ) if category else CurrentNeed.objects.none()

        urgency = None
        category_match = False
        if matching_needs.exists():
            need = matching_needs.first()
            category_match = True
            urgency = need.urgency
            score += 20
            urgency_scores = {'LOW': 0, 'MEDIUM': 5, 'HIGH': 8, 'CRITICAL': 10}
            score += urgency_scores.get(need.urgency, 0)

        # Storage capacity scoring (10 pts max)
        capacity_scores = {'Large': 10, 'Medium': 7, 'Small': 4}
        score += capacity_scores.get(ap.storage_capacity, 5)

        # Past acceptance rate (10 pts max)
        if ap.total_received > 0:
            score += min(ap.total_received, 10)

        # Rating bonus (10 pts max)
        if ap.average_rating > 0:
            score += int(float(ap.average_rating) * 2)

        score = min(score, 100)

        suggestions.append({
            'id': ap.user.id,
            'organization_name': ap.organization_name,
            'contact_person': ap.contact_person,
            'address': ap.address,
            'city': ap.city or '',
            'latitude': float(ap.latitude) if ap.latitude else None,
            'longitude': float(ap.longitude) if ap.longitude else None,
            'storage_capacity': ap.storage_capacity or 'Unknown',
            'verification_status': ap.verification_status,
            'has_pickup_capability': ap.has_pickup_capability,
            'total_received': ap.total_received,
            'average_rating': float(ap.average_rating),
            'distance': round(distance, 2) if distance else None,
            'score': score,
            'category_match': category_match,
            'urgency': urgency,
        })

    # Sort by score descending
    suggestions.sort(key=lambda x: x['score'], reverse=True)

    return Response(suggestions)
