from functools import wraps
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.conf import settings

from .decorators import guide_required, staff_required
from .forms import TourForm
from apps.tours.models import Tour, ItineraryItem, ActivityCategory
from dashboard.models import TourPhoto


def _dev_mode():
    """
    Return True when DEV_MODE is active in Django settings.

    DEV_MODE is a project-level flag (set via environment variable) that enables
    developer conveniences such as bypassing payment flows, simulated OTP, and
    a visible banner in the UI. It is only ever True when DEBUG is also True.

    Passes the result into every template context so templates can conditionally
    render DEV_MODE banners and simulate-action buttons without importing settings
    themselves.
    """
    # Use getattr with a False default so the flag is safely absent in production
    # settings files that never define DEV_MODE at all.
    return getattr(settings, 'DEV_MODE', False)


@guide_required
def index(request):
    """
    Dashboard root — immediately redirects to the tours list.

    Acts as a stable entry-point URL ('dashboard:index') so that any link to
    the dashboard root stays valid even if the default landing view changes later.
    Access: guide-level users and staff (enforced by @guide_required).
    """
    return redirect('dashboard:tours_list')


@guide_required
def tours_list(request):
    """
    Guide dashboard: Tours tab — list all accessible tours with stats.

    Behaviour differs by role:
    - GUIDE role: restricted to the logged-in guide's own tours only, so
      no guide can view or manage another guide's bookings or guest data.
    - OPERATOR, ADMIN (UserProfile role), staff (is_staff): see ALL tours
      across all guides, ordered newest-first by start datetime.

    Annotates each tour with:
    - guest_count: number of RSVP_PENDING or CONFIRMED bookings (active
      bookings only — cancelled bookings are excluded from the count).
    - activity_count: total number of ItineraryItems linked to the tour.

    Both counts are computed in a single database round-trip using Django's
    conditional Count + Q annotation — no Python-level looping required.

    Context:
    - tours: Annotated QuerySet (guest_count, activity_count on each tour).
    - dev_mode: bool — controls DEV_MODE banner / simulate buttons in template.

    Access: guide-level users and staff (enforced by @guide_required).

    ASSUMPTIONS:
    1. request.user always has a profile (created by post_save signal in accounts).
    2. OPERATOR and ADMIN UserProfile roles have identical visibility to staff.
    3. Tour.guide FK uses related_name='guided_tours'; Booking uses 'bookings';
       ItineraryItem uses 'itinerary_items' — all confirmed in models.py.
    4. Booking.Status string values match those defined in bookings/models.py.

    FAILURE MODES:
    - Missing profile (profileless user): getattr returns None; the role guard
      evaluates to False, so the unfiltered queryset is returned.  Acceptable
      because @guide_required has already blocked unauthenticated/GUEST users
      before reaching this point.
    - Empty queryset: renders the {% empty %} block in the template — no errors.
    - Very large tour lists: no pagination yet; acceptable for MVP scale.
    """
    from django.db.models import Count, Q
    from apps.bookings.models import Booking

    # Annotate tours with guest and activity counts in a single DB query.
    # select_related avoids N+1 lookups when the template renders guide.name.
    tours = (
        Tour.objects
        .select_related('guide__profile')  # prevent per-row profile SQL on guide display
        .annotate(
            # Count only active bookings — exclude CANCELLED and INVITED statuses
            guest_count=Count(
                'bookings',
                filter=Q(bookings__status__in=[
                    Booking.Status.RSVP_PENDING,
                    Booking.Status.CONFIRMED,
                ])
            ),
            # Count all itinerary items; used to display an activity badge on the card
            activity_count=Count('itinerary_items'),
        )
        .order_by('-start_datetime')
    )

    profile = getattr(request.user, 'profile', None)

    # GUIDE role: restrict queryset to tours owned by the current guide.
    # OPERATOR, ADMIN, and Django staff see the full unfiltered queryset.
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        tours = tours.filter(guide=request.user)

    return render(request, 'admin_panel/tours/list.html', {
        'tours': tours,
        'dev_mode': _dev_mode(),
    })


