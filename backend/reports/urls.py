from django.urls import path

from .views import ReportExportView, ReportSummaryView

urlpatterns = [
    path('summary/', ReportSummaryView.as_view(), name='report-summary'),
    path('export/', ReportExportView.as_view(), name='report-export'),
]
