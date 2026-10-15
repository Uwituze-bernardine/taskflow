"""
Authorization rules for projects (FR-008 to FR-012) and the project-level parts of
task rules. Kept in one module so views, serializers and tests all agree.
"""
from django.db.models import Q

from users.models import Role

# Who may create projects (FR-008). Change here to widen/narrow it.
PROJECT_CREATOR_ROLES = (Role.ADMIN, Role.PROJECT_MANAGER)
# Who may create tasks (FR-015), always additionally limited to projects they take part in.
TASK_CREATOR_ROLES = (Role.ADMIN, Role.PROJECT_MANAGER, Role.TEAM_LEADER)
# Roles that can be the manager of a project.
PROJECT_MANAGER_ROLES = (Role.ADMIN, Role.PROJECT_MANAGER)

CLOSED_STATUSES = ('ARCHIVED', 'CLOSED')
# Statuses that count towards project progress (cancelled work is not "outstanding").
COUNTED_TASK_STATUSES = ['TODO', 'IN_PROGRESS', 'BLOCKED', 'UNDER_REVIEW', 'COMPLETED']


def is_admin(user):
    return user.role == Role.ADMIN


def visible_projects(user):
    """FR-012: administrators see everything, everyone else sees projects they manage or belong to."""
    from .models import Project

    qs = Project.objects.all()
    if is_admin(user):
        return qs
    return qs.filter(Q(manager=user) | Q(members=user)).distinct()


def can_create_project(user):
    return user.role in PROJECT_CREATOR_ROLES


def can_manage_project(user, project):
    """FR-009/010/011: edit, archive/close and manage members."""
    return is_admin(user) or project.manager_id == user.id


def is_project_participant(user, project):
    """True for the manager and every member. Uses prefetched members when available."""
    if project.manager_id == user.id:
        return True
    return any(m.id == user.id for m in project.members.all())


def can_create_task_in_project(user, project):
    if project.status in CLOSED_STATUSES:
        return False
    if is_admin(user) or project.manager_id == user.id:
        return True
    return user.role in TASK_CREATOR_ROLES and is_project_participant(user, project)


def with_progress(qs):
    """
    Annotate a Project queryset with `n_tasks`/`n_done` (FR-013, FR-075) so progress can be
    read without an extra query per project - shared by the project API, dashboard and reports.
    """
    from django.db.models import Count, Q

    open_tasks = Q(tasks__parent_task__isnull=True, tasks__is_archived=False)
    return qs.annotate(
        n_tasks=Count('tasks', filter=open_tasks & Q(tasks__status__in=COUNTED_TASK_STATUSES), distinct=True),
        n_done=Count('tasks', filter=open_tasks & Q(tasks__status='COMPLETED'), distinct=True),
    )


def project_progress(project):
    """Reads the annotation from `with_progress` when present, else falls back to a query."""
    if hasattr(project, 'n_tasks'):
        return round(project.n_done / project.n_tasks * 100) if project.n_tasks else 0
    total, done = project.task_counts()
    return round(done / total * 100) if total else 0
