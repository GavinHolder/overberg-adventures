import os

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render


def service_worker(request):
    """Serve service worker from root scope so it can control all app pages."""
    sw_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR / 'static', 'js', 'service-worker.js')
    # Fall back to dev static path if STATIC_ROOT not set or file doesn't exist there
    if not os.path.exists(sw_path):
        sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'service-worker.js')
    with open(sw_path) as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response
