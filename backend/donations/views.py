from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from .models import Donation
from .serializers import DonationSerializer, DonationDetailSerializer, DonationStatusUpdateSerializer
from ai_engine.matching import get_ai_suggestion
from ai_engine.impact_calculator import calculate_donation_impact
from analytics.models import ImpactMetrics
from users.models import User


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

        # Check if user manually selected an acceptor
        selected_acceptor_id = self.request.data.get('selected_acceptor')
        if selected_acceptor_id:
            try:
                chosen = User.objects.get(id=int(selected_acceptor_id), role='ACCEPTOR')
                donation.acceptor = chosen
                donation.status = 'MATCHED'
            except (User.DoesNotExist, ValueError, TypeError):
                pass

        # Always run AI matching for suggestion/reference
        try:
            suggested_acceptor, score = get_ai_suggestion(donation)
            if suggested_acceptor:
                donation.ai_suggested_acceptor = suggested_acceptor
                donation.matching_score = score
                # Only set MATCHED status if not already set by user selection
                if donation.status == 'CREATED':
                    donation.status = 'MATCHED'
        except Exception:
            pass  # Don't fail donation creation if AI matching fails

        donation.save()

        # Calculate impact metrics
        try:
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
        except Exception:
            pass  # Don't fail donation creation if impact calc fails


# Statuses that indicate the donation is still editable/deletable
PRE_ACCEPTANCE_STATUSES = ('CREATED', 'MATCHED')


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

    def perform_update(self, serializer):
        donation = self.get_object()
        if donation.status not in PRE_ACCEPTANCE_STATUSES:
            raise PermissionDenied('Donation cannot be edited after acceptance.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status not in PRE_ACCEPTANCE_STATUSES:
            raise PermissionDenied('Donation cannot be deleted after acceptance.')
        instance.delete()


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
    
    if donation.status not in ['CREATED', 'MATCHED']:
        return Response({'error': 'Donation cannot be rejected in its current status'}, status=status.HTTP_400_BAD_REQUEST)
    
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


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def trigger_fallback(request, donation_id):
    """Manually trigger waste fallback for a donation."""
    try:
        donation = Donation.objects.get(id=donation_id, donor=request.user)
    except Donation.DoesNotExist:
        return Response({'error': 'Donation not found'}, status=status.HTTP_404_NOT_FOUND)

    from ai_engine.fallback import check_and_trigger_fallback
    result = check_and_trigger_fallback(donation)
    if result:
        return Response({'message': 'Waste fallback triggered', **result})
    return Response({'message': 'Fallback not applicable for this donation'}, status=status.HTTP_400_BAD_REQUEST)
