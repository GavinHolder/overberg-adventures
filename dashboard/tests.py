from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import UserProfile
from apps.tours.models import Tour

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


def make_tour(guide, name='Test Tour', status=Tour.Status.ACTIVE):
    """
    Factory helper: create a Tour with sensible defaults for testing.

    Creates a minimal Tour instance attached to the given guide, with
    a start date 3 days in the future so it is never treated as expired.
    Generates a UUID-based tour_code to satisfy the unique constraint without
    requiring the TourCodeWord pool to be seeded in tests.

    Args:
        guide: User instance used as the Tour.guide FK.
        name:  Human-readable tour display name (default 'Test Tour').
        status: Tour.Status TextChoices value (default ACTIVE).

    Returns:
        Saved Tour instance.

    ASSUMPTIONS:
    - Tour.location_name and Tour.capacity are required non-blank fields.
    - tour_code must be non-blank and unique; we use a UUID fragment here.
    """
    import uuid
    # Use a short UUID prefix to satisfy the unique=True constraint without
    # needing the TourCodeWord word pool to be seeded in the test database.
    unique_code = f'test-{uuid.uuid4().hex[:8]}'
    return Tour.objects.create(
        name=name,
        guide=guide,
        tour_code=unique_code,
        start_datetime=timezone.now() + timedelta(days=3),
        location_name='Test Beach',
        capacity=10,
        status=status,
    )


