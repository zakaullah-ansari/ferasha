"""Fit profile persistence, jsonb validation and append-only revision tests."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.tailoring.models import BespokeFitProfile, FitProfileRevision
from tests.factories import make_user

pytestmark = pytest.mark.django_db

VALID = {
    "bust": 36,
    "waist": 30,
    "hip": 38,
    "shoulder": 14,
    "kameez_length": 42,
    "sleeve_length": 22,
}


def make_profile(user=None, **kw):
    user = user or make_user()
    defaults = dict(
        user=user,
        label="My measurements",
        measurements=dict(VALID),
        unit_system="inch",
    )
    defaults.update(kw)
    return BespokeFitProfile.objects.create(**defaults)


class TestPersistence:
    def test_valid_profile_saves(self):
        profile = make_profile()
        profile.refresh_from_db()
        assert profile.measurements["bust"] == 36.0

    def test_preferences_persist(self):
        profile = make_profile(
            preferences={"sleeve_type": "full", "lining_preference": "full"}
        )
        profile.refresh_from_db()
        assert profile.preferences["lining_preference"] == "full"

    def test_jsonb_survives_round_trip(self):
        profile = make_profile()
        reloaded = BespokeFitProfile.objects.get(pk=profile.pk)
        assert set(reloaded.measurements) == set(VALID)


class TestValidationOnSave:
    """A jsonb column is only as trustworthy as its narrowest write path."""

    def test_implausible_measurement_rejected_on_save(self):
        with pytest.raises(ValidationError):
            make_profile(measurements={"bust": 400})

    def test_unknown_key_rejected_on_save(self):
        with pytest.raises(ValidationError):
            make_profile(measurements={"wingspan": 60})

    def test_incoherent_pair_rejected_on_save(self):
        with pytest.raises(ValidationError):
            make_profile(measurements={"bust": 34, "underbust": 40})

    def test_bad_preference_rejected_on_save(self):
        with pytest.raises(ValidationError):
            make_profile(preferences={"lining_preference": "sometimes"})

    def test_garment_required_fields_enforced(self):
        with pytest.raises(ValidationError):
            make_profile(measurements={"bust": 36}, garment_type="suit_set")

    def test_validation_also_applies_to_updates(self):
        """Not only creation - an edit must be validated too."""
        profile = make_profile()
        profile.measurements = {"bust": 999}
        with pytest.raises(ValidationError):
            profile.save()

    def test_cm_profile_validated_in_cm(self):
        cm = {k: round(v * 2.54, 1) for k, v in VALID.items()}
        profile = make_profile(measurements=cm, unit_system="cm")
        assert profile.measurements["bust"] == pytest.approx(91.4, abs=0.1)


class TestConstraints:
    def test_duplicate_label_per_user_rejected(self):
        user = make_user()
        make_profile(user=user, label="Mine")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_profile(user=user, label="Mine")

    def test_same_label_different_users_allowed(self):
        make_profile(user=make_user(), label="Mine")
        assert make_profile(user=make_user(), label="Mine").pk

    def test_only_one_default_per_user(self):
        user = make_user()
        make_profile(user=user, label="A", is_default=True)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_profile(user=user, label="B", is_default=True)

    def test_multiple_non_default_allowed(self):
        user = make_user()
        make_profile(user=user, label="A", is_default=True)
        assert make_profile(user=user, label="B", is_default=False).pk


class TestRevisionHistory:
    """Disputes require knowing exactly what was specified at the time."""

    def test_revision_records_measurements(self):
        profile = make_profile()
        revision = FitProfileRevision.objects.create(
            profile=profile,
            revision=1,
            measurements=dict(profile.measurements),
            unit_system=profile.unit_system,
        )
        assert revision.measurements["bust"] == 36.0

    def test_revisions_cannot_be_modified(self):
        profile = make_profile()
        revision = FitProfileRevision.objects.create(
            profile=profile, revision=1, measurements={"bust": 36}, unit_system="inch"
        )
        revision.measurements = {"bust": 40}
        with pytest.raises(ValidationError, match="append-only"):
            revision.save()

    def test_revisions_cannot_be_deleted(self):
        profile = make_profile()
        revision = FitProfileRevision.objects.create(
            profile=profile, revision=1, measurements={"bust": 36}, unit_system="inch"
        )
        with pytest.raises(ValidationError, match="append-only"):
            revision.delete()

    def test_revision_numbers_unique_per_profile(self):
        profile = make_profile()
        FitProfileRevision.objects.create(
            profile=profile, revision=1, measurements={"bust": 36}, unit_system="inch"
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                FitProfileRevision.objects.create(
                    profile=profile, revision=1, measurements={"bust": 38},
                    unit_system="inch",
                )

    def test_history_survives_profile_change(self):
        profile = make_profile()
        FitProfileRevision.objects.create(
            profile=profile, revision=1, measurements=dict(VALID), unit_system="inch"
        )
        profile.measurements = {**VALID, "bust": 38}
        profile.save()

        original = FitProfileRevision.objects.get(profile=profile, revision=1)
        assert original.measurements["bust"] == 36
        profile.refresh_from_db()
        assert profile.measurements["bust"] == 38.0


class TestSnapshot:
    def test_snapshot_is_a_detached_copy(self):
        profile = make_profile()
        snapshot = profile.snapshot()
        profile.measurements = {**VALID, "bust": 44}
        profile.save()
        assert snapshot["measurements"]["bust"] == 36.0

    def test_snapshot_carries_provenance(self):
        profile = make_profile()
        snapshot = profile.snapshot()
        assert snapshot["profile_id"] == str(profile.id)
        assert snapshot["unit_system"] == "inch"
        assert "captured_at" in snapshot

    def test_snapshot_is_json_safe(self):
        import json

        assert json.loads(json.dumps(make_profile().snapshot()))
