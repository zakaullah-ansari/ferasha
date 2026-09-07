"""Test settings.

Ferasha targets PostgreSQL 16 in every real environment. This module exists so
the HTTP/serializer/permission layers can be exercised on SQLite in CI sandboxes
and pre-commit hooks where a Postgres server is unavailable.

It is NOT a substitute for the Postgres test run: jsonb operators, GIN indexes
and several CheckConstraints are only meaningfully validated against Postgres.
The CI pipeline runs the full suite against a real postgres:16 service.
"""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "insecure-test-key")
os.environ.setdefault("JWT_SIGNING_KEY", "insecure-test-jwt-key")
os.environ.setdefault("DATABASE_URL", "postgresql://ferasha:pw@127.0.0.1:5432/ferasha")
os.environ.setdefault("DJANGO_DEBUG", "1")

from .settings import *  # noqa: F403,E402
from .settings import INSTALLED_APPS  # noqa: E402

USE_SQLITE_FOR_TESTS = os.environ.get("FERASHA_TEST_SQLITE", "1") == "1"

if USE_SQLITE_FOR_TESTS:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
            "TEST": {"NAME": ":memory:"},
        }
    }
    # django.contrib.postgres requires a PostgreSQL backend to load.
    INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django.contrib.postgres"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

REST_FRAMEWORK = {
    **globals()["REST_FRAMEWORK"],
    "DEFAULT_THROTTLE_RATES": {"anon": "10000/min", "user": "10000/min", "login": "10000/min"},
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEBUG = False
SECURE_SSL_REDIRECT = False
