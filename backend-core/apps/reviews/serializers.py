"""Review serializers with verified-purchase enforcement."""

from __future__ import annotations

from rest_framework import serializers

from apps.orders.models import OrderLine, OrderStatus

from .models import Review, ReviewPhoto, ReviewStatus


class ReviewPhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ReviewPhoto
        fields = ("id", "url", "display_order")

    def get_url(self, obj) -> str | None:
        """Customer photos pass the same privacy pipeline as vendor imagery."""
        return obj.asset.public_url


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_verified_purchase = serializers.BooleanField(read_only=True)
    photos = ReviewPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = (
            "id", "product", "author_name", "rating", "title", "body",
            "fit_feedback", "modesty_as_described", "is_verified_purchase",
            "helpful_count", "photos", "created_at",
        )
        read_only_fields = (
            "id", "author_name", "is_verified_purchase", "helpful_count",
            "photos", "created_at",
        )

    def get_author_name(self, obj) -> str:
        """Only a first name is published - a full name plus a purchase history
        is more personal data than a review needs to expose."""
        full = (obj.author.full_name or "").strip()
        return full.split(" ")[0] if full else "Ferasha customer"

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        product = attrs.get("product") or getattr(self.instance, "product", None)

        if self.instance is None and Review.objects.filter(
            product=product, author=user
        ).exists():
            raise serializers.ValidationError(
                {"product": "You have already reviewed this product."}
            )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        product = validated_data["product"]

        # Link a delivered purchase if one exists. This drives the verified
        # badge and cannot be supplied by the client.
        line = (
            OrderLine.objects.filter(
                order__customer=user,
                order__status__in=[OrderStatus.DELIVERED, OrderStatus.RETURN_REQUESTED],
                variant__product=product,
            )
            .order_by("-created_at")
            .first()
        )
        validated_data["author"] = user
        validated_data["order_line"] = line
        validated_data["status"] = ReviewStatus.PENDING
        return super().create(validated_data)
