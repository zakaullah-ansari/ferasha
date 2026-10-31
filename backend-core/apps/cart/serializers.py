from __future__ import annotations

from rest_framework import serializers
from .models import Cart, CartItem
from apps.catalog.models import ProductVariant

class CartItemSerializer(serializers.ModelSerializer):
    variant_details = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ("id", "variant", "quantity", "variant_details")

    def get_variant_details(self, obj):
        variant = obj.variant
        return {
            "sku": variant.sku,
            "colour": variant.colour,
            "size": variant.size,
            "price": variant.price, # Assuming price is a property/field
        }

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Cart
        fields = ("id", "items", "total_items", "total_price")

    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_total_price(self, obj):
        # Note: In a real system, we would use a specialized
        # lazy-loading sum query to avoid N+1 here.
        total = 0
        for item in obj.items.all():
            # We access the price via the variant
            # Since ProductVariant.price is a property in the model,
            # we handle it here.
            total += item.variant.price * item.quantity
        return total