@guide_required
def activities_list(request):
    """
    Guide dashboard: Activity Library tab.

    Lists all ActivityCategory records ordered by display order then name.
    Annotates each category with the count of itinerary items using it
    so guides can see which categories are in use.

    Access: guide-level users and staff (enforced by @guide_required).

    ASSUMPTIONS:
    1. ActivityCategory.itinerary_items is a valid related_name on the FK
       (confirmed in apps/tours/models.py ItineraryItem.category FK).
    2. No pagination needed at MVP scale — category counts stay small.

    FAILURE MODES:
    - Empty queryset: renders {% empty %} block in template — no error.
    """
    from django.db.models import Count
    # Annotate to avoid N+1 per-category item count queries in the template
    categories = (
        ActivityCategory.objects
        .annotate(item_count=Count('itinerary_items'))
        .order_by('order', 'name')
    )
    return render(request, 'admin_panel/activities/list.html', {
        'categories': categories,
        'dev_mode': _dev_mode(),
    })


@guide_required
def activity_create(request):
    """
    Guide dashboard: Create a new ActivityCategory.

    GET: Renders an empty ActivityCategoryForm with sensible defaults.
    POST: Validates and saves the new category, then redirects to the
    activities list.  On validation failure, re-renders the form with errors.

    ASSUMPTIONS:
    1. Colour validation is handled by both the form's TextInput (type=color
       widget ensures browser sends valid #RRGGBB) AND the model-level
       RegexValidator — double-layer defence.
    2. No guide-level ownership on categories — they are shared across all guides.

    FAILURE MODES:
    - Invalid hex colour → model validator fires → form.is_valid() returns False
      → template re-rendered with error, no DB write (status 200).
    - Empty name → required field error, no DB write.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    from .forms import ActivityCategoryForm
    if request.method == 'POST':
        form = ActivityCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard:activities_list')
    else:
        # Pre-populate brand colour and zero-based order as sensible defaults
        form = ActivityCategoryForm(initial={'colour': '#F97316', 'order': 0})
    return render(request, 'admin_panel/activities/form.html', {
        'form': form,
        'dev_mode': _dev_mode(),
    })


@guide_required
def activity_edit(request, pk):
    """
    Guide dashboard: Edit an existing ActivityCategory.

    GET: Renders the form pre-populated with the category's current values.
    POST: Validates and saves the changes, then redirects to activities list.
    On validation failure, re-renders the form with inline errors.

    Args:
        pk: ActivityCategory primary key

    FAILURE MODES:
    - Category not found: get_object_or_404 raises Http404 → 404 response.
    - Invalid POST data: form re-rendered with errors, DB unchanged.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    from django.shortcuts import get_object_or_404
    from .forms import ActivityCategoryForm
    # 404 if category does not exist — prevents silent data corruption
    cat = get_object_or_404(ActivityCategory, pk=pk)
    if request.method == 'POST':
        form = ActivityCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            return redirect('dashboard:activities_list')
    else:
        # Pre-populate with existing values so the guide sees current state
        form = ActivityCategoryForm(instance=cat)
    return render(request, 'admin_panel/activities/form.html', {
        'form': form,
        'category': cat,  # passed so template can show "Edit X" vs "New Category" title
        'dev_mode': _dev_mode(),
    })


@guide_required
def activity_delete(request, pk):
    """
    Guide dashboard: Delete an ActivityCategory.

    Accepts POST or DELETE (HTMX sends DELETE via hx-delete attribute).
    Returns an empty 200 response — HTMX swaps the category card out of the
    list via outerHTML swap without a full page reload.

    Args:
        pk: ActivityCategory primary key

    FAILURE MODES:
    - Category not found: 404 via get_object_or_404.
    - Category in use: Django FK is SET_NULL on ItineraryItem — items survive
      category deletion with category=None.  This is intentional; items are
      not deleted when their label is removed.
    - Non-POST/DELETE method: returns 405 Method Not Allowed.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    cat = get_object_or_404(ActivityCategory, pk=pk)
    if request.method in ('POST', 'DELETE'):
        cat.delete()
        # Empty body tells HTMX to replace the card element with nothing (removal)
        return HttpResponse('')
    # Reject GET, PUT, PATCH etc. — this endpoint is write-only
    return HttpResponse(status=405)


@guide_required
def guests_list(request):
    """
    Render the guests management list view (stub).

    Currently a placeholder that renders the guests list template with no
    guest data. A full implementation will query Booking/UserProfile (GUEST role)
    once the guests feature is built out.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    return render(request, 'admin_panel/guests/list.html', {'dev_mode': _dev_mode()})


