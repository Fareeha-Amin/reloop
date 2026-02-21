from django.urls import path
from .views import suggest_ngos

urlpatterns = [
    path('suggest-ngos/', suggest_ngos, name='suggest-ngos'),
]
