from django.utils import timezone
from rest_framework import viewsets

from notifications.models import Category
from notifications.services import notify
from tasks.access import visible_tasks
from .models import Comment
from .permissions import CommentPermission
from .serializers import CommentSerializer


class CommentViewSet(viewsets.ModelViewSet):
    """FR-043 create, FR-044 chronological order, FR-045/046 mentions, FR-047/048 history & moderation."""

    serializer_class = CommentSerializer
    permission_classes = [CommentPermission]
    filterset_fields = ['task']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        # FR-043: comments are only visible on tasks the current user may see.
        # Meta.ordering (created_at) gives FR-044's chronological order.
        return (
            Comment.objects.filter(task__in=visible_tasks(self.request.user))
            .select_related('author', 'task')
            .prefetch_related('mentioned_users', 'revisions')
        )

    def _notify_mentions(self, comment, exclude_ids=()):
        for user in comment.mentioned_users.exclude(pk__in=exclude_ids):
            if user.id != comment.author_id:
                notify(user, f'{comment.author.get_full_name() or comment.author.username} mentioned you in a comment.', task=comment.task, category=Category.MENTIONED)  # FR-046

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        self._notify_mentions(comment)

    def perform_update(self, serializer):
        before = set(serializer.instance.mentioned_users.values_list('id', flat=True))
        old_body = serializer.instance.body
        new_body = serializer.validated_data.get('body', old_body)
        if new_body != old_body:
            from .models import CommentRevision
            CommentRevision.objects.create(
                comment=serializer.instance, body=old_body, edited_by=self.request.user,
            )
            getattr(serializer.instance, '_prefetched_objects_cache', {}).pop('revisions', None)
        comment = serializer.save(edited_at=timezone.now())  # FR-048
        self._notify_mentions(comment, exclude_ids=before)  # only notify newly-added mentions

    def perform_destroy(self, instance):
        # FR-047/048: soft delete, so the discussion history is preserved.
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.deleted_by = self.request.user
        instance.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
