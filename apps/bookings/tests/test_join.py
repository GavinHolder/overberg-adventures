from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import UserProfile
from apps.tours.models import Tour, TourCodeWord
from apps.bookings.models import Booking


def _make_user(email='g@g.com'):
    User = get_user_model()
    u = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(
        first_name='Gavin', last_name='Holder', indemnity_accepted=True
    )
    return u


def _make_tour(code='fynbos', capacity=10):
    TourCodeWord.objects.get_or_create(word=code, defaults={'is_used': True})
    return Tour.objects.create(
        name='Overstrand Unlocked', tour_code=code,
        start_datetime=timezone.now(), location_name='Kleinmond',
        capacity=capacity, status=Tour.Status.ACTIVE,
    )


class JoinLookupTest(TestCase):
    def test_get_not_allowed(self):
        self.client.force_login(_make_user())
        resp = self.client.get('/app/join/')
        self.assertEqual(resp.status_code, 405)

    def test_redirects_unauthenticated(self):
        resp = self.client.post('/app/join/', {'tour_code': 'fynbos'})
        self.assertIn('/accounts/login/', resp['Location'])

    def test_valid_code_redirects_to_confirm(self):
        _make_tour('fynbos')
        self.client.force_login(_make_user())
        resp = self.client.post('/app/join/', {'tour_code': 'FYNBOS'})
        self.assertRedirects(resp, '/app/join/fynbos/')

    def test_invalid_code_redirects_home_with_message(self):
        self.client.force_login(_make_user())
        resp = self.client.post('/app/join/', {'tour_code': 'unknown'}, follow=True)
        self.assertRedirects(resp, '/')
        self.assertContains(resp, 'not found')

    def test_already_booked_redirects_to_itinerary(self):
        user = _make_user()
        tour = _make_tour('pelican')
        booking = Booking.objects.create(user=user, tour=tour, status=Booking.Status.CONFIRMED)
        self.client.force_login(user)
        resp = self.client.post('/app/join/', {'tour_code': 'pelican'})
        self.assertRedirects(resp, f'/app/itinerary/{booking.id}/')


class JoinConfirmTest(TestCase):
    def test_confirm_page_shows_tour_info(self):
        _make_tour('milkwood')
        self.client.force_login(_make_user())
        resp = self.client.get('/app/join/milkwood/')
        self.assertContains(resp, 'Overstrand Unlocked')
        self.assertContains(resp, 'Kleinmond')

    def test_confirm_page_shows_user_name(self):
        _make_tour('whale')
        self.client.force_login(_make_user())
        resp = self.client.get('/app/join/whale/')
        self.assertContains(resp, 'Gavin Holder')

    def test_confirm_page_has_csrf_form(self):
        _make_tour('kogelberg')
        self.client.force_login(_make_user())
        resp = self.client.get('/app/join/kogelberg/')
        self.assertContains(resp, 'csrfmiddlewaretoken')
        self.assertContains(resp, 'Join This Trip')

    def test_post_creates_booking_and_redirects(self):
        tour = _make_tour('milkwood2')
        user = _make_user()
        self.client.force_login(user)
        resp = self.client.post('/app/join/milkwood2/')
        booking = Booking.objects.get(user=user, tour=tour)
        self.assertRedirects(resp, f'/app/itinerary/{booking.id}/')

    def test_full_tour_redirects_home_with_message(self):
        tour = _make_tour('whale2', capacity=1)
        other = _make_user('other@test.com')
        Booking.objects.create(user=other, tour=tour, status=Booking.Status.CONFIRMED)
        self.client.force_login(_make_user('me@test.com'))
        resp = self.client.post('/app/join/whale2/', follow=True)
        self.assertRedirects(resp, '/')
        self.assertContains(resp, 'full')

    def test_already_enrolled_redirects_to_itinerary(self):
        tour = _make_tour('fynbos2')
        user = _make_user()
        booking = Booking.objects.create(user=user, tour=tour, status=Booking.Status.CONFIRMED)
        self.client.force_login(user)
        resp = self.client.get('/app/join/fynbos2/')
        self.assertRedirects(resp, f'/app/itinerary/{booking.id}/')
