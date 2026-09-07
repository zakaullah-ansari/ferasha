from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FitProfileViewSet, MeasurementGuideView

router = DefaultRouter()
router.register("fit-profiles", FitProfileViewSet, basename="fit-profile")

app_name = "tailoring"

urlpatterns = [
    path("tailoring/measurement-guide/", MeasurementGuideView.as_view(), name="measurement-guide"),
    path("tailoring/", include(router.urls)),
]
