"""Shared abstract base models."""

from __future__ import annotations

import uuid

from django.db import models


class UUIDModel(models.Model):
    """Primary key as a UUID.

    Sequential integer keys leak business volume (an order id of 47 tells a
    competitor how many orders exist) and make id-guessing enumeration trivial.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimestampedModel):
    class Meta:
        abstract = True
