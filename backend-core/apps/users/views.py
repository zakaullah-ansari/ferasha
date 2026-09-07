"""Identity API: registration, JWT issuance, profile and address management."""

from __future__ import annotations

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Address
from .permissions import IsOwnerOrBackOffice
from .serializers import (
    AddressSerializer,
    FerashaTokenObtainPairSerializer,
    PasswordChangeSerializer,
    RegistrationSerializer,
    UserSerializer,
)


class LoginRateThrottle(AnonRateThrottle):
    """Tighter bucket for credential endpoints than the global anon rate."""

    scope = "login"
    rate = "10/min"


class FerashaTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/token/ - exchange credentials for a JWT pair."""

    serializer_class = FerashaTokenObtainPairSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)


class RegistrationView(CreateAPIView):
    """POST /api/v1/auth/register/ - public self-service signup."""

    serializer_class = RegistrationSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (LoginRateThrottle,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = FerashaTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "user": UserSerializer(user, context=self.get_serializer_context()).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ - blacklist the supplied refresh token."""

    permission_classes = (IsAuthenticated,)

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

    @transaction.atomic
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password updated. Please sign in again on other devices."},
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
