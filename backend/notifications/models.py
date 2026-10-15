from django.conf import settings
from django.db import models


class Category(models.TextChoices):
    """Matches the keys in notifications/preferences.py."""
    ASSIGNED = 'assigned', 'Task assigned'  # FR-054
    STATUS_CHANGED = 'status_changed', 'Status changed'  # FR-055
    MENTIONED = 'mentioned', 'Mentioned in a comment'  # FR-056
    DUE_SOON = 'due_soon', 'Due soon'  # FR-057
    OVERDUE = 'overdue', 'Overdue'  # FR-058
    OTHER = 'other', 'Other'


class Notification(models.Model):
    """FR-054 to FR-060: notifications and reminders."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    message = models.CharField(max_length=500)
    task = models.ForeignKey(
        'tasks.Task', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  # FR-060: notification history

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['task', 'category', 'recipient'])]  # used to de-duplicate reminders

    def __str__(self):
        return f'{self.recipient}: {self.message[:40]}'


class NotificationSettings(models.Model):
    """FR-095: system-wide notification configuration an administrator controls."""

    due_soon_days = models.PositiveIntegerField(
        default=2, help_text='How many days before the due date a task becomes "due soon" (FR-057).'
    )

    @classmethod
    def current(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'Notification settings (due soon: {self.due_soon_days} day(s) ahead)'
