"""Read-only API for the owner dashboard (frontend /dashboard).

Editing stays in the Django admin; this serves the numbers and queues the
owner checks first.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsBackOffice

from .services import dashboard_summary


class DashboardSummaryView(APIView):
    permission_classes = (IsBackOffice,)

    @extend_schema(summary="Owner dashboard: revenue, open orders by stage, queues")
    def get(self, request):
        return Response(dashboard_summary())
