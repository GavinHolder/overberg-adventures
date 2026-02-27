from django.core.management.base import BaseCommand
from apps.tours.models import TourCodeWord

OVERBERG_WORDS = [
    'fynbos', 'pelican', 'milkwood', 'protea', 'renosterveld', 'klipspringer',
    'bontebok', 'greenbul', 'kogelberg', 'kleinmond', 'hermanus', 'palmiet',
    'whale', 'lagoon', 'dune', 'estuary', 'sugarbird', 'agulhas',
    'overstrand', 'baboon', 'rockpool', 'saltwater', 'granite', 'bluegum',
    'peninsula', 'anchor', 'tidal', 'fernwood', 'beacon', 'crest',
    'strandloper', 'otter', 'egret', 'kingfisher', 'heron', 'ibis',
    'geranium', 'orchid', 'buchu', 'rooibos', 'honeybush', 'milkwood',
    'fynbos', 'protea', 'pelargonium', 'leucadendron', 'restio',
    'paarl', 'elgin', 'stanford', 'gansbaai', 'pringle', 'rooi',
    'walker', 'sunrise', 'trailhead', 'summit', 'compass', 'canyon',
]
# Deduplicate while preserving list
OVERBERG_WORDS = list(dict.fromkeys(OVERBERG_WORDS))


class Command(BaseCommand):
    help = 'Seed Overberg/nature themed single-word tour codes'

    def handle(self, *args, **options):
        created_count = 0
        for word in OVERBERG_WORDS:
            _, created = TourCodeWord.objects.get_or_create(word=word)
            if created:
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {created_count} new words '
                f'({TourCodeWord.objects.count()} total in pool, '
                f'{TourCodeWord.objects.filter(is_used=False).count()} available)'
            )
        )
