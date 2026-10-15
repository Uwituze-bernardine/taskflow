from django.conf import settings
from django.db import models

from tasks.models import Task

DEFAULT_ALLOWED_EXTENSIONS = 'pdf,png,jpg,jpeg,gif,docx,doc,xlsx,xls,pptx,csv,txt,zip'
DEFAULT_MAX_SIZE_MB = 25


class AttachmentSettings(models.Model):
    """
    FR-052: the configured file size and type restrictions. A single row (id=1);
    administrators change it, everyone can read it so the upload form can show the limits.
    """
    allowed_extensions = models.CharField(max_length=500, default=DEFAULT_ALLOWED_EXTENSIONS)
    max_size_mb = models.PositiveIntegerField(default=DEFAULT_MAX_SIZE_MB)

    @classmethod
    def current(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def extension_list(self):
        return [e.strip().lower() for e in self.allowed_extensions.split(',') if e.strip()]

    def __str__(self):
        return f'Attachment settings (≤{self.max_size_mb}MB, {self.allowed_extensions})'


class Attachment(models.Model):
    """FR-049 to FR-053: files attached to a task."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/%Y/%m/')
    filename = models.CharField(max_length=255)  # FR-051
    content_type = models.CharField(max_length=150, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='uploaded_attachments'
    )  # FR-051
    uploaded_at = models.DateTimeField(auto_now_add=True)  # FR-051
    size_bytes = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.filename
