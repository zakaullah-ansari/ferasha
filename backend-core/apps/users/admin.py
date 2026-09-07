"""Django admin registration for identity models."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Address, User


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = ("kind", "recipient_name", "city", "state_code", "country_code", "is_default")
    show_change_link = True


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-created_at",)
    list_display = ("email", "full_name", "role", "is_active", "email_verified_at", "created_at")
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "created_at")
    search_fields = ("email", "full_name", "phone")
    readonly_fields = ("id", "created_at", "updated_at", "last_login", "date_joined")
    inlines = (AddressInline,)

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Profile"), {"fields": ("full_name", "phone", "preferences")}),
        (_("Role & permissions"), {
            "fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Verification"), {
            "fields": ("email_verified_at", "phone_verified_at", "accepted_terms_at"),
        }),
        (_("Timestamps"), {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "role", "password1", "password2"),
        }),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "user", "kind", "city", "state_code", "country_code", "is_default")
    list_filter = ("kind", "country_code", "state_code", "is_default")
    search_fields = ("recipient_name", "user__email", "city", "postal_code", "gstin")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("user",)
