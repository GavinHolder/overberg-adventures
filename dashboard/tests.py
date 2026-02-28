from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()


def make_user(email, role=UserProfile.Role.GUEST, is_staff=False):
    """
    Factory helper: create a User with a pre-configured UserProfile role.

    Creates the user via create_user (sets unusable password correctly),
    then mutates the auto-created profile (via post_save signal) to the
    requested role and optionally grants is_staff.

    Args:
        email:    Used as both username and email for simplicity in tests.
        role:     UserProfile.Role value; defaults to GUEST.
        is_staff: If True, sets user.is_staff = True (Django admin access).

    Returns:
        Saved User instance with profile.role set and is_staff applied.
    """
    user = User.objects.create_user(username=email, email=email, password='pass')
    # The post_save signal creates the profile automatically; mutate its role here
    # rather than creating a second profile to avoid IntegrityError on the OneToOne.
    user.profile.role = role
    user.profile.save()
    if is_staff:
        user.is_staff = True
        user.save()
    return user


class DashboardAccessTest(TestCase):
    """
    Verify that the @guide_required decorator enforces role-based access control
    on dashboard views.

    Covers:
    - GUEST role → 403 Forbidden
    - GUIDE, OPERATOR, ADMIN roles → 200 OK
    - Django staff (is_staff=True) → 200 OK regardless of UserProfile role
    - Unauthenticated request → 302 redirect to login
    - Correct template rendered for authorised access
    """

    def test_guest_cannot_access_dashboard(self):
        """Guests get 403 forbidden."""
        user = make_user('guest@test.com', UserProfile.Role.GUEST)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 403)

    def test_guide_can_access_dashboard(self):
        """GUIDE-role users receive a 200 response on the tours list."""
        user = make_user('guide@test.com', UserProfile.Role.GUIDE)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_operator_can_access_dashboard(self):
        """OPERATOR-role users receive a 200 response on the tours list."""
        user = make_user('op@test.com', UserProfile.Role.OPERATOR)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_role_can_access_dashboard(self):
        """ADMIN-role users (UserProfile.role, not is_staff) receive a 200 response."""
        user = make_user('admin@test.com', UserProfile.Role.ADMIN)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_staff_can_access_dashboard(self):
        """Django staff users (is_staff=True) bypass role checks and get 200."""
        user = make_user('staff@test.com', is_staff=True)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 200)

    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated requests are redirected (302) to the accounts login URL."""
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/', resp['Location'])

    def test_tours_list_renders_template(self):
        """Authorised guide requests render the expected tours list template."""
        user = make_user('guide2@test.com', UserProfile.Role.GUIDE)
        self.client.force_login(user)
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertTemplateUsed(resp, 'admin_panel/tours/list.html')
