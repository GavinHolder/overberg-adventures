from django.conf import settings


def dev_mode(request):
    return {'dev_mode': getattr(settings, 'DEV_MODE', False)}
