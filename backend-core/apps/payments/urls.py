from django.urls import path
from .views import PaymentWebhookView

urlpatterns = [
    path("webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
]
