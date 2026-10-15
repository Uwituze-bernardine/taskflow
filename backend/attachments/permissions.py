from rest_framework import permissions

from projects.access import is_admin
from tasks.access import can_manage_task, in_closed_project


class AttachmentPermission(permissions.BasePermission):
    """FR-049 upload, FR-053 remove - both "authorized users": visibility + not read-only."""
    message = 'You do not have permission to do that.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, attachment):
        user = request.user
        if view.action in ('retrieve', 'download'):
            return True  # already scoped to visible tasks by the queryset
        if view.action == 'destroy':
            allowed = attachment.uploaded_by_id == user.id or is_admin(user) or can_manage_task(user, attachment.task)
            if not allowed:
                self.message = 'You can only remove your own uploads.'
            elif in_closed_project(attachment.task) and not is_admin(user):
                self.message = 'This task belongs to a closed or archived project.'
                allowed = False
            return allowed
        return True
