"""
Django config package.

The Celery app is imported here so that @shared_task
decorators resolve correctly across all apps.
"""

from .celery import app as celery_app


__all__ = ("celery_app",)