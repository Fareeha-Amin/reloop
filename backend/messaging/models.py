from django.db import models
from django.conf import settings
from donations.models import Donation


class Message(models.Model):
    """Donation-specific chat messages between donor and acceptor."""

    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} on Donation #{self.donation.id}"
