"""Demo settings: runs the real server on a file-backed SQLite database.

Used only for local smoke-testing the HTTP surface in environments without a
PostgreSQL server. Production and CI always use ``config.settings`` against
PostgreSQL 16.
"""

from __future__ import annotations

import os

from .settings_test import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DEMO_DB_PATH", "/tmp/ferasha_demo.sqlite3"),
    }
}

CORS_ALLOW_ALL_ORIGINS = True
SECURE_SSL_REDIRECT = False
