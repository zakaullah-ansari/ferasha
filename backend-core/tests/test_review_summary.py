"""The review summary a product page shows: published reviews only."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.reviews.models import FitFeedback, Review, ReviewStatus
from tests.factories import make_product, make_user

pytestmark = pytest.mark.django_db

SUMMARY = reverse("reviews:review-summary")


def review(product, rating, *, status=ReviewStatus.PUBLISHED, fit="", modesty=None):
    return Review.objects.create(
        product=product, author=make_user(), rating=rating, status=status,
        fit_feedback=fit, modesty_as_described=modesty,
    )


def test_counts_only_published_reviews(api_client):
    product = make_product()
    review(product, 5, fit=FitFeedback.TRUE_TO_SIZE, modesty=True)
    review(product, 4, fit=FitFeedback.TRUE_TO_SIZE, modesty=True)
    review(product, 2, fit=FitFeedback.RAN_SMALL, modesty=False)
    review(product, 1, status=ReviewStatus.PENDING, fit=FitFeedback.RAN_LARGE, modesty=False)
    review(make_product(), 5)  # another product

    data = api_client.get(SUMMARY, {"product": product.pk}).json()

    assert data == {
        "count": 3,
        "average": "3.7",
        "distribution": {"1": 0, "2": 1, "3": 0, "4": 1, "5": 1},
        "fit": {"ran_small": 1, "true_to_size": 2, "ran_large": 0},
        "modesty_as_described": {"yes": 2, "no": 1},
    }


def test_a_product_without_reviews(api_client):
    data = api_client.get(SUMMARY, {"product": make_product().pk}).json()

    assert data["count"] == 0 and data["average"] is None


def test_the_product_is_required(api_client):
    assert api_client.get(SUMMARY).status_code == 400
