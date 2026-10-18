from datetime import timedelta

from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from audit.services import task_history
from notifications.models import Category
from notifications.services import notify
from projects.access import COUNTED_TASK_STATUSES, is_project_participant
from users.models import User
from users.permissions import ReadOnlyOrIsAdmin
from .access import team_queryset, visible_tasks
from .dependencies import check_predecessors, dependency_candidates
from .filters import TaskOrderingFilter, TaskQueryFilter, TaskSearchFilter
from .models import CustomPriority, CustomTaskStatus, SavedTaskFilter, Task, TaskStatusHistory, TaskTag
from .permissions import TaskPermission
from .workflow import apply_status, validate_transition, workflow_options
from .serializers import (
    CustomPrioritySerializer, CustomTaskStatusSerializer, TaskSerializer, TaskStatusChangeSerializer,
    TaskStatusHistorySerializer, TaskTagSerializer, SavedTaskFilterSerializer,
)


class TaskViewSet(viewsets.ModelViewSet):
    """
    FR-015 to FR-025 task management and FR-026 to FR-031 assignment.
    Every query is limited to the tasks the current user may see (FR-024).
    """
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]
    filter_backends = [DjangoFilterBackend, TaskQueryFilter, TaskSearchFilter, TaskOrderingFilter]
    filterset_fields = ['project', 'status', 'custom_status', 'priority', 'assigned_to', 'created_by', 'due_date', 'parent_task']
    search_fields = ['title', 'description']
    ordering_fields = ['priority', 'due_date', 'status', 'created_at']
    ordering = ['-created_at']  # annotated queries lose Meta.ordering, so be explicit
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = (
            visible_tasks(self.request.user)
            .select_related('project', 'assigned_to', 'created_by', 'parent_task', 'custom_status')
            .prefetch_related(
                'project__members',
                Prefetch('depends_on', queryset=Task.objects.select_related('custom_status')),
                Prefetch('blocks', queryset=Task.objects.select_related('custom_status')),
            )
            .annotate(  # FR-037 / FR-040: subtask counts without one query per task
                n_sub=Count('subtasks', filter=Q(subtasks__is_archived=False, subtasks__status__in=COUNTED_TASK_STATUSES), distinct=True),
                n_sub_done=Count('subtasks', filter=Q(subtasks__is_archived=False, subtasks__status='COMPLETED'), distinct=True),
            )
        )
        if self.action in ('list', 'mine', 'team'):
            params = self.request.query_params
            # Subtasks travel with their parent: an archived parent hides them from the lists.
            qs = qs.filter(is_archived=params.get('archived') == 'true').exclude(parent_task__is_archived=True)
            if params.get('top_level') == 'true':
                qs = qs.filter(parent_task__isnull=True)
        return qs

    def _fresh(self, task):
        """Re-read a task with its counts/prefetches so the response reflects what just changed."""
        return self.get_serializer(self.get_queryset().get(pk=task.pk)).data

    def _page(self, qs):
        qs = self.filter_queryset(qs)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    # -- create / update / archive (FR-015, FR-022, FR-023) ----------------

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)
        if task.assigned_to:
            notify(task.assigned_to, f'You were assigned to task "{task.title}".', task=task, category=Category.ASSIGNED)  # FR-027

    def perform_update(self, serializer):
        task = serializer.instance
        task._actor = self.request.user
        previous_assignee = task.assigned_to_id
        serializer.save()
        if task.assigned_to_id and task.assigned_to_id != previous_assignee:
            notify(task.assigned_to, f'You were assigned to task "{task.title}".', task=task, category=Category.ASSIGNED)  # FR-027

    def perform_destroy(self, instance):
        """DELETE archives (FR-023). Administrators can add ?permanent=true to erase it."""
        if self.request.query_params.get('permanent') == 'true':
            instance._actor = self.request.user
            instance.delete()
            return
        instance._actor = self.request.user
        instance.is_archived = True
        instance.save(update_fields=['is_archived'])

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        task = self.get_object()
        task._actor = request.user
        task.is_archived = True
        task.save(update_fields=['is_archived'])
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        task = self.get_object()
        task._actor = request.user
        task.is_archived = False
        task.save(update_fields=['is_archived'])
        return Response(self.get_serializer(task).data)

    # -- views of "my" and "my team's" work (FR-029, FR-030) ---------------

    @action(detail=False, methods=['get'])
    def mine(self, request):
        """FR-029: tasks assigned to me."""
        return self._page(self.get_queryset().filter(assigned_to=request.user))

    @action(detail=False, methods=['get'])
    def team(self, request):
        """
        FR-030: tasks assigned to the members of my teams. A project manager's team is the
        members of the projects they manage; a team leader's team is the members of the
        projects they belong to; administrators see everyone's assigned tasks.
        """
        if not request.user.is_manager:
            raise PermissionDenied('Only managers can view their team\'s tasks.')
        return self._page(team_queryset(request.user, self.get_queryset()))

    # -- assignment (FR-026, FR-027, FR-028, FR-031) -----------------------

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign, reassign (or unassign with user_id = null) a task."""
        task = self.get_object()  # object permission enforces FR-031
        raw = request.data.get('user_id')
        assignee = None
        if raw not in (None, ''):
            try:
                assignee = User.objects.filter(pk=int(raw), is_active_member=True).first()
            except (TypeError, ValueError):
                assignee = None
            if assignee is None:
                raise ValidationError({'user_id': 'No active user with this id.'})
            if task.project is not None and not is_project_participant(assignee, task.project):
                raise ValidationError({'user_id': 'The assignee must be a member of the task\'s project.'})
        if (assignee.id if assignee else None) != task.assigned_to_id:
            task._actor = request.user
            task.assigned_to = assignee
            task.save(update_fields=['assigned_to'])
            if assignee:
                notify(assignee, f'You were assigned to task "{task.title}".', task=task, category=Category.ASSIGNED)  # FR-027
        return Response(self.get_serializer(task).data)

    # -- status and workflow (FR-032 to FR-037) ----------------------------

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """
        FR-061/062: tasks with a due date in [start, end] (default: the current month).
        FR-065: filter by project, status or assignee - the same query params as the task
        list, since they share the same filterset.
        """
        start = parse_date(request.query_params.get('start') or '') or timezone.localdate().replace(day=1)
        end = parse_date(request.query_params.get('end') or '')
        if not end:
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
        qs = self.filter_queryset(self.get_queryset()).filter(due_date__range=(start, end))
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def workflow(self, request):
        """FR-033/035: every status a task can be moved to, in workflow order."""
        return Response(workflow_options())

    @action(detail=True, methods=['post'], url_path='status')
    def change_status(self, request, pk=None):
        task = self.get_object()
        serializer = TaskStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        custom = serializer.validated_data.get('custom_status')
        category = custom.category if custom else serializer.validated_data['status']
        if category == task.status and (custom.id if custom else None) == task.custom_status_id:
            return Response(self._fresh(task))
        validate_transition(task, category)  # FR-036 and FR-042
        next_occurrence = apply_status(task, category, custom, request.user)  # FR-034 / FR-064
        data = self._fresh(task)
        if next_occurrence:
            data['next_occurrence'] = self.get_serializer(self.get_queryset().get(pk=next_occurrence.pk)).data
        return Response(data)

    @action(detail=True, methods=['get'], url_path='status-history')
    def status_history(self, request, pk=None):
        """FR-034: every status change with who made it and when."""
        rows = self.get_object().status_history.select_related('changed_by')
        return Response(TaskStatusHistorySerializer(rows, many=True).data)

    # -- history and subtasks (FR-025, FR-038 to FR-040) -------------------

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """FR-025: what changed on this task, by whom and when (newest first)."""
        return Response(task_history(self.get_object()))

    @action(detail=True, methods=['get', 'post'])
    def subtasks(self, request, pk=None):
        """GET lists a task's subtasks (FR-040); POST creates one under it (FR-038)."""
        parent = self.get_object()
        if request.method == 'GET':
            subtasks = self.get_queryset().filter(parent_task=parent, is_archived=False).order_by('id')
            return Response(self.get_serializer(subtasks, many=True).data)
        data = request.data.copy()
        data['parent_task'] = parent.pk  # the URL decides the parent, never the body
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        subtask = serializer.save(created_by=request.user)
        if subtask.assigned_to:  # FR-039 / FR-027
            notify(subtask.assigned_to, f'You were assigned to task "{subtask.title}".', task=subtask, category=Category.ASSIGNED)
        return Response(self._fresh(subtask), status=201)

    # -- dependencies (FR-041, FR-042) -------------------------------------

    @action(detail=True, methods=['get'], url_path='dependency-candidates')
    def dependency_candidates(self, request, pk=None):
        """Tasks that could validly become a predecessor of this one (for the picker)."""
        found = dependency_candidates(self.get_object(), request.user, request.query_params.get('search', ''))
        return Response([
            {'id': t.id, 'title': t.title, 'status': t.status, 'status_label': t.status_label} for t in found
        ])

    @action(detail=True, methods=['post'], url_path='dependencies')
    def add_dependency(self, request, pk=None):
        """Make this task wait for `predecessor`."""
        task = self.get_object()
        try:
            predecessor = self.get_queryset().filter(pk=int(request.data.get('predecessor'))).first()
        except (TypeError, ValueError):
            predecessor = None
        if predecessor is None:
            raise ValidationError({'predecessor': 'No task with this id.'})
        check_predecessors(task=task, project=task.project, parent=task.parent_task, predecessors=[predecessor])
        task._actor = request.user
        task.depends_on.add(predecessor)
        return Response(self._fresh(task))

    @action(detail=True, methods=['delete'], url_path=r'dependencies/(?P<predecessor_id>[0-9]+)')
    def remove_dependency(self, request, pk=None, predecessor_id=None):
        task = self.get_object()
        task._actor = request.user
        task.depends_on.remove(int(predecessor_id))
        return Response(self._fresh(task))


