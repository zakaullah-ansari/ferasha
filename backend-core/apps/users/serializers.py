"""DRF serializers for identity, registration and JWT issuance."""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address, UserRole

User = get_user_model()


class FerashaTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Issue JWTs carrying the claims the FastAPI ai-engine needs.

    The ai-engine verifies these tokens with the shared HS256 signing key and
    authorises purely on the embedded claims - it never queries the Django
    database for identity. Keep this claim set stable; it is a contract.
    """

    @classmethod
    def get_token(cls, user):  # type: ignore[override]
        token = super().get_token(user)
        token["email"] = user.email
        token["full_name"] = user.full_name
        token["role"] = user.role
        token["is_back_office"] = user.is_back_office
        token["email_verified"] = user.email_is_verified
        return token

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        data = super().validate(attrs)
        user = self.user

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": _("This account has been deactivated.")}, code="inactive_account"
            )

        data["user"] = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "email_verified": user.email_is_verified,
            "preferences": user.preferences,
        }
        return data


class AddressSerializer(serializers.ModelSerializer):
    """Address CRUD. ``state_code`` drives GST place-of-supply resolution."""

    class Meta:
        model = Address
        fields = (
            "id",
            "kind",
            "recipient_name",
            "phone",
            "line1",
            "line2",
            "city",
            "state_code",
            "postal_code",
            "country_code",
            "gstin",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # Import locally to keep the tax engine a leaf dependency.
        from apps.taxes.constants import INDIAN_STATE_GST_CODES

        country = (attrs.get("country_code") or getattr(self.instance, "country_code", "IN")).upper()
        state = (attrs.get("state_code") or getattr(self.instance, "state_code", "")).upper()

        if country == "IN":
            if not state:
                raise serializers.ValidationError(
                    {"state_code": _("State is required for addresses within India.")}
                )
            if state not in INDIAN_STATE_GST_CODES:
                raise serializers.ValidationError(
                    {"state_code": _("Unknown Indian state or union territory code.")}
                )
            postal = attrs.get("postal_code") or getattr(self.instance, "postal_code", "")
            if not (postal.isdigit() and len(postal) == 6):
                raise serializers.ValidationError(
                    {"postal_code": _("Indian PIN codes must be exactly 6 digits.")}
                )

        gstin = (attrs.get("gstin") or "").upper()
        if gstin and country == "IN" and not gstin.startswith(INDIAN_STATE_GST_CODES[state]):
            raise serializers.ValidationError(
                {"gstin": _("GSTIN state prefix does not match the address state.")}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Address:
        user = self.context["request"].user
        validated_data["user"] = user
        if validated_data.get("is_default"):
            Address.objects.filter(
                user=user, kind=validated_data.get("kind", Address.Kind.SHIPPING), is_default=True
            ).update(is_default=False)
        elif not Address.objects.filter(user=user, kind=validated_data.get("kind", Address.Kind.SHIPPING)).exists():
            validated_data["is_default"] = True
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance: Address, validated_data: dict[str, Any]) -> Address:
        if validated_data.get("is_default"):
            Address.objects.filter(
                user=instance.user, kind=validated_data.get("kind", instance.kind), is_default=True
            ).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Read/update representation of the authenticated user."""

    addresses = AddressSerializer(many=True, read_only=True)
    email_verified = serializers.BooleanField(source="email_is_verified", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "preferences",
            "email_verified",
            "addresses",
            "date_joined",
            "created_at",
        )
        read_only_fields = ("id", "email", "role", "email_verified", "date_joined", "created_at")

    def validate_preferences(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Preferences must be a JSON object."))
        allowed = {
            "hide_model_faces",
            "default_currency",
            "preferred_unit_system",
            "modesty_filter_default",
            "marketing_opt_in",
            "preferred_language",
        }
        unknown = set(value) - allowed
        if unknown:
            raise serializers.ValidationError(
                _("Unsupported preference keys: %(keys)s") % {"keys": ", ".join(sorted(unknown))}
            )
        if "preferred_unit_system" in value and value["preferred_unit_system"] not in {"cm", "inch"}:
            raise serializers.ValidationError(_("preferred_unit_system must be 'cm' or 'inch'."))
        return value


class RegistrationSerializer(serializers.ModelSerializer):
    """Public self-service registration. Always creates a CUSTOMER."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"}, min_length=10)
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})
    accept_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "phone", "password", "password_confirm", "accept_terms")
        read_only_fields = ("id",)

    def validate_email(self, value: str) -> str:
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            # Deliberately generic: do not confirm account existence to anonymous callers.
            raise serializers.ValidationError(_("This email address cannot be registered."))
        return value

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(_("You must accept the terms of service."))
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": _("Passwords do not match.")})

        candidate = User(email=attrs["email"], full_name=attrs.get("full_name", ""))
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Any:
        validated_data.pop("accept_terms", None)
        password = validated_data.pop("password")
        return User.objects.create_user(
            password=password,
            role=UserRole.CUSTOMER,
            accepted_terms_at=timezone.now(),
            **validated_data,
        )


class PasswordChangeSerializer(serializers.Serializer):
    """Authenticated password rotation."""

    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"}, min_length=10)
    new_password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Current password is incorrect."))
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": _("Passwords do not match.")})
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError(
                {"new_password": _("New password must differ from the current password.")}
            )
        user = self.context["request"].user
        try:
            validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs

    @transaction.atomic
    def save(self, **kwargs: Any) -> Any:
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        # Rotating the password must not leave stolen refresh tokens usable.
        revoke_all_refresh_tokens(user)
        return user


def revoke_all_refresh_tokens(user) -> int:
    """Blacklist every outstanding refresh token for ``user``.

    Called after any credential change. Access tokens already issued remain
    valid until they expire (they are stateless by design), which is why the
    access lifetime is kept short; refresh is the durable credential and it is
    what an attacker would rely on for persistence.
    """
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    revoked = 0
    for token in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        revoked += int(created)
    return revoked


class EmailVerificationRequestSerializer(serializers.Serializer):
    """Request a fresh verification email.

    Accepts an email so the flow works for a signed-out user who lost the
    original message. The view's response is identical whether or not the
    address exists.
    """

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class EmailVerificationConfirmSerializer(serializers.Serializer):
    """Consume a verification token."""

    token = serializers.CharField(write_only=True, max_length=512)

    def validate_token(self, value: str) -> str:
        from .tokens import TokenInvalid, read_email_verification_token

        try:
            self._user = read_email_verification_token(value, User)
        except TokenInvalid as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    @transaction.atomic
    def save(self, **kwargs: Any) -> Any:
        user = self._user
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at", "updated_at"])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Begin a password reset. Never reveals whether the account exists."""

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Complete a password reset with a single-use token."""

    token = serializers.CharField(write_only=True, max_length=512)
    new_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}, min_length=10
    )
    new_password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_token(self, value: str) -> str:
        from .tokens import TokenInvalid, read_password_reset_token

        try:
            self._user = read_password_reset_token(value, User)
        except TokenInvalid as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": _("Passwords do not match.")}
            )
        # ``_user`` is only present when the token validated; DRF still runs
        # object-level validate() after a field error in some code paths.
        user = getattr(self, "_user", None)
        if user is not None:
            try:
                validate_password(attrs["new_password"], user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs

    @transaction.atomic
    def save(self, **kwargs: Any) -> Any:
        user = self._user
        user.set_password(self.validated_data["new_password"])
        # Completing a reset proves control of the mailbox, so the address is
        # verified as a side effect. This also rotates the token fingerprint,
        # which is what makes the reset link single-use.
        if user.email_verified_at is None:
            user.email_verified_at = timezone.now()
        user.save(update_fields=["password", "email_verified_at", "updated_at"])
        revoke_all_refresh_tokens(user)
        return user
