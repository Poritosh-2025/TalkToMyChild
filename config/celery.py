"""
Celery configuration for Paradise AI.

All settings are loaded from Django settings.py via the CELERY_ namespace.
Task routing, time limits, and queue config are defined there.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
