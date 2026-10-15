from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.access import visible_projects
from .export import report_to_csv
from .metrics import build_report, default_range
from .permissions import IsManagerOrAdmin
from .serializers import ReportFiltersSerializer, ReportSerializer


def _resolve_filters(request):
    """FR-082: parse & validate ?start=&end=&project=, returning (start, end, project|None)."""
    filters = ReportFiltersSerializer(data=request.query_params)
    filters.is_valid(raise_exception=True)
    default_start, default_end = default_range()
    start = filters.validated_data.get('start', default_start)
    end = filters.validated_data.get('end', default_end)
    project = None
    if 'project' in filters.validated_data:
        project = visible_projects(request.user).filter(pk=filters.validated_data['project']).first()
        if project is None:
            from rest_framework.exceptions import NotFound
            raise NotFound('No such project.')
    return start, end, project


class ReportSummaryView(APIView):
    """FR-078 to FR-084: GET /api/reports/summary/?start=&end=&project= - the report as JSON."""
    permission_classes = [IsManagerOrAdmin]

    def get(self, request):
        start, end, project = _resolve_filters(request)
        report = build_report(request.user, start, end, project)
        return Response(ReportSerializer(report).data)


class ReportExportView(APIView):
    """FR-083: GET /api/reports/export/?start=&end=&project= - the same report as a CSV download."""
    permission_classes = [IsManagerOrAdmin]

    def get(self, request):
        start, end, project = _resolve_filters(request)
        report = build_report(request.user, start, end, project)
        csv_text = report_to_csv(report)
        response = HttpResponse(csv_text, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="report_{start}_to_{end}.csv"'
        return response
