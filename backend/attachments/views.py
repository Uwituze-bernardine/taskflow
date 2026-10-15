from django.http import FileResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from tasks.access import visible_tasks
from .models import Attachment, AttachmentSettings
from .permissions import AttachmentPermission
from .serializers import AttachmentSerializer, AttachmentSettingsSerializer


class AttachmentViewSet(viewsets.ModelViewSet):
    """FR-049 upload, FR-050 download, FR-051 metadata, FR-052 restrictions, FR-053 remove."""

    serializer_class = AttachmentSerializer
    permission_classes = [AttachmentPermission]
    filterset_fields = ['task']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        # FR-050: an attachment is only reachable - list, retrieve, or download -
        # through a task the current user may see.
        return (
            Attachment.objects.filter(task__in=visible_tasks(self.request.user))
            .select_related('uploaded_by', 'task')
        )

    def perform_create(self, serializer):
        file = self.request.FILES['file']
        serializer.save(
            uploaded_by=self.request.user,
            filename=file.name,
            content_type=getattr(file, 'content_type', '') or '',
            size_bytes=file.size,
        )

    def perform_destroy(self, instance):
        instance.file.delete(save=False)
        instance.delete()

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """FR-050: the only sanctioned way to read a file's bytes - always permission-checked."""
        attachment = self.get_object()
        response = FileResponse(attachment.file.open('rb'), as_attachment=True, filename=attachment.filename)
        if attachment.content_type:
            response['Content-Type'] = attachment.content_type
        return response


class AttachmentSettingsView(RetrieveUpdateAPIView):
    """FR-052: a singleton - everyone can read the current limits; only administrators can change them."""
    serializer_class = AttachmentSettingsSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        from users.permissions import IsAdmin

        if self.request.method == 'PATCH':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_object(self):
        return AttachmentSettings.current()
