"""
Access control decorators for the Overstrand Adventures admin backend.

The admin backend (/backend/) is separate from the guide portal (/guide/).
Only operators, admins, and Django staff can access the backend.
Guides only access /guide/.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

# Roles permitted to access the admin backend
BACKEND_ROLES = {'OPERATOR', 'ADMIN'}


def backend_required(view_func):
    """
    Restricts access to the admin backend.

    Allowed:
    - request.user.is_staff → unconditional access (Django admins/superusers)
    - UserProfile.role in {'OPERATOR', 'ADMIN'}

    Denied:
    - Unauthenticated → redirected to login
    - GUIDE or GUEST roles → 403 PermissionDenied

    ASSUMPTIONS:
    - Every authenticated user has a UserProfile (created by post_save signal).
    - GUIDE users access /guide/ instead — not the backend.

    FAILURE MODES:
    - Missing profile: treated as denied (403), not 500.
    """
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        profile = getattr(request.user, 'profile', None)
        if not profile or profile.role not in BACKEND_ROLES:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped


def superuser_required(view_func):
    """Restricts to superusers only — for the most sensitive operations."""
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
