from django.db import models, transaction
from django.contrib.auth import get_user_model
from apps.tours.models import Tour

User = get_user_model()


class BookingManager(models.Manager):
    def create_from_rsvp(self, user, tour):
        """
        Atomically check capacity and create RSVP_PENDING booking.
        Uses select_for_update to prevent concurrent overbooking.

        ASSUMPTIONS:
        1. tour.capacity is set and > 0
        2. user is authenticated
        3. unique_together handles duplicate booking attempts gracefully

        FAILURE MODES:
        - Concurrent RSVPs: select_for_update locks tour row until transaction commits
        - DB unavailable: transaction rolls back, caller receives DatabaseError
        """
        with transaction.atomic():
            # Lock the tour row to prevent concurrent overbooking
            locked_tour = Tour.objects.select_for_update().get(pk=tour.pk)
            confirmed_count = self.filter(
                tour=locked_tour,
                status__in=[Booking.Status.RSVP_PENDING, Booking.Status.CONFIRMED],
            ).count()
            if confirmed_count >= locked_tour.capacity:
                raise ValueError(f'Tour at capacity ({locked_tour.capacity})')
            return self.create(user=user, tour=locked_tour, status=Booking.Status.RSVP_PENDING)


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
