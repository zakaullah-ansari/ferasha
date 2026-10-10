"""Order API. Read + atelier transitions; checkout arrives in Phase 5."""

from __future__ import annotations

from django.db.models import Count
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsAtelierOrBackOffice, IsOwnerOrBackOffice

from .models import Order
from .serializers import OrderDetailSerializer, OrderListSerializer
from .state_machine import IllegalTransition, transition_order


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated, IsOwnerOrBackOffice)
    lookup_field = "order_number"

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()

        qs = (
            Order.objects.select_related("tax_snapshot", "customer")
            .prefetch_related("lines__tailoring_spec", "events")
            .annotate(line_count=Count("lines", distinct=True))
        )
        if user.is_back_office:
            return qs
        if user.role in {"tailor", "stylist"}:
            return qs.filter(
                status__in=[
                    "measurement_review", "in_atelier", "stitching", "quality_check",
                ]
            )
        return qs.filter(customer=user)

    def get_serializer_class(self):
        return OrderDetailSerializer if self.action == "retrieve" else OrderListSerializer

    @extend_schema(summary="Advance an order through the atelier pipeline")
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsAtelierOrBackOffice],
    )
    def transition(self, request, order_number=None):
        order = self.get_object()
        target = request.data.get("status")
        if not target:
            return Response(
                {"detail": "A target status is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            transition_order(
                order,
                target,
                actor=request.user,
                reason=str(request.data.get("reason", ""))[:300],
            )
        except IllegalTransition as exc:
            # A 409 rather than a 400: the request is well-formed, but conflicts
            # with the order's current state.
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        order.refresh_from_db()
        return Response(
            OrderDetailSerializer(order, context={"request": request}).data
        )
