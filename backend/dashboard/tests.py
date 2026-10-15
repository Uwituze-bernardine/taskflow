"""FR-071 to FR-077: the personal dashboard."""
from django.urls import reverse
from django.utils import timezone

from projects.models import Project
from taskflow.test_utils import ApiTestCase
from tasks.models import Task


class DashboardTests(ApiTestCase):
    def make(self, **extra):
        data = dict(title='T', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    # ---- FR-071/072/073/074: personalized counts ------------------------------------

    def test_dashboard_reflects_my_tasks_not_everyone_elses(self):
        today = timezone.localdate()
        self.make(assigned_to=self.member, status='TODO')
        self.make(assigned_to=self.member, status='IN_PROGRESS')
        self.make(assigned_to=self.member, status='COMPLETED')
        self.make(assigned_to=self.member, status='TODO', due_date=today - timezone.timedelta(days=2))  # overdue
        self.make(assigned_to=self.member2, status='TODO')  # someone else's - not counted

        self.as_user(self.member)
        res = self.client.get(reverse('dashboard'))
        self.assertEqual(res.status_code, 200)
        my = res.data['my_tasks']
        self.assertEqual((my['total'], my['TODO'], my['IN_PROGRESS'], my['COMPLETED'], my['overdue']), (4, 2, 1, 1, 1))

    def test_pending_and_overdue_lists_exclude_finished_tasks(self):
        today = timezone.localdate()
        pending = self.make(assigned_to=self.member, status='TODO')
        overdue = self.make(assigned_to=self.member, status='TODO', due_date=today - timezone.timedelta(days=1))
        self.make(assigned_to=self.member, status='COMPLETED')
        self.make(assigned_to=self.member, status='CANCELLED', due_date=today - timezone.timedelta(days=5))

        self.as_user(self.member)
        res = self.client.get(reverse('dashboard'))
        pending_ids = {t['id'] for t in res.data['pending_tasks']}
        overdue_ids = {t['id'] for t in res.data['overdue_tasks']}
        self.assertEqual(pending_ids, {pending.id, overdue.id})
        self.assertEqual(overdue_ids, {overdue.id})

    def test_archived_tasks_are_excluded(self):
        self.make(assigned_to=self.member, is_archived=True)
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('dashboard')).data['my_tasks']['total'], 0)

    # ---- FR-075: project progress ----------------------------------------------------

    def test_dashboard_lists_my_projects_with_progress(self):
        self.make(status='COMPLETED')
        self.make(status='TODO')
        other = Project.objects.create(name='Other', manager=self.other_pm, created_by=self.other_pm, status='ACTIVE')
        Task.objects.create(title='Elsewhere', project=other, created_by=self.other_pm, status='COMPLETED')

        self.as_user(self.pm)
        res = self.client.get(reverse('dashboard'))
        by_id = {p['id']: p for p in res.data['projects']}
        self.assertIn(self.project.id, by_id)
        self.assertNotIn(other.id, by_id)  # not a participant there
        self.assertEqual((by_id[self.project.id]['progress'], by_id[self.project.id]['task_count']), (50, 2))

    def test_archived_projects_are_excluded(self):
        self.project.status = 'ARCHIVED'
        self.project.save()
        self.as_user(self.pm)
        ids = {p['id'] for p in self.client.get(reverse('dashboard')).data['projects']}
        self.assertNotIn(self.project.id, ids)

    # ---- FR-076: team-level stats for managers, not for team members -----------------

    def test_team_member_has_no_team_stats(self):
        self.as_user(self.member)
        self.assertIsNone(self.client.get(reverse('dashboard')).data['team_stats'])

    def test_manager_sees_team_stats_by_status_and_employee(self):
        today = timezone.localdate()
        self.make(assigned_to=self.member, status='TODO')
        self.make(assigned_to=self.member, status='IN_PROGRESS')
        self.make(assigned_to=self.member2, status='TODO', due_date=today - timezone.timedelta(days=1))
        self.make(status='TODO')  # unassigned: not part of anyone's workload

        self.as_user(self.pm)
        res = self.client.get(reverse('dashboard'))
        stats = res.data['team_stats']
        self.assertEqual((stats['total'], stats['overdue']), (3, 1))
        self.assertEqual(stats['by_status']['TODO'], 2)
        by_user = {e['user']['id']: e for e in stats['by_employee']}
        self.assertEqual(by_user[self.member.id]['total'], 2)
        self.assertEqual((by_user[self.member2.id]['total'], by_user[self.member2.id]['overdue']), (1, 1))

    def test_team_leader_team_stats_scoped_to_their_projects(self):
        other = Project.objects.create(name='Other', manager=self.other_pm, created_by=self.other_pm, status='ACTIVE')
        Task.objects.create(title='Elsewhere', project=other, created_by=self.other_pm, assigned_to=self.outsider)
        self.make(assigned_to=self.member)  # in self.project, which self.lead belongs to
        self.as_user(self.lead)
        stats = self.client.get(reverse('dashboard')).data['team_stats']
        self.assertEqual(stats['total'], 1)

    # ---- FR-077: visual indicators - the task payloads carry what the UI needs -------

    def test_task_entries_include_status_and_priority_for_visual_indicators(self):
        self.make(assigned_to=self.member, status='IN_PROGRESS', priority='CRITICAL')
        self.as_user(self.member)
        task = self.client.get(reverse('dashboard')).data['pending_tasks'][0]
        self.assertEqual((task['status'], task['priority'], task['status_label'], task['priority_label']),
                          ('IN_PROGRESS', 'CRITICAL', 'In Progress', 'Critical'))

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 401)
