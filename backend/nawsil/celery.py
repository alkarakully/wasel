import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nawsil.settings")

app = Celery("nawsil")
# All Celery settings live in Django settings with a CELERY_ prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
