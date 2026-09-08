"""Demo settings: runs the real server on a file-backed SQLite database.

Used only for local smoke-testing the HTTP surface in environments without a
PostgreSQL server. Production and CI always use ``config.settings`` against
PostgreSQL 16.
"""

from __future__ import annotations

import os

from .settings_test import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DEMO_DB_PATH", "/tmp/ferasha_demo.sqlite3"),  # noqa: S108 - throwaway demo DB, never production
    }
}

CORS_ALLOW_ALL_ORIGINS = True
SECURE_SSL_REDIRECT = False

# The demo is proxied over HTTPS by the sandbox preview host. Django checks the
# Origin header against this list for unsafe methods, so without the wildcard
# entry the Swagger "Try it out" POSTs would fail CSRF validation.
CSRF_TRUSTED_ORIGINS = ["https://*.e2b.app", "https://*.e2b.dev", "http://localhost:8000"]
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