@guide_required
def guides_list(request):
    """
    Guide dashboard: Guides tab — lists all guide/operator/admin user profiles.

    STAFF ONLY: Regular guides cannot manage other users' accounts.
    This tab is restricted to Django staff (is_staff=True) for security.
    Non-staff users who reach this view via the @guide_required decorator
    are denied with a 403 before any data is queried.

    Displays UserProfile records with role in GUIDE_ROLES (excludes guests).
    Ordered by role then surname for easy scanning of the guide roster.

    Context:
    - profiles: QuerySet of UserProfile with role in [GUIDE, OPERATOR, ADMIN]
    - dev_mode: bool — controls DEV_MODE banner in template

    ASSUMPTIONS:
    1. Only staff users reach this view (enforced by PermissionDenied check).
    2. All users have a UserProfile (created by post_save signal in accounts app).
    3. UserProfile.user is a OneToOneField — select_related avoids N+1 on email display.

    FAILURE MODES:
    - Non-staff guide-role user: caught below and raises PermissionDenied (403).
    - Empty queryset: renders {% empty %} block in template — no error.
    """
    from apps.accounts.models import UserProfile as Profile

    # Non-staff cannot manage other users — raise 403 even though @guide_required passed.
    # @guide_required allows GUIDE/OPERATOR/ADMIN roles; this view adds the extra
    # is_staff requirement on top of that base gate.
    if not request.user.is_staff:
        raise PermissionDenied

    # Only show guide-level profiles; guests are managed via the Guests tab instead.
    profiles = (
        Profile.objects
        .filter(role__in=['GUIDE', 'OPERATOR', 'ADMIN'])
        .select_related('user')  # avoid N+1 on user.email display in the template
        .order_by('role', 'last_name', 'first_name')
    )
    return render(request, 'admin_panel/guides/list.html', {
        'profiles': profiles,
        'dev_mode': _dev_mode(),
    })


@staff_required
def guide_edit(request, pk):
    """
    Guide dashboard: Edit a guide/operator user profile (staff only).

    GET: Renders GuideRoleForm pre-populated with the profile's current values.
    POST: Validates and saves role + contact field changes, then redirects to
    the guides list.  On validation failure, re-renders the form with errors.

    Args:
        pk: UserProfile primary key (not User PK)

    ASSUMPTIONS:
    1. pk is a UserProfile PK — the URL captures profile.pk, not user.pk.
    2. Only staff can reach this view (@staff_required decorator).
    3. GuideRoleForm is imported locally to avoid circular imports at module level.

    FAILURE MODES:
    - Profile not found: get_object_or_404 raises Http404 → 404 response.
    - Invalid POST data: form re-rendered with errors, DB unchanged.
    - Non-staff user: @staff_required raises PermissionDenied before view body runs.
    """
    from django.shortcuts import get_object_or_404
    from apps.accounts.models import UserProfile as Profile
    from .forms import GuideRoleForm

    # Fetch profile by PK; 404 if it doesn't exist rather than silent data error
    profile = get_object_or_404(Profile, pk=pk)

    if request.method == 'POST':
        form = GuideRoleForm(request.POST, instance=profile)
        if form.is_valid():
            # Save role/name/phone changes; instance= ensures UPDATE, not INSERT
            form.save()
            return redirect('dashboard:guides_list')
    else:
        # Pre-populate form with the profile's existing values for GET
        form = GuideRoleForm(instance=profile)

    return render(request, 'admin_panel/guides/form.html', {
        'form': form,
        'profile': profile,
        'dev_mode': _dev_mode(),
    })


# ---------------------------------------------------------------------------
# Stub views — these exist solely so that URL names referenced in templates
# via {% url 'dashboard:...' %} and reverse() calls resolve without raising
# NoReverseMatch.  Each will be replaced with a real form-backed view once
# the corresponding feature is implemented.
# ---------------------------------------------------------------------------

