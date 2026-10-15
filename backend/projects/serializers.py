from django.utils import timezone
from django.db.models import Count
from rest_framework import serializers

from users.models import Role, User
from users.serializers import UserDirectorySerializer
from .access import (
    CLOSED_STATUSES, PROJECT_MANAGER_ROLES, can_create_task_in_project, can_manage_project,
    is_admin,
)
from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    manager = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active_member=True), required=False
    )
    manager_detail = UserDirectorySerializer(source='manager', read_only=True)
    members_detail = UserDirectorySerializer(source='members', many=True, read_only=True)
    progress = serializers.SerializerMethodField()  # FR-013
    task_count = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'manager', 'manager_detail',
            'members', 'members_detail', 'status', 'start_date', 'end_date',  # FR-014
            'progress', 'task_count', 'permissions',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'members', 'created_by', 'created_at', 'updated_at']

    # -- computed ----------------------------------------------------------

    def _counts(self, obj):
        if hasattr(obj, 'n_tasks'):  # annotated by the viewset: no extra queries
            return obj.n_tasks, obj.n_done
        return obj.task_counts()

    def get_progress(self, obj):
        total, done = self._counts(obj)
        return round(done / total * 100) if total else 0

    def get_task_count(self, obj):
        return self._counts(obj)[0]

    def get_permissions(self, obj):
        """Tells the UI which controls to show; the API enforces the same rules."""
        user = self.context['request'].user
        manage = can_manage_project(user, obj)
        closed = obj.status in CLOSED_STATUSES
        return {
            'edit': manage and not closed,
            'manage_members': manage and not closed,
            'archive': manage and obj.status != 'ARCHIVED',
            'close': manage and not closed,
            'reopen': manage and closed,
            'create_tasks': can_create_task_in_project(user, obj),
        }

    # -- validation --------------------------------------------------------

    def validate_status(self, value):
        if value in CLOSED_STATUSES:
            raise serializers.ValidationError('Use the archive or close action for this.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        instance = self.instance

        start = attrs.get('start_date', instance.start_date if instance else None)
        end = attrs.get('end_date', instance.end_date if instance else None)
        if start and end and end < start:
            raise serializers.ValidationError(
                {'end_date': 'The expected completion date cannot be before the start date.'}
            )

        if instance is None:
            attrs.setdefault('manager', user)
            if not is_admin(user) and attrs['manager'] != user:
                raise serializers.ValidationError({'manager': 'You can only create projects that you manage.'})
        if 'manager' in attrs and attrs['manager'].role not in PROJECT_MANAGER_ROLES:
            raise serializers.ValidationError(
                {'manager': 'The project manager must be a Project Manager or an Administrator.'}
            )
        return attrs


class ProjectDetailSerializer(ProjectSerializer):
    """Adds a task breakdown for the project page."""
    status_counts = serializers.SerializerMethodField()
    overdue_count = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ['status_counts', 'overdue_count']

    def _open_tasks(self, obj):
        return obj.tasks.filter(parent_task__isnull=True, is_archived=False)

    def get_status_counts(self, obj):
        from tasks.models import TaskStatus

        counts = {value: 0 for value in TaskStatus.values}
        for row in self._open_tasks(obj).values('status').annotate(n=Count('id')):
            counts[row['status']] = row['n']
        return counts

    def get_overdue_count(self, obj):
        return (
            self._open_tasks(obj)
            .filter(due_date__lt=timezone.localdate())
            .exclude(status__in=['COMPLETED', 'CANCELLED'])
            .count()
        )


class ProjectMemberSerializer(serializers.Serializer):
    """FR-011: add a member."""
    user_id = serializers.IntegerField()
