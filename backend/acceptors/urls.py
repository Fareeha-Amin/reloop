from django.urls import path
from .views import (
    CurrentNeedListCreateView,
    CurrentNeedDetailView,
    nearby_acceptors,
    verify_acceptor
)

urlpatterns = [
    path('needs/', CurrentNeedListCreateView.as_view(), name='current-need-list'),
    path('needs/<int:pk>/', CurrentNeedDetailView.as_view(), name='current-need-detail'),
    path('nearby/', nearby_acceptors, name='nearby-acceptors'),
    path('<int:acceptor_id>/verify/', verify_acceptor, name='verify-acceptor'),
]
