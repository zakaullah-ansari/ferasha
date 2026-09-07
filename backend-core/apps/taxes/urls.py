from __future__ import annotations

from django.urls import path

from .views import TaxQuoteView, TaxRateReferenceView

app_name = "taxes"

urlpatterns = [
    path("tax/quote/", TaxQuoteView.as_view(), name="tax-quote"),
    path("tax/reference/", TaxRateReferenceView.as_view(), name="tax-reference"),
]
