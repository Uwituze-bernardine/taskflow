from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """FR-085 to FR-089: accountability/traceability audit trail."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audit_entries'
    )  # FR-086
    action = models.CharField(max_length=100)  # e.g. 'task.updated', 'task.status_changed'
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    changes = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)  # FR-087

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.timestamp} {self.actor} {self.action} {self.model_name}#{self.object_id}'
