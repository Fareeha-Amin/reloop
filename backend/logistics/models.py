from django.db import models
from django.conf import settings
from donations.models import Donation


class LogisticsProvider(models.Model):
    """Third-party logistics providers (Rapido, Porter, Uber, etc.)."""
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]
    
    name = models.CharField(max_length=100)
    api_endpoint = models.URLField(blank=True)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'logistics_providers'
    
    def __str__(self):
        return self.name


class PickupRequest(models.Model):
    """Pickup coordination for donations."""
    
    PICKUP_TYPE_CHOICES = [
        ('PLATFORM_ARRANGED', 'Platform Arranged'),
        ('SELF_SCHEDULED', 'Self Scheduled by Acceptor'),
        ('DROP_OFF', 'Donor Drop-off'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SCHEDULED', 'Scheduled'),
        ('PICKED_UP', 'Picked Up'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE, related_name='pickup_request')
    pickup_type = models.CharField(max_length=20, choices=PICKUP_TYPE_CHOICES)
    
    # For platform-arranged pickups
    logistics_provider = models.ForeignKey(
        LogisticsProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Scheduling
    scheduled_time = models.DateTimeField(null=True, blank=True)
    actual_pickup_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Cost calculation
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    base_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    platform_commission = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Tracking
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    booking_id = models.CharField(max_length=100, blank=True)  # Simulated booking ID
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pickup_requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pickup for Donation #{self.donation.id} - {self.get_status_display()}"
