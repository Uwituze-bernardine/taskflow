from rest_framework import permissions

from projects.access import is_admin
from tasks.access import can_manage_task, in_closed_project


class CommentPermission(permissions.BasePermission):
    """
    FR-043: creating a comment is checked in the serializer (it needs the target task).
    FR-048: authors edit their own comments; authors, task managers, and administrators
    may remove one ("subject to permissions" - moderation is part of managing the task).
    """
    message = 'You do not have permission to do that.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, comment):
        user = request.user
        if view.action == 'retrieve':
            return True
        is_author = comment.author_id == user.id
        if view.action in ('update', 'partial_update'):
            if comment.is_deleted:
                self.message = 'This comment has been deleted.'
                return False
            if not is_author:
                self.message = 'You can only edit your own comments.'
                return False
            if in_closed_project(comment.task):
                self.message = 'This task belongs to a closed or archived project.'
                return False
            return True
        if view.action == 'destroy':
            allowed = is_author or is_admin(user) or can_manage_task(user, comment.task)
            if not allowed:
                self.message = 'You can only delete your own comments.'
            return allowed
        return True
