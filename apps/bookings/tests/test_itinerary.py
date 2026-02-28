from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.tours.models import Tour, TourCodeWord, ItineraryItem, ActivityCategory
from apps.bookings.models import Booking

User = get_user_model()


def _make_user(email='g@g.com', first='Gavin', last='Holder'):
    u = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(
        first_name=first, last_name=last, indemnity_accepted=True
    )
    return u


def _make_tour(guide, code='fynbos'):
    TourCodeWord.objects.get_or_create(word=code, defaults={'is_used': True})
    return Tour.objects.create(
        name='Kogelberg Trek', tour_code=code,
        start_datetime=timezone.now(), location_name='Kleinmond',
        capacity=10, status=Tour.Status.ACTIVE, guide=guide,
    )


def _make_category():
    return ActivityCategory.objects.first() or ActivityCategory.objects.create(
        name='Adventure', colour='#F97316', icon='bi-mountain'
    )


class ItineraryEmptyTest(TestCase):
    def test_no_bookings_shows_empty_state(self):
        self.client.force_login(_make_user())
        resp = self.client.get('/app/itinerary/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "haven't joined")

    def test_unauthenticated_redirects(self):
        resp = self.client.get('/app/itinerary/')
        self.assertIn('/accounts/login/', resp['Location'])


class ItineraryDetailTest(TestCase):
    def setUp(self):
        self.guide = _make_user('guide@g.com', 'Tyrone', 'Allan')
        self.guest = _make_user('guest@g.com', 'James', 'Allan')
        self.tour = _make_tour(self.guide)
        self.booking = Booking.objects.create(
            user=self.guest, tour=self.tour, status=Booking.Status.INVITED
        )

    def test_shows_tour_name(self):
        self.client.force_login(self.guest)
        resp = self.client.get(f'/app/itinerary/{self.booking.id}/')
        self.assertContains(resp, 'Kogelberg Trek')

    def test_shows_location(self):
        self.client.force_login(self.guest)
        resp = self.client.get(f'/app/itinerary/{self.booking.id}/')
        self.assertContains(resp, 'Kleinmond')

    def test_shows_rsvp_button_when_invited(self):
        self.client.force_login(self.guest)
        resp = self.client.get(f'/app/itinerary/{self.booking.id}/')
        self.assertContains(resp, 'RSVP')

    def test_other_user_cannot_access(self):
        other = _make_user('other@g.com')
        self.client.force_login(other)
        resp = self.client.get(f'/app/itinerary/{self.booking.id}/')
        self.assertEqual(resp.status_code, 404)

    def test_shows_itinerary_items(self):
        cat = _make_category()
        ItineraryItem.objects.create(
            tour=self.tour, day=1, title='Morning Hike', category=cat,
            start_time=timezone.now().time(), duration_minutes=120,
        )
        self.client.force_login(self.guest)
        resp = self.client.get(f'/app/itinerary/{self.booking.id}/')
        self.assertContains(resp, 'Morning Hike')

    def test_rsvp_post_updates_status(self):
        self.client.force_login(self.guest)
        resp = self.client.post(f'/app/itinerary/{self.booking.id}/rsvp/')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.RSVP_PENDING)
        self.assertRedirects(resp, f'/app/itinerary/{self.booking.id}/')
