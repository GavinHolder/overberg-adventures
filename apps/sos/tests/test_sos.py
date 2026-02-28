from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile
from apps.sos.models import SosConfig, EmergencyContact


def _make_user(email='s@s.com'):
    User = get_user_model()
    u = User.objects.create_user(username=email, email=email, password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='Sam', indemnity_accepted=True)
    return u


class SOSViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        resp = self.client.get(reverse('sos:sos'))
        self.assertIn('/accounts/login/', resp['Location'])

    def test_sos_screen_loads(self):
        self.client.force_login(_make_user())
        self.assertEqual(self.client.get(reverse('sos:sos')).status_code, 200)

    def test_shows_sa_emergency_numbers_when_enabled(self):
        SosConfig.objects.create(show_sa_emergency_numbers=True)
        self.client.force_login(_make_user())
        resp = self.client.get(reverse('sos:sos'))
        self.assertContains(resp, '10111')
        self.assertContains(resp, '10177')
        self.assertContains(resp, '112')

    def test_hides_sa_numbers_when_disabled(self):
        SosConfig.objects.create(show_sa_emergency_numbers=False)
        self.client.force_login(_make_user())
        resp = self.client.get(reverse('sos:sos'))
        self.assertNotContains(resp, 'SAPS')

    def test_shows_emergency_contacts(self):
        SosConfig.objects.create(show_emergency_contacts=True)
        EmergencyContact.objects.create(name='Mountain Rescue', phone='+27219876543', role='SAR')
        self.client.force_login(_make_user())
        self.assertContains(self.client.get(reverse('sos:sos')), 'Mountain Rescue')

    def test_hides_inactive_contacts(self):
        SosConfig.objects.create(show_emergency_contacts=True)
        EmergencyContact.objects.create(name='Hidden', phone='000', is_active=False)
        self.client.force_login(_make_user())
        self.assertNotContains(self.client.get(reverse('sos:sos')), 'Hidden')

    def test_shows_first_aid_guides_when_enabled(self):
        SosConfig.objects.create(show_first_aid=True)
        self.client.force_login(_make_user())
        resp = self.client.get(reverse('sos:sos'))
        self.assertContains(resp, 'Snake Bite')
        self.assertContains(resp, 'Burns')

    def test_hides_first_aid_when_disabled(self):
        SosConfig.objects.create(show_first_aid=False)
        self.client.force_login(_make_user())
        self.assertNotContains(self.client.get(reverse('sos:sos')), 'Snake Bite')

    def test_no_guide_whatsapp_hides_sos_card(self):
        """No active booking = no guide WhatsApp card shown"""
        SosConfig.objects.create(show_whatsapp_sos=True)
        self.client.force_login(_make_user())
        self.assertNotContains(self.client.get(reverse('sos:sos')), 'Alert Your Guide')

    def test_shows_gps_share_when_enabled(self):
        SosConfig.objects.create(show_gps_share=True)
        self.client.force_login(_make_user())
        self.assertContains(self.client.get(reverse('sos:sos')), 'Generate GPS Link')
