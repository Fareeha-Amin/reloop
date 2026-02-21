from rest_framework import serializers
from .models import Donation, DonationImage
from users.serializers import UserSerializer
from ai_engine.image_validator import validate_donation_image
from geopy.geocoders import Nominatim


class DonationImageSerializer(serializers.ModelSerializer):
    """Serializer for donation images."""
    
    class Meta:
        model = DonationImage
        fields = ['id', 'image', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
    
    def validate_image(self, value):
        """Validate uploaded image."""
        is_valid, message = validate_donation_image(value)
        if not is_valid:
            raise serializers.ValidationError(message)
        return value


class DonationSerializer(serializers.ModelSerializer):
    """Serializer for creating and listing donations."""
    images = DonationImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    donor_name = serializers.CharField(source='donor.username', read_only=True)
    acceptor_name = serializers.CharField(source='acceptor.acceptor_profile.organization_name', read_only=True, allow_null=True)
    ai_suggested_acceptor_name = serializers.CharField(source='ai_suggested_acceptor.acceptor_profile.organization_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Donation
        fields = '__all__'
        read_only_fields = ['donor', 'acceptor', 'ai_suggested_acceptor', 'matching_score', 'status', 'pickup_latitude', 'pickup_longitude']
    
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        
        # Geocode pickup address
        try:
            geolocator = Nominatim(user_agent="reloop")
            location = geolocator.geocode(validated_data['pickup_address'])
            if location:
                validated_data['pickup_latitude'] = location.latitude
                validated_data['pickup_longitude'] = location.longitude
        except Exception:
            pass
        
        # Create donation
        donation = Donation.objects.create(**validated_data)
        
        # Create images
        for image in uploaded_images:
            DonationImage.objects.create(donation=donation, image=image)
        
        # Trigger AI matching (will be done in view)
        
        return donation


class DonationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for donation with all related data."""
    images = DonationImageSerializer(many=True, read_only=True)
    donor = UserSerializer(read_only=True)
    acceptor = UserSerializer(read_only=True)
    ai_suggested_acceptor = UserSerializer(read_only=True)
    
    class Meta:
        model = Donation
        fields = '__all__'


class DonationStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating donation status."""
    
    class Meta:
        model = Donation
        fields = ['status']
