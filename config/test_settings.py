"""
Test-only Django settings.

Swaps the primary PostgreSQL database for an in-memory SQLite
database so the test suite can run without a live database server.

Usage:
    python manage.py test deliveries --settings=config.test_settings
"""

from .settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}