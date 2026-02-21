from django.db import models
from django.conf import settings


class CurrentNeed(models.Model):
    """Track current needs of acceptor organizations."""
    
    CATEGORY_CHOICES = [
        ('CLOTHES', 'Clothes'),
        ('TOYS', 'Toys'),
        ('BOOKS', 'Books'),
    ]
    
    URGENCY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    acceptor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='current_needs'
    )
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    quantity_needed = models.IntegerField()
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='MEDIUM')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'current_needs'
        ordering = ['-urgency', '-created_at']
    
    def __str__(self):
        return f"{self.acceptor.acceptor_profile.organization_name} needs {self.quantity_needed} {self.get_category_display()}"
