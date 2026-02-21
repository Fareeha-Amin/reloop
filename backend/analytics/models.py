from django.db import models
from django.conf import settings
from donations.models import Donation


class ImpactMetrics(models.Model):
    """Environmental impact tracking for donations."""
    
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE, related_name='impact_metrics')
    
    # Environmental metrics
    waste_diverted_kg = models.DecimalField(max_digits=8, decimal_places=2)
    carbon_offset_kg = models.DecimalField(max_digits=8, decimal_places=2)
    impact_points = models.IntegerField()
    
    # Impact level badge
    IMPACT_LEVEL_CHOICES = [
        ('BRONZE', 'Bronze'),
        ('SILVER', 'Silver'),
        ('GOLD', 'Gold'),
        ('PLATINUM', 'Platinum'),
    ]
    impact_level = models.CharField(max_length=10, choices=IMPACT_LEVEL_CHOICES, default='BRONZE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'impact_metrics'
    
    def __str__(self):
        return f"Impact for Donation #{self.donation.id} - {self.impact_points} points"


class DriveEvent(models.Model):
    """Corporate/School collaboration donation drives."""
    
    EVENT_TYPE_CHOICES = [
        ('CORPORATE', 'Corporate'),
        ('SCHOOL', 'School'),
        ('COMMUNITY', 'Community'),
    ]
    
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_drives'
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    event_type = models.CharField(max_length=15, choices=EVENT_TYPE_CHOICES)
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Targets
    target_items = models.IntegerField(default=0)
    collected_items = models.IntegerField(default=0)
    
    # Participants
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='participated_drives',
        blank=True
    )
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PLANNED')
    
    # Recognition
    public_recognition = models.BooleanField(default=True)
    badge_earned = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'drive_events'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.get_event_type_display()})"


class Review(models.Model):
    """Donor ratings for acceptors."""
    
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE, related_name='review')
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_reviews'
    )
    acceptor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_reviews'
    )
    
    rating = models.IntegerField()  # 1-5
    comment = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reviews'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.donor.username} for {self.acceptor.acceptor_profile.organization_name} - {self.rating}★"
