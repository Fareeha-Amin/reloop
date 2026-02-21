from django.db import models
from django.conf import settings
from donations.models import Donation
import uuid


class Payment(models.Model):
    """Payment transactions for logistics services."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2)
    logistics_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    
    # Simulated payment gateway fields
    payment_method = models.CharField(max_length=50, default='Card')
    gateway_response = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.get_status_display()}"


class Commission(models.Model):
    """Platform commission tracking."""
    
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='commission_record')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    
    # For reporting
    month = models.IntegerField()
    year = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'commissions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Commission ₹{self.amount} from Payment {self.payment.transaction_id}"
