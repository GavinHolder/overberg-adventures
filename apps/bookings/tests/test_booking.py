import pytest
from django.contrib.auth import get_user_model
from apps.tours.models import Tour

User = get_user_model()


@pytest.fixture
def make_user(db):
    counter = {'n': 0}
    def _make():
        counter['n'] += 1
        n = counter['n']
        return User.objects.create_user(
            username=f'user{n}', email=f'user{n}@test.com', password='pass'
        )
    return _make


@pytest.fixture
def make_tour(db):
    from django.utils import timezone
    from datetime import timedelta
    counter = {'n': 0}
    def _make(capacity=10):
        counter['n'] += 1
        n = counter['n']
        return Tour.objects.create(
            name=f'Tour {n}',
            start_datetime=timezone.now() + timedelta(days=7),
            location_name='Hermanus',
            location_lat='-34.4',
            location_lng='19.2',
            capacity=capacity,
        )
    return _make


@pytest.mark.django_db
def test_booking_created_from_rsvp(make_user, make_tour):
    from apps.bookings.models import Booking
    user = make_user()
    tour = make_tour(capacity=10)
    booking = Booking.objects.create_from_rsvp(user=user, tour=tour)
    assert booking.status == Booking.Status.RSVP_PENDING
    assert tour.bookings.count() == 1


@pytest.mark.django_db
def test_tour_capacity_respected(make_user, make_tour):
    from apps.bookings.models import Booking
    tour = make_tour(capacity=1)
    u1, u2 = make_user(), make_user()
    Booking.objects.create_from_rsvp(user=u1, tour=tour)
    with pytest.raises(ValueError, match='capacity'):
        Booking.objects.create_from_rsvp(user=u2, tour=tour)


@pytest.mark.django_db
def test_booking_unique_per_user_tour(make_user, make_tour):
    from apps.bookings.models import Booking
    from django.db import IntegrityError
    user = make_user()
    tour = make_tour()
    Booking.objects.create_from_rsvp(user=user, tour=tour)
    with pytest.raises(IntegrityError):
        Booking.objects.create(user=user, tour=tour, status=Booking.Status.RSVP_PENDING)


@pytest.mark.django_db
def test_booking_str(make_user, make_tour):
    from apps.bookings.models import Booking
    user = make_user()
    tour = make_tour()
    booking = Booking.objects.create_from_rsvp(user=user, tour=tour)
    result = str(booking)
    assert user.username in result
    assert tour.name in result


@pytest.mark.django_db
def test_tour_spots_remaining_after_booking(make_user, make_tour):
    """Phase 5 re-enables this — Tour.spots_remaining accounts for RSVP_PENDING bookings."""
    from apps.bookings.models import Booking
    tour = make_tour(capacity=10)
    u1 = make_user()
    Booking.objects.create_from_rsvp(user=u1, tour=tour)
    tour.refresh_from_db()
    assert tour.spots_remaining == 9
    assert not tour.is_full


@pytest.mark.django_db
def test_tour_is_full_when_at_capacity(make_user, make_tour):
    from apps.bookings.models import Booking
    tour = make_tour(capacity=2)
    u1, u2 = make_user(), make_user()
    Booking.objects.create_from_rsvp(user=u1, tour=tour)
    Booking.objects.create_from_rsvp(user=u2, tour=tour)
    tour.refresh_from_db()
    assert tour.is_full