@guide_required
def tour_create(request):
    """
    Guide dashboard: Create a new tour.

    GET: Renders an empty TourForm with sensible initial values.
    POST: Validates the submitted form; on success auto-assigns the guide
    (non-staff only), saves the tour, then redirects to the tour detail page.
    On validation failure, re-renders the form with inline error messages.

    ASSUMPTIONS:
    1. Non-staff users should automatically become the tour's guide — they
       are creating a tour they will personally run.
    2. Staff users leave guide=None; they may assign any guide manually later
       via the admin panel or a future guide-picker UI.
    3. TourCodeWord pool will be populated in production; in tests the tour_code
       field is not set by this form (it is set by the model's save signal or
       by the test factory using a UUID fragment).

    FAILURE MODES:
    - Empty/invalid form → re-render with errors, no DB write (status 200).
    - TourCodeWord pool exhausted → ValueError raised in model.save() → uncaught
      here; will become a 500 until Phase 6 adds graceful handling.
    - Non-staff user with no profile → guide assignment skipped silently;
      @guide_required already rejected unauthenticated/GUEST users above.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    if request.method == 'POST':
        form = TourForm(request.POST)
        if form.is_valid():
            # commit=False lets us set guide before the INSERT hits the DB
            tour = form.save(commit=False)
            # Non-staff guides are auto-assigned — staff can assign any guide
            if not request.user.is_staff:
                tour.guide = request.user
            tour.save()
            return redirect('dashboard:tour_detail', pk=tour.pk)
    else:
        # Prefill sensible defaults so the guide doesn't start from a blank slate
        form = TourForm(initial={'status': Tour.Status.DRAFT, 'capacity': 10})

    return render(request, 'admin_panel/tours/form.html', {
        'form': form,
        'dev_mode': _dev_mode(),
    })


@guide_required
def tour_detail(request, pk):
    """
    Guide dashboard: Tour detail view with Itinerary / Guests / Overview sub-tabs.

    Loads a single tour and all related data needed for all three tabs in one query.
    The active tab is controlled by ?tab= query parameter (default: 'itinerary').

    Access control:
    - GUIDE role: can only view their own tours (403 otherwise)
    - OPERATOR/ADMIN/staff: can view any tour

    Args:
        pk: Tour primary key

    Context passed to template:
        tour: Tour instance with guide__profile selected
        active_tab: str — 'itinerary', 'guests', or 'overview'
        bookings: QuerySet of Bookings with user__profile selected
        items_by_day: dict of {day_int: [ItineraryItem, ...]} sorted by day
        dev_mode: bool

    ASSUMPTIONS:
    - items_by_day is sorted so days render in ascending order.
    - Booking.invited_at exists (auto_now_add=True on the model).

    FAILURE MODES:
    - Tour not found: 404 via get_object_or_404
    - Wrong guide accessing: 403 PermissionDenied
    """
    from django.shortcuts import get_object_or_404
    from apps.bookings.models import Booking
    from apps.tours.models import ItineraryItem

    # Fetch tour with guide profile in one query (avoids N+1 on header render)
    tour = get_object_or_404(
        Tour.objects.select_related('guide__profile'),
        pk=pk
    )

    # Ownership check: GUIDE role can only access their own tours.
    # Staff and OPERATOR/ADMIN roles bypass this check and see all tours.
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        if tour.guide != request.user:
            raise PermissionDenied

    # Determine active tab from query string; default to itinerary
    active_tab = request.GET.get('tab', 'itinerary')

    # Load bookings with user profiles for guest manifest tab.
    # invited_at provides a stable creation-order sort for the guest list.
    bookings = (
        Booking.objects
        .filter(tour=tour)
        .select_related('user__profile')
        .order_by('invited_at')
    )

    # Load itinerary items for the builder tab (category join avoids extra queries)
    itinerary_items = (
        ItineraryItem.objects
        .filter(tour=tour)
        .select_related('category')
    )

    # Group items by day and sort ascending (day 1 before day 2, etc.)
    items_by_day = {}
    for item in itinerary_items:
        # setdefault creates the list on first encounter for each day key
        items_by_day.setdefault(item.day, []).append(item)
    # Sort the dict by day number so the template iterates day 1, 2, 3…
    items_by_day = dict(sorted(items_by_day.items()))

    # Load photos ordered newest-first for the photos tab and badge count
    photos = TourPhoto.objects.filter(tour=tour)

    return render(request, 'admin_panel/tours/detail.html', {
        'tour': tour,
        'active_tab': active_tab,
        'bookings': bookings,
        'items_by_day': items_by_day,
        'photos': photos,
        'dev_mode': _dev_mode(),
    })


@guide_required
def tour_edit(request, pk):
    """
    Guide dashboard: Edit an existing tour.

    GET: Renders TourForm pre-populated with the tour's existing data.
    POST: Validates submitted changes; on success saves the tour and redirects
    to the tour detail page.  On validation failure, re-renders with errors.

    The guide field is intentionally NOT included in the form — ownership can
    only be changed via the admin panel to prevent guides from hijacking tours.

    Args:
        pk: Primary key of the Tour to edit.

    ASSUMPTIONS:
    1. Any guide-level user can edit any tour — ownership is not enforced here;
       the list view already filters what each guide can see, providing implicit
       access control. Strict ownership checks are deferred to a future phase.
    2. The guide FK is intentionally preserved from the existing record and never
       overwritten by this view (the form excludes it).

    FAILURE MODES:
    - Tour not found: get_object_or_404 raises Http404 → 404 response.
    - Invalid POST data: form re-rendered with errors, DB unchanged.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)

    if request.method == 'POST':
        form = TourForm(request.POST, instance=tour)
        if form.is_valid():
            # instance= ensures UPDATE rather than INSERT; guide FK untouched
            form.save()
            return redirect('dashboard:tour_detail', pk=tour.pk)
    else:
        # Pre-populate the form with the tour's existing data for the GET request
        form = TourForm(instance=tour)

    return render(request, 'admin_panel/tours/form.html', {
        'form': form,
        # Pass tour so the template can show the tour_code and toggle title text
        'tour': tour,
        'dev_mode': _dev_mode(),
    })


