from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, DonorProfile, AcceptorProfile
from geopy.geocoders import Nominatim


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    # Optional profile fields passed alongside user creation
    address = serializers.CharField(write_only=True, required=False, default='')
    organization_name = serializers.CharField(write_only=True, required=False, default='')
    contact_person = serializers.CharField(write_only=True, required=False, default='')
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone_number', 'role',
            'address', 'organization_name', 'contact_person',
        ]
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        
        # Validate required NGO fields
        if data.get('role') == 'ACCEPTOR':
            if not data.get('organization_name'):
                raise serializers.ValidationError({"organization_name": "Organization name is required for NGOs."})
            if not data.get('contact_person'):
                raise serializers.ValidationError({"contact_person": "Contact person is required for NGOs."})
        
        return data
    
    def create(self, validated_data):
        # Pop non-User fields
        validated_data.pop('password_confirm')
        address = validated_data.pop('address', '')
        organization_name = validated_data.pop('organization_name', '')
        contact_person = validated_data.pop('contact_person', '')
        
        user = User.objects.create_user(**validated_data)
        
        # Create profile based on role
        if user.role == 'DONOR':
            DonorProfile.objects.create(user=user, address=address)
        elif user.role == 'ACCEPTOR':
            AcceptorProfile.objects.create(
                user=user,
                organization_name=organization_name,
                contact_person=contact_person,
                address=address,
            )
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        data['user'] = user
        return data


class DonorProfileSerializer(serializers.ModelSerializer):
    """Serializer for donor profile."""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = DonorProfile
        fields = '__all__'
        read_only_fields = ['user', 'latitude', 'longitude', 'city', 'state', 'impact_score', 'total_donations']
    
    def update(self, instance, validated_data):
        # Geocode address if changed
        if 'address' in validated_data and validated_data['address'] != instance.address:
            try:
                geolocator = Nominatim(user_agent="reloop")
                location = geolocator.geocode(validated_data['address'])
                if location:
                    validated_data['latitude'] = location.latitude
                    validated_data['longitude'] = location.longitude
                    address_parts = location.address.split(',')
                    if len(address_parts) >= 2:
                        validated_data['city'] = address_parts[-3].strip()
                        validated_data['state'] = address_parts[-2].strip()
            except Exception:
                pass
        
        return super().update(instance, validated_data)


class AcceptorProfileSerializer(serializers.ModelSerializer):
    """Serializer for acceptor profile."""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = AcceptorProfile
        fields = '__all__'
        read_only_fields = ['user', 'latitude', 'longitude', 'city', 'state', 'verification_status', 'verified_at', 'total_received', 'average_rating']
    
    def update(self, instance, validated_data):
        # Geocode address if changed
        if 'address' in validated_data and validated_data['address'] != instance.address:
            try:
                geolocator = Nominatim(user_agent="reloop")
                location = geolocator.geocode(validated_data['address'])
                if location:
                    validated_data['latitude'] = location.latitude
                    validated_data['longitude'] = location.longitude
                    address_parts = location.address.split(',')
                    if len(address_parts) >= 2:
                        validated_data['city'] = address_parts[-3].strip()
                        validated_data['state'] = address_parts[-2].strip()
            except Exception:
                pass
        
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user details."""
    donor_profile = DonorProfileSerializer(read_only=True)
    acceptor_profile = AcceptorProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'donor_profile', 'acceptor_profile']
        read_only_fields = ['id', 'username']
