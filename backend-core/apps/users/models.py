"""Identity models for Ferasha.

``backend-core`` is the single source of truth for identity across the
monorepo. It mints HS256 JWTs which the FastAPI ``ai-engine`` verifies with the
shared ``JWT_SIGNING_KEY``; the AI engine never issues credentials of its own.
"""

from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    """Coarse-grained role, used for route-level authorisation."""

    CUSTOMER = "customer", _("Customer")
    VENDOR = "vendor", _("Vendor / Atelier Partner")
    TAILOR = "tailor", _("Master Tailor")
    STYLIST = "stylist", _("Personal Stylist")
    STAFF = "staff", _("Operations Staff")
    ADMIN = "admin", _("Administrator")


class UserManager(BaseUserManager):
    """Email-first manager; Ferasha has no separate username concept."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("An email address is required to create a user.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean(exclude=["password", "last_login"])
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", UserRole.CUSTOMER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("email_verified_at", timezone.now())
        if extra_fields["is_staff"] is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


phone_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{7,14}$",
    message=_("Enter a valid phone number in E.164 format, e.g. +919820012345."),
)


class User(AbstractUser):
    """Custom user keyed by UUID and authenticated by email address."""

    # AbstractUser ships a required ``username``; Ferasha authenticates on email.
    username = None  # type: ignore[assignment]
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    full_name = models.CharField(_("full name"), max_length=180)
    phone = models.CharField(
        _("phone"), max_length=16, blank=True, validators=[phone_validator]
    )
    role = models.CharField(
        _("role"), max_length=16, choices=UserRole.choices, default=UserRole.CUSTOMER, db_index=True
    )

    # Modesty and personalisation preferences applied storewide for this user.
    preferences = models.JSONField(
        _("preferences"),
        default=dict,
        blank=True,
        help_text=_(
            "Free-form storefront preferences, e.g. "
            '{"hide_model_faces": true, "default_currency": "INR"}.'
        ),
    )

    email_verified_at = models.DateTimeField(_("email verified at"), null=True, blank=True)
    phone_verified_at = models.DateTimeField(_("phone verified at"), null=True, blank=True)
    accepted_terms_at = models.DateTimeField(_("accepted terms at"), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["role", "is_active"], name="user_role_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    def clean(self) -> None:
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()
        self.full_name = " ".join(self.full_name.split())

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        return super().save(*args, **kwargs)

    # -- Role helpers -------------------------------------------------------
    @property
    def is_vendor(self) -> bool:
        return self.role == UserRole.VENDOR

    @property
    def is_tailor(self) -> bool:
        return self.role == UserRole.TAILOR

    @property
    def is_back_office(self) -> bool:
        return self.role in {UserRole.STAFF, UserRole.ADMIN} or self.is_staff

    @property
    def email_is_verified(self) -> bool:
        return self.email_verified_at is not None

    def get_full_name(self) -> str:
        return self.full_name

    def get_short_name(self) -> str:
        return self.full_name.split(" ")[0] if self.full_name else self.email


class Address(models.Model):
    """Shipping / billing address. Drives GST place-of-supply resolution."""

    class Kind(models.TextChoices):
        SHIPPING = "shipping", _("Shipping")
        BILLING = "billing", _("Billing")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SHIPPING)

    recipient_name = models.CharField(max_length=180)
    phone = models.CharField(max_length=16, validators=[phone_validator])
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120)
    # ISO 3166-2:IN subdivision code without the "IN-" prefix, e.g. "MH".
    state_code = models.CharField(max_length=8, blank=True, db_index=True)
    postal_code = models.CharField(max_length=16)
    country_code = models.CharField(max_length=2, default="IN", db_index=True)

    gstin = models.CharField(
        max_length=15,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}$",
                message=_("Enter a valid 15-character GSTIN."),
            )
        ],
        help_text=_("Optional B2B GSTIN for input tax credit."),
    )

    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = _("addresses")
        ordering = ("-is_default", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "kind"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(country_code__regex=r"^[A-Z]{2}$"),
                name="address_country_code_is_iso_alpha2",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.recipient_name}, {self.city} ({self.country_code})"

    def save(self, *args, **kwargs):
        self.country_code = self.country_code.upper().strip()
        self.state_code = self.state_code.upper().strip()
        self.gstin = self.gstin.upper().strip()
        return super().save(*args, **kwargs)