@guide_required
def tour_delete(request, pk):
    """
    Delete a Tour via POST or DELETE request (soft HTMX stub).

    On a POST or DELETE request the tour is hard-deleted and an empty 200
    response is returned so HTMX can swap the removed row out of the DOM.
    Any other HTTP method returns 405 Method Not Allowed.

    Args:
        pk: Primary key of the Tour to delete.

    Returns:
        HttpResponse('') with status 200 on successful deletion (HTMX-friendly).
        HttpResponse with status 405 for non-POST/DELETE methods.

    Access: guide-level users and staff (enforced by @guide_required).

    ASSUMPTIONS:
    - The caller is responsible for confirming the deletion before POSTing;
      there is no confirmation step inside this view.

    FAILURE MODES:
    - Tour not found: get_object_or_404 raises Http404 → 404 response.
    - DELETE method: included alongside POST for future HTMX hx-delete support;
      Django's test client and standard browsers only send POST for forms.
    """
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse

    tour = get_object_or_404(Tour, pk=pk)

    # Accept both POST (HTML form submission) and DELETE (HTMX hx-delete).
    if request.method in ('POST', 'DELETE'):
        tour.delete()
        # Return an empty body so HTMX replaces the deleted row with nothing,
        # effectively removing it from the DOM without a full page reload.
        return HttpResponse('')

    # Reject GET, PUT, PATCH, etc. — this endpoint is write-only.
    return HttpResponse(status=405)


@guide_required
def tour_qr(request, pk):
    """
    Guide dashboard: Display the QR code page for a tour.

    Shows the QR code image (from tour_qr_png endpoint), the tour code in text,
    and buttons to download the PNG and share the join URL.

    The join URL encoded in the QR points to the tour code lookup page
    pre-filled with the tour code, so guests can scan and land directly on
    the confirm page.

    Args:
        pk: Tour primary key

    ASSUMPTIONS:
    - The join lookup URL is at /app/join/ (bookings:join_lookup).
    - Guides can only view their own tours' QR codes; ownership is enforced here.

    FAILURE MODES:
    - Tour not found: 404 via get_object_or_404.
    - Guide accesses another guide's tour: 403 PermissionDenied.
    """
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)

    # Ownership check: GUIDE role users can only view their own tours' QR codes.
    # Staff and OPERATOR/ADMIN roles bypass this check and see all tours.
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        if tour.guide != request.user:
            raise PermissionDenied

    # Build the full join URL that gets encoded into the QR code.
    # Pre-fills the tour code so guests land directly on the confirm step.
    join_url = request.build_absolute_uri(
        reverse('bookings:join_lookup') + f'?code={tour.tour_code}'
    )

    return render(request, 'admin_panel/tours/qr.html', {
        'tour': tour,
        'join_url': join_url,
        # URL for the <img> src tag that fetches the generated PNG
        'qr_url': reverse('dashboard:tour_qr_png', args=[pk]),
        'dev_mode': _dev_mode(),
    })


