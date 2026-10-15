from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.response import Response

from users.models import User
from .access import CLOSED_STATUSES, visible_projects, with_progress
from .models import Project, ProjectMembership
from .permissions import ProjectPermission
from .serializers import ProjectDetailSerializer, ProjectMemberSerializer, ProjectSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    """
    FR-008 create, FR-009 edit, FR-010 archive/close, FR-011 members,
    FR-012 view, FR-013 progress, FR-014 dates.

    Projects are never deleted (that would delete their tasks); they are archived or closed.
    """
    permission_classes = [ProjectPermission]
    filterset_fields = ['status', 'manager']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'start_date', 'end_date']
    # DELETE is allowed only for the member-removal action; deleting a project itself is refused.
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    ordering = ['-created_at']  # annotated queries lose Meta.ordering, so be explicit

    def get_serializer_class(self):
        return ProjectSerializer if self.action == 'list' else ProjectDetailSerializer

    def get_queryset(self):
        qs = with_progress(
            visible_projects(self.request.user).select_related('manager').prefetch_related('members')
        )
        params = self.request.query_params
        if self.action == 'list' and 'status' not in params and params.get('include_archived') != 'true':
            qs = qs.exclude(status='ARCHIVED')
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed('DELETE', detail='Projects are archived or closed, not deleted.')

    def _fresh(self, project):
        """Re-read with annotations/prefetches so the response reflects the change."""
        return Response(self.get_serializer(self.get_queryset().get(pk=project.pk)).data)

    # -- members (FR-011) --------------------------------------------------

    @action(detail=True, methods=['post'], url_path='members')
    def add_member(self, request, pk=None):
        project = self.get_object()
        serializer = ProjectMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(pk=serializer.validated_data['user_id'], is_active_member=True).first()
        if user is None:
            raise ValidationError({'user_id': 'No active user with this id.'})
        if user.id == project.manager_id:
            raise ValidationError({'user_id': 'The project manager is already part of the project.'})
        ProjectMembership.objects.get_or_create(project=project, user=user)
        return self._fresh(project)

    @action(detail=True, methods=['delete'], url_path=r'members/(?P<user_id>[0-9]+)')
    def remove_member(self, request, pk=None, user_id=None):
        from tasks.models import Task

        project = self.get_object()
        open_tasks = (
            Task.objects.filter(project=project, assigned_to_id=user_id, is_archived=False)
            .exclude(status__in=['COMPLETED', 'CANCELLED'])
            .count()
        )
        if open_tasks:
            raise ValidationError({
                'detail': f'This member still has {open_tasks} open task(s) in the project. '
                          'Reassign or complete them first.'
            })
        ProjectMembership.objects.filter(project=project, user_id=user_id).delete()
        return self._fresh(project)

    # -- lifecycle (FR-010) ------------------------------------------------

    def _set_status(self, request, new_status, allowed_from=None, error=None):
        project = self.get_object()
        if allowed_from is not None and project.status not in allowed_from:
            raise ValidationError({'detail': error})
        project.status = new_status
        project.save(update_fields=['status', 'updated_at'])
        return self._fresh(project)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        return self._set_status(
            request, 'ARCHIVED', ['PLANNED', 'ACTIVE', 'ON_HOLD', 'CLOSED'], 'This project is already archived.'
        )

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        return self._set_status(
            request, 'CLOSED', ['PLANNED', 'ACTIVE', 'ON_HOLD'], 'This project is already closed or archived.'
        )

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        return self._set_status(request, 'ACTIVE', list(CLOSED_STATUSES), 'This project is not closed or archived.')
