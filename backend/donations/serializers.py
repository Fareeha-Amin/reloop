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
    # Accept selected_acceptor from frontend (used in view's perform_create)
    selected_acceptor = serializers.IntegerField(write_only=True, required=False)
    donor_name = serializers.CharField(source='donor.username', read_only=True)
    acceptor_name = serializers.CharField(source='acceptor.acceptor_profile.organization_name', read_only=True, allow_null=True)
    ai_suggested_acceptor_name = serializers.CharField(source='ai_suggested_acceptor.acceptor_profile.organization_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Donation
        fields = [
            'id', 'donor', 'acceptor', 'ai_suggested_acceptor',
            'category', 'quantity', 'condition', 'description',
            'pickup_address', 'pickup_latitude', 'pickup_longitude',
            'preferred_pickup_start', 'preferred_pickup_end',
            'delivery_method', 'logistics_provider_choice',
            'donation_deadline', 'is_priority', 'suggested_pickup_time',
            'status', 'matching_score',
            'created_at', 'updated_at',
            'images', 'uploaded_images', 'selected_acceptor',
            'donor_name', 'acceptor_name', 'ai_suggested_acceptor_name',
        ]
        read_only_fields = ['id', 'donor', 'acceptor', 'ai_suggested_acceptor', 'matching_score', 'status', 'pickup_latitude', 'pickup_longitude', 'created_at', 'updated_at']
    
    def validate_is_priority(self, value):
        """Handle is_priority coming as string from FormData."""
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)
    
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        # Pop selected_acceptor — it's handled in the view's perform_create
        validated_data.pop('selected_acceptor', None)
        
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
