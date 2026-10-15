"""Authorization rules for tasks (FR-015 to FR-031)."""
from django.db.models import Q

from projects.access import (
    CLOSED_STATUSES, TASK_CREATOR_ROLES, is_admin, is_project_participant,
)

from .models import Task


def visible_tasks(user):
    """
    FR-024: tasks a user may see - everything for administrators; otherwise tasks of
    projects they belong to, plus tasks they created or are assigned to.
    """
    qs = Task.objects.all()
    if is_admin(user):
        return qs
    return qs.filter(
        Q(project__manager=user) | Q(project__members=user)
        | Q(assigned_to=user) | Q(created_by=user)
        # subtasks of tasks I created or own stay visible to me (matters for tasks without a project)
        | Q(parent_task__assigned_to=user) | Q(parent_task__created_by=user)
    ).distinct()


def in_closed_project(task):
    return task.project is not None and task.project.status in CLOSED_STATUSES


def can_manage_task(user, task):
    """FR-022/023/026/028: edit, archive and (re)assign a task."""
    if is_admin(user):
        return True
    # FR-039: whoever owns a task also owns its breakdown, so they can run its subtasks.
    if task.parent_task_id and task.parent_task.assigned_to_id == user.id:
        return True
    project = task.project
    if project is not None:
        if project.manager_id == user.id:
            return True
        return user.role in TASK_CREATOR_ROLES and is_project_participant(user, project)
    return user.role in TASK_CREATOR_ROLES and task.created_by_id == user.id


def can_change_status(user, task):
    """FR-032: managers and the person the task is assigned to."""
    return can_manage_task(user, task) or task.assigned_to_id == user.id


def team_queryset(user, base_qs=None):
    """
    FR-030/076: tasks assigned to a manager's team. A project manager's team is the
    members of the projects they manage; a team leader's team is the members of the
    projects they belong to; administrators see everyone's assigned tasks.
    Raises nothing - callers decide what to do if `user` isn't a manager.
    """
    from django.db.models import Q

    from projects.access import is_admin
    from users.models import Role

    qs = (base_qs if base_qs is not None else visible_tasks(user)).filter(assigned_to__isnull=False)
    if is_admin(user):
        return qs
    scope = Q(project__manager=user)
    if user.role == Role.TEAM_LEADER:
        scope |= Q(project__members=user)
    return qs.filter(scope).distinct()


def can_add_subtask(user, task):
    """FR-038: managers of the task, and the person it is assigned to, can break it down."""
    if task.parent_task_id is not None or task.is_archived:
        return False
    return can_manage_task(user, task) or task.assigned_to_id == user.id


def task_participants(task):
    """
    Users who can see `task` and so may be @mentioned in its comments (FR-045): the
    project's manager and members (or the creator/assignee for a standalone task), plus
    every administrator, since they can see everything.
    """
    from django.db.models import Q

    from users.models import Role, User

    if task.project_id:
        ids = {task.project.manager_id} | set(task.project.members.values_list('id', flat=True))
    else:
        ids = {task.created_by_id}
    if task.assigned_to_id:
        ids.add(task.assigned_to_id)
    ids.discard(None)
    return User.objects.filter(Q(id__in=ids) | Q(role=Role.ADMIN), is_active_member=True)
