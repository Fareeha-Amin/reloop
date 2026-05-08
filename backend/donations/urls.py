from django.urls import path
from .views import (
    DonationListCreateView,
    DonationDetailView,
    accept_donation,
    reject_donation,
    update_donation_status,
    trigger_fallback,
    donor_action,
)

urlpatterns = [
    path('', DonationListCreateView.as_view(), name='donation-list-create'),
    path('<int:pk>/', DonationDetailView.as_view(), name='donation-detail'),
    path('<int:donation_id>/accept/', accept_donation, name='accept-donation'),
    path('<int:donation_id>/reject/', reject_donation, name='reject-donation'),
    path('<int:donation_id>/status/', update_donation_status, name='update-donation-status'),
    path('<int:donation_id>/fallback/', trigger_fallback, name='trigger-fallback'),
    path('<int:donation_id>/donor-action/', donor_action, name='donor-action'),
]