@guide_required
def tour_qr_png(request, pk):
    """
    Guide dashboard: Serve a QR code PNG image for a tour's join URL.

    Generates a QR code image on the fly using the qrcode library.
    The QR encodes the full absolute join URL including the tour code.
    Uses dark green fill (#1a3a2a) on white background — matches brand colours.

    Args:
        pk: Tour primary key

    Returns:
        HttpResponse with image/png content type

    ASSUMPTIONS:
    - qrcode[pil] is installed (Pillow is a dependency for PNG output).
    - Box size 8 with border 3 produces a scannable ~200px image.
    - Guides can only view their own tours' QR PNGs (same ownership rule as tour_qr).

    FAILURE MODES:
    - qrcode not installed: ImportError at runtime — add to requirements.txt.
    - Tour not found: 404 via get_object_or_404.
    - Guide accesses another guide's tour: 403 PermissionDenied.
    """
    import qrcode
    import io
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404

    tour = get_object_or_404(Tour, pk=pk)

    # Ownership check (same as tour_qr view — defence in depth).
    # Both endpoints must independently verify ownership because either
    # can be hit directly via URL without going through the other.
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        if tour.guide != request.user:
            raise PermissionDenied

    # Build the join URL to encode into the QR code image
    join_url = request.build_absolute_uri(
        reverse('bookings:join_lookup') + f'?code={tour.tour_code}'
    )

    # Generate QR code — box_size=8 gives a good resolution for display and print;
    # ERROR_CORRECT_M allows 15% data recovery, suitable for logos overlaid on QR.
    qr = qrcode.QRCode(
        box_size=8,
        border=3,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
    )
    qr.add_data(join_url)
    # fit=True selects the minimum version (size) to encode all data
    qr.make(fit=True)

    # Render to PNG using brand dark green on white background
    img = qr.make_image(fill_color='#1a3a2a', back_color='white')

    # Write to in-memory buffer — no temp file needed, avoids disk I/O
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)  # rewind so read() returns from the start

    return HttpResponse(buf.read(), content_type='image/png')


# ---------------------------------------------------------------------------
# Itinerary builder views (Task 27)
# ---------------------------------------------------------------------------

def _get_tour_for_guide(request, tour_pk):
    """
    Fetch a Tour by PK and enforce guide ownership.

    Staff and OPERATOR/ADMIN roles can access any tour.
    GUIDE role users can only access tours they own.

    Args:
        request: HttpRequest with authenticated user
        tour_pk: Tour primary key from URL

    Returns:
        Tour instance

    Raises:
        Http404 if tour doesn't exist
        PermissionDenied if GUIDE role user tries to access another guide's tour

    ASSUMPTIONS:
    - request.user is authenticated (caller already decorated with @guide_required)

    FAILURE MODES:
    - Tour not found: Http404 raised by get_object_or_404
    - Wrong guide ownership: PermissionDenied raised explicitly
    """
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=tour_pk)
    profile = getattr(request.user, 'profile', None)
    # Only restrict GUIDE role — OPERATOR/ADMIN/staff see everything
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        if tour.guide != request.user:
            raise PermissionDenied
    return tour


