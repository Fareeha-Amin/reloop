from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Sum, Count, Q
from .models import ImpactMetrics, DriveEvent, Review
from .serializers import (
    ImpactMetricsSerializer,
    DriveEventSerializer,
    ReviewSerializer,
    UserImpactDashboardSerializer,
    LeaderboardSerializer
)
from donations.models import Donation
from users.models import DonorProfile


class ImpactMetricsListView(generics.ListAPIView):
    """List impact metrics."""
    serializer_class = ImpactMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'DONOR':
            return ImpactMetrics.objects.filter(donation__donor=user)
        elif user.role == 'ADMIN':
            return ImpactMetrics.objects.all()
        return ImpactMetrics.objects.none()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_impact_dashboard(request):
    """Get user's impact dashboard."""
    user = request.user
    
    if user.role != 'DONOR':
        return Response({'error': 'Only donors have impact dashboards'}, status=status.HTTP_403_FORBIDDEN)
    
    # Aggregate impact metrics
    metrics = ImpactMetrics.objects.filter(donation__donor=user).aggregate(
        total_waste=Sum('waste_diverted_kg'),
        total_carbon=Sum('carbon_offset_kg'),
        total_points=Sum('impact_points')
    )
    
    # Get donor profile
    donor_profile = user.donor_profile
    
    # Get recent donations
    recent_donations = Donation.objects.filter(donor=user).order_by('-created_at')[:5]
    
    # Determine impact level
    total_points = metrics['total_points'] or 0
    if total_points >= 1000:
        impact_level = 'PLATINUM'
    elif total_points >= 500:
        impact_level = 'GOLD'
    elif total_points >= 200:
        impact_level = 'SILVER'
    else:
        impact_level = 'BRONZE'
    
    from donations.serializers import DonationSerializer
    
    data = {
        'total_donations': donor_profile.total_donations,
        'total_waste_diverted': metrics['total_waste'] or 0,
        'total_carbon_offset': metrics['total_carbon'] or 0,
        'total_impact_points': total_points,
        'impact_level': impact_level,
        'recent_donations': DonationSerializer(recent_donations, many=True).data
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def leaderboard(request):
    """Get global leaderboard."""
    leaderboard_type = request.query_params.get('type', 'donors')  # donors or cities
    
    if leaderboard_type == 'donors':
        # Top donors by impact score
        top_donors = DonorProfile.objects.order_by('-impact_score')[:10]
        
        data = []
        for rank, donor in enumerate(top_donors, 1):
            data.append({
                'username': donor.user.username,
                'total_donations': donor.total_donations,
                'impact_score': donor.impact_score,
                'rank': rank
            })
        
        return Response(data)
    
    elif leaderboard_type == 'cities':
        # Top cities by total donations
        from django.db.models import Count
        cities = DonorProfile.objects.values('city').annotate(
            total_donations=Count('user__donations')
        ).order_by('-total_donations')[:10]
        
        return Response(list(cities))
    
    return Response({'error': 'Invalid leaderboard type'}, status=status.HTTP_400_BAD_REQUEST)


class DriveEventListCreateView(generics.ListCreateAPIView):
    """List and create drive events."""
    serializer_class = DriveEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return DriveEvent.objects.all()
        return DriveEvent.objects.filter(
            Q(organizer=user) | Q(participants=user)
        ).distinct()
    
    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)


class DriveEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a drive event."""
    serializer_class = DriveEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'ADMIN':
            return DriveEvent.objects.all()
        return DriveEvent.objects.filter(organizer=user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_drive(request, drive_id):
    """Join a drive event."""
    try:
        drive = DriveEvent.objects.get(id=drive_id)
    except DriveEvent.DoesNotExist:
        return Response({'error': 'Drive not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if drive.status != 'ACTIVE':
        return Response({'error': 'Drive is not active'}, status=status.HTTP_400_BAD_REQUEST)
    
    drive.participants.add(request.user)
    
    return Response(DriveEventSerializer(drive).data)


class ReviewListCreateView(generics.ListCreateAPIView):
    """List and create reviews."""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'DONOR':
            return Review.objects.filter(donor=user)
        elif user.role == 'ACCEPTOR':
            return Review.objects.filter(acceptor=user)
        elif user.role == 'ADMIN':
            return Review.objects.all()
        return Review.objects.none()
    
    def perform_create(self, serializer):
        donation_id = self.request.data.get('donation')
        try:
            donation = Donation.objects.get(id=donation_id, donor=self.request.user)
        except Donation.DoesNotExist:
            raise serializers.ValidationError("Donation not found or not yours")
        
        if donation.status != 'COMPLETED':
            raise serializers.ValidationError("Can only review completed donations")
        
        review = serializer.save(
            donor=self.request.user,
            acceptor=donation.acceptor,
            donation=donation
        )
        
        # Update acceptor's average rating
        acceptor_profile = donation.acceptor.acceptor_profile
        reviews = Review.objects.filter(acceptor=donation.acceptor)
        avg_rating = reviews.aggregate(avg=Sum('rating'))['avg'] / reviews.count()
        acceptor_profile.average_rating = avg_rating
        acceptor_profile.save()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def platform_statistics(request):
    """Get platform-wide statistics (Admin only)."""
    if request.user.role != 'ADMIN':
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    from users.models import User
    from payments.models import Payment
    
    stats = {
        'total_users': User.objects.count(),
        'total_donors': User.objects.filter(role='DONOR').count(),
        'total_acceptors': User.objects.filter(role='ACCEPTOR').count(),
        'total_donations': Donation.objects.count(),
        'completed_donations': Donation.objects.filter(status='COMPLETED').count(),
        'total_payments': Payment.objects.filter(status='SUCCESS').count(),
        'total_impact_points': ImpactMetrics.objects.aggregate(total=Sum('impact_points'))['total'] or 0,
        'total_waste_diverted': ImpactMetrics.objects.aggregate(total=Sum('waste_diverted_kg'))['total'] or 0,
    }
    
    return Response(stats)
