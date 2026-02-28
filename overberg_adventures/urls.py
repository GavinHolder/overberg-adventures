from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.landing.views import service_worker

urlpatterns = [
    path('admin/', admin.site.urls),
    path('service-worker.js', service_worker, name='service-worker'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
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
