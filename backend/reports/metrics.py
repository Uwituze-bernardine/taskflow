"""
FR-078 to FR-084: report metrics, shared by the JSON summary and the CSV export so the
two can never show different numbers for the same request.
"""
from datetime import timedelta

from django.utils import timezone

from projects.access import visible_projects, with_progress
from tasks.access import visible_tasks
from tasks.models import Priority, TaskStatus, TaskStatusHistory
from users.serializers import UserDirectorySerializer

FINISHED = (TaskStatus.COMPLETED, TaskStatus.CANCELLED)


def default_range():
    end = timezone.localdate()
    return end - timedelta(days=30), end


def build_report(user, start, end, project=None):
    """
    All counts are scoped to what `user` can see (their own projects for a manager, everything
    for an administrator), optionally narrowed further to one `project`.

    `tasks_created`/`tasks_completed`/`tasks_by_priority` are counted within [start, end].
    `tasks_overdue`/`tasks_by_status`/`tasks_by_employee`/`projects` are a snapshot of the
    current state (an overdue task or a project's progress doesn't belong to a date range) -
    each is labelled accordingly in the response so the UI/export can say so.

    Implementation note: `visible_tasks()` is built from an OR of several joined conditions
    (project manager/members/assignee/creator/...). Those extra joins are harmless for a plain
    `.distinct()` row fetch, but silently corrupt SQL `GROUP BY` aggregates run directly on top
    of it (confirmed while building the dashboard). To stay correct, everything here fetches
    task rows once via plain iteration (which `.distinct()` handles properly) and tallies them
    in Python, rather than ever calling `.values().annotate()` on a `visible_tasks()` queryset.
    """
    scope = visible_tasks(user).filter(is_archived=False)
    if project is not None:
        scope = scope.filter(project=project)
    tasks = list(scope.select_related('assigned_to', 'project'))
    task_ids = [t.id for t in tasks]

    created_in_range = [t for t in tasks if start <= t.created_at.date() <= end]
    tasks_by_priority = {p: 0 for p in Priority.values}
    for t in created_in_range:
        tasks_by_priority[t.priority] += 1

    tasks_by_status = {s: 0 for s in TaskStatus.values}
    for t in tasks:
        tasks_by_status[t.status] += 1

    overdue_tasks = sorted((t for t in tasks if t.is_overdue), key=lambda t: t.due_date)

    completions = list(
        TaskStatusHistory.objects.filter(
            task_id__in=task_ids, to_status=TaskStatus.COMPLETED,
            changed_at__date__gte=start, changed_at__date__lte=end,
        ).select_related('task')
    )
    completion_days = [(c.changed_at.date() - c.task.created_at.date()).days for c in completions]
    avg_completion_days = round(sum(completion_days) / len(completion_days), 1) if completion_days else None

    by_employee = {}
    for t in tasks:
        if t.assigned_to_id is None:
            continue
        entry = by_employee.setdefault(t.assigned_to_id, {
            'user': UserDirectorySerializer(t.assigned_to).data, 'total': 0, 'completed': 0, 'overdue': 0,
        })
        entry['total'] += 1
        if t.status == TaskStatus.COMPLETED:
            entry['completed'] += 1
        if t.is_overdue:
            entry['overdue'] += 1
    tasks_by_employee = sorted(by_employee.values(), key=lambda e: -e['total'])

    projects_qs = with_progress(visible_projects(user))
    if project is not None:
        projects_qs = projects_qs.filter(pk=project.pk)
    projects_data = [{
        'id': p.id, 'name': p.name, 'status': p.status,
        'progress': round(p.n_done / p.n_tasks * 100) if p.n_tasks else 0,
        'task_count': p.n_tasks,
    } for p in projects_qs.order_by('name')]

    return {
        'start': start,
        'end': end,
        'tasks_created': len(created_in_range),  # FR-078
        'tasks_completed': len(completions),  # FR-078
        'tasks_overdue': len(overdue_tasks),  # FR-079 (current)
        'overdue_tasks': [{
            'id': t.id, 'title': t.title, 'project': t.project.name if t.project_id else None,
            'assignee': UserDirectorySerializer(t.assigned_to).data if t.assigned_to_id else None,
            'due_date': t.due_date,
        } for t in overdue_tasks],  # FR-079 (current)
        'avg_completion_days': avg_completion_days,  # FR-084
        'tasks_by_priority': tasks_by_priority,  # FR-084 (created in range)
        'tasks_by_status': tasks_by_status,  # FR-084 (current)
        'tasks_by_employee': tasks_by_employee,  # FR-081 / FR-084 (current workload)
        'projects': projects_data,  # FR-080 / FR-084 (current)
    }
