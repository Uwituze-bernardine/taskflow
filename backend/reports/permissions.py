from rest_framework.permissions import BasePermission


class IsManagerOrAdmin(BasePermission):
    """Reports are for managers (FR-078 to FR-084): project managers, team leaders, admins."""
    message = 'Only managers can view reports.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_manager)
