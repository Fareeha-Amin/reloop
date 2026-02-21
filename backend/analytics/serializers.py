from rest_framework import serializers
from .models import ImpactMetrics, DriveEvent, Review
from donations.serializers import DonationSerializer


class ImpactMetricsSerializer(serializers.ModelSerializer):
    """Serializer for impact metrics."""
    donation_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ImpactMetrics
        fields = '__all__'
    
    def get_donation_details(self, obj):
        return {
            'id': obj.donation.id,
            'category': obj.donation.category,
            'quantity': obj.donation.quantity,
        }


class DriveEventSerializer(serializers.ModelSerializer):
    """Serializer for drive events."""
    organizer_name = serializers.CharField(source='organizer.username', read_only=True)
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DriveEvent
        fields = '__all__'
        read_only_fields = ['organizer', 'collected_items']
    
    def get_participant_count(self, obj):
        return obj.participants.count()


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviews."""
    donor_name = serializers.CharField(source='donor.username', read_only=True)
    acceptor_name = serializers.CharField(source='acceptor.acceptor_profile.organization_name', read_only=True)
    
    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['donor', 'acceptor', 'donation']


class UserImpactDashboardSerializer(serializers.Serializer):
    """Serializer for user impact dashboard."""
    total_donations = serializers.IntegerField()
    total_waste_diverted = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_carbon_offset = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_impact_points = serializers.IntegerField()
    impact_level = serializers.CharField()
    recent_donations = DonationSerializer(many=True)


class LeaderboardSerializer(serializers.Serializer):
    """Serializer for leaderboard."""
    username = serializers.CharField()
    total_donations = serializers.IntegerField()
    impact_score = serializers.IntegerField()
    rank = serializers.IntegerField()
