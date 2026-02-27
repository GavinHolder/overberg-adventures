from django.db import models
from django.contrib.auth import get_user_model
from apps.tours.models import Tour

User = get_user_model()


class BookingManager(models.Manager):
    def create_from_rsvp(self, user, tour):
        """
        Create an RSVP_PENDING booking if tour has capacity.
        Raises ValueError if tour is full.

        ASSUMPTIONS:
        1. tour.capacity is set and > 0
        2. user is authenticated
        3. Caller handles unique_together violation for duplicate bookings
        """
        confirmed_count = self.filter(
            tour=tour, status__in=['RSVP_PENDING', 'CONFIRMED']
        ).count()
        if confirmed_count >= tour.capacity:
            raise ValueError(f'Tour at capacity ({tour.capacity})')
        return self.create(user=user, tour=tour, status=Booking.Status.RSVP_PENDING)


class Booking(models.Model):
    class Status(models.TextChoices):
        INVITED = 'INVITED', 'Invited'
        RSVP_PENDING = 'RSVP_PENDING', 'RSVP Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RSVP_PENDING)
    tour_code = models.CharField(max_length=50, blank=True)  # assigned after payment
    invited_at = models.DateTimeField(auto_now_add=True)
    rsvp_deadline = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    objects = BookingManager()

    class Meta:
        unique_together = [['tour', 'user']]

    def __str__(self):
        return f'{self.user} — {self.tour} ({self.status})'
