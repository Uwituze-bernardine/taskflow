"""FR-071 to FR-077: a personalized work overview."""
from django.db.models import Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.access import visible_projects, with_progress
from tasks.access import team_queryset, visible_tasks
from tasks.models import Task, TaskStatus
from tasks.serializers import TaskSerializer
from users.serializers import UserDirectorySerializer

FINISHED = (TaskStatus.COMPLETED, TaskStatus.CANCELLED)


def _status_counts(qs):
    """
    `qs` is normally built on `visible_tasks()`, whose OR'd, multi-joined Q object (project
    manager/members/assignee/creator/...) leaves extra JOINs (e.g. to project membership) in
    the query even after further filtering. Grouping directly on that queryset - even with
    `Count(..., distinct=True)` - lets those leftover joins corrupt the GROUP BY, splitting one
    status into several bogus groups. Re-querying by a plain id list sidesteps the joins
    entirely, so the aggregate can't be contaminated by them.
    """
    task_ids = list(qs.values_list('id', flat=True))
    counts = {value: 0 for value in TaskStatus.values}
    for row in Task.objects.filter(id__in=task_ids).values('status').annotate(n=Count('id')):
        counts[row['status']] = row['n']
    return counts


class DashboardView(APIView):
    """FR-071: GET /api/dashboard/ - everything the logged-in user's dashboard needs in one call."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()

        my_tasks = visible_tasks(user).filter(assigned_to=user, is_archived=False)
        status_counts = _status_counts(my_tasks)
        overdue_qs = my_tasks.filter(due_date__lt=today).exclude(status__in=FINISHED)

        # FR-072/073/074/077: pending and overdue tasks, with status/priority for visual indicators.
        pending_qs = (
            my_tasks.exclude(status__in=FINISHED)
            .select_related('project', 'assigned_to', 'custom_status', 'custom_priority')
            .order_by('due_date')[:10]
        )
        overdue_list_qs = overdue_qs.select_related('project', 'assigned_to', 'custom_status', 'custom_priority')[:10]
        ctx = {'request': request}

        # FR-075: progress of the projects I'm part of.
        projects = with_progress(visible_projects(user).exclude(status='ARCHIVED')).order_by('name')[:10]
        project_data = [{
            'id': p.id, 'name': p.name, 'status': p.status,
            'progress': round(p.n_done / p.n_tasks * 100) if p.n_tasks else 0,
            'task_count': p.n_tasks,
        } for p in projects]

        data = {
            'my_tasks': {
                'total': sum(status_counts.values()),
                **status_counts,
                'overdue': overdue_qs.count(),
            },
            'pending_tasks': TaskSerializer(pending_qs, many=True, context=ctx).data,
            'overdue_tasks': TaskSerializer(overdue_list_qs, many=True, context=ctx).data,
            'projects': project_data,
            'team_stats': None,
        }

        # FR-076: managers also see team-level stats.
        if user.is_manager:
            team_qs = team_queryset(user)
            team_status_counts = _status_counts(team_qs.filter(is_archived=False))
            team_overdue = team_qs.filter(is_archived=False, due_date__lt=today).exclude(status__in=FINISHED)
            by_employee = {}
            for t in team_qs.filter(is_archived=False).select_related('assigned_to'):
                entry = by_employee.setdefault(t.assigned_to_id, {
                    'user': UserDirectorySerializer(t.assigned_to).data, 'total': 0, 'completed': 0, 'overdue': 0,
                })
                entry['total'] += 1
                if t.status == TaskStatus.COMPLETED:
                    entry['completed'] += 1
                if t.is_overdue:
                    entry['overdue'] += 1
            data['team_stats'] = {
                'total': sum(team_status_counts.values()),
                'by_status': team_status_counts,
                'overdue': team_overdue.count(),
                'by_employee': sorted(by_employee.values(), key=lambda e: -e['total']),
            }

        return Response(data)
