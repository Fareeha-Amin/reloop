"""
Management command to check donation deadlines and trigger waste fallback.
Run via: python manage.py check_deadlines
Can be scheduled via cron or Celery beat.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from donations.models import Donation
from ai_engine.fallback import check_and_trigger_fallback


class Command(BaseCommand):
    help = 'Check expired donation deadlines and trigger waste fallback'

    def handle(self, *args, **options):
        now = timezone.now()
        expired = Donation.objects.filter(
            donation_deadline__lt=now,
            status__in=['CREATED', 'MATCHED', 'REJECTED'],
        )

        triggered = 0
        for donation in expired:
            result = check_and_trigger_fallback(donation)
            if result:
                triggered += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Fallback triggered for donation #{donation.id}: '
                        f'{result["collector"]} (₹{result["donor_commission"]} credit)'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f'Done. Checked {expired.count()} expired donations, triggered {triggered} fallbacks.')
        )
