from django.urls import path
from .views import (
    ImpactMetricsListView,
    user_impact_dashboard,
    leaderboard,
    DriveEventListCreateView,
    DriveEventDetailView,
    join_drive,
    ReviewListCreateView,
    platform_statistics
)

urlpatterns = [
    path('impact/', ImpactMetricsListView.as_view(), name='impact-metrics'),
    path('dashboard/', user_impact_dashboard, name='impact-dashboard'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('drives/', DriveEventListCreateView.as_view(), name='drive-list'),
    path('drives/<int:pk>/', DriveEventDetailView.as_view(), name='drive-detail'),
    path('drives/<int:drive_id>/join/', join_drive, name='join-drive'),
    path('reviews/', ReviewListCreateView.as_view(), name='review-list'),
    path('statistics/', platform_statistics, name='platform-statistics'),
]
