from django.urls import path
from .views import (
    PaymentListView,
    initiate_payment,
    complete_payment,
    CommissionListView,
    commission_summary
)

urlpatterns = [
    path('', PaymentListView.as_view(), name='payment-list'),
    path('initiate/', initiate_payment, name='initiate-payment'),
    path('<int:payment_id>/complete/', complete_payment, name='complete-payment'),
    path('commissions/', CommissionListView.as_view(), name='commission-list'),
    path('commissions/summary/', commission_summary, name='commission-summary'),
]
