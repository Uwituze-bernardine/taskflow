from rest_framework import mixins, viewsets

from users.permissions import IsManager
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    FR-088: authorized users view activity history.
    FR-089: read-only for everyone via the API - only Django admin/superusers
    can alter records directly, ordinary users cannot modify audit records.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsManager]
    filterset_fields = ['model_name', 'object_id', 'actor']
