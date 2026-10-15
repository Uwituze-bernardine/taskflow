from django.conf import settings
from django.db import models

from projects.access import COUNTED_TASK_STATUSES
from projects.models import Project


class Priority(models.TextChoices):
    """FR-020"""
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class Recurrence(models.TextChoices):
    """FR-064: how a completed task's next occurrence is scheduled."""
    NONE = 'NONE', 'Does not repeat'
    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'
    YEARLY = 'YEARLY', 'Yearly'


class TaskStatus(models.TextChoices):
    """
    FR-033: the predefined statuses. These are also the workflow *categories*: every custom
    status (FR-035) belongs to one of them, so progress, dependency and completion rules
    always know what a custom status means.
    """
    TODO = 'TODO', 'To Do'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    BLOCKED = 'BLOCKED', 'Blocked'
    UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class CustomPriority(models.Model):
    """FR-093: an administrator-defined priority, refining one of the four base levels."""
    name = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class TaskTag(models.Model):
    """FR-094: the registry of known tags administrators curate for consistency/autocomplete.
    A task's own `tags` stay freeform strings (see Task.tags) - this registry doesn't
    constrain them, it just gives the UI a managed list to suggest from."""
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomTaskStatus(models.Model):
    """
    FR-035: an administrator-defined status such as "QA Testing".
    It refines one of the six predefined statuses (`category`), which is what the workflow
    rules use. Retire a status with `is_active = False`; it cannot be deleted while tasks use it.
    """
    name = models.CharField(max_length=50, unique=True)
    category = models.CharField(
        max_length=30, choices=TaskStatus.choices, default=TaskStatus.IN_PROGRESS,
        help_text='The predefined status this one behaves like.',
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Task(models.Model):
    """
    FR-015 to FR-025, FR-032 to FR-042: the core task entity, including
    subtasks (self-referential parent_task) and dependencies.
    """

    title = models.CharField(max_length=250)  # FR-016
    description = models.TextField(blank=True)  # FR-016
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True
    )  # FR-017
    parent_task = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='subtasks',
    )  # FR-038: subtasks (one level deep)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tasks',
    )  # FR-018 / FR-039
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='created_tasks',
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )  # FR-019: always one of the 4 base levels (the category)
    custom_priority = models.ForeignKey(
        'CustomPriority', on_delete=models.PROTECT, null=True, blank=True, related_name='tasks',
        help_text='Optional refinement of `priority` chosen from the administrator-defined priorities (FR-093).',
    )
    status = models.CharField(
        max_length=30, choices=TaskStatus.choices, default=TaskStatus.TODO
    )  # FR-032: always one of the predefined statuses (the category)
    custom_status = models.ForeignKey(
        CustomTaskStatus, on_delete=models.PROTECT, null=True, blank=True, related_name='tasks',
        help_text='Optional refinement of `status` chosen from the administrator-defined statuses.',
    )  # FR-035
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)  # FR-021
    tags = models.JSONField(default=list, blank=True)
    depends_on = models.ManyToManyField(
        'self', symmetrical=False, related_name='blocks', blank=True,
    )  # FR-041: dependencies
    enforce_dependencies = models.BooleanField(
        default=False,
        help_text='If true, blocks starting this task until predecessors complete (FR-042).',
    )
    # FR-064: recurrence is configured on the first task of a series; completing any task in
    # the series creates the next one with the same settings (see tasks/recurrence.py).
    recurrence = models.CharField(max_length=10, choices=Recurrence.choices, default=Recurrence.NONE)
    recurrence_interval = models.PositiveIntegerField(
        default=1, help_text='Repeat every N days/weeks/months/years.'
    )
    recurrence_end_date = models.DateField(
        null=True, blank=True, help_text='Stop creating new occurrences after this date.'
    )
    recurrence_of = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='recurrence_instances',
        help_text='The first task of this recurring series.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)  # FR-023

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def is_recurring(self):
        return self.recurrence != Recurrence.NONE

    @property
    def recurrence_series_id(self):
        """The id every occurrence of this series shares - the root task's own id."""
        return self.recurrence_of_id or self.id

    # -- status ------------------------------------------------------------

    @property
    def status_label(self):
        """What people see: the custom status name if one is set, else the predefined label."""
        return self.custom_status.name if self.custom_status_id else self.get_status_display()

    @property
    def priority_label(self):
        """What people see: the custom priority name if one is set, else the predefined label."""
        return self.custom_priority.name if self.custom_priority_id else self.get_priority_display()

    # -- subtasks and progress (FR-037, FR-040) ----------------------------

    def subtask_counts(self):
        """(counted, completed) subtasks. Cancelled and archived subtasks are not counted."""
        qs = self.subtasks.filter(is_archived=False, status__in=COUNTED_TASK_STATUSES)
        return qs.count(), qs.filter(status=TaskStatus.COMPLETED).count()

    @property
    def progress(self):
        """
        FR-037: 100 when completed; otherwise the share of counted subtasks that are
        completed; a task without subtasks is 0 until it is completed.
        """
        if self.status == TaskStatus.COMPLETED:
            return 100
        total, done = self.subtask_counts()
        return round(done / total * 100) if total else 0

    # -- dates and dependencies (FR-041, FR-042) ---------------------------

    @property
    def is_overdue(self):
        from django.utils import timezone

        return bool(
            self.due_date
            and self.due_date < timezone.localdate()
            and self.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
        )

    def unfinished_predecessors(self):
        """Predecessors that still have to be completed (archived ones no longer count)."""
        return [
            p for p in self.depends_on.all()
            if not p.is_archived and p.status != TaskStatus.COMPLETED
        ]

    @property
    def is_blocked_by_dependencies(self):
        """FR-042: dependencies are enforced for this task and a predecessor is unfinished."""
        return self.enforce_dependencies and bool(self.unfinished_predecessors())


class TaskStatusHistory(models.Model):
    """FR-034: record date/user responsible for each status change."""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    from_label = models.CharField(max_length=100, blank=True)  # e.g. "QA Testing"
    to_label = models.CharField(max_length=100, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
