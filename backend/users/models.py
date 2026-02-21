from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """Custom User model with role-based access control."""
    
    ROLE_CHOICES = [
        ('DONOR', 'Donor'),
        ('ACCEPTOR', 'Acceptor'),
        ('ADMIN', 'Admin'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='DONOR')
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class DonorProfile(models.Model):
    """Profile for donors with location and impact tracking."""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='donor_profile')
    address = models.TextField(blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    impact_score = models.IntegerField(default=0)
    total_donations = models.IntegerField(default=0)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'donor_profiles'
    
    def __str__(self):
        return f"Donor: {self.user.username}"


class AcceptorProfile(models.Model):
    """Profile for NGOs/Institutions accepting donations."""
    
    VERIFICATION_STATUS = [
        ('PENDING', 'Pending'),
        ('VERIFIED', 'Verified'),
        ('REJECTED', 'Rejected'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='acceptor_profile')
    organization_name = models.CharField(max_length=255)
    registration_id = models.CharField(max_length=100, blank=True, null=True)
    contact_person = models.CharField(max_length=255)
    address = models.TextField(blank=True, default='')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    
    # Capabilities
    has_pickup_capability = models.BooleanField(default=False)
    storage_capacity = models.CharField(max_length=50, blank=True)  # e.g., "Large", "Medium", "Small"
    
    # Verification
    verification_status = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS,
        default='PENDING'
    )
    verification_document = models.FileField(upload_to='verification_docs/', null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    total_received = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'acceptor_profiles'
    
    def __str__(self):
        return f"{self.organization_name} ({self.get_verification_status_display()})"
