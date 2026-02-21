"""
Seed data script for ReLoop platform.
Run with: python manage.py shell < seed_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reloop.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import DonorProfile, AcceptorProfile
from donations.models import Donation, DonationImage
from acceptors.models import CurrentNeed
from logistics.models import LogisticsProvider
from analytics.models import ImpactMetrics
from ai_engine.impact_calculator import calculate_donation_impact

User = get_user_model()

print("🌱 Starting seed data generation...")

# Clear existing data (optional)
print("Clearing existing data...")
User.objects.all().delete()
LogisticsProvider.objects.all().delete()

# Create admin user
print("Creating admin user...")
admin = User.objects.create_superuser(
    username='admin',
    email='admin@reloop.com',
    password='admin123',
    role='ADMIN',
    first_name='Admin',
    last_name='User'
)

# Create logistics providers
print("Creating logistics providers...")
providers = [
    LogisticsProvider.objects.create(
        name='Rapido',
        api_endpoint='https://api.rapido.com',
        commission_percentage=10.0,
        status='ACTIVE'
    ),
    LogisticsProvider.objects.create(
        name='Porter',
        api_endpoint='https://api.porter.in',
        commission_percentage=12.0,
        status='ACTIVE'
    ),
    LogisticsProvider.objects.create(
        name='Uber',
        api_endpoint='https://api.uber.com',
        commission_percentage=8.0,
        status='ACTIVE'
    ),
]

# Create donor users
print("Creating donor users...")
donors_data = [
    {
        'username': 'john_donor',
        'email': 'john@example.com',
        'first_name': 'John',
        'last_name': 'Doe',
        'phone_number': '+919876543210',
        'address': 'MG Road, Bangalore, Karnataka',
        'latitude': 12.9716,
        'longitude': 77.5946,
        'city': 'Bangalore',
        'state': 'Karnataka'
    },
    {
        'username': 'sarah_donor',
        'email': 'sarah@example.com',
        'first_name': 'Sarah',
        'last_name': 'Smith',
        'phone_number': '+919876543211',
        'address': 'Koramangala, Bangalore, Karnataka',
        'latitude': 12.9352,
        'longitude': 77.6245,
        'city': 'Bangalore',
        'state': 'Karnataka'
    },
]

donors = []
for data in donors_data:
    user = User.objects.create_user(
        username=data['username'],
        email=data['email'],
        password='donor123',
        role='DONOR',
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone_number=data['phone_number']
    )
    profile = DonorProfile.objects.create(
        user=user,
        address=data['address'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        city=data['city'],
        state=data['state']
    )
    donors.append(user)

# Create acceptor users (NGOs)
print("Creating acceptor users (NGOs)...")
acceptors_data = [
    {
        'username': 'helping_hands_ngo',
        'email': 'contact@helpinghands.org',
        'first_name': 'Helping',
        'last_name': 'Hands',
        'phone_number': '+919876543220',
        'organization_name': 'Helping Hands Foundation',
        'registration_id': 'NGO-BLR-001',
        'contact_person': 'Rajesh Kumar',
        'address': 'Indiranagar, Bangalore, Karnataka',
        'latitude': 12.9784,
        'longitude': 77.6408,
        'city': 'Bangalore',
        'state': 'Karnataka',
        'has_pickup_capability': True,
        'storage_capacity': 'Large'
    },
    {
        'username': 'bright_future_school',
        'email': 'admin@brightfuture.edu',
        'first_name': 'Bright',
        'last_name': 'Future',
        'phone_number': '+919876543221',
        'organization_name': 'Bright Future School',
        'registration_id': 'SCH-BLR-002',
        'contact_person': 'Priya Sharma',
        'address': 'Whitefield, Bangalore, Karnataka',
        'latitude': 12.9698,
        'longitude': 77.7500,
        'city': 'Bangalore',
        'state': 'Karnataka',
        'has_pickup_capability': False,
        'storage_capacity': 'Medium'
    },
    {
        'username': 'hope_orphanage',
        'email': 'info@hopeorphanage.org',
        'first_name': 'Hope',
        'last_name': 'Orphanage',
        'phone_number': '+919876543222',
        'organization_name': 'Hope Children Orphanage',
        'registration_id': 'ORG-BLR-003',
        'contact_person': 'Anita Desai',
        'address': 'Jayanagar, Bangalore, Karnataka',
        'latitude': 12.9250,
        'longitude': 77.5838,
        'city': 'Bangalore',
        'state': 'Karnataka',
        'has_pickup_capability': True,
        'storage_capacity': 'Medium'
    },
]

acceptors = []
for data in acceptors_data:
    user = User.objects.create_user(
        username=data['username'],
        email=data['email'],
        password='acceptor123',
        role='ACCEPTOR',
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone_number=data['phone_number']
    )
    profile = AcceptorProfile.objects.create(
        user=user,
        organization_name=data['organization_name'],
        registration_id=data['registration_id'],
        contact_person=data['contact_person'],
        address=data['address'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        city=data['city'],
        state=data['state'],
        has_pickup_capability=data['has_pickup_capability'],
        storage_capacity=data['storage_capacity'],
        verification_status='VERIFIED'
    )
    acceptors.append(user)

# Create current needs for acceptors
print("Creating current needs...")
needs_data = [
    {'acceptor': acceptors[0], 'category': 'CLOTHES', 'quantity_needed': 100, 'urgency': 'HIGH'},
    {'acceptor': acceptors[0], 'category': 'BOOKS', 'quantity_needed': 50, 'urgency': 'MEDIUM'},
    {'acceptor': acceptors[1], 'category': 'BOOKS', 'quantity_needed': 200, 'urgency': 'CRITICAL'},
    {'acceptor': acceptors[1], 'category': 'TOYS', 'quantity_needed': 30, 'urgency': 'LOW'},
    {'acceptor': acceptors[2], 'category': 'CLOTHES', 'quantity_needed': 150, 'urgency': 'HIGH'},
    {'acceptor': acceptors[2], 'category': 'TOYS', 'quantity_needed': 75, 'urgency': 'MEDIUM'},
]

for need_data in needs_data:
    CurrentNeed.objects.create(**need_data)

# Create sample donations
print("Creating sample donations...")
donations_data = [
    {
        'donor': donors[0],
        'category': 'CLOTHES',
        'quantity': 25,
        'condition': 'GENTLY_USED',
        'description': 'Winter clothes for children',
        'pickup_address': 'MG Road, Bangalore',
        'pickup_latitude': 12.9716,
        'pickup_longitude': 77.5946,
        'status': 'CREATED'
    },
    {
        'donor': donors[1],
        'category': 'BOOKS',
        'quantity': 50,
        'condition': 'NEW',
        'description': 'Educational books for primary school',
        'pickup_address': 'Koramangala, Bangalore',
        'pickup_latitude': 12.9352,
        'pickup_longitude': 77.6245,
        'status': 'CREATED'
    },
]

for donation_data in donations_data:
    donation = Donation.objects.create(**donation_data)
    
    # Calculate and create impact metrics
    impact_data = calculate_donation_impact(donation)
    ImpactMetrics.objects.create(
        donation=donation,
        **impact_data
    )
    
    # Update donor profile
    donor_profile = donation.donor.donor_profile
    donor_profile.total_donations += 1
    donor_profile.impact_score += impact_data['impact_points']
    donor_profile.save()

print("✅ Seed data generation complete!")
print("\n📊 Summary:")
print(f"  - Admin users: 1")
print(f"  - Donors: {len(donors)}")
print(f"  - Acceptors (NGOs): {len(acceptors)}")
print(f"  - Logistics Providers: {len(providers)}")
print(f"  - Donations: {len(donations_data)}")
print("\n🔑 Login Credentials:")
print("  Admin: username='admin', password='admin123'")
print("  Donor: username='john_donor', password='donor123'")
print("  Acceptor: username='helping_hands_ngo', password='acceptor123'")
