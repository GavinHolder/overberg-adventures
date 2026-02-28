from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile


def _make_user():
    User = get_user_model()
    u = User.objects.create_user(
        username='p@p.com', email='p@p.com', password='x', is_active=True
    )
    UserProfile.objects.filter(user=u).update(
        first_name='Gavin', last_name='Holder',
        phone_whatsapp='+27795029661', indemnity_accepted=True,
        fitness_level=3, role='GUEST',
    )
    return u


class ProfileViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        resp = self.client.get(reverse('accounts:profile'))
        self.assertIn('/accounts/login/', resp['Location'])

    def test_shows_name_and_role(self):
        self.client.force_login(_make_user())
        resp = self.client.get(reverse('accounts:profile'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Gavin Holder')
        self.assertContains(resp, 'Guest Traveller')

    def test_shows_phone(self):
        self.client.force_login(_make_user())
        self.assertContains(
            self.client.get(reverse('accounts:profile')), '+27795029661'
        )

    def test_shows_fitness_label(self):
        self.client.force_login(_make_user())
        self.assertContains(
            self.client.get(reverse('accounts:profile')), 'Average'
        )
