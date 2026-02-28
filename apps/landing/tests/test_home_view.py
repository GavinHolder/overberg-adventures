from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.tours.models import Tour, TourCodeWord
from apps.bookings.models import Booking


def _make_user(email='g@g.com'):
    User = get_user_model()
    u = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='Gavin', indemnity_accepted=True)
    return u


def _make_tour(code='fynbos', name='Kogelberg Trek'):
    TourCodeWord.objects.get_or_create(word=code, defaults={'is_used': True})
    return Tour.objects.create(
        name=name, tour_code=code,
        start_datetime=timezone.now(), location_name='Kleinmond',
        capacity=10, status=Tour.Status.ACTIVE,
    )


class HomeViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        resp = self.client.get('/')
        self.assertRedirects(resp, '/accounts/login/')

    def test_redirects_incomplete_setup(self):
        User = get_user_model()
        u = User.objects.create_user(username='x@x.com', email='x@x.com', password='x', is_active=True)
        self.client.force_login(u)
        resp = self.client.get('/')
        self.assertRedirects(resp, '/accounts/setup/', fetch_redirect_response=False)

    def test_shows_welcome(self):
        self.client.force_login(_make_user())
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Welcome, Gavin')

    def test_shows_no_tours_message(self):
        self.client.force_login(_make_user())
        resp = self.client.get('/')
        self.assertContains(resp, "haven't joined any tours")

    def test_shows_tour_code_form(self):
        self.client.force_login(_make_user())
        resp = self.client.get('/')
        self.assertContains(resp, 'tour_code')
        self.assertContains(resp, '/app/join/')

    def test_shows_my_tours_when_booked(self):
        user = _make_user()
        tour = _make_tour()
        Booking.objects.create(user=user, tour=tour, status=Booking.Status.CONFIRMED)
        self.client.force_login(user)
        resp = self.client.get('/')
        self.assertContains(resp, 'MY TOURS')
        self.assertContains(resp, 'Kogelberg Trek')

    def test_cancelled_booking_not_shown(self):
        user = _make_user()
        tour = _make_tour('pelican', 'Pelican Bay')
        Booking.objects.create(user=user, tour=tour, status=Booking.Status.CANCELLED)
        self.client.force_login(user)
        resp = self.client.get('/')
        self.assertNotContains(resp, 'Pelican Bay')
