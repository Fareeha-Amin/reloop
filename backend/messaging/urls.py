from django.urls import path
from .views import donation_messages, unread_count, per_donation_unread

urlpatterns = [
    path('<int:donation_id>/', donation_messages, name='donation-messages'),
    path('unread/', unread_count, name='unread-count'),
    path('unread/per-donation/', per_donation_unread, name='per-donation-unread'),
]
