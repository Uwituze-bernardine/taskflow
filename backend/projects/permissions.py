from rest_framework import permissions

from .access import CLOSED_STATUSES, can_create_project, can_manage_project

EDIT_ACTIONS = ('update', 'partial_update', 'add_member', 'remove_member')


class ProjectPermission(permissions.BasePermission):
    message = 'You do not have permission to change this project.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action == 'create' and not can_create_project(user):
            self.message = 'Only administrators and project managers can create projects.'
            return False
        return True

    def has_object_permission(self, request, view, project):
        if view.action == 'retrieve':
            return True
        if not can_manage_project(request.user, project):
            self.message = 'Only the project manager or an administrator can do that.'
            return False
        if view.action in EDIT_ACTIONS and project.status in CLOSED_STATUSES:
            self.message = 'This project is archived or closed. Reopen it before making changes.'
            return False
        return True
