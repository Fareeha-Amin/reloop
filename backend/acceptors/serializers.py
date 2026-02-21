from rest_framework import serializers
from .models import CurrentNeed
from users.models import AcceptorProfile
from users.serializers import AcceptorProfileSerializer


class CurrentNeedSerializer(serializers.ModelSerializer):
    """Serializer for current needs."""
    
    class Meta:
        model = CurrentNeed
        fields = '__all__'
        read_only_fields = ['acceptor']


class AcceptorMapSerializer(serializers.ModelSerializer):
    """Serializer for displaying acceptors on map."""
    organization_name = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    city = serializers.CharField()
    verification_status = serializers.CharField()
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    current_needs = CurrentNeedSerializer(many=True, read_only=True, source='user.current_needs')
    
    class Meta:
        model = AcceptorProfile
        fields = ['id', 'organization_name', 'latitude', 'longitude', 'city', 'verification_status', 'average_rating', 'has_pickup_capability', 'current_needs']