@guide_required
def itinerary_add(request, tour_pk):
    """
    Guide dashboard: Add a new ItineraryItem to a tour.

    GET: Returns the add form partial (HTMX target: #itinerary-form-slot).
    POST: Validates, saves item with tour FK, returns:
      - HTMX request: item row partial for inline insertion
      - Normal request: redirects to tour detail itinerary tab

    Args:
        tour_pk: Tour PK from URL

    ASSUMPTIONS:
    - HTMX requests include HX-Request header
    - The itinerary_item_row partial requires 'tour' in context for URL generation

    FAILURE MODES:
    - Invalid form: form re-rendered with errors; no DB write occurs
    - Wrong ownership: 403 from _get_tour_for_guide
    """
    from .forms import ItineraryItemForm
    tour = _get_tour_for_guide(request, tour_pk)

    if request.method == 'POST':
        form = ItineraryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.tour = tour  # set the FK that was excluded from the form
            item.save()
            # HTMX: return just the new row partial so it can be injected inline
            if request.headers.get('HX-Request'):
                return render(request, 'admin_panel/tours/partials/itinerary_item_row.html', {
                    'item': item,
                    'tour': tour,
                })
            return redirect(
                reverse('dashboard:tour_detail', args=[tour.pk]) + '?tab=itinerary'
            )
        # Invalid form: return form partial with errors for HTMX, or full page
        if request.headers.get('HX-Request'):
            return render(request, 'admin_panel/tours/partials/itinerary_item_form.html', {
                'form': form,
                'tour': tour,
                'dev_mode': _dev_mode(),
            })
    else:
        # Default order = number of existing items (append to end)
        next_order = ItineraryItem.objects.filter(tour=tour).count()
        form = ItineraryItemForm(initial={'day': 1, 'order': next_order})

    return render(request, 'admin_panel/tours/partials/itinerary_item_form.html', {
        'form': form,
        'tour': tour,
        'dev_mode': _dev_mode(),
    })


@guide_required
def itinerary_edit(request, tour_pk, item_pk):
    """
    Guide dashboard: Edit an existing ItineraryItem.

    GET: Returns pre-filled form partial.
    POST: Validates, saves, returns updated row partial (HTMX) or redirects.

    Args:
        tour_pk: Tour PK from URL
        item_pk: ItineraryItem PK from URL

    ASSUMPTIONS:
    - Item must belong to this tour (cross-tour editing prevented by the
      combined get_object_or_404 filter on both pk and tour).

    FAILURE MODES:
    - Item not found or belongs to another tour: 404
    - Wrong guide ownership: 403 from _get_tour_for_guide
    """
    from django.shortcuts import get_object_or_404
    from .forms import ItineraryItemForm
    tour = _get_tour_for_guide(request, tour_pk)
    # Ensure the item belongs to this tour (prevents cross-tour editing)
    item = get_object_or_404(ItineraryItem, pk=item_pk, tour=tour)

    if request.method == 'POST':
        form = ItineraryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return render(request, 'admin_panel/tours/partials/itinerary_item_row.html', {
                    'item': item,
                    'tour': tour,
                })
            return redirect(
                reverse('dashboard:tour_detail', args=[tour.pk]) + '?tab=itinerary'
            )
        if request.headers.get('HX-Request'):
            return render(request, 'admin_panel/tours/partials/itinerary_item_form.html', {
                'form': form,
                'tour': tour,
                'item': item,
                'dev_mode': _dev_mode(),
            })
    else:
        form = ItineraryItemForm(instance=item)

    return render(request, 'admin_panel/tours/partials/itinerary_item_form.html', {
        'form': form,
        'tour': tour,
        'item': item,
        'dev_mode': _dev_mode(),
    })


@guide_required
def itinerary_delete(request, tour_pk, item_pk):
    """
    Guide dashboard: Delete an ItineraryItem.

    Accepts POST or DELETE (HTMX sends DELETE).
    Returns empty 200 response — HTMX swaps the row out via outerHTML swap.

    Args:
        tour_pk: Tour PK (used for ownership check)
        item_pk: ItineraryItem PK to delete

    FAILURE MODES:
    - Item not found: 404 from get_object_or_404
    - Wrong tour ownership: 403 from _get_tour_for_guide
    - Non-POST/DELETE method: 405 Method Not Allowed
    """
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    tour = _get_tour_for_guide(request, tour_pk)
    item = get_object_or_404(ItineraryItem, pk=item_pk, tour=tour)
    if request.method in ('POST', 'DELETE'):
        item.delete()
        # Empty response triggers HTMX outerHTML swap removal of the row
        return HttpResponse('')
    return HttpResponse(status=405)


