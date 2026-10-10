"""
Celery application for SolidTrack.

This module is imported once at Django startup via
config/__init__.py. It loads Celery configuration from
Django settings under the CELERY_* namespace and
auto-discovers tasks from every installed app's tasks.py.
"""

import os

from celery import Celery


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)


app = Celery("SolidTrack")

# Load CELERY_* settings from Django settings.
app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)

# Discover @shared_task definitions in every app's tasks.py.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Smoke-test task.

    Run with:
        celery -A config call config.celery.debug_task
    """
    print(f"Request: {self.request!r}")