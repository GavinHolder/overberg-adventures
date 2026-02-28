from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import UserProfile
from apps.tours.models import Tour, ItineraryItem, ActivityCategory
from datetime import time as dtime

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


class TourDetailTest(TestCase):
    """
    Tests for the tour detail view (Task 26).
    Covers: rendering, sub-tab presence, tour code display,
    capacity stats, and guide ownership enforcement.
    """

    def setUp(self):
        """Create a guide and a tour they own."""
        self.guide = make_user('guide@detail.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)
        self.tour = make_tour(self.guide, 'Detail Tour')

    def test_detail_shows_tour_name(self):
        """Tour detail page renders with the tour name visible."""
        resp = self.client.get(reverse('dashboard:tour_detail', args=[self.tour.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Detail Tour')

    def test_detail_shows_sub_tabs(self):
        """All three sub-tabs (Itinerary, Guests, Overview) are rendered."""
        resp = self.client.get(reverse('dashboard:tour_detail', args=[self.tour.pk]))
        self.assertContains(resp, 'Itinerary')
        self.assertContains(resp, 'Guests')
        self.assertContains(resp, 'Overview')

    def test_detail_shows_tour_code(self):
        """Tour code is displayed on the overview tab (default shown on detail load)."""
        resp = self.client.get(
            reverse('dashboard:tour_detail', args=[self.tour.pk]),
            {'tab': 'overview'}
        )
        self.assertContains(resp, self.tour.tour_code)

    def test_detail_shows_capacity(self):
        """Capacity number is visible on the overview tab."""
        resp = self.client.get(
            reverse('dashboard:tour_detail', args=[self.tour.pk]),
            {'tab': 'overview'}
        )
        self.assertContains(resp, str(self.tour.capacity))

    def test_guide_cannot_access_other_guide_tour(self):
        """A guide cannot view another guide's tour detail — returns 403."""
        other = make_user('other@detail.com', UserProfile.Role.GUIDE)
        other_tour = make_tour(other, 'Other Tour')
        resp = self.client.get(reverse('dashboard:tour_detail', args=[other_tour.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_staff_can_access_any_tour(self):
        """Staff can access any tour's detail regardless of guide ownership."""
        staff = make_user('staff@detail.com', is_staff=True)
        self.client.force_login(staff)
        resp = self.client.get(reverse('dashboard:tour_detail', args=[self.tour.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_default_tab_is_itinerary(self):
        """Without ?tab=, the itinerary tab is active by default."""
        resp = self.client.get(reverse('dashboard:tour_detail', args=[self.tour.pk]))
        self.assertContains(resp, 'itinerary')


def make_category(name='Hike'):
    """Factory: create an ActivityCategory with minimal required fields."""
    return ActivityCategory.objects.create(name=name, icon='geo-alt', colour='#198754')


class ItineraryBuilderTest(TestCase):
    """
    Tests for the itinerary builder (Task 27).
    Covers: add item, HTMX partial response, edit, delete, reorder,
    and ownership enforcement (guides can't edit other guides' tours).
    """

    def setUp(self):
        """Create a guide, log them in, create their tour and a category."""
        self.guide = make_user('guide@itinerary.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)
        self.tour = make_tour(self.guide)
        self.category = make_category()

    def _item_data(self, title='Morning Hike', day=1, order=0):
        """Helper: return valid POST data for an ItineraryItem."""
        return {
            'title': title,
            'day': day,
            'order': order,
            'start_time': '07:00',
            'duration_minutes': 120,
            'category': self.category.pk,
            'location_name': 'Kogelberg Peak',
            'description': '',
            'difficulty': 'MODERATE',
        }

    def test_add_item_creates_itinerary_item(self):
        """POST to itinerary_add creates an ItineraryItem linked to the tour."""
        self.client.post(
            reverse('dashboard:itinerary_add', args=[self.tour.pk]),
            self._item_data('Morning Hike'),
        )
        self.assertEqual(ItineraryItem.objects.count(), 1)
        item = ItineraryItem.objects.first()
        self.assertEqual(item.title, 'Morning Hike')
        self.assertEqual(item.tour, self.tour)

    def test_add_item_htmx_returns_partial(self):
        """HTMX request returns the item row partial (not a full page)."""
        resp = self.client.post(
            reverse('dashboard:itinerary_add', args=[self.tour.pk]),
            self._item_data('Beach Walk'),
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Beach Walk')

    def test_edit_item_updates_title(self):
        """POST to itinerary_edit updates the item's title in the DB."""
        item = ItineraryItem.objects.create(
            tour=self.tour, title='Old Title', day=1, order=0,
            start_time=dtime(8, 0), duration_minutes=60, difficulty='EASY',
            category=self.category,
        )
        self.client.post(
            reverse('dashboard:itinerary_edit', args=[self.tour.pk, item.pk]),
            self._item_data('New Title'),
        )
        item.refresh_from_db()
        self.assertEqual(item.title, 'New Title')

    def test_delete_item_removes_it(self):
        """DELETE request removes the ItineraryItem and returns 200."""
        item = ItineraryItem.objects.create(
            tour=self.tour, title='To Delete', day=1, order=0,
            start_time=dtime(8, 0), duration_minutes=30, difficulty='EASY',
        )
        resp = self.client.delete(
            reverse('dashboard:itinerary_delete', args=[self.tour.pk, item.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ItineraryItem.objects.filter(pk=item.pk).exists())

    def test_reorder_updates_order_field(self):
        """POST to itinerary_reorder with JSON payload updates item order values."""
        import json
        item1 = ItineraryItem.objects.create(
            tour=self.tour, title='Item 1', day=1, order=0,
            start_time=dtime(8, 0), duration_minutes=30, difficulty='EASY',
        )
        item2 = ItineraryItem.objects.create(
            tour=self.tour, title='Item 2', day=1, order=1,
            start_time=dtime(9, 0), duration_minutes=30, difficulty='EASY',
        )
        # Swap the order
        resp = self.client.post(
            reverse('dashboard:itinerary_reorder', args=[self.tour.pk]),
            data=json.dumps([
                {'id': item1.pk, 'order': 1},
                {'id': item2.pk, 'order': 0},
            ]),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        item1.refresh_from_db()
        item2.refresh_from_db()
        self.assertEqual(item1.order, 1)
        self.assertEqual(item2.order, 0)

    def test_guide_cannot_edit_other_tour_item(self):
        """A guide gets 403 when trying to edit an item on another guide's tour."""
        other = make_user('other@itinerary.com', UserProfile.Role.GUIDE)
        other_tour = make_tour(other)
        item = ItineraryItem.objects.create(
            tour=other_tour, title='Restricted', day=1, order=0,
            start_time=dtime(9, 0), duration_minutes=60, difficulty='EASY',
        )
        resp = self.client.post(
            reverse('dashboard:itinerary_edit', args=[other_tour.pk, item.pk]),
            self._item_data('Hacked'),
        )
        self.assertEqual(resp.status_code, 403)


from apps.bookings.models import Booking


class GuestManifestTest(TestCase):
    """
    Tests for the guest manifest tab on the tour detail page (Task 28).
    Covers: enrolled guests display, empty state, RSVP status badge,
    dietary info, medical info visibility.
    """

    def setUp(self):
        """Create a guide, their tour, and log in as guide."""
        self.guide = make_user('guide@guests.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)
        self.tour = make_tour(self.guide)

    def _get_guests_tab(self):
        """Helper: GET the guests tab on the tour detail page."""
        return self.client.get(
            reverse('dashboard:tour_detail', args=[self.tour.pk]),
            {'tab': 'guests'}
        )

    def test_guests_tab_shows_enrolled_guest_name(self):
        """Confirmed guests are listed by full name on the guests tab."""
        guest = make_user('guest@manifest.com', UserProfile.Role.GUEST)
        guest.profile.first_name = 'Alice'
        guest.profile.last_name = 'Botha'
        guest.profile.save()
        Booking.objects.create(tour=self.tour, user=guest, status=Booking.Status.CONFIRMED)
        resp = self._get_guests_tab()
        self.assertContains(resp, 'Alice')

    def test_guests_tab_shows_empty_state(self):
        """Empty state message is shown when no guests are enrolled."""
        resp = self._get_guests_tab()
        self.assertContains(resp, 'No guests')

    def test_guests_tab_shows_rsvp_status_badge(self):
        """RSVP_PENDING guests show a pending badge."""
        guest = make_user('rsvp@manifest.com', UserProfile.Role.GUEST)
        Booking.objects.create(tour=self.tour, user=guest, status=Booking.Status.RSVP_PENDING)
        resp = self._get_guests_tab()
        self.assertContains(resp, 'RSVP')

    def test_guests_tab_shows_dietary_requirements(self):
        """Dietary requirements are visible on the guest manifest."""
        guest = make_user('diet@manifest.com', UserProfile.Role.GUEST)
        guest.profile.dietary_requirements = 'Vegan'
        guest.profile.save()
        Booking.objects.create(tour=self.tour, user=guest, status=Booking.Status.CONFIRMED)
        resp = self._get_guests_tab()
        self.assertContains(resp, 'Vegan')

    def test_guests_tab_shows_medical_conditions(self):
        """Medical conditions are visible so guides can prepare."""
        guest = make_user('med@manifest.com', UserProfile.Role.GUEST)
        guest.profile.medical_conditions = 'Asthma'
        guest.profile.save()
        Booking.objects.create(tour=self.tour, user=guest, status=Booking.Status.CONFIRMED)
        resp = self._get_guests_tab()
        self.assertContains(resp, 'Asthma')

    def test_guests_tab_shows_guest_count(self):
        """The enrolled guest count is displayed."""
        guest1 = make_user('g1@manifest.com', UserProfile.Role.GUEST)
        guest2 = make_user('g2@manifest.com', UserProfile.Role.GUEST)
        Booking.objects.create(tour=self.tour, user=guest1, status=Booking.Status.CONFIRMED)
        Booking.objects.create(tour=self.tour, user=guest2, status=Booking.Status.RSVP_PENDING)
        resp = self._get_guests_tab()
        self.assertContains(resp, '2 enrolled')


class ActivityLibraryTest(TestCase):
    """
    Tests for the Activity Library tab (Task 29).
    Covers: list display, create, edit, delete operations on ActivityCategory.
    """

    def setUp(self):
        """Create a guide user and log them in."""
        self.guide = make_user('guide@activities.com', UserProfile.Role.GUIDE)
        self.client.force_login(self.guide)

    def test_activities_list_shows_category_names(self):
        """Activity categories are listed by name."""
        ActivityCategory.objects.create(name='Hiking', icon='geo-alt', colour='#198754')
        resp = self.client.get(reverse('dashboard:activities_list'))
        self.assertContains(resp, 'Hiking')

    def test_activities_list_empty_state(self):
        """Empty state is shown when no categories exist."""
        resp = self.client.get(reverse('dashboard:activities_list'))
        self.assertContains(resp, 'No activity categories')

    def test_create_category_post_creates_record(self):
        """POST to activity_create creates an ActivityCategory record."""
        resp = self.client.post(reverse('dashboard:activity_create'), {
            'name': 'Snorkelling',
            'icon': 'water',
            'colour': '#0d6efd',
            'is_active': True,
            'order': 0,
        })
        self.assertTrue(ActivityCategory.objects.filter(name='Snorkelling').exists())

    def test_create_category_redirects_on_success(self):
        """Successful POST redirects to the activities list."""
        resp = self.client.post(reverse('dashboard:activity_create'), {
            'name': 'Kayaking',
            'icon': 'water',
            'colour': '#0d9488',
            'is_active': True,
            'order': 1,
        })
        self.assertRedirects(resp, reverse('dashboard:activities_list'))

    def test_edit_category_updates_name(self):
        """POST to activity_edit updates the category name in the DB."""
        cat = ActivityCategory.objects.create(name='Old Cat', icon='star', colour='#F97316')
        self.client.post(reverse('dashboard:activity_edit', args=[cat.pk]), {
            'name': 'New Cat',
            'icon': 'star',
            'colour': '#F97316',
            'is_active': True,
            'order': 0,
        })
        cat.refresh_from_db()
        self.assertEqual(cat.name, 'New Cat')

    def test_delete_category_removes_record(self):
        """DELETE request removes the ActivityCategory record."""
        cat = ActivityCategory.objects.create(name='Wine Tasting', icon='cup', colour='#6f42c1')
        resp = self.client.delete(reverse('dashboard:activity_delete', args=[cat.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ActivityCategory.objects.filter(pk=cat.pk).exists())

    def test_create_invalid_colour_shows_error(self):
        """Invalid hex colour fails validation and does not create a record."""
        resp = self.client.post(reverse('dashboard:activity_create'), {
            'name': 'Bad Colour',
            'icon': 'star',
            'colour': 'not-a-colour',
            'is_active': True,
            'order': 0,
        })
        self.assertFalse(ActivityCategory.objects.filter(name='Bad Colour').exists())
        self.assertEqual(resp.status_code, 200)  # form re-rendered


class GuidesTabTest(TestCase):
    """
    Tests for the Guides tab (Task 30).
    Covers: list displays guide/operator/admin profiles, excludes guests,
    staff-only restriction, role editing.
    """

    def setUp(self):
        """Create a staff user (required for guides tab access)."""
        self.admin = make_user('admin@guides.com', is_staff=True)
        self.client.force_login(self.admin)

    def test_guides_list_shows_guide_users(self):
        """Guide-role users appear in the guides list."""
        guide = make_user('g1@guides.com', UserProfile.Role.GUIDE)
        guide.profile.first_name = 'Bob'
        guide.profile.save()
        resp = self.client.get(reverse('dashboard:guides_list'))
        self.assertContains(resp, 'Bob')

    def test_guides_list_excludes_guests(self):
        """Guest-role users do NOT appear in the guides list."""
        guest = make_user('guest@guides.com', UserProfile.Role.GUEST)
        guest.profile.first_name = 'GuestOnly'
        guest.profile.save()
        resp = self.client.get(reverse('dashboard:guides_list'))
        self.assertNotContains(resp, 'GuestOnly')

    def test_edit_guide_role_updates_profile(self):
        """POST to guide_edit updates the UserProfile role."""
        guide = make_user('edit@guides.com', UserProfile.Role.GUIDE)
        resp = self.client.post(
            reverse('dashboard:guide_edit', args=[guide.profile.pk]),
            {
                'role': 'OPERATOR',
                'first_name': guide.profile.first_name,
                'last_name': guide.profile.last_name,
                'phone_whatsapp': guide.profile.phone_whatsapp,
            }
        )
        guide.profile.refresh_from_db()
        self.assertEqual(guide.profile.role, 'OPERATOR')

    def test_edit_guide_redirects_on_success(self):
        """Successful role edit redirects to the guides list."""
        guide = make_user('redirect@guides.com', UserProfile.Role.GUIDE)
        resp = self.client.post(
            reverse('dashboard:guide_edit', args=[guide.profile.pk]),
            {
                'role': 'GUIDE',
                'first_name': 'Test',
                'last_name': 'Guide',
                'phone_whatsapp': '',
            }
        )
        self.assertRedirects(resp, reverse('dashboard:guides_list'))

    def test_non_staff_cannot_access_guides_tab(self):
        """Regular guides (non-staff) cannot access the guides management tab."""
        guide = make_user('regularguide@test.com', UserProfile.Role.GUIDE)
        self.client.force_login(guide)
        resp = self.client.get(reverse('dashboard:guides_list'))
        self.assertEqual(resp.status_code, 403)

    def test_guides_list_shows_operator_users(self):
        """OPERATOR-role users also appear in the guides list."""
        op = make_user('op@guides.com', UserProfile.Role.OPERATOR)
        op.profile.first_name = 'OpUser'
        op.profile.save()
        resp = self.client.get(reverse('dashboard:guides_list'))
        self.assertContains(resp, 'OpUser')
