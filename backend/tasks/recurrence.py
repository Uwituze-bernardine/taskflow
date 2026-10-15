"""FR-064: recurring tasks - advancing dates and spawning the next occurrence."""
import calendar
from datetime import date, timedelta

from .models import Recurrence


def _add_months(d, months):
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def advance(d, rule, interval):
    """The next date after `d` for a recurrence `rule` repeating every `interval` units."""
    interval = max(1, interval)
    if rule == Recurrence.DAILY:
        return d + timedelta(days=interval)
    if rule == Recurrence.WEEKLY:
        return d + timedelta(weeks=interval)
    if rule == Recurrence.MONTHLY:
        return _add_months(d, interval)
    if rule == Recurrence.YEARLY:
        return _add_months(d, interval * 12)
    return d


def next_occurrence_due_date(task):
    """
    The due date the next occurrence would have, or None if the series has ended
    (no due date to advance from, or past `recurrence_end_date`).
    """
    if not task.is_recurring or task.due_date is None:
        return None
    candidate = advance(task.due_date, task.recurrence, task.recurrence_interval)
    if task.recurrence_end_date and candidate > task.recurrence_end_date:
        return None
    return candidate


def spawn_next_occurrence(task, actor):
    """
    Create the next task in `task`'s recurring series (FR-064), copying its planning
    fields but not its progress: fresh status, no comments/attachments/history carried over.
    Returns the new Task, or None if the series doesn't continue (no next due date).
    """
    from .models import Task, TaskStatus

    next_due = next_occurrence_due_date(task)
    if next_due is None:
        return None

    shifted_start = None
    if task.start_date and task.due_date:
        shifted_start = next_due - (task.due_date - task.start_date)

    return Task.objects.create(
        title=task.title,
        description=task.description,
        project=task.project,
        assigned_to=task.assigned_to,
        created_by=actor,
        priority=task.priority,
        status=TaskStatus.TODO,
        start_date=shifted_start,
        due_date=next_due,
        tags=list(task.tags),
        recurrence=task.recurrence,
        recurrence_interval=task.recurrence_interval,
        recurrence_end_date=task.recurrence_end_date,
        recurrence_of_id=task.recurrence_series_id,
    )
