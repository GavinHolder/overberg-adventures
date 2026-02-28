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
    Render the tour management list view.

    Behaviour differs by role:
    - Staff and OPERATOR/ADMIN roles: see ALL tours across all guides, ordered
      newest-first by start datetime.
    - GUIDE role: filtered to only their own tours (guide=request.user), so a
      guide cannot view or manage another guide's bookings.

    Context:
    - tours: QuerySet of Tour objects with guide + profile pre-fetched to avoid
      N+1 queries in the template.
    - dev_mode: bool — controls DEV_MODE banner and simulate buttons in template.

    Access: guide-level users and staff (enforced by @guide_required).

    ASSUMPTIONS:
    - Tour.guide is a ForeignKey to AUTH_USER_MODEL (the guide who owns the tour).
    - UserProfile is accessible via request.user.profile (created by post_save signal).

    FAILURE MODES:
    - Missing profile: getattr returns None; the role check falls through to the
      unfiltered queryset (all tours visible), which is acceptable because the
      @guide_required decorator would have already raised PermissionDenied before
      reaching this view for a truly profileless user.
    """
    # Eagerly join guide and guide.profile in a single SQL query to prevent
    # per-row profile lookups when iterating over tours in the template.
    tours = Tour.objects.select_related('guide__profile').order_by('-start_datetime')

    profile = getattr(request.user, 'profile', None)

    # Restrict GUIDE-role users to their own tours only.
    # Staff and OPERATOR/ADMIN roles see the full queryset without filtering.
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
