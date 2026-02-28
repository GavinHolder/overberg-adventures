from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile


def _make_user(email='m@m.com'):
    User = get_user_model()
    u = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='M', indemnity_accepted=True)
    return u


class MapViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        resp = self.client.get(reverse('maps:map'))
        self.assertIn('/accounts/login/', resp['Location'])

    def test_map_screen_loads(self):
        self.client.force_login(_make_user())
        resp = self.client.get(reverse('maps:map'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="map"')

    def test_shows_itinerary_button_with_booking(self):
        from django.utils import timezone
        from apps.tours.models import Tour, TourCodeWord
        from apps.bookings.models import Booking
        user = _make_user('map2@m.com')
        TourCodeWord.objects.get_or_create(word='maptest', defaults={'is_used': True})
        tour = Tour.objects.create(
            name='Map Tour', tour_code='maptest',
            start_datetime=timezone.now(), location_name='Hermanus',
            capacity=10, status=Tour.Status.ACTIVE,
        )
        booking = Booking.objects.create(user=user, tour=tour, status=Booking.Status.CONFIRMED)
        self.client.force_login(user)
        resp = self.client.get(reverse('maps:map'))
        self.assertContains(resp, 'VIEW ITINERARY')
        self.assertContains(resp, f'/app/itinerary/{booking.id}/')

    def test_no_itinerary_button_without_booking(self):
        self.client.force_login(_make_user())
        resp = self.client.get(reverse('maps:map'))
        self.assertNotContains(resp, 'VIEW ITINERARY')
