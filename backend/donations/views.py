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
PRE_ACCEPTANCE_STATUSES = ('CREATED', 'MATCHED', 'RE_MATCHING', 'ESCALATED')


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
    """Acceptor rejects a donation — triggers automatic re-matching."""
    if request.user.role != 'ACCEPTOR':
        return Response({'error': 'Only acceptors can reject donations'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        donation = Donation.objects.get(id=donation_id)
    except Donation.DoesNotExist:
        return Response({'error': 'Donation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if donation.status not in ['CREATED', 'MATCHED']:
        return Response({'error': 'Donation cannot be rejected in its current status'}, status=status.HTTP_400_BAD_REQUEST)

    # Record the rejection
    rejector_name = ''
    try:
        rejector_name = request.user.acceptor_profile.organization_name
    except Exception:
        rejector_name = request.user.username

    donation.last_rejected_by = request.user
    donation.rejection_count += 1

    # Add to excluded list (avoid duplicates)
    excluded = donation.excluded_acceptors or []
    if request.user.id not in excluded:
        excluded.append(request.user.id)
    donation.excluded_acceptors = excluded

    # Clear all NGO assignments — donation is entering RE_MATCHING or ESCALATED,
    # so any prior suggestion or acceptor is stale and must not linger in the UI.
    donation.ai_suggested_acceptor = None
    donation.acceptor = None

    # Determine next state
    if donation.rejection_count >= Donation.MAX_REJECTIONS:
        # Max rejections reached — escalate to donor
        donation.status = 'ESCALATED'
        donation.save()
        return Response({
            **DonationDetailSerializer(donation).data,
            'rejection_info': {
                'rejected_by': rejector_name,
                'rejection_count': donation.rejection_count,
                'action': 'escalated',
                'message': f'Donation escalated after {donation.rejection_count} rejections. Donor action required.',
            }
        })

    # Set to RE_MATCHING — donor will see this state and choose an action
    # (re-match, upgrade priority, or redirect to recycling)
    donation.status = 'RE_MATCHING'
    donation.save()

    return Response({
        **DonationDetailSerializer(donation).data,
        'rejection_info': {
            'rejected_by': rejector_name,
            'rejection_count': donation.rejection_count,
            'action': 're_matching',
            'message': f'Declined by {rejector_name}. Awaiting donor action.',
        }
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def donor_action(request, donation_id):
    """Donor takes action on an escalated or re-matching donation."""
    if request.user.role != 'DONOR':
        return Response({'error': 'Only donors can perform this action'}, status=status.HTTP_403_FORBIDDEN)

    try:
        donation = Donation.objects.get(id=donation_id, donor=request.user)
    except Donation.DoesNotExist:
        return Response({'error': 'Donation not found'}, status=status.HTTP_404_NOT_FOUND)

    if donation.status not in ['RE_MATCHING', 'ESCALATED']:
        return Response({'error': 'Action not available for this donation status'}, status=status.HTTP_400_BAD_REQUEST)

    action = request.data.get('action')

    if action == 're_match':
        # Ensure current acceptor is excluded before re-matching
        excluded = donation.excluded_acceptors or []
        if donation.ai_suggested_acceptor_id and donation.ai_suggested_acceptor_id not in excluded:
            excluded.append(donation.ai_suggested_acceptor_id)
            donation.excluded_acceptors = excluded
        donation.ai_suggested_acceptor = None
        donation.acceptor = None

        # Re-trigger matching with exclusions
        try:
            new_acceptor, score = get_ai_suggestion(
                donation,
                exclude_user_ids=donation.excluded_acceptors
            )
        except Exception:
            new_acceptor, score = None, 0

        if new_acceptor:
            donation.ai_suggested_acceptor = new_acceptor
            donation.matching_score = score
            donation.status = 'MATCHED'
            donation.save()
            return Response({
                **DonationDetailSerializer(donation).data,
                'message': 'Successfully re-matched with a new NGO.',
            })
        else:
            donation.status = 'ESCALATED'
            donation.save()
            return Response({
                **DonationDetailSerializer(donation).data,
                'message': 'No available NGOs found. Consider upgrading to priority or redirecting to a recycling partner.',
            })

    elif action == 'upgrade_priority':
        donation.is_priority = True

        # Ensure current acceptor is excluded before re-matching
        excluded = donation.excluded_acceptors or []
        if donation.ai_suggested_acceptor_id and donation.ai_suggested_acceptor_id not in excluded:
            excluded.append(donation.ai_suggested_acceptor_id)
            donation.excluded_acceptors = excluded
        donation.ai_suggested_acceptor = None
        donation.acceptor = None
        donation.save()

        # Re-trigger matching with priority boost
        try:
            new_acceptor, score = get_ai_suggestion(
                donation,
                exclude_user_ids=donation.excluded_acceptors
            )
        except Exception:
            new_acceptor, score = None, 0

        if new_acceptor:
            donation.ai_suggested_acceptor = new_acceptor
            donation.matching_score = score
            donation.status = 'MATCHED'
            donation.save()
            return Response({
                **DonationDetailSerializer(donation).data,
                'message': 'Priority upgraded and re-matched with a new NGO.',
            })
        else:
            donation.status = 'ESCALATED'
            donation.save()
            return Response({
                **DonationDetailSerializer(donation).data,
                'message': 'Priority upgraded but no NGOs available. Consider redirecting to a recycling partner.',
            })

    elif action == 'waste_redirect':
        from ai_engine.fallback import check_and_trigger_fallback
        result = check_and_trigger_fallback(donation, force=True)
        if result:
            return Response({
                **DonationDetailSerializer(donation).data,
                'message': 'Redirected to recycling partner.',
                'fallback_info': result,
            })
        return Response({
            **DonationDetailSerializer(donation).data,
            'message': 'No recycling partners available at this time.',
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({'error': f'Unknown action: {action}'}, status=status.HTTP_400_BAD_REQUEST)


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
