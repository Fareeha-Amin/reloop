from rest_framework import serializers
from .models import LogisticsProvider, PickupRequest


class LogisticsProviderSerializer(serializers.ModelSerializer):
    """Serializer for logistics providers."""
    
    class Meta:
        model = LogisticsProvider
        fields = '__all__'


class PickupRequestSerializer(serializers.ModelSerializer):
    """Serializer for pickup requests."""
    provider_name = serializers.CharField(source='logistics_provider.name', read_only=True, allow_null=True)
    donation_details = serializers.SerializerMethodField()
    
    class Meta:
        model = PickupRequest
        fields = '__all__'
        read_only_fields = ['booking_id', 'distance_km', 'base_cost', 'platform_commission', 'total_cost']
    
    def get_donation_details(self, obj):
        return {
            'id': obj.donation.id,
            'category': obj.donation.category,
            'quantity': obj.donation.quantity,
            'donor': obj.donation.donor.username,
        }


class PickupCostCalculationSerializer(serializers.Serializer):
    """Serializer for calculating pickup costs."""
    distance_km = serializers.DecimalField(max_digits=6, decimal_places=2)
    provider_id = serializers.IntegerField(required=False)
