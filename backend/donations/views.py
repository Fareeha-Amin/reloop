from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import Donation
from .serializers import DonationSerializer, DonationDetailSerializer, DonationStatusUpdateSerializer
from ai_engine.matching import get_ai_suggestion
from ai_engine.impact_calculator import calculate_donation_impact
from analytics.models import ImpactMetrics


class DonationListCreateView(generics.ListCreateAPIView):
    """List all donations or create a new donation."""
    serializer_class = DonationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'DONOR':
            return Donation.objects.filter(donor=user)
        elif user.role == 'ACCEPTOR':
            return Donation.objects.filter(
                acceptor=user
            ) | Donation.objects.filter(
                ai_suggested_acceptor=user,
                status='MATCHED'
            )
        elif user.role == 'ADMIN':
            return Donation.objects.all()
        return Donation.objects.none()
    
    def perform_create(self, serializer):
        donation = serializer.save(donor=self.request.user)
        
        # Run AI matching
        suggested_acceptor, score = get_ai_suggestion(donation)
        if suggested_acceptor:
            donation.ai_suggested_acceptor = suggested_acceptor
            donation.matching_score = score
            donation.status = 'MATCHED'
            donation.save()
        
        # Calculate impact metrics
        impact_data = calculate_donation_impact(donation)
        ImpactMetrics.objects.create(
            donation=donation,
            **impact_data
        )
        
        # Update donor profile
        donor_profile = self.request.user.donor_profile
        donor_profile.total_donations += 1
        donor_profile.impact_score += impact_data['impact_points']
        donor_profile.save()


class DonationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a donation."""
    serializer_class = DonationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'DONOR':
            return Donation.objects.filter(donor=user)
        elif user.role == 'ACCEPTOR':
            return Donation.objects.filter(acceptor=user) | Donation.objects.filter(ai_suggested_acceptor=user)
        elif user.role == 'ADMIN':
            return Donation.objects.all()
        return Donation.objects.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def accept_donation(request, donation_id):
    """Acceptor accepts a donation."""
    if request.user.role != 'ACCEPTOR':
        return Response({'error': 'Only acceptors can accept donations'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        donation = Donation.objects.get(id=donation_id)
    except Donation.DoesNotExist:
        return Response({'error': 'Donation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if donation.status not in ['CREATED', 'MATCHED']:
        return Response({'error': 'Donation cannot be accepted'}, status=status.HTTP_400_BAD_REQUEST)
    
    donation.acceptor = request.user
    donation.status = 'ACCEPTED'
    donation.save()
    
    return Response(DonationDetailSerializer(donation).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_donation(request, donation_id):
    """Acceptor rejects a donation."""
    if request.user.role != 'ACCEPTOR':
        return Response({'error': 'Only acceptors can reject donations'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        donation = Donation.objects.get(id=donation_id)
    except Donation.DoesNotExist:
        return Response({'error': 'Donation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if donation.ai_suggested_acceptor != request.user:
        return Response({'error': 'You cannot reject this donation'}, status=status.HTTP_403_FORBIDDEN)
    
    donation.status = 'REJECTED'
    donation.save()
    
    return Response(DonationDetailSerializer(donation).data)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_donation_status(request, donation_id):
    """Update donation status."""
    try:
        donation = Donation.objects.get(id=donation_id)
    except Donation.DoesNotExist:
        return Response({'error': 'Donation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check permissions
    if request.user.role == 'DONOR' and donation.donor != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    elif request.user.role == 'ACCEPTOR' and donation.acceptor != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = DonationStatusUpdateSerializer(donation, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    
    return Response(DonationDetailSerializer(donation).data)
