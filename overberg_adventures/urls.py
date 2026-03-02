from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied

from apps.landing.views import service_worker


def admin_redirect(request):
    """
    Redirect non-superusers away from Django admin to the custom backend.
    Superusers pass through to Django admin normally.
    """
    if request.user.is_authenticated and request.user.is_superuser:
        return HttpResponseRedirect('/admin/login/' if not request.user.is_active else '/admin/')
    return HttpResponseRedirect('/backend/')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('service-worker.js', service_worker, name='service-worker'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('backend/', include('adminpanel.urls', namespace='backend')),
    path('guide/', include('dashboard.urls', namespace='dashboard')),
    path('app/sos/', include('apps.sos.urls', namespace='sos')),
    path('app/map/', include('apps.maps.urls', namespace='maps')),
    path('app/', include('apps.bookings.urls', namespace='bookings')),
    path('', include('apps.landing.urls', namespace='landing')),
    path('webpush/', include('webpush.urls')),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
