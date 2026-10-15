"""Rules for task dependencies (FR-041)."""
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .access import visible_tasks
from .models import Task


def _reachable(start_ids, field_from, field_to):
    """All task ids reachable from `start_ids` by following the dependency table."""
    through = Task.depends_on.through
    seen, frontier = set(), set(start_ids)
    while frontier:
        seen |= frontier
        frontier = set(
            through.objects.filter(**{f'{field_from}__in': frontier}).values_list(field_to, flat=True)
        ) - seen
    return seen


def would_create_cycle(task_id, predecessor_ids):
    """True if making `task_id` depend on `predecessor_ids` would loop back to itself."""
    # Follow "depends on" edges upwards from each new predecessor; hitting the task means a loop.
    return task_id in _reachable(predecessor_ids, 'from_task_id', 'to_task_id')


def dependents_of(task_id):
    """Every task that (directly or indirectly) waits for `task_id`, excluding itself."""
    return _reachable([task_id], 'to_task_id', 'from_task_id') - {task_id}


def check_predecessors(*, task, project, parent, predecessors):
    """
    Raises a 400 unless every predecessor is a valid dependency: not the task itself,
    not archived, in the same project, not the task's own parent/subtask, and no loop.
    `task` is None while the task is being created.
    """
    project_id = project.id if project else None
    for p in predecessors:
        if task is not None and p.pk == task.pk:
            raise ValidationError({'depends_on': 'A task cannot depend on itself.'})
        if p.is_archived:
            raise ValidationError({'depends_on': f'"{p.title}" is archived.'})
        if p.project_id != project_id:
            raise ValidationError({'depends_on': f'"{p.title}" is not in the same project.'})
        if (parent is not None and p.pk == parent.pk) or (task is not None and p.parent_task_id == task.pk):
            raise ValidationError({'depends_on': 'A task cannot depend on its own parent or subtasks.'})
    if task is not None and would_create_cycle(task.pk, [p.pk for p in predecessors]):
        raise ValidationError({'depends_on': 'This would create a circular dependency.'})


def dependency_candidates(task, user, search=''):
    """Tasks that could validly become a predecessor of `task` (for the picker in the UI)."""
    qs = (
        visible_tasks(user)
        .filter(project_id=task.project_id, is_archived=False)
        .exclude(pk=task.pk)
        .exclude(pk__in=task.depends_on.values('pk'))
        .exclude(pk__in=dependents_of(task.pk))
        .exclude(parent_task=task)
    )
    if task.parent_task_id:
        qs = qs.exclude(pk=task.parent_task_id)
    search = search.strip()
    if search:
        cond = Q(title__icontains=search)
        if search.isdigit():
            cond |= Q(pk=int(search))
        qs = qs.filter(cond)
    return qs.order_by('-created_at')[:25]
