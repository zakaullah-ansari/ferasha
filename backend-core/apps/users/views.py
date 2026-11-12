"""Identity API: registration, JWT issuance, profile and address management."""

from __future__ import annotations

import hashlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext as _
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .emails import (
    send_email_verification,
    send_password_changed_notice,
    send_password_reset,
)
from .models import Address
from .permissions import IsOwnerOrBackOffice
from .serializers import (
    AddressSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationRequestSerializer,
    FerashaTokenObtainPairSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationSerializer,
    SocialCallbackSerializer,
    UserSerializer,
)
from .social import SocialAuthError, configured_provider, configured_providers, sign_in

User = get_user_model()


class LoginRateThrottle(AnonRateThrottle):
    """Tighter bucket for credential endpoints than the global anon rate."""

    scope = "login"
    rate = "10/min"


class CredentialEmailThrottle(AnonRateThrottle):
    """Bucket for endpoints that send mail to an arbitrary address.

    Rate limited harder than login: an unthrottled endpoint here is both an
    account-enumeration oracle (via timing) and a way to use Ferasha's sending
    reputation to spam a third party.
    """

    scope = "credential_email"
    rate = "5/hour"


def _login_failure_key(email: object) -> str:
    # Hashed so the cache never holds email addresses.
    normalised = str(email or "").strip().lower()
    return "login-fail:" + hashlib.sha256(normalised.encode()).hexdigest()


class FerashaTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/token/ - exchange credentials for a JWT pair.

    Two limits: per IP (``LoginRateThrottle``) and per account. The second
    stops guessing spread across many IPs; it counts unknown emails exactly
    like real ones, so it reveals nothing about who has an account.
    """

    serializer_class = FerashaTokenObtainPairSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)

    def post(self, request, *args, **kwargs):
        key = _login_failure_key(request.data.get("email"))
        if cache.get(key, 0) >= settings.LOGIN_FAILURE_LIMIT:
            return Response(
                {
                    "detail": _(
                        "Too many wrong passwords for this account. Please wait 15 minutes, "
                        "or reset your password."
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            # Wrong password or unknown email (simplejwt raises, DRF renders the 401).
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=settings.LOGIN_FAILURE_WINDOW_SECONDS)
            raise
        cache.delete(key)
        return response


class RegistrationView(CreateAPIView):
    """POST /api/v1/auth/register/ - public self-service signup."""

    serializer_class = RegistrationSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_email_verification(user)

        refresh = FerashaTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "user": UserSerializer(user, context=self.get_serializer_context()).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class SocialProvidersView(APIView):
    """GET /api/v1/auth/social/providers/ - the outside sign-ins switched on here."""

    permission_classes = (AllowAny,)
    serializer_class = None

    @extend_schema(
        summary="Social sign-in providers",
        description="Only providers with keys configured are listed; the storefront shows a button per entry.",
        responses=inline_serializer(
            name="SocialProviders",
            fields={
                "providers": drf_serializers.ListField(
                    child=inline_serializer(
                        name="SocialProvider",
                        fields={"id": drf_serializers.CharField(), "name": drf_serializers.CharField()},
                    )
                )
            },
        ),
        tags=["auth"],
    )
    def get(self, request):
        return Response(
            {"providers": [{"id": p.id, "name": p.name} for p in configured_providers()]}
        )


class SocialAuthorizeView(APIView):
    """POST /api/v1/auth/social/<provider>/authorize/ - start a provider sign-in.

    Returns the provider URL plus the state, PKCE verifier and nonce the
    storefront keeps (httpOnly cookie) until the browser returns.
    """

    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)
    serializer_class = None

    @extend_schema(
        summary="Start a social sign-in",
        request=None,
        responses={
            200: inline_serializer(
                name="SocialAuthorization",
                fields={
                    "authorization_url": drf_serializers.URLField(),
                    "state": drf_serializers.CharField(),
                    "code_verifier": drf_serializers.CharField(),
                    "nonce": drf_serializers.CharField(),
                },
            ),
            404: OpenApiResponse(description="Unknown or unconfigured provider."),
        },
        tags=["auth"],
    )
    def post(self, request, provider: str):
        oauth = configured_provider(provider)
        if oauth is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        started = oauth.authorize()
        return Response(
            {
                "authorization_url": started.authorization_url,
                "state": started.state,
                "code_verifier": started.code_verifier,
                "nonce": started.nonce,
            }
        )


class SocialCallbackView(APIView):
    """POST /api/v1/auth/social/<provider>/ - finish a provider sign-in, issue JWTs."""

    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)
    serializer_class = SocialCallbackSerializer

    @extend_schema(
        summary="Finish a social sign-in",
        request=SocialCallbackSerializer,
        responses={
            200: inline_serializer(
                name="SocialSession",
                fields={
                    "user": UserSerializer(),
                    "access": drf_serializers.CharField(),
                    "refresh": drf_serializers.CharField(),
                    "created": drf_serializers.BooleanField(),
                },
            ),
            400: OpenApiResponse(description="The provider's answer could not be verified."),
            403: OpenApiResponse(description="Deactivated or back-office account."),
            409: OpenApiResponse(description="Email belongs to an account this provider cannot vouch for."),
        },
        tags=["auth"],
    )
    def post(self, request, provider: str):
        oauth = configured_provider(provider)
        if oauth is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SocialCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            identity = oauth.exchange(**serializer.validated_data)
            user, created = sign_in(identity)
        except SocialAuthError as exc:
            return Response({"detail": str(exc)}, status=exc.status)
        refresh = FerashaTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "user": UserSerializer(user, context={"request": request, "view": self}).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "created": created,
            }
        )


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ - blacklist the supplied refresh token."""

    permission_classes = (IsAuthenticated,)
    serializer_class = None

    @extend_schema(
        summary="Sign out",
        description=(
            "Blacklists the supplied refresh token. Idempotent: replaying an "
            "already-blacklisted token still returns 205."
        ),
        request=inline_serializer(
            name="LogoutRequest",
            fields={"refresh": drf_serializers.CharField(help_text="The refresh token to revoke.")},
        ),
        responses={
            205: OpenApiResponse(description="Session ended; client should discard both tokens."),
            400: OpenApiResponse(description="No refresh token supplied."),
        },
        tags=["auth"],
    )
    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response(
                {"detail": "A refresh token is required to log out."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            # Already expired or blacklisted - logout is idempotent.
            return Response(status=status.HTTP_205_RESET_CONTENT)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class CurrentUserView(RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/auth/me/"""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return (
            type(self.request.user)
            .objects.prefetch_related("addresses")
            .get(pk=self.request.user.pk)
        )


class PasswordChangeView(APIView):
    """POST /api/v1/auth/password/change/"""

    permission_classes = (IsAuthenticated,)
    serializer_class = PasswordChangeSerializer

    @extend_schema(
        summary="Change password",
        description=(
            "Rotates the password of the authenticated user. All other refresh "
            "tokens are revoked and an out-of-band notification email is sent."
        ),
        request=PasswordChangeSerializer,
        responses={
            200: inline_serializer(
                name="PasswordChangeResponse",
                fields={"detail": drf_serializers.CharField()},
            ),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["auth"],
    )
    @transaction.atomic
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_password_changed_notice(user)
        return Response(
            {"detail": "Password updated. All other sessions have been signed out."},
            status=status.HTTP_200_OK,
        )

    def get_serializer_context(self):
        return {"request": self.request, "view": self}


class AddressViewSet(viewsets.ModelViewSet):
    """CRUD for the authenticated user's address book."""

    serializer_class = AddressSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrBackOffice)
    filterset_fields = ("kind", "country_code", "state_code", "is_default")

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Address.objects.none()
        # Back office still scopes to a user via ?user= to avoid accidental
        # enumeration of the entire address book.
        queryset = Address.objects.select_related("user")
        if user.is_back_office:
            requested = self.request.query_params.get("user")
            return queryset.filter(user_id=requested) if requested else queryset.filter(user=user)
        return queryset.filter(user=user)


# --------------------------------------------------------------------------- #
# Email verification and password reset
#
# Every endpoint below returns an identical response whether or not the address
# corresponds to a real account. Anonymous callers must not be able to probe
# membership - see the same rule in RegistrationSerializer.validate_email.
# --------------------------------------------------------------------------- #

_NEUTRAL_EMAIL_RESPONSE = {
    "detail": "If that email address matches an account, a message is on its way.",
}


class EmailVerificationRequestView(APIView):
    """POST /api/v1/auth/email/verify/request/ - (re)send a verification link."""

    permission_classes = (AllowAny,)
    throttle_classes = (CredentialEmailThrottle,)
    serializer_class = EmailVerificationRequestSerializer

    def post(self, request):
        serializer = EmailVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True
        ).first()
        # Silently skip already-verified accounts: re-sending would let a
        # caller distinguish verified from unverified addresses.
        if user is not None and not user.email_is_verified:
            send_email_verification(user)
        return Response(_NEUTRAL_EMAIL_RESPONSE, status=status.HTTP_202_ACCEPTED)


class EmailVerificationConfirmView(APIView):
    """POST /api/v1/auth/email/verify/confirm/ - consume a verification token."""

    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)
    serializer_class = EmailVerificationConfirmSerializer

    @transaction.atomic
    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "detail": "Email address confirmed.",
                "user": UserSerializer(user, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """POST /api/v1/auth/password/reset/request/"""

    permission_classes = (AllowAny,)
    throttle_classes = (CredentialEmailThrottle,)
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True
        ).first()
        if user is not None:
            send_password_reset(user)
        return Response(_NEUTRAL_EMAIL_RESPONSE, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    """POST /api/v1/auth/password/reset/confirm/

    On success every refresh token is revoked: a reset is the remedy for a
    suspected compromise, so any session the attacker holds must die with it.
    """

    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)
    serializer_class = PasswordResetConfirmSerializer

    @transaction.atomic
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_password_changed_notice(user)
        return Response(
            {"detail": "Password reset. Please sign in with your new password."},
            status=status.HTTP_200_OK,
        )
