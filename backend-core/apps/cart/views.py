"""Cart API. One active cart per authenticated customer."""

from __future__ import annotations

from django.db.models import Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import services
from .models import Cart, CartItem
from .serializers import (
    AddItemSerializer,
    CartSerializer,
    MergeSerializer,
    SetQuantitySerializer,
)


class CartViewSet(viewsets.ViewSet):
    """GET the bag, add / set / remove lines, merge a guest bag at sign-in."""

    permission_classes = (IsAuthenticated,)

    def _render(self, cart: Cart, *, status_code: int = status.HTTP_200_OK, **extra) -> Response:
        # Re-read with the relations the serializer walks, so a bag of N lines
        # costs a fixed number of queries rather than 3N.
        cart = Cart.objects.prefetch_related(
            Prefetch(
                "items",
                queryset=CartItem.objects.select_related("variant__product").order_by(
                    "created_at"
                ),
            )
        ).get(pk=cart.pk)
        return Response({**CartSerializer(cart).data, **extra}, status=status_code)

    def list(self, request):
        return self._render(services.get_active_cart(request.user))

    def create(self, request):
        payload = AddItemSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cart = services.get_active_cart(request.user)
        try:
            services.add_item(cart, **payload.validated_data)
        except services.CartError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._render(cart, status_code=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="set-quantity")
    def set_quantity(self, request):
        payload = SetQuantitySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cart = services.get_active_cart(request.user)
        try:
            services.set_quantity(cart, **payload.validated_data)
        except services.CartError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._render(cart)

    @action(detail=False, methods=["delete"], url_path=r"items/(?P<variant_id>[0-9a-f-]{36})")
    def remove_item(self, request, variant_id=None):
        cart = services.get_active_cart(request.user)
        if not services.remove_item(cart, variant_id):
            return Response(
                {"detail": "That item is not in your bag."}, status=status.HTTP_404_NOT_FOUND
            )
        return self._render(cart)

    @action(detail=False, methods=["post"])
    def clear(self, request):
        cart = services.get_active_cart(request.user)
        services.clear(cart)
        return self._render(cart)

    @action(detail=False, methods=["post"])
    def merge(self, request):
        payload = MergeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cart = services.get_active_cart(request.user)
        skipped = services.merge_items(cart, payload.validated_data["items"])
        return self._render(cart, skipped=skipped)
