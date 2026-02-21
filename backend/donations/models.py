from django.db import models
from django.conf import settings


class Donation(models.Model):
    """Main donation model tracking items from donors."""
    
    CATEGORY_CHOICES = [
        ('CLOTHES', 'Clothes'),
        ('TOYS', 'Toys'),
        ('BOOKS', 'Books'),
    ]
    
    CONDITION_CHOICES = [
        ('NEW', 'New'),
        ('GENTLY_USED', 'Gently Used'),
        ('USED', 'Used'),
    ]
    
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('MATCHED', 'Matched'),
        ('ACCEPTED', 'Accepted'),
        ('PICKUP_SCHEDULED', 'Pickup Scheduled'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
        ('WASTE_COLLECTED', 'Waste Collected'),
    ]

    DELIVERY_METHOD_CHOICES = [
        ('PLATFORM_LOGISTICS', 'Platform Logistics'),
        ('NGO_PICKUP', 'Custom NGO Pickup'),
        ('SELF_DROP', 'Self Drop-off'),
    ]

    LOGISTICS_PROVIDER_CHOICES = [
        ('PORTER', 'Porter'),
        ('RAPIDO', 'Rapido'),
        ('UBER', 'Uber'),
    ]
    
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='donations'
    )
    acceptor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_donations'
    )
    
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    quantity = models.IntegerField()
    condition = models.CharField(max_length=15, choices=CONDITION_CHOICES)
    description = models.TextField(blank=True)
    
    # Pickup details
    pickup_address = models.TextField()
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    preferred_pickup_start = models.DateTimeField(null=True, blank=True)
    preferred_pickup_end = models.DateTimeField(null=True, blank=True)

    # Delivery / scheduling
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES, default='SELF_DROP')
    logistics_provider_choice = models.CharField(max_length=10, choices=LOGISTICS_PROVIDER_CHOICES, blank=True, null=True)
    donation_deadline = models.DateTimeField(null=True, blank=True)
    is_priority = models.BooleanField(default=False)
    suggested_pickup_time = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')
    
    # AI matching
    ai_suggested_acceptor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_suggested_donations'
    )
    matching_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'donations'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.quantity} items by {self.donor.username}"


class DonationImage(models.Model):
    """Multiple images for each donation."""
    
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='donation_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'donation_images'
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"Image for donation #{self.donation.id}"


class WasteCollector(models.Model):
    """Waste management companies for fallback collection."""

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]

    name = models.CharField(max_length=255)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    fee_per_kg = models.DecimalField(max_digits=6, decimal_places=2, default=5.00)
    commission_to_donor_pct = models.DecimalField(max_digits=5, decimal_places=2, default=60.00)
    platform_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'waste_collectors'

    def __str__(self):
        return self.name
