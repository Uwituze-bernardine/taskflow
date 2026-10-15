from rest_framework import permissions

from .models import Role


class IsAdmin(permissions.BasePermission):
    """FR-006: restrict access based on role. Admin-only actions."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )


class IsAdminOrSelf(permissions.BasePermission):
    """Users may view/edit their own profile; admins may manage any (FR-003, FR-007)."""

    def has_object_permission(self, request, view, obj):
        return request.user.role == Role.ADMIN or obj == request.user


class IsManager(permissions.BasePermission):
    """Project managers, team leaders and admins (used for project/task authoring)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_manager
        )


class ReadOnlyOrIsManager(permissions.BasePermission):
    """Anyone authenticated can read; only managers can write."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_manager
        )


class ReadOnlyOrIsAdmin(permissions.BasePermission):
    """Any signed-in user can read; only administrators can write."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role == Role.ADMIN