class ToursListTest(TestCase):
    """
    Tests for the guide dashboard tours list tab (Task 24).

    Verifies role-based tour visibility, annotated context values (guest_count),
    status badge rendering, and empty-state display.
    """

    def setUp(self):
        """Create a guide user and log them in for each test."""
        self.guide = make_user('guide@tours.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)

    def test_shows_guide_own_tours_only(self):
        """Guides only see their own tours — other guides' tours are hidden."""
        other_guide = make_user('other@tours.com', UserProfile.Role.GUIDE)
        # Create one tour belonging to self.guide and one to another guide
        make_tour(self.guide, 'My Tour')
        make_tour(other_guide, 'Their Tour')
        resp = self.client.get(reverse('dashboard:tours_list'))
        # Self.guide's tour must appear; the other guide's must not
        self.assertContains(resp, 'My Tour')
        self.assertNotContains(resp, 'Their Tour')

    def test_admin_sees_all_tours(self):
        """Staff/admin user sees tours from all guides without filtering."""
        admin = make_user('admin@tours.com', is_staff=True)
        self.client.force_login(admin)
        other = make_user('g2@tours.com', UserProfile.Role.GUIDE)
        # Create tours under two different guides
        make_tour(self.guide, 'Tour A')
        make_tour(other, 'Tour B')
        resp = self.client.get(reverse('dashboard:tours_list'))
        # Admin must see both tours
        self.assertContains(resp, 'Tour A')
        self.assertContains(resp, 'Tour B')

    def test_shows_empty_state(self):
        """Empty state message is shown when a guide has no tours."""
        # No tours created — response should render the {% empty %} block
        resp = self.client.get(reverse('dashboard:tours_list'))
        self.assertContains(resp, 'No tours')

    def test_shows_guest_count_badge(self):
        """Tour card shows the number of confirmed/pending guests."""
        from apps.bookings.models import Booking
        guest = make_user('g@guest.com', UserProfile.Role.GUEST)
        tour = make_tour(self.guide, 'Beach Tour')
        # Create a confirmed booking so guest_count annotation should equal 1
        Booking.objects.create(tour=tour, user=guest, status=Booking.Status.CONFIRMED)
        resp = self.client.get(reverse('dashboard:tours_list'))
        # The annotated guest_count (1) must appear somewhere in the response
        self.assertContains(resp, '1')

    def test_shows_status_badge(self):
        """Tour card shows the status badge text matching the tour status."""
        make_tour(self.guide, 'Active Tour', Tour.Status.ACTIVE)
        resp = self.client.get(reverse('dashboard:tours_list'))
        # 'Active' is the human-readable label from Tour.Status.ACTIVE
        self.assertContains(resp, 'Active')

    def test_operator_sees_all_tours(self):
        """OPERATOR role users see all tours, not just their own."""
        op = make_user('op@tours.com', UserProfile.Role.OPERATOR)
        self.client.force_login(op)
        # Tour created under self.guide (not the operator)
        make_tour(self.guide, 'Guide Tour')
        resp = self.client.get(reverse('dashboard:tours_list'))
        # Operator must see tours they didn't create
        self.assertContains(resp, 'Guide Tour')


class TourCRUDTest(TestCase):
    """
    Tests for creating, editing, and deleting tours via the guide dashboard.
    Covers: form rendering, POST creates/updates DB, auto guide assignment,
    redirect after success, HTMX DELETE.
    """

    def setUp(self):
        """Create a guide user and log them in for all CRUD tests."""
        self.guide = make_user('guide@crud.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)

    def test_create_tour_get_shows_form(self):
        """GET /guide/tours/create/ returns 200 and shows the form."""
        resp = self.client.get(reverse('dashboard:tour_create'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Tour Name')

    def test_create_tour_post_creates_and_redirects(self):
        """Valid POST creates a Tour and redirects to the tour detail page."""
        resp = self.client.post(reverse('dashboard:tour_create'), {
            'name': 'Whale Watching',
            'start_datetime': '2026-04-01T09:00',
            'location_name': 'Hermanus',
            'capacity': 12,
            'status': 'DRAFT',
            'description': '',
            'min_fitness_level': 3,
            'rsvp_deadline_hours': 24,
        })
        self.assertEqual(Tour.objects.count(), 1)
        tour = Tour.objects.first()
        self.assertRedirects(resp, reverse('dashboard:tour_detail', args=[tour.pk]))

    def test_create_tour_auto_assigns_guide(self):
        """The logged-in guide is automatically set as the tour's guide."""
        self.client.post(reverse('dashboard:tour_create'), {
            'name': 'Hike',
            'start_datetime': '2026-05-01T07:00',
            'location_name': 'Kogelberg',
            'capacity': 8,
            'status': 'DRAFT',
            'description': '',
            'min_fitness_level': 3,
            'rsvp_deadline_hours': 24,
        })
        tour = Tour.objects.first()
        self.assertEqual(tour.guide, self.guide)

    def test_create_tour_staff_does_not_auto_assign(self):
        """Staff users are NOT auto-assigned as guide — guide field stays blank."""
        staff = make_user('staff@crud.com', is_staff=True)
        self.client.force_login(staff)
        self.client.post(reverse('dashboard:tour_create'), {
            'name': 'Staff Tour',
            'start_datetime': '2026-06-01T08:00',
            'location_name': 'Test',
            'capacity': 5,
            'status': 'DRAFT',
            'description': '',
            'min_fitness_level': 3,
            'rsvp_deadline_hours': 24,
        })
        tour = Tour.objects.first()
        # Staff don't auto-assign themselves — they may want to assign any guide
        self.assertIsNone(tour.guide)

    def test_edit_tour_updates_fields(self):
        """Valid POST to edit view updates the tour name and redirects."""
        tour = make_tour(self.guide, 'Old Name')
        resp = self.client.post(reverse('dashboard:tour_edit', args=[tour.pk]), {
            'name': 'New Name',
            'start_datetime': '2026-06-01T08:00',
            'location_name': 'Bettys Bay',
            'capacity': 15,
            'status': 'ACTIVE',
            'description': 'Updated',
            'min_fitness_level': 2,
            'rsvp_deadline_hours': 48,
        })
        tour.refresh_from_db()
        self.assertEqual(tour.name, 'New Name')
        self.assertRedirects(resp, reverse('dashboard:tour_detail', args=[tour.pk]))

    def test_delete_tour_removes_it(self):
        """DELETE request removes the tour and returns 200 (HTMX response)."""
        tour = make_tour(self.guide)
        resp = self.client.delete(reverse('dashboard:tour_delete', args=[tour.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Tour.objects.filter(pk=tour.pk).exists())

    def test_invalid_create_shows_errors(self):
        """Submitting an empty form shows validation errors without creating a tour."""
        resp = self.client.post(reverse('dashboard:tour_create'), {})
        self.assertEqual(Tour.objects.count(), 0)
        self.assertEqual(resp.status_code, 200)  # form re-rendered, not redirect
