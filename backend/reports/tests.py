"""FR-078 to FR-084: reporting and analytics."""
import csv
import io

from django.urls import reverse
from django.utils import timezone

from projects.models import Project
from taskflow.test_utils import ApiTestCase
from tasks.models import Task

TODAY = timezone.localdate()


class ReportTests(ApiTestCase):
    def make(self, **extra):
        data = dict(title='T', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    def change_status(self, task, status, user=None):
        self.as_user(user or self.pm)
        return self.client.post(reverse('task-change-status', args=[task.id]), {'status': status})

    # ---- access -----------------------------------------------------------------------

    def test_only_managers_can_view_reports(self):
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('report-summary')).status_code, 403)
        self.as_user(self.lead)
        self.assertEqual(self.client.get(reverse('report-summary')).status_code, 200)
        self.as_user(self.pm)
        self.assertEqual(self.client.get(reverse('report-summary')).status_code, 200)
        self.as_user(self.admin)
        self.assertEqual(self.client.get(reverse('report-summary')).status_code, 200)

    # ---- FR-078: task completion ------------------------------------------------------

    def test_tasks_created_and_completed_counted_within_range(self):
        self.make(title='in range')
        a = self.make(title='completed in range', assigned_to=self.member)
        self.change_status(a, 'COMPLETED', self.member)

        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'))
        self.assertEqual((res.data['tasks_created'], res.data['tasks_completed']), (2, 1))

    def test_date_range_filters_creation_and_completion(self):
        old_task = self.make(title='old')
        old_dt = timezone.make_aware(timezone.datetime.combine(TODAY - timezone.timedelta(days=100), timezone.datetime.min.time()))
        Task.objects.filter(pk=old_task.pk).update(created_at=old_dt)
        self.make(title='recent')

        self.as_user(self.pm)
        start = (TODAY - timezone.timedelta(days=5)).isoformat()
        res = self.client.get(reverse('report-summary'), {'start': start, 'end': TODAY.isoformat()})
        self.assertEqual(res.data['tasks_created'], 1)

    def test_invalid_range_rejected(self):
        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'), {'start': '2026-05-01', 'end': '2026-01-01'})
        self.assertEqual(res.status_code, 400)

    # ---- FR-079: overdue --------------------------------------------------------------

    def test_overdue_report_lists_current_overdue_tasks(self):
        overdue = self.make(title='late', assigned_to=self.member, due_date=TODAY - timezone.timedelta(days=3))
        self.make(title='fine', assigned_to=self.member, due_date=TODAY + timezone.timedelta(days=3))
        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'))
        self.assertEqual(res.data['tasks_overdue'], 1)
        self.assertEqual(res.data['overdue_tasks'][0]['id'], overdue.id)
        self.assertEqual(res.data['overdue_tasks'][0]['assignee']['username'], self.member.username)

    def test_overdue_is_not_restricted_by_date_range(self):
        # Overdue is "right now", not something that happened within [start, end].
        overdue = self.make(assigned_to=self.member, due_date=TODAY - timezone.timedelta(days=50))
        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'), {'start': TODAY.isoformat(), 'end': TODAY.isoformat()})
        self.assertEqual(res.data['tasks_overdue'], 1)

    # ---- FR-080: project progress -------------------------------------------------------

    def test_project_progress_included(self):
        self.make(status='COMPLETED')
        self.make(status='TODO')
        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'))
        row = next(p for p in res.data['projects'] if p['id'] == self.project.id)
        self.assertEqual((row['progress'], row['task_count']), (50, 2))

    def test_project_filter_narrows_everything(self):
        other = Project.objects.create(name='Other', manager=self.pm, created_by=self.pm, status='ACTIVE')
        self.make(project=other, title='elsewhere')
        self.make(title='here')
        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'), {'project': self.project.id})
        self.assertEqual(res.data['tasks_created'], 1)
        self.assertEqual([p['id'] for p in res.data['projects']], [self.project.id])

    def test_project_filter_respects_visibility(self):
        other = Project.objects.create(name='Hidden', manager=self.other_pm, created_by=self.other_pm, status='ACTIVE')
        self.as_user(self.pm)
        self.assertEqual(self.client.get(reverse('report-summary'), {'project': other.id}).status_code, 404)

    # ---- FR-081: workload --------------------------------------------------------------

    def test_workload_by_employee(self):
        a = self.make(assigned_to=self.member, status='TODO')
        b = self.make(assigned_to=self.member, status='COMPLETED')
        self.make(assigned_to=self.member2, status='TODO', due_date=TODAY - timezone.timedelta(days=1))
        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'))
        by_user = {e['user']['id']: e for e in res.data['tasks_by_employee']}
        self.assertEqual((by_user[self.member.id]['total'], by_user[self.member.id]['completed']), (2, 1))
        self.assertEqual(by_user[self.member2.id]['overdue'], 1)

    # ---- FR-082: already covered by range tests above; manager scoping too -----------

    def test_pm_only_sees_their_own_scope_admin_sees_everything(self):
        other = Project.objects.create(name='Other', manager=self.other_pm, created_by=self.other_pm, status='ACTIVE')
        Task.objects.create(title='elsewhere', project=other, created_by=self.other_pm)
        self.make(title='mine')

        self.as_user(self.pm)
        self.assertEqual(self.client.get(reverse('report-summary')).data['tasks_created'], 1)
        self.as_user(self.admin)
        self.assertEqual(self.client.get(reverse('report-summary')).data['tasks_created'], 2)

    # ---- FR-084: metrics for charts -----------------------------------------------------

    def test_by_priority_and_by_status_breakdowns(self):
        self.make(priority='HIGH', status='TODO')
        self.make(priority='HIGH', status='IN_PROGRESS')
        self.make(priority='LOW', status='TODO')
        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'))
        self.assertEqual(res.data['tasks_by_priority']['HIGH'], 2)
        self.assertEqual(res.data['tasks_by_priority']['LOW'], 1)
        self.assertEqual(res.data['tasks_by_status']['TODO'], 2)
        self.assertEqual(res.data['tasks_by_status']['IN_PROGRESS'], 1)

    def test_average_completion_time(self):
        a = self.make(assigned_to=self.member)
        past_dt = timezone.make_aware(timezone.datetime.combine(TODAY - timezone.timedelta(days=4), timezone.datetime.min.time()))
        Task.objects.filter(pk=a.pk).update(created_at=past_dt)
        self.change_status(a, 'COMPLETED', self.member)
        self.as_user(self.pm)
        res = self.client.get(reverse('report-summary'))
        self.assertEqual(res.data['avg_completion_days'], 4.0)

    def test_average_completion_time_is_null_without_completions(self):
        self.make()
        self.as_user(self.pm)
        self.assertIsNone(self.client.get(reverse('report-summary')).data['avg_completion_days'])

    # ---- FR-083: export ------------------------------------------------------------------

    def test_export_requires_manager(self):
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('report-export')).status_code, 403)

    def test_export_is_a_csv_matching_the_summary(self):
        self.make(title='Ship it', priority='CRITICAL', status='TODO', assigned_to=self.member)
        overdue = self.make(title='Late one', assigned_to=self.member2, due_date=TODAY - timezone.timedelta(days=2))

        self.as_user(self.pm)
        summary = self.client.get(reverse('report-summary')).data
        res = self.client.get(reverse('report-export'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="report_', res['Content-Disposition'])

        text = res.content.decode()
        rows = list(csv.reader(io.StringIO(text)))
        self.assertIn(['Tasks created', str(summary['tasks_created'])], rows)
        self.assertIn(['Tasks overdue (current)', str(summary['tasks_overdue'])], rows)
        self.assertIn(['CRITICAL', '1'], rows)
        self.assertTrue(any(row and row[0] == str(overdue.id) for row in rows))
