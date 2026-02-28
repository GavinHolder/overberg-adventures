from django.test import TestCase
from django.urls import reverse


class URLsTest(TestCase):
    def test_home(self):
        self.assertEqual(reverse('landing:home'), '/')

    def test_itinerary_home(self):
        self.assertEqual(reverse('bookings:itinerary_home'), '/app/itinerary/')

    def test_itinerary_detail(self):
        self.assertEqual(reverse('bookings:itinerary_detail', args=[1]), '/app/itinerary/1/')

    def test_join_lookup(self):
        self.assertEqual(reverse('bookings:join_lookup'), '/app/join/')

    def test_join_confirm(self):
        self.assertEqual(reverse('bookings:join_confirm', args=['fynbos']), '/app/join/fynbos/')

    def test_sos(self):
        self.assertEqual(reverse('sos:sos'), '/app/sos/')

    def test_map(self):
        self.assertEqual(reverse('maps:map'), '/app/map/')

    def test_profile(self):
        self.assertEqual(reverse('accounts:profile'), '/accounts/profile/')
