from django.core.management.base import BaseCommand
from apps.tours.models import ActivityCategory

INITIAL_CATEGORIES = [
    {'name': 'Hiking', 'icon': 'geo-alt', 'colour': '#F97316', 'order': 1},
    {'name': 'Food & Dining', 'icon': 'cup-hot', 'colour': '#0D9488', 'order': 2},
    {'name': 'Kayaking', 'icon': 'water', 'colour': '#0284C7', 'order': 3},
    {'name': 'Cycling', 'icon': 'bicycle', 'colour': '#7C3AED', 'order': 4},
    {'name': 'Scenic Drive', 'icon': 'car-front', 'colour': '#D97706', 'order': 5},
    {'name': 'Whale Watching', 'icon': 'droplet-fill', 'colour': '#0891B2', 'order': 6},
    {'name': 'Swimming', 'icon': 'tsunami', 'colour': '#2563EB', 'order': 7},
    {'name': 'Photography', 'icon': 'camera', 'colour': '#DB2777', 'order': 8},
    {'name': 'Cultural', 'icon': 'building', 'colour': '#65A30D', 'order': 9},
    {'name': 'Accommodation', 'icon': 'house', 'colour': '#6B7280', 'order': 10},
]


class Command(BaseCommand):
    help = 'Seed initial activity categories'

    def handle(self, *args, **options):
        created_count = 0
        for data in INITIAL_CATEGORIES:
            _, created = ActivityCategory.objects.get_or_create(
                name=data['name'], defaults=data
            )
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {created_count} new categories '
                f'({ActivityCategory.objects.count()} total)'
            )
        )
