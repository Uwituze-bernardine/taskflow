"""
Workflow rules for task statuses (FR-032 to FR-037) and the status-related dependency
rule (FR-042). Views call these so every path enforces the same rules.
"""
from rest_framework.exceptions import ValidationError

from notifications.models import Category
from notifications.services import notify
from .models import CustomTaskStatus, TaskStatus, TaskStatusHistory
from .recurrence import spawn_next_occurrence

# Moving into any of these means the work has started (or finished).
PROGRESSING = (TaskStatus.IN_PROGRESS, TaskStatus.UNDER_REVIEW, TaskStatus.COMPLETED)
_CATEGORY_ORDER = [value for value, _ in TaskStatus.choices]


def workflow_options():
    """
    Every status a task can be moved to, in workflow order: the six predefined statuses,
    each followed by the active custom statuses that behave like it.
    """
    options = [
        {'key': value, 'label': label, 'category': value, 'custom_status': None, 'builtin': True}
        for value, label in TaskStatus.choices
    ]
    for custom in CustomTaskStatus.objects.filter(is_active=True):
        options.append({
            'key': f'custom:{custom.id}', 'label': custom.name, 'category': custom.category,
            'custom_status': custom.id, 'builtin': False,
        })
    options.sort(key=lambda o: (_CATEGORY_ORDER.index(o['category']), not o['builtin']))
    return options  # sort is stable, so custom statuses keep their configured order


def open_subtask_count(task):
    """Counted subtasks that are not completed yet."""
    if hasattr(task, 'n_sub'):
        return task.n_sub - task.n_sub_done
    total, done = task.subtask_counts()
    return total - done


def _waiting_text(predecessors):
    return ', '.join(f'"{p.title}" ({p.status_label})' for p in predecessors)


def completion_problems(task):
    """FR-036: required information / conditions that are missing before a task can be completed."""
    problems = []
    if task.assigned_to_id is None:
        problems.append('Assign the task to someone.')
    open_subtasks = open_subtask_count(task)
    if open_subtasks:
        problems.append(f'{open_subtasks} subtask(s) are not completed yet.')
    return problems


def dependency_problem(task):
    """FR-042: text explaining why a task may not start yet, or None."""
    if not task.enforce_dependencies:
        return None
    waiting = task.unfinished_predecessors()
    return f'Waiting for: {_waiting_text(waiting)}.' if waiting else None


def completion_blockers(task):
    """Everything currently preventing completion, for display next to the task."""
    problems = completion_problems(task)
    waiting = dependency_problem(task)
    if waiting:
        problems.append(waiting)
    return problems


def validate_transition(task, category):
    """Raises a 400 when the task may not move to `category`."""
    if category in PROGRESSING:
        waiting = dependency_problem(task)
        if waiting:
            raise ValidationError({'detail': f'This task cannot start yet. {waiting}'})
    if category == TaskStatus.COMPLETED:
        problems = completion_problems(task)
        if problems:
            raise ValidationError({'detail': 'This task cannot be completed yet. ' + ' '.join(problems)})


def apply_status(task, category, custom, actor):
    """
    Change a task's status and record who did it and when (FR-034), then notify the assignee.
    Cancelling a task also cancels its unfinished subtasks.
    """
    old_category, old_label = task.status, task.status_label
    task._actor = actor
    task.status = category
    task.custom_status = custom
    task.save(update_fields=['status', 'custom_status'])
    TaskStatusHistory.objects.create(
        task=task, from_status=old_category, to_status=category,
        from_label=old_label, to_label=task.status_label, changed_by=actor,
    )
    if task.assigned_to:
        notify(task.assigned_to, f'Task "{task.title}" status changed to {task.status_label}.', task=task, category=Category.STATUS_CHANGED)  # FR-055

    if category == TaskStatus.CANCELLED:
        unfinished = task.subtasks.filter(is_archived=False).exclude(
            status__in=[TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        )
        for subtask in unfinished:
            apply_status(subtask, TaskStatus.CANCELLED, None, actor)

    # FR-064: completing a top-level task in a recurring series starts the next occurrence.
    if category == TaskStatus.COMPLETED and task.is_recurring and task.parent_task_id is None:
        next_task = spawn_next_occurrence(task, actor)
        if next_task and next_task.assigned_to:
            notify(next_task.assigned_to, f'You were assigned to task "{next_task.title}".', task=next_task, category=Category.ASSIGNED)  # FR-027
        return next_task
    return None
