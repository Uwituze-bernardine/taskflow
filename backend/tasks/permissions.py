from rest_framework import permissions

from projects.access import TASK_CREATOR_ROLES, is_admin
from .access import can_add_subtask, can_change_status, can_manage_task, in_closed_project

READ_ACTIONS = ('retrieve', 'history', 'status_history')


class TaskPermission(permissions.BasePermission):
    message = 'You do not have permission to change this task.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action == 'create' and user.role not in TASK_CREATOR_ROLES:
            self.message = 'Only administrators, project managers and team leaders can create tasks.'
            return False
        return True

    def has_object_permission(self, request, view, task):
        user, action = request.user, view.action
        if action in READ_ACTIONS or (action == 'subtasks' and request.method in permissions.SAFE_METHODS):
            return True
        if action == 'destroy' and request.query_params.get('permanent') == 'true':
            self.message = 'Only administrators can permanently delete tasks.'
            return is_admin(user)
        if in_closed_project(task):
            self.message = 'This task belongs to a closed or archived project. Reopen the project to change it.'
            return False
        if action == 'change_status':
            return can_change_status(user, task)
        if action == 'subtasks':  # POST: add a subtask (FR-038)
            allowed = can_add_subtask(user, task)
            if not allowed:
                self.message = 'You cannot add subtasks to this task.'
            return allowed
        allowed = can_manage_task(user, task)
        if not allowed and action == 'assign':  # FR-031
            self.message = 'You are not authorized to assign this task.'
        return allowed
