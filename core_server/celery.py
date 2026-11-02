import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_server.settings')

app = Celery('voxscribe')

# Read config from Django settings, namespace all celery-related configs
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks()
