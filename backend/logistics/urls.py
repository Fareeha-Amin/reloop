from django.urls import path
from .views import (
    LogisticsProviderListView,
    PickupRequestListCreateView,
    PickupRequestDetailView,
    calculate_pickup_cost
)

urlpatterns = [
    path('providers/', LogisticsProviderListView.as_view(), name='logistics-providers'),
    path('pickups/', PickupRequestListCreateView.as_view(), name='pickup-requests'),
    path('pickups/<int:pk>/', PickupRequestDetailView.as_view(), name='pickup-detail'),
    path('calculate-cost/', calculate_pickup_cost, name='calculate-cost'),
]
