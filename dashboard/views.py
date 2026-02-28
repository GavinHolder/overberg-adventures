from functools import wraps
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.conf import settings

from .decorators import guide_required, staff_required
from .forms import TourForm
from apps.tours.models import Tour, ItineraryItem, ActivityCategory


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
    Render the guides management list view (stub).

    Currently a placeholder that renders the guides list template with no
    guide data. A full implementation will query UserProfile filtered to
    guide-level roles once the guides management feature is built out.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    return render(request, 'admin_panel/guides/list.html', {'dev_mode': _dev_mode()})


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

    return render(request, 'admin_panel/tours/detail.html', {
        'tour': tour,
        'active_tab': active_tab,
        'bookings': bookings,
        'items_by_day': items_by_day,
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
    Stub: QR code view for a tour (not yet implemented).

    Fetches the Tour by primary key (404 if not found) and renders the list
    template with that single tour so the URL resolves. A real implementation
    will generate and display a QR code linking to the guest RSVP flow for
    the tour's unique tour code.

    Args:
        pk: Primary key of the Tour whose QR code should be shown.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/list.html', {'tours': [tour], 'dev_mode': _dev_mode()})


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
