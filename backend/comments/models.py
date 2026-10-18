from django.conf import settings
from django.db import models

from tasks.models import Task


class Comment(models.Model):
    """FR-043 to FR-048: task discussion."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    # FR-045: computed from @username mentions in `body` (see comments/mentions.py) rather
    # than a field the client sets directly, so a mention always means "this text really
    # names someone who can see the task", not just "whoever the client claims to tag".
    mentioned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='mentioned_in_comments', blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)  # FR-044: chronological order
    edited_at = models.DateTimeField(null=True, blank=True)
    # FR-047: comments are soft-deleted, so the discussion history is preserved even
    # after a removal; the body stays in the database but the API hides it (see the serializer).
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='deleted_comments',
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author} on {self.task}'


class CommentRevision(models.Model):
    """An immutable copy of the previous body whenever a comment is edited."""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='revisions')
    body = models.TextField()
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='comment_revisions',
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['saved_at']
