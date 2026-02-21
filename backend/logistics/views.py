from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import LogisticsProvider, PickupRequest
from .serializers import LogisticsProviderSerializer, PickupRequestSerializer, PickupCostCalculationSerializer
from donations.models import Donation
from ai_engine.matching import calculate_distance
from ai_engine.scheduler import get_optimal_pickup_time
import uuid


class LogisticsProviderListView(generics.ListAPIView):
    """List all active logistics providers."""
    queryset = LogisticsProvider.objects.filter(status='ACTIVE')
    serializer_class = LogisticsProviderSerializer
    permission_classes = [permissions.IsAuthenticated]


class PickupRequestListCreateView(generics.ListCreateAPIView):
    """List and create pickup requests."""
    serializer_class = PickupRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'DONOR':
            return PickupRequest.objects.filter(donation__donor=user)
        elif user.role == 'ACCEPTOR':
            return PickupRequest.objects.filter(donation__acceptor=user)
        elif user.role == 'ADMIN':
            return PickupRequest.objects.all()
        return PickupRequest.objects.none()
    
    def perform_create(self, serializer):
        donation_id = self.request.data.get('donation')
        try:
            donation = Donation.objects.get(id=donation_id)
        except Donation.DoesNotExist:
            raise serializers.ValidationError("Donation not found")
        
        # Check if pickup request already exists
        if hasattr(donation, 'pickup_request'):
            raise serializers.ValidationError("Pickup request already exists for this donation")
        
        pickup_request = serializer.save()
        
        # Calculate costs if platform-arranged
        if pickup_request.pickup_type == 'PLATFORM_ARRANGED':
            self._calculate_and_set_costs(pickup_request, donation)
        
        # Set optimal pickup time using AI
        if donation.acceptor and hasattr(donation.acceptor, 'acceptor_profile'):
            optimal_time = get_optimal_pickup_time(donation, donation.acceptor.acceptor_profile)
            pickup_request.scheduled_time = optimal_time
            pickup_request.save()
    
    def _calculate_and_set_costs(self, pickup_request, donation):
        """Calculate logistics costs."""
        # Calculate distance
        if donation.pickup_latitude and donation.acceptor:
            acceptor_profile = donation.acceptor.acceptor_profile
            distance = calculate_distance(
                donation.pickup_latitude,
                donation.pickup_longitude,
                acceptor_profile.latitude,
                acceptor_profile.longitude
            )
            if distance:
                pickup_request.distance_km = distance
                
                # Base cost calculation: ₹20 per km
                base_cost = distance * 20
                pickup_request.base_cost = base_cost
                
                # Platform commission (8-12%)
                commission_rate = pickup_request.logistics_provider.commission_percentage if pickup_request.logistics_provider else 10
                commission = base_cost * (commission_rate / 100)
                pickup_request.platform_commission = commission
                
                # Total cost
                pickup_request.total_cost = base_cost + commission
                
                # Generate booking ID
                pickup_request.booking_id = f"RELOOP-{uuid.uuid4().hex[:8].upper()}"
                pickup_request.status = 'SCHEDULED'
                
                pickup_request.save()


class PickupRequestDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve and update pickup request."""
    serializer_class = PickupRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'DONOR':
            return PickupRequest.objects.filter(donation__donor=user)
        elif user.role == 'ACCEPTOR':
            return PickupRequest.objects.filter(donation__acceptor=user)
        elif user.role == 'ADMIN':
            return PickupRequest.objects.all()
        return PickupRequest.objects.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def calculate_pickup_cost(request):
    """Calculate estimated pickup cost."""
    serializer = PickupCostCalculationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    distance = serializer.validated_data['distance_km']
    provider_id = serializer.validated_data.get('provider_id')
    
    # Base cost: ₹20 per km
    base_cost = float(distance) * 20
    
    # Get commission rate
    commission_rate = 10  # Default
    if provider_id:
        try:
            provider = LogisticsProvider.objects.get(id=provider_id)
            commission_rate = float(provider.commission_percentage)
        except LogisticsProvider.DoesNotExist:
            pass
    
    commission = base_cost * (commission_rate / 100)
    total_cost = base_cost + commission
    
    return Response({
        'distance_km': float(distance),
        'base_cost': round(base_cost, 2),
        'platform_commission': round(commission, 2),
        'commission_rate': commission_rate,
        'total_cost': round(total_cost, 2),
    })
