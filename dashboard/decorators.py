from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

GUIDE_ROLES = {'GUIDE', 'OPERATOR', 'ADMIN'}


def guide_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)
        profile = getattr(request.user, 'profile', None)
        if not profile or profile.role not in GUIDE_ROLES:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped


def staff_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
