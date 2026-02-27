from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ActivityCategory(models.Model):
    """Tour activity categories — fully dynamic, client manages in backend."""
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, default='geo-alt')  # Bootstrap Icons name
    colour = models.CharField(max_length=7, default='#F97316')  # hex colour
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Activity Categories'

    def __str__(self):
        return self.name


class TourCodeWord(models.Model):
    """Pool of Overberg/nature-themed single words for tour codes."""
    word = models.CharField(max_length=50, unique=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['word']

    def __str__(self):
        return self.word

    @classmethod
    def generate(cls):
        """Pick a random unused word. Raises ValueError if pool exhausted."""
        word_obj = cls.objects.filter(is_used=False).order_by('?').first()
        if not word_obj:
            raise ValueError(
                'Tour code word pool exhausted — run seed_tour_codes or add words via admin.'
            )
        word_obj.is_used = True
        word_obj.used_at = timezone.now()
        word_obj.save()
        return word_obj.word


class Tour(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    guide = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='guided_tours'
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    location_name = models.CharField(max_length=200)
    location_lat = models.DecimalField(max_digits=10, decimal_places=7, default=0)
    location_lng = models.DecimalField(max_digits=10, decimal_places=7, default=0)
    capacity = models.PositiveSmallIntegerField(default=20)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    # Map data
    polygon = models.JSONField(null=True, blank=True)  # GeoJSON polygon for tour area
    # Restrictions
    min_fitness_level = models.PositiveSmallIntegerField(default=1)
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    # RSVP deadline (hours before start)
    rsvp_deadline_hours = models.PositiveSmallIntegerField(default=24)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_datetime']

    def __str__(self):
        return f'{self.name} ({self.start_datetime.strftime("%d %b %Y")})'

    @property
    def spots_remaining(self):
        # bookings reverse relation added when Booking model (Phase 5) is created
        if not hasattr(self, 'bookings'):
            return self.capacity
        confirmed = self.bookings.filter(
            status__in=['RSVP_PENDING', 'CONFIRMED']
        ).count()
        return max(0, self.capacity - confirmed)

    @property
    def is_full(self):
        return self.spots_remaining == 0


class ItineraryItem(models.Model):
    class Difficulty(models.TextChoices):
        EASY = 'EASY', 'Easy'
        MODERATE = 'MODERATE', 'Moderate'
        HARD = 'HARD', 'Hard'

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='itinerary_items')
    day = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ActivityCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    start_time = models.TimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    location_name = models.CharField(max_length=200, blank=True)
    location_lat = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    location_lng = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    difficulty = models.CharField(
        max_length=10, choices=Difficulty.choices, default=Difficulty.EASY
    )
    distance_km = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )

    class Meta:
        ordering = ['day', 'order', 'start_time']

    def __str__(self):
        return f'Day {self.day} - {self.title}'

    @property
    def duration_display(self):
        h, m = divmod(self.duration_minutes, 60)
        if h and m:
            return f'{h} hr {m} min'
        if h:
            return f'{h} hr'
        return f'{m} min'


class MapRouteWaypoint(models.Model):
    """Ordered waypoints for a tour route (walking or driving)."""
    class RouteType(models.TextChoices):
        WALKING = 'WALKING', 'Walking'
        DRIVING = 'DRIVING', 'Driving'

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='waypoints')
    route_type = models.CharField(max_length=10, choices=RouteType.choices, default=RouteType.WALKING)
    order = models.PositiveSmallIntegerField(default=0)
    lat = models.DecimalField(max_digits=10, decimal_places=7)
    lng = models.DecimalField(max_digits=10, decimal_places=7)
    label = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['route_type', 'order']
