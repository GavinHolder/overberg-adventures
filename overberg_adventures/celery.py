import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'overberg_adventures.settings')

app = Celery('overberg_adventures')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
