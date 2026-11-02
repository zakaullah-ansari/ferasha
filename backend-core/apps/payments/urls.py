from __future__ import annotations

from django.urls import path

from .views import InitiatePaymentView, RazorpayWebhookView, VerifyPaymentView

app_name = "payments"

urlpatterns = [
    path(
        "payments/orders/<str:order_number>/initiate/",
        InitiatePaymentView.as_view(),
        name="initiate",
    ),
    path(
        "payments/orders/<str:order_number>/verify/",
        VerifyPaymentView.as_view(),
        name="verify",
    ),
    path(
        "payments/webhooks/razorpay/",
        RazorpayWebhookView.as_view(),
        name="razorpay-webhook",
    ),
]