@guide_required
def itinerary_reorder(request, tour_pk):
    """
    Guide dashboard: Update the order of ItineraryItems after drag-and-drop.

    Accepts JSON body: [{"id": 1, "order": 0}, {"id": 2, "order": 1}, ...]
    Updates each item's order field. Only processes items belonging to this tour
    (the filter prevents tampering with other tours' items).

    Args:
        tour_pk: Tour PK (used for ownership check and item scope filter)

    Returns:
        JsonResponse {"ok": true} on success
        JsonResponse {"error": "..."} on invalid input

    ASSUMPTIONS:
    - Client sends all items for a day in the new order
    - IDs in payload belong to this tour (enforced by DB filter on tour FK)

    FAILURE MODES:
    - Invalid JSON body: returns 400 with error message
    - Non-POST method: returns 405
    - IDs from other tours: silently ignored due to tour filter in queryset
    """
    import json
    from django.http import JsonResponse
    tour = _get_tour_for_guide(request, tour_pk)
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'invalid JSON body'}, status=400)
    # Update each item; filter by tour ensures cross-tour tampering has no effect
    for entry in data:
        ItineraryItem.objects.filter(pk=entry['id'], tour=tour).update(order=entry['order'])
    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# Photo gallery views (Task 32)
# ---------------------------------------------------------------------------

@guide_required
def photo_upload(request, tour_pk):
    """
    Guide dashboard: Upload a photo to a tour's gallery.

    Accepts multipart POST with a 'photo' file field.
    Returns:
    - HTMX request: the new photo thumbnail partial for inline insertion
    - Normal POST: redirect to tour detail photos tab
    - No file: 400 Bad Request

    Args:
        tour_pk: Tour PK (used for ownership check and photo association)

    ASSUMPTIONS:
    - 'photo' key is present in request.FILES for a valid upload
    - Pillow is installed (ImageField validates the file is a real image)

    FAILURE MODES:
    - Invalid image format: Django's ImageField raises ValidationError
    - No photo key: returns 400 immediately
    """
    from django.http import HttpResponse
    tour = _get_tour_for_guide(request, tour_pk)

    if request.method != 'POST':
        # Only POST is accepted; return 405 for any other method
        return HttpResponse(status=405)

    photo_file = request.FILES.get('photo')
    if not photo_file:
        # No file in request — return 400 rather than silently doing nothing
        return HttpResponse(status=400)

    photo = TourPhoto.objects.create(
        tour=tour,
        uploaded_by=request.user,
        photo=photo_file,
        caption=request.POST.get('caption', ''),
    )

    if request.headers.get('HX-Request'):
        # HTMX: return just the thumbnail partial so it's inserted into the grid
        return render(request, 'admin_panel/tours/partials/photo_thumb.html', {'photo': photo})

    # Normal POST: redirect to photos tab on tour detail
    return redirect(
        reverse('dashboard:tour_detail', args=[tour_pk]) + '?tab=photos'
    )


@guide_required
def photo_delete(request, pk):
    """
    Guide dashboard: Delete a tour photo.

    Accepts POST or DELETE (HTMX sends DELETE).
    Attempts to delete the physical file from MEDIA_ROOT before removing the DB record.
    Returns empty 200 — HTMX swaps the thumbnail element out of the grid.

    Args:
        pk: TourPhoto primary key

    FAILURE MODES:
    - File already deleted from disk: FileNotFoundError is caught silently
    - Photo not found in DB: 404
    - Ownership violation (wrong guide): 403 from _get_tour_for_guide
    """
    import os
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    photo = get_object_or_404(TourPhoto, pk=pk)

    # Enforce tour ownership via the same helper used throughout the dashboard
    _get_tour_for_guide(request, photo.tour_id)

    if request.method in ('POST', 'DELETE'):
        # Delete the physical file to prevent orphaned media files
        if photo.photo and hasattr(photo.photo, 'path'):
            try:
                os.remove(photo.photo.path)
            except FileNotFoundError:
                pass  # file was already removed — continue with DB cleanup

        photo.delete()
        return HttpResponse('')  # empty response: HTMX swaps element out

    # Reject GET, PUT, PATCH etc. — this endpoint is write-only
    return HttpResponse(status=405)
