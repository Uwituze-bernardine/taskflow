from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import preferences as prefs
from .models import Notification, NotificationSettings
from .serializers import (
    NotificationPreferencesSerializer, NotificationSerializer, NotificationSettingsSerializer,
)


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """FR-060: notification history; read-only, scoped to the current user."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_read', 'category']

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        return Response({'count': self.get_queryset().filter(is_read=False).count()})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response(status=204)

    @action(detail=False, methods=['get', 'patch'], url_path='preferences')
    def preferences(self, request):
        """FR-059: read or change which categories of notification the current user gets."""
        user = request.user
        if request.method == 'PATCH':
            serializer = NotificationPreferencesSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            stored = dict(user.notification_preferences or {})
            stored.update(serializer.validated_data)
            user.notification_preferences = stored
            user.save(update_fields=['notification_preferences'])
        return Response(prefs.effective(user))


class NotificationSettingsView(RetrieveUpdateAPIView):
    """FR-095: a singleton - everyone can read it, only administrators can change it."""
    serializer_class = NotificationSettingsSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        from users.permissions import IsAdmin

        if self.request.method == 'PATCH':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_object(self):
        return NotificationSettings.current()
