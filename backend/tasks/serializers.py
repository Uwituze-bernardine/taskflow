from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from projects.access import (
    CLOSED_STATUSES, can_create_task_in_project, is_admin, is_project_participant,
)
from users.serializers import UserDirectorySerializer
from . import workflow
from .access import (
    can_add_subtask, can_change_status, can_manage_task, in_closed_project, visible_tasks,
)
from .dependencies import check_predecessors
from .models import (
    CustomPriority, CustomTaskStatus, Recurrence, SavedTaskFilter, Task, TaskStatus,
    TaskStatusHistory, TaskTag,
)
from .recurrence import next_occurrence_due_date

FINISHED = (TaskStatus.COMPLETED, TaskStatus.CANCELLED)


class SavedTaskFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedTaskFilter
        fields = ['id', 'name', 'filters', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('A saved filter needs a name.')
        return value

    def validate_filters(self, value):
        allowed = {
            'status', 'priority', 'project', 'assigned_to', 'tag',
            'created_after', 'created_before', 'due_after', 'due_before',
        }
        if not isinstance(value, dict) or not set(value).issubset(allowed):
            raise serializers.ValidationError('The filter contains unsupported fields.')
        return value


def _mini(task):
    return {'id': task.id, 'title': task.title, 'status': task.status, 'status_label': task.status_label}


class TaskStatusHistorySerializer(serializers.ModelSerializer):
    """FR-034: who changed the status, when, and from/to what."""
    changed_by_detail = UserDirectorySerializer(source='changed_by', read_only=True)

    class Meta:
        model = TaskStatusHistory
        fields = [
            'id', 'from_status', 'to_status', 'from_label', 'to_label',
            'changed_by', 'changed_by_detail', 'changed_at',
        ]
        read_only_fields = fields


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_detail = UserDirectorySerializer(source='assigned_to', read_only=True)
    created_by_detail = UserDirectorySerializer(source='created_by', read_only=True)
    project_name = serializers.SerializerMethodField()
    parent_title = serializers.SerializerMethodField()
    status_label = serializers.ReadOnlyField()
    priority_label = serializers.ReadOnlyField()  # FR-093
    progress = serializers.SerializerMethodField()  # FR-037
    is_overdue = serializers.ReadOnlyField()
    is_blocked_by_dependencies = serializers.ReadOnlyField()  # FR-042
    subtask_count = serializers.SerializerMethodField()  # FR-040
    subtasks_done = serializers.SerializerMethodField()  # FR-040
    depends_on_detail = serializers.SerializerMethodField()
    blocks_detail = serializers.SerializerMethodField()
    blocked_by = serializers.SerializerMethodField()
    completion_blockers = serializers.SerializerMethodField()  # FR-036
    is_recurring = serializers.ReadOnlyField()
    next_occurrence_due_date = serializers.SerializerMethodField()  # FR-064
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'project', 'project_name', 'parent_task', 'parent_title',
            'assigned_to', 'assigned_to_detail', 'created_by', 'created_by_detail',
            'priority', 'custom_priority', 'priority_label', 'status', 'custom_status', 'status_label',
            'start_date', 'due_date', 'tags',
            'depends_on', 'depends_on_detail', 'blocks_detail', 'enforce_dependencies',
            'is_blocked_by_dependencies', 'blocked_by', 'completion_blockers',
            'progress', 'is_overdue', 'subtask_count', 'subtasks_done', 'is_archived',
            'recurrence', 'recurrence_interval', 'recurrence_end_date', 'recurrence_of',
            'is_recurring', 'next_occurrence_due_date',
            'permissions', 'created_at', 'updated_at',
        ]
        # Status changes go through /status/ (rules, history, notifications: FR-032/034) and
        # archiving through /archive/ + /restore/, never through a plain update.
        read_only_fields = [
            'id', 'created_by', 'status', 'custom_status', 'is_archived',
            'recurrence_of', 'created_at', 'updated_at',
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated:
            # People can only link to tasks they can see (no probing of other projects).
            visible = visible_tasks(request.user)
            fields['parent_task'].queryset = visible
            fields['depends_on'].child_relation.queryset = visible
        return fields

    # -- computed ----------------------------------------------------------

    def _subtasks(self, obj):
        if hasattr(obj, 'n_sub'):  # annotated by the viewset: no extra queries
            return obj.n_sub, obj.n_sub_done
        return obj.subtask_counts()

    def get_project_name(self, obj):
        return obj.project.name if obj.project_id else None

    def get_parent_title(self, obj):
        return obj.parent_task.title if obj.parent_task_id else None

    def get_progress(self, obj):
        if obj.status == TaskStatus.COMPLETED:
            return 100
        total, done = self._subtasks(obj)
        return round(done / total * 100) if total else 0

    def get_subtask_count(self, obj):
        return self._subtasks(obj)[0]

    def get_subtasks_done(self, obj):
        return self._subtasks(obj)[1]

    def get_depends_on_detail(self, obj):
        return [_mini(p) for p in obj.depends_on.all()]

    def get_blocks_detail(self, obj):
        return [_mini(t) for t in obj.blocks.all() if not t.is_archived]

    def get_blocked_by(self, obj):
        return [_mini(p) for p in obj.unfinished_predecessors()] if obj.enforce_dependencies else []

    def get_completion_blockers(self, obj):
        return [] if obj.status in FINISHED else workflow.completion_blockers(obj)

    def get_next_occurrence_due_date(self, obj):
        return next_occurrence_due_date(obj)

    def get_permissions(self, obj):
        """Tells the UI which controls to show; the API enforces the same rules."""
        user = self.context['request'].user
        closed = in_closed_project(obj)
        manage = can_manage_task(user, obj) and not closed
        return {
            'edit': manage,
            'assign': manage,
            'archive': manage,
            'change_status': can_change_status(user, obj) and not closed,
            'add_subtask': can_add_subtask(user, obj) and not closed and obj.status not in FINISHED,
            'delete_permanently': is_admin(user),
        }

    # -- validation --------------------------------------------------------

    def validate_tags(self, value):
        tags = []
        for tag in value:
            tag = str(tag).strip()
            if tag and tag.lower() not in [t.lower() for t in tags]:
                tags.append(tag[:30])
        if len(tags) > 20:
            raise serializers.ValidationError('A task can have at most 20 tags.')
        return tags

    def _validate_new_subtask(self, user, parent, attrs):
        """FR-038: a subtask hangs under a top-level, open task and lives in its project."""
        if parent.parent_task_id:
            raise serializers.ValidationError({'parent_task': 'Subtasks cannot have subtasks of their own.'})
        if parent.is_archived:
            raise serializers.ValidationError({'parent_task': 'This task is archived.'})
        if in_closed_project(parent):
            raise serializers.ValidationError({'parent_task': 'The task belongs to a closed or archived project.'})
        if parent.status in FINISHED:
            raise serializers.ValidationError(
                {'parent_task': 'This task is already completed or cancelled. Reopen it before adding subtasks.'}
            )
        if not can_add_subtask(user, parent):
            raise PermissionDenied('You cannot add subtasks to this task.')
        if 'project' in attrs and attrs['project'] != parent.project:
            raise serializers.ValidationError({'project': "A subtask always belongs to its parent's project."})
        attrs['project'] = parent.project

    def validate_custom_priority(self, value):
        if value is not None and not value.is_active:
            raise serializers.ValidationError('This priority has been deactivated.')
        return value

    def validate_recurrence_interval(self, value):
        if value < 1:
            raise serializers.ValidationError('The interval must be at least 1.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        instance = self.instance
        parent = attrs['parent_task'] if 'parent_task' in attrs else (instance.parent_task if instance else None)
        is_new_subtask = instance is None and parent is not None

        # FR-064: recurrence only makes sense for a top-level task with a due date to advance from.
        recurrence = attrs.get('recurrence', instance.recurrence if instance else Recurrence.NONE)
        if recurrence != Recurrence.NONE:
            if parent is not None:
                raise serializers.ValidationError({'recurrence': 'Subtasks cannot repeat.'})
            due = attrs.get('due_date', instance.due_date if instance else None)
            if due is None:
                raise serializers.ValidationError({'recurrence': 'A recurring task needs a due date to repeat from.'})

        if is_new_subtask:
            self._validate_new_subtask(user, parent, attrs)
        elif instance is not None and 'parent_task' in attrs and attrs['parent_task'] != instance.parent_task:
            raise serializers.ValidationError({'parent_task': 'A task cannot be moved under a different parent.'})

        project = attrs['project'] if 'project' in attrs else (instance.project if instance else None)
        project_changed = instance is None or ('project' in attrs and attrs['project'] != instance.project)

        if instance is not None and project_changed and (instance.parent_task_id or instance.subtasks.exists()):
            raise serializers.ValidationError({
                'project': "Subtasks always belong to their parent's project, so a task with subtasks "
                           "(or a subtask) cannot be moved to another project."
            })
        if project is not None and project_changed and not is_new_subtask:
            if project.status in CLOSED_STATUSES:
                raise serializers.ValidationError({'project': 'Closed or archived projects cannot receive tasks.'})
            if not can_create_task_in_project(user, project):
                raise PermissionDenied('You cannot put tasks in this project.')

        # FR-018/026/039: the assignee must be an active user and, for project tasks, part of the project.
        if 'assigned_to' in attrs or project_changed:
            assignee = attrs['assigned_to'] if 'assigned_to' in attrs else (instance.assigned_to if instance else None)
            if assignee is not None:
                if not assignee.is_active_member:
                    raise serializers.ValidationError({'assigned_to': 'This user is deactivated.'})
                if project is not None and not is_project_participant(assignee, project):
                    raise serializers.ValidationError(
                        {'assigned_to': "The assignee must be a member of the task's project."}
                    )

        # FR-093: a custom priority always carries its base category along with it.
        if 'custom_priority' in attrs and attrs['custom_priority'] is not None:
            attrs['priority'] = attrs['custom_priority'].category

        # FR-041: dependencies must make sense.
        if 'depends_on' in attrs:
            check_predecessors(task=instance, project=project, parent=parent, predecessors=attrs['depends_on'])

        start = attrs.get('start_date', instance.start_date if instance else None)
        due = attrs.get('due_date', instance.due_date if instance else None)
        if start and due and due < start:
            raise serializers.ValidationError({'due_date': 'The due date cannot be before the start date.'})
        return attrs


class TaskStatusChangeSerializer(serializers.Serializer):
    """FR-032: pick a predefined status, or an administrator-defined one (FR-035) - not both."""
    status = serializers.ChoiceField(choices=TaskStatus.choices, required=False)
    custom_status = serializers.PrimaryKeyRelatedField(
        queryset=CustomTaskStatus.objects.filter(is_active=True), required=False
    )

    def validate(self, attrs):
        if ('status' in attrs) == ('custom_status' in attrs):
            raise serializers.ValidationError('Send either "status" or "custom_status".')
        return attrs


class CustomTaskStatusSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomTaskStatus
        fields = ['id', 'name', 'category', 'order', 'is_active', 'task_count']

    def get_task_count(self, obj):
        return obj.task_count if hasattr(obj, 'task_count') else obj.tasks.count()

    def validate_name(self, value):
        value = value.strip()
        if value.lower() in {label.lower() for _, label in TaskStatus.choices}:
            raise serializers.ValidationError('This name is already used by a predefined status.')
        clash = CustomTaskStatus.objects.filter(name__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError('A status with this name already exists.')
        return value

    def validate_category(self, value):
        if self.instance is not None and value != self.instance.category and self.instance.tasks.exists():
            # Tasks store the category, so changing it under them would leave them inconsistent.
            raise serializers.ValidationError('Tasks are using this status, so its category cannot be changed.')
        return value


class CustomPrioritySerializer(serializers.ModelSerializer):
    """FR-093: administrator-configurable priorities."""
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomPriority
        fields = ['id', 'name', 'category', 'order', 'is_active', 'task_count']

    def get_task_count(self, obj):
        return obj.task_count if hasattr(obj, 'task_count') else obj.tasks.count()

    def validate_name(self, value):
        value = value.strip()
        if value.lower() in {'low', 'medium', 'high', 'critical'}:
            raise serializers.ValidationError('This name is already used by a predefined priority.')
        clash = CustomPriority.objects.filter(name__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError('A priority with this name already exists.')
        return value

    def validate_category(self, value):
        if self.instance is not None and value != self.instance.category and self.instance.tasks.exists():
            raise serializers.ValidationError('Tasks are using this priority, so its category cannot be changed.')
        return value


class TaskTagSerializer(serializers.ModelSerializer):
    """FR-094: the administrator-curated registry of known tags."""

    class Meta:
        model = TaskTag
        fields = ['id', 'name']

    def validate_name(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError('A tag name is required.')
        clash = TaskTag.objects.filter(name__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError('This tag already exists.')
        return value
