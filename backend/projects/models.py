from django.conf import settings
from django.db import models


class ProjectStatus(models.TextChoices):
    PLANNED = 'PLANNED', 'Planned'
    ACTIVE = 'ACTIVE', 'Active'
    ON_HOLD = 'ON_HOLD', 'On Hold'
    ARCHIVED = 'ARCHIVED', 'Archived'
    CLOSED = 'CLOSED', 'Closed'


class Project(models.Model):
    """FR-008 to FR-014: project container for related tasks."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='managed_projects',
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='projects', blank=True,
        through='ProjectMembership',
    )
    status = models.CharField(
        max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.PLANNED
    )
    start_date = models.DateField(null=True, blank=True)  # FR-014
    end_date = models.DateField(null=True, blank=True)  # FR-014
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='created_projects',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def task_counts(self):
        """(total, completed) over top-level, non-archived, non-cancelled tasks."""
        from .access import COUNTED_TASK_STATUSES

        qs = self.tasks.filter(
            parent_task__isnull=True, is_archived=False, status__in=COUNTED_TASK_STATUSES
        )
        return qs.count(), qs.filter(status='COMPLETED').count()

    @property
    def progress(self):
        """FR-013: percentage of associated tasks that are completed."""
        total, done = self.task_counts()
        return round(done / total * 100) if total else 0


class ProjectMembership(models.Model):
    """FR-011: add/remove project members."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')
