from functools import wraps
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.conf import settings

from .decorators import guide_required, staff_required
from apps.tours.models import Tour


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
    Render the activities management list view (stub).

    Currently a placeholder that renders the activities list template with no
    activity data. A full implementation will query the Activity model once
    the activities app is built out.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    return render(request, 'admin_panel/activities/list.html', {'dev_mode': _dev_mode()})


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
    Stub: tour creation form (not yet implemented).

    Renders the tour list template with an empty tours collection so the URL
    resolves and the template renders without errors. A real implementation
    will render a ModelForm for Tour creation and handle POST.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    return render(request, 'admin_panel/tours/list.html', {'tours': [], 'dev_mode': _dev_mode()})


@guide_required
def tour_detail(request, pk):
    """
    Stub: tour detail view (not yet implemented).

    Fetches the Tour by primary key (404 if not found) and renders the list
    template with that single tour so the URL resolves. A real implementation
    will use a dedicated detail template.

    Args:
        pk: Primary key of the Tour to display.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    # Deferred import keeps the module-level import surface minimal while
    # this view is still a stub.
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/list.html', {'tours': [tour], 'dev_mode': _dev_mode()})


@guide_required
def tour_edit(request, pk):
    """
    Stub: tour edit form (not yet implemented).

    Fetches the Tour by primary key (404 if not found) and renders the list
    template with that single tour so the URL resolves. A real implementation
    will render a pre-populated ModelForm and handle POST updates.

    Args:
        pk: Primary key of the Tour to edit.

    Access: guide-level users and staff (enforced by @guide_required).
    """
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/list.html', {'tours': [tour], 'dev_mode': _dev_mode()})


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
