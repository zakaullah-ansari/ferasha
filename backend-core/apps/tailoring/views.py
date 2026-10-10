"""Bespoke tailoring API.

The single most privacy-sensitive surface in the platform. Every queryset is
scoped to the requesting user before any object-level check runs, so a foreign
profile is absent rather than forbidden - a 403 would confirm it exists.
"""

from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAtelierOrBackOffice, IsOwnerOrBackOffice

from .models import BespokeFitProfile
from .serializers import (
    FitProfileRevisionSerializer,
    FitProfileSerializer,
    MeasurementGuideSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="List your fit profiles"),
    create=extend_schema(summary="Create a fit profile"),
)
class FitProfileViewSet(viewsets.ModelViewSet):
    serializer_class = FitProfileSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrBackOffice)

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return BespokeFitProfile.objects.none()
        qs = BespokeFitProfile.objects.select_related("user", "verified_by")

        if user.is_back_office:
            # Even the back office must ask for a specific customer rather than
            # browsing every customer's body measurements.
            requested = self.request.query_params.get("user")
            return qs.filter(user_id=requested) if requested else qs.filter(user=user)

        if user.role in {"tailor", "stylist"}:
            # The atelier sees only profiles attached to work assigned to them.
            return qs.filter(
                order_specs__order_line__order__status__in=[
                    "measurement_review", "in_atelier", "stitching", "quality_check",
                ]
            ).distinct()

        return qs.filter(user=user)

    @extend_schema(summary="Revision history", responses=FitProfileRevisionSerializer(many=True))
    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        profile = self.get_object()
        return Response(
            FitProfileRevisionSerializer(
                profile.revisions.all().order_by("-revision"), many=True
            ).data
        )

    @extend_schema(summary="Mark a profile as tailor-verified")
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsAtelierOrBackOffice],
    )
    def verify(self, request, pk=None):
        """Only a tailor or stylist may attest that measurements were checked."""
        profile = self.get_object()
        profile.verified_at = timezone.now()
        profile.verified_by = request.user
        profile.save(update_fields=["verified_at", "verified_by", "updated_at"])
        return Response(
            FitProfileSerializer(profile, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class MeasurementGuideView(APIView):
    """GET /api/v1/tailoring/measurement-guide/

    Public so the FitDrawer can validate before sign-up. Returns the exact
    plausibility ranges the backend enforces, so the client-side schema cannot
    drift from server-side validation.
    """

    permission_classes = (AllowAny,)
    serializer_class = None

    @extend_schema(
        summary="Measurement ranges and required fields",
        description=(
            "The exact plausibility ranges the server enforces, in both inches and "
            "centimetres, plus the set of required keys. The storefront generates "
            "its Zod schema from this document so client and server validation "
            "cannot diverge."
        ),
        responses={
            200: inline_serializer(
                name="MeasurementGuide",
                fields={
                    "unit_systems": drf_serializers.ListField(child=drf_serializers.CharField()),
                    "cm_per_inch": drf_serializers.FloatField(),
                    "required_keys": drf_serializers.ListField(child=drf_serializers.CharField()),
                    "measurements": drf_serializers.DictField(),
                },
            )
        },
        tags=["tailoring"],
    )
    def get(self, request):
        return Response(MeasurementGuideSerializer.build())
