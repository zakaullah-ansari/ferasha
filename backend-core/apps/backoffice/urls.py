from __future__ import annotations

from django.urls import path

from .views import DashboardSummaryView

app_name = "backoffice"

urlpatterns = [
    path("back-office/summary/", DashboardSummaryView.as_view(), name="summary"),
]