class CustomTaskStatusViewSet(viewsets.ModelViewSet):
    """
    FR-035: everyone can read the statuses, only administrators can change them.
    A status that tasks use cannot be deleted - deactivate it to retire it.
    """
    queryset = CustomTaskStatus.objects.annotate(task_count=Count('tasks'))
    serializer_class = CustomTaskStatusSerializer
    permission_classes = [ReadOnlyOrIsAdmin]
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        status_obj = self.get_object()
        in_use = status_obj.tasks.count()
        if in_use:
            raise ValidationError({'detail': f'{in_use} task(s) use this status. Deactivate it instead of deleting it.'})
        return super().destroy(request, *args, **kwargs)


class CustomPriorityViewSet(viewsets.ModelViewSet):
    """
    FR-093: everyone can read the priorities, only administrators can change them.
    A priority that tasks use cannot be deleted - deactivate it to retire it.
    """
    queryset = CustomPriority.objects.annotate(task_count=Count('tasks'))
    serializer_class = CustomPrioritySerializer
    permission_classes = [ReadOnlyOrIsAdmin]
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        priority_obj = self.get_object()
        in_use = priority_obj.tasks.count()
        if in_use:
            raise ValidationError({'detail': f'{in_use} task(s) use this priority. Deactivate it instead of deleting it.'})
        return super().destroy(request, *args, **kwargs)


class TaskTagViewSet(viewsets.ModelViewSet):
    """FR-094: everyone can read the tag registry (for autocomplete), only administrators curate it."""
    queryset = TaskTag.objects.all()
    serializer_class = TaskTagSerializer
    permission_classes = [ReadOnlyOrIsAdmin]
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']


class SavedTaskFilterViewSet(viewsets.ModelViewSet):
    """FR-025: users can save and manage their own named task-list filters."""
    serializer_class = SavedTaskFilterSerializer
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return SavedTaskFilter.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
