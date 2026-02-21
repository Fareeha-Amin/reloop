from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from .models import CurrentNeed
from .serializers import CurrentNeedSerializer, AcceptorMapSerializer
from users.models import AcceptorProfile
from ai_engine.matching import calculate_distance


class CurrentNeedListCreateView(generics.ListCreateAPIView):
    """List and create current needs."""
    serializer_class = CurrentNeedSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'ACCEPTOR':
            return CurrentNeed.objects.filter(acceptor=self.request.user)
        return CurrentNeed.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(acceptor=self.request.user)


class CurrentNeedDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a current need."""
    serializer_class = CurrentNeedSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'ACCEPTOR':
            return CurrentNeed.objects.filter(acceptor=self.request.user)
        return CurrentNeed.objects.none()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def nearby_acceptors(request):
    """Get nearby verified acceptors for map display."""
    # Get user's location (from donor profile or query params)
    lat = request.query_params.get('lat')
    lon = request.query_params.get('lon')
    category = request.query_params.get('category')
    max_distance = float(request.query_params.get('max_distance', 50))  # km
    
    if not lat or not lon:
        # Try to get from donor profile
        if hasattr(request.user, 'donor_profile'):
            lat = request.user.donor_profile.latitude
            lon = request.user.donor_profile.longitude
    
    if not lat or not lon:
        return Response({'error': 'Location required'}, status=status.HTTP_400_BAD_REQUEST)
    
    lat = float(lat)
    lon = float(lon)
    
    # Get all verified acceptors
    acceptors = AcceptorProfile.objects.filter(
        verification_status='VERIFIED',
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    # Filter by category if provided
    if category:
        acceptors = acceptors.filter(
            user__current_needs__category=category,
            user__current_needs__is_active=True
        ).distinct()
    
    # Calculate distances and filter
    nearby = []
    for acceptor in acceptors:
        distance = calculate_distance(lat, lon, acceptor.latitude, acceptor.longitude)
        if distance and distance <= max_distance:
            acceptor_data = AcceptorMapSerializer(acceptor).data
            acceptor_data['distance'] = round(distance, 2)
            nearby.append(acceptor_data)
    
    # Sort by distance
    nearby.sort(key=lambda x: x['distance'])
    
    return Response(nearby)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_acceptor(request, acceptor_id):
    """Admin endpoint to verify an acceptor."""
    if request.user.role != 'ADMIN':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        acceptor = AcceptorProfile.objects.get(id=acceptor_id)
    except AcceptorProfile.DoesNotExist:
        return Response({'error': 'Acceptor not found'}, status=status.HTTP_404_NOT_FOUND)
    
    action = request.data.get('action')  # 'approve' or 'reject'
    
    if action == 'approve':
        acceptor.verification_status = 'VERIFIED'
        from django.utils import timezone
        acceptor.verified_at = timezone.now()
    elif action == 'reject':
        acceptor.verification_status = 'REJECTED'
    else:
        return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
    
    acceptor.save()
    
    from users.serializers import AcceptorProfileSerializer
    return Response(AcceptorProfileSerializer(acceptor).data)
