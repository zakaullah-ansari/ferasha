"""Integration tests for identity: registration, JWT claims, authz isolation."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.users.models import Address, UserRole

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestRegistration:
    def test_successful_registration_returns_tokens(self, api_client):
        response = api_client.post(
            reverse("users:register"),
            {
                "email": "New.User@Example.com",
                "full_name": "New User",
                "password": "Correct-Horse-9182",
                "password_confirm": "Correct-Horse-9182",
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        assert "access" in response.data and "refresh" in response.data
        assert response.data["user"]["email"] == "new.user@example.com"
        assert response.data["user"]["role"] == UserRole.CUSTOMER

        user = User.objects.get(email="new.user@example.com")
        assert user.accepted_terms_at is not None
        assert user.check_password("Correct-Horse-9182")

    def test_password_mismatch_rejected(self, api_client):
        response = api_client.post(
            reverse("users:register"),
            {
                "email": "a@example.com",
                "full_name": "A",
                "password": "Correct-Horse-9182",
                "password_confirm": "Different-Horse-9182",
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "password_confirm" in response.data

    def test_weak_password_rejected(self, api_client):
        response = api_client.post(
            reverse("users:register"),
            {
                "email": "a@example.com",
                "full_name": "A",
                "password": "password12",
                "password_confirm": "password12",
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "password" in response.data

    def test_terms_must_be_accepted(self, api_client):
        response = api_client.post(
            reverse("users:register"),
            {
                "email": "a@example.com",
                "full_name": "A",
                "password": "Correct-Horse-9182",
                "password_confirm": "Correct-Horse-9182",
                "accept_terms": False,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "accept_terms" in response.data

    def test_duplicate_email_does_not_leak_existence(self, api_client, customer):
        response = api_client.post(
            reverse("users:register"),
            {
                "email": "AYESHA@example.com",
                "full_name": "Impostor",
                "password": "Correct-Horse-9182",
                "password_confirm": "Correct-Horse-9182",
                "accept_terms": True,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "cannot be registered" in str(response.data["email"][0])
        assert "already" not in str(response.data["email"][0]).lower()


class TestTokenIssuance:
    def test_token_contains_ai_engine_claims(self, customer):
        from apps.users.serializers import FerashaTokenObtainPairSerializer

        token = FerashaTokenObtainPairSerializer.get_token(customer)
        assert token["email"] == customer.email
        assert token["role"] == UserRole.CUSTOMER
        assert token["is_back_office"] is False
        assert token["email_verified"] is False

    def test_login_returns_user_payload(self, api_client, customer):
        response = api_client.post(
            reverse("users:token-obtain-pair"),
            {"email": customer.email, "password": "Correct-Horse-9182"},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["user"]["id"] == str(customer.id)

    def test_bad_credentials_rejected(self, api_client, customer):
        response = api_client.post(
            reverse("users:token-obtain-pair"),
            {"email": customer.email, "password": "wrong-password-here"},
            format="json",
        )
        assert response.status_code == 401

    def test_inactive_account_cannot_log_in(self, api_client, customer):
        customer.is_active = False
        customer.save(update_fields=["is_active"])
        response = api_client.post(
            reverse("users:token-obtain-pair"),
            {"email": customer.email, "password": "Correct-Horse-9182"},
            format="json",
        )
        assert response.status_code == 401

    def test_back_office_claim_true_for_staff(self, staff_user):
        from apps.users.serializers import FerashaTokenObtainPairSerializer

        token = FerashaTokenObtainPairSerializer.get_token(staff_user)
        assert token["is_back_office"] is True


class TestCurrentUser:
    def test_requires_authentication(self, api_client):
        assert api_client.get(reverse("users:current-user")).status_code == 401

    def test_returns_own_profile(self, auth_client, customer):
        response = auth_client.get(reverse("users:current-user"))
        assert response.status_code == 200
        assert response.data["email"] == customer.email

    def test_role_is_not_self_assignable(self, auth_client, customer):
        response = auth_client.patch(
            reverse("users:current-user"), {"role": UserRole.ADMIN}, format="json"
        )
        assert response.status_code == 200
        customer.refresh_from_db()
        assert customer.role == UserRole.CUSTOMER

    def test_unknown_preference_key_rejected(self, auth_client):
        response = auth_client.patch(
            reverse("users:current-user"),
            {"preferences": {"nonsense_key": True}},
            format="json",
        )
        assert response.status_code == 400
        assert "preferences" in response.data

    def test_valid_preferences_accepted(self, auth_client, customer):
        response = auth_client.patch(
            reverse("users:current-user"),
            {"preferences": {"hide_model_faces": True, "preferred_unit_system": "inch"}},
            format="json",
        )
        assert response.status_code == 200
        customer.refresh_from_db()
        assert customer.preferences["hide_model_faces"] is True


class TestAddressIsolation:
    """A customer must never see another customer's address book."""

    def _make_address(self, user, **kw):
        defaults = dict(
            recipient_name="Ayesha Khan",
            phone="+919820012345",
            line1="12 Altamount Road",
            city="Mumbai",
            state_code="MH",
            postal_code="400026",
            country_code="IN",
        )
        defaults.update(kw)
        return Address.objects.create(user=user, **defaults)

    def test_list_excludes_other_users_addresses(self, auth_client, customer, other_customer):
        self._make_address(customer)
        self._make_address(other_customer, recipient_name="Zainab Ali")

        response = auth_client.get(reverse("users:address-list"))
        assert response.status_code == 200
        names = [a["recipient_name"] for a in response.data["results"]]
        assert names == ["Ayesha Khan"]

    def test_cannot_retrieve_foreign_address(self, auth_client, other_customer):
        foreign = self._make_address(other_customer, recipient_name="Zainab Ali")
        response = auth_client.get(reverse("users:address-detail", args=[foreign.id]))
        assert response.status_code == 404

    def test_first_address_becomes_default(self, auth_client):
        response = auth_client.post(
            reverse("users:address-list"),
            {
                "recipient_name": "Ayesha Khan",
                "phone": "+919820012345",
                "line1": "12 Altamount Road",
                "city": "Mumbai",
                "state_code": "MH",
                "postal_code": "400026",
                "country_code": "IN",
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        assert response.data["is_default"] is True

    def test_setting_new_default_unsets_previous(self, auth_client, customer):
        first = self._make_address(customer, is_default=True)
        response = auth_client.post(
            reverse("users:address-list"),
            {
                "recipient_name": "Ayesha Khan (Office)",
                "phone": "+919820012345",
                "line1": "Nariman Point",
                "city": "Mumbai",
                "state_code": "MH",
                "postal_code": "400021",
                "country_code": "IN",
                "is_default": True,
            },
            format="json",
        )
        assert response.status_code == 201, response.data
        first.refresh_from_db()
        assert first.is_default is False


class TestAddressValidation:
    def _post(self, client, **overrides):
        payload = {
            "recipient_name": "Ayesha Khan",
            "phone": "+919820012345",
            "line1": "12 Altamount Road",
            "city": "Mumbai",
            "state_code": "MH",
            "postal_code": "400026",
            "country_code": "IN",
        }
        payload.update(overrides)
        return client.post(reverse("users:address-list"), payload, format="json")

    def test_indian_address_requires_state(self, auth_client):
        response = self._post(auth_client, state_code="")
        assert response.status_code == 400
        assert "state_code" in response.data

    def test_unknown_state_rejected(self, auth_client):
        response = self._post(auth_client, state_code="ZZ")
        assert response.status_code == 400

    def test_pin_code_must_be_six_digits(self, auth_client):
        response = self._post(auth_client, postal_code="4002")
        assert response.status_code == 400
        assert "postal_code" in response.data

    def test_gstin_state_prefix_must_match(self, auth_client):
        # 07 is Delhi, address is Maharashtra (27).
        response = self._post(auth_client, gstin="07AABCU9603R1ZM")
        assert response.status_code == 400
        assert "gstin" in response.data

    def test_matching_gstin_accepted(self, auth_client):
        response = self._post(auth_client, gstin="27AABCU9603R1ZM")
        assert response.status_code == 201, response.data

    def test_international_address_needs_no_state(self, auth_client):
        response = self._post(
            auth_client, country_code="AE", state_code="", postal_code="00000", city="Dubai"
        )
        assert response.status_code == 201, response.data


class TestPasswordChange:
    def test_requires_correct_current_password(self, auth_client):
        response = auth_client.post(
            reverse("users:password-change"),
            {
                "current_password": "wrong-password",
                "new_password": "Brand-New-Pass-77",
                "new_password_confirm": "Brand-New-Pass-77",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "current_password" in response.data

    def test_successful_change(self, auth_client, customer):
        response = auth_client.post(
            reverse("users:password-change"),
            {
                "current_password": "Correct-Horse-9182",
                "new_password": "Brand-New-Pass-77",
                "new_password_confirm": "Brand-New-Pass-77",
            },
            format="json",
        )
        assert response.status_code == 200, response.data
        customer.refresh_from_db()
        assert customer.check_password("Brand-New-Pass-77")

    def test_new_password_must_differ(self, auth_client):
        response = auth_client.post(
            reverse("users:password-change"),
            {
                "current_password": "Correct-Horse-9182",
                "new_password": "Correct-Horse-9182",
                "new_password_confirm": "Correct-Horse-9182",
            },
            format="json",
        )
        assert response.status_code == 400


class TestUserModel:
    def test_email_normalised_to_lowercase(self, db):
        user = User.objects.create_user(
            email="MiXeD@Example.COM", password="Correct-Horse-9182", full_name="Mixed Case"
        )
        assert user.email == "mixed@example.com"

    def test_superuser_defaults(self, db):
        admin = User.objects.create_superuser(
            email="admin@ferasha.com", password="Correct-Horse-9182", full_name="Admin"
        )
        assert admin.is_staff and admin.is_superuser
        assert admin.role == UserRole.ADMIN
        assert admin.is_back_office is True

    def test_email_is_required(self, db):
        with pytest.raises(ValueError, match="email address is required"):
            User.objects.create_user(email="", password="x", full_name="No Email")

    def test_str_representation(self, customer):
        assert str(customer) == "Ayesha Khan <ayesha@example.com>"
