from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

# Roles that are allowed to access the guide dashboard.
# GUEST is excluded — guests are tour participants, not staff.
GUIDE_ROLES = {'GUIDE', 'OPERATOR', 'ADMIN'}


def guide_required(view_func):
    """
    Decorator that restricts view access to guide-level users and staff.

    Allowed:
    - request.user.is_staff → unconditional bypass (superusers/Django admins)
    - UserProfile.role in GUIDE_ROLES ('GUIDE', 'OPERATOR', 'ADMIN')

    Denied:
    - Unauthenticated users → redirected to login (via @login_required)
    - Authenticated guests (role='GUEST') → 403 PermissionDenied

    ASSUMPTIONS:
    - Every User has a related UserProfile (created by post_save signal in accounts app)
    - UserProfile.role is one of the Role TextChoices values defined on UserProfile

    FAILURE MODES:
    - Missing profile (profile=None): treated as denied, raises PermissionDenied
      rather than AttributeError — prevents 500 on a broken signup flow
    """
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        # Staff (superusers, Django admins) bypass role checks entirely —
        # they manage the system and must never be locked out by role logic.
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)

        # Safely retrieve the reverse-related profile via the accessor name 'profile'.
        # getattr with a None default guards against a missing profile rather than
        # raising RelatedObjectDoesNotExist (a subclass of AttributeError).
        profile = getattr(request.user, 'profile', None)

        # Deny access if the profile is missing or the role is not in the allowed set.
        # A missing profile is treated identically to an insufficient role so that
        # error responses don't reveal whether the account has a profile at all.
        if not profile or profile.role not in GUIDE_ROLES:
            raise PermissionDenied

        return view_func(request, *args, **kwargs)
    return wrapped


def staff_required(view_func):
    """
    Decorator that restricts view access to Django staff/superusers only.

    Used for sensitive operations such as editing guide roles or viewing all users.
    Regular guides (even those with OPERATOR or ADMIN UserProfile roles) cannot
    access staff-only views — only Django's is_staff flag grants entry.

    FAILURE MODES:
    - A guide with UserProfile.role='ADMIN' is still denied; the decorator
      deliberately ignores UserProfile.role to keep the permission boundary sharp.
    """
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        # Only Django's is_staff flag grants access — UserProfile.role is irrelevant.
        # This keeps a hard separation between "guide-level admin" (OPERATOR/ADMIN role)
        # and "Django-level admin" (is_staff=True / the /admin/ site).
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
