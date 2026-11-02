from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    size = serializers.CharField(source="variant.size", read_only=True)
    colour = serializers.CharField(source="variant.colour", read_only=True)
    unit_price = serializers.DecimalField(
        source="variant.price", max_digits=12, decimal_places=2, read_only=True
    )
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "variant_id", "sku", "product_name", "product_slug",
            "size", "colour", "quantity", "unit_price", "line_total",
        )
        read_only_fields = fields

    def get_line_total(self, obj: CartItem) -> str:
        return str(obj.variant.price * obj.quantity)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("items", "total_items", "subtotal")
        read_only_fields = fields

    def get_total_items(self, obj: Cart) -> int:
        return sum(item.quantity for item in obj.items.all())

    def get_subtotal(self, obj: Cart) -> str:
        total = sum(
            (item.variant.price * item.quantity for item in obj.items.all()), Decimal("0.00")
        )
        return str(total)


class AddItemSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class SetQuantitySerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=0)


class MergeSerializer(serializers.Serializer):
    items = AddItemSerializer(many=True, allow_empty=True)
    replace = serializers.BooleanField(default=False)
