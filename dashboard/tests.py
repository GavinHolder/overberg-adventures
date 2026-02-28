from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()


def make_user(email, role=UserProfile.Role.GUEST, is_staff=False):
    user = User.objects.create_user(username=email, email=email, password='pass')
    user.profile.role = role
    user.profile.save()
    if is_staff:
        user.is_staff = True
        user.save()
    return user


class DashboardAccessTest(TestCase):
    def test_guest_cannot_access_dashboard(self):
        """Guests get 403 forbidden."""
        user = make_user('guest@test.com', UserProfile.Role.GUEST)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 403)

    def test_guide_can_access_dashboard(self):
        user = make_user('guide@test.com', UserProfile.Role.GUIDE)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_operator_can_access_dashboard(self):
        user = make_user('op@test.com', UserProfile.Role.OPERATOR)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_role_can_access_dashboard(self):
        user = make_user('admin@test.com', UserProfile.Role.ADMIN)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_staff_can_access_dashboard(self):
        user = make_user('staff@test.com', is_staff=True)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_redirects_to_login(self):
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/', resp['Location'])

    def test_tours_list_renders_template(self):
        user = make_user('guide2@test.com', UserProfile.Role.GUIDE)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertTemplateUsed(resp, 'admin_panel/tours/list.html')
