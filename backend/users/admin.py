from django.contrib import admin
from users.models import User, DonorProfile, AcceptorProfile
from donations.models import Donation, DonationImage
from acceptors.models import CurrentNeed
from logistics.models import LogisticsProvider, PickupRequest
from payments.models import Payment, Commission
from analytics.models import ImpactMetrics, DriveEvent, Review

# Register models for admin panel
admin.site.register(User)
admin.site.register(DonorProfile)
admin.site.register(AcceptorProfile)
admin.site.register(Donation)
admin.site.register(DonationImage)
admin.site.register(CurrentNeed)
admin.site.register(LogisticsProvider)
admin.site.register(PickupRequest)
admin.site.register(Payment)
admin.site.register(Commission)
admin.site.register(ImpactMetrics)
admin.site.register(DriveEvent)
admin.site.register(Review)
