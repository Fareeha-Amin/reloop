"""
Management command to seed sample WasteCollector entries.
Usage: python manage.py seed_waste_collectors
"""
from django.core.management.base import BaseCommand
from donations.models import WasteCollector


SAMPLE_COLLECTORS = [
    {
        'name': 'GreenCycle Recyclers',
        'address': 'Plot 12, Industrial Area, Hyderabad',
        'latitude': 17.4065,
        'longitude': 78.4772,
        'fee_per_kg': 8.00,
        'commission_to_donor_pct': 60.00,
        'platform_fee_pct': 10.00,
        'status': 'ACTIVE',
    },
    {
        'name': 'EcoScrap Solutions',
        'address': '45 Jubilee Hills, Hyderabad',
        'latitude': 17.4319,
        'longitude': 78.4093,
        'fee_per_kg': 6.50,
        'commission_to_donor_pct': 55.00,
        'platform_fee_pct': 12.00,
        'status': 'ACTIVE',
    },
    {
        'name': 'ReNew Waste Partners',
        'address': 'Sector 7, Gachibowli, Hyderabad',
        'latitude': 17.4401,
        'longitude': 78.3489,
        'fee_per_kg': 7.00,
        'commission_to_donor_pct': 65.00,
        'platform_fee_pct': 8.00,
        'status': 'ACTIVE',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with sample waste/recycling collectors'

    def handle(self, *args, **options):
        created_count = 0
        for data in SAMPLE_COLLECTORS:
            _, created = WasteCollector.objects.get_or_create(
                name=data['name'],
                defaults=data,
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {data['name']}")
            else:
                self.stdout.write(f"  Already exists: {data['name']}")

        self.stdout.write(self.style.SUCCESS(
            f'\nDone — {created_count} new collector(s) seeded ({len(SAMPLE_COLLECTORS)} total checked).'
        ))
