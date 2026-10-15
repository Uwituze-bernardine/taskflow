from django.urls import reverse

from projects.models import Project
from taskflow.test_utils import ApiTestCase
from tasks.models import Task


class ProjectTests(ApiTestCase):
    def payload(self, **extra):
        return {'name': 'Gemini', 'description': 'd', **extra}

    def new_task(self, **extra):
        data = dict(title='T', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    # FR-008
    def test_pm_creates_project_and_becomes_its_manager(self):
        self.as_user(self.pm)
        res = self.client.post(reverse('project-list'), self.payload())
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['manager'], self.pm.id)
        self.assertEqual(res.data['status'], 'PLANNED')

    def test_only_admin_and_pm_can_create(self):
        for user in (self.lead, self.member):
            self.as_user(user)
            self.assertEqual(self.client.post(reverse('project-list'), self.payload()).status_code, 403)
        self.as_user(self.admin)
        res = self.client.post(reverse('project-list'), self.payload(manager=self.other_pm.id))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['manager'], self.other_pm.id)

    def test_manager_must_be_pm_or_admin_and_pm_cannot_assign_someone_else(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.post(reverse('project-list'), self.payload(manager=self.member.id)).status_code, 400)
        self.as_user(self.pm)
        self.assertEqual(self.client.post(reverse('project-list'), self.payload(manager=self.other_pm.id)).status_code, 400)

    # FR-014
    def test_dates_are_validated(self):
        self.as_user(self.pm)
        res = self.client.post(reverse('project-list'), self.payload(start_date='2026-05-01', end_date='2026-04-01'))
        self.assertEqual(res.status_code, 400)
        ok = self.client.post(reverse('project-list'), self.payload(start_date='2026-05-01', end_date='2026-06-01'))
        self.assertEqual((ok.status_code, ok.data['end_date']), (201, '2026-06-01'))

    # FR-012
    def test_visibility(self):
        self.as_user(self.outsider)
        self.assertNotIn(self.project.id, self.ids(self.client.get(reverse('project-list'))))
        self.assertEqual(self.client.get(reverse('project-detail', args=[self.project.id])).status_code, 404)
        for user in (self.pm, self.member, self.lead, self.admin):
            self.as_user(user)
            self.assertIn(self.project.id, self.ids(self.client.get(reverse('project-list'))), user.username)
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('project-detail', args=[self.project.id])).status_code, 200)

    # FR-009
    def test_only_the_manager_or_admin_can_edit(self):
        url = reverse('project-detail', args=[self.project.id])
        self.as_user(self.pm)
        res = self.client.patch(url, {'name': 'Apollo 2', 'status': 'ON_HOLD'})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['name'], 'Apollo 2')
        for user in (self.lead, self.member):  # participants may look but not touch
            self.as_user(user)
            self.assertEqual(self.client.patch(url, {'name': 'x'}).status_code, 403, user.username)
        self.as_user(self.other_pm)  # not on the project at all: it is invisible to them
        self.assertEqual(self.client.patch(url, {'name': 'x'}).status_code, 404)
        self.as_user(self.admin)
        self.assertEqual(self.client.patch(url, {'name': 'By admin'}).status_code, 200)

    def test_status_cannot_be_set_to_closed_through_edit(self):
        self.as_user(self.pm)
        res = self.client.patch(reverse('project-detail', args=[self.project.id]), {'status': 'CLOSED'})
        self.assertEqual(res.status_code, 400)

    # FR-010
    def test_close_archive_reopen_lifecycle(self):
        pid = self.project.id
        self.as_user(self.member)
        self.assertEqual(self.client.post(reverse('project-close', args=[pid])).status_code, 403)
        self.as_user(self.pm)
        res = self.client.post(reverse('project-close', args=[pid]))
        self.assertEqual((res.status_code, res.data['status']), (200, 'CLOSED'))
        self.assertEqual(self.client.patch(reverse('project-detail', args=[pid]), {'name': 'x'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('project-close', args=[pid])).status_code, 400)
        res = self.client.post(reverse('project-archive', args=[pid]))
        self.assertEqual(res.data['status'], 'ARCHIVED')
        self.assertNotIn(pid, self.ids(self.client.get(reverse('project-list'))))
        self.assertIn(pid, self.ids(self.client.get(reverse('project-list'), {'include_archived': 'true'})))
        self.assertIn(pid, self.ids(self.client.get(reverse('project-list'), {'status': 'ARCHIVED'})))
        res = self.client.post(reverse('project-reopen', args=[pid]))
        self.assertEqual(res.data['status'], 'ACTIVE')
        self.assertEqual(self.client.patch(reverse('project-detail', args=[pid]), {'name': 'Back'}).status_code, 200)

    def test_projects_cannot_be_deleted(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.delete(reverse('project-detail', args=[self.project.id])).status_code, 405)

    # FR-011
    def test_manager_adds_and_removes_members(self):
        url = reverse('project-add-member', args=[self.project.id])
        self.as_user(self.member)
        self.assertEqual(self.client.post(url, {'user_id': self.outsider.id}).status_code, 403)
        self.as_user(self.pm)
        res = self.client.post(url, {'user_id': self.outsider.id})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn(self.outsider.id, res.data['members'])
        res = self.client.delete(reverse('project-remove-member', args=[self.project.id, self.outsider.id]))
        self.assertEqual(res.status_code, 200, res.data)
        self.assertNotIn(self.outsider.id, res.data['members'])

    def test_add_member_rules(self):
        url = reverse('project-add-member', args=[self.project.id])
        self.as_user(self.pm)
        self.assertEqual(self.client.post(url, {'user_id': self.pm.id}).status_code, 400)  # already the manager
        self.assertEqual(self.client.post(url, {'user_id': 99999}).status_code, 400)
        self.outsider.is_active_member = False
        self.outsider.save()
        self.assertEqual(self.client.post(url, {'user_id': self.outsider.id}).status_code, 400)  # deactivated

    def test_member_with_open_tasks_cannot_be_removed(self):
        task = self.new_task(assigned_to=self.member)
        self.as_user(self.pm)
        url = reverse('project-remove-member', args=[self.project.id, self.member.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 400)
        self.assertIn('open task', str(res.data))
        task.status = 'COMPLETED'
        task.save()
        self.assertEqual(self.client.delete(url).status_code, 200)

    # FR-013
    def test_progress_counts_completed_top_level_active_tasks(self):
        self.new_task(status='COMPLETED')
        self.new_task(status='TODO')
        self.new_task(status='IN_PROGRESS')
        self.new_task(status='CANCELLED')                    # not counted
        self.new_task(status='COMPLETED', is_archived=True)  # not counted
        parent = self.new_task(status='TODO')
        self.new_task(status='COMPLETED', parent_task=parent)  # subtasks not counted here
        self.as_user(self.pm)
        detail = self.client.get(reverse('project-detail', args=[self.project.id])).data
        self.assertEqual((detail['task_count'], detail['progress']), (4, 25))
        self.assertEqual(detail['status_counts']['COMPLETED'], 1)
        listed = next(p for p in self.client.get(reverse('project-list')).data['results'] if p['id'] == self.project.id)
        self.assertEqual((listed['task_count'], listed['progress']), (4, 25))

    def test_progress_is_zero_without_tasks(self):
        self.as_user(self.pm)
        self.assertEqual(self.client.get(reverse('project-detail', args=[self.project.id])).data['progress'], 0)

    def test_permissions_flags_match_role(self):
        for user, edit, create_tasks in ((self.pm, True, True), (self.lead, False, True), (self.member, False, False)):
            self.as_user(user)
            flags = self.client.get(reverse('project-detail', args=[self.project.id])).data['permissions']
            self.assertEqual((flags['edit'], flags['create_tasks']), (edit, create_tasks), user.username)

    def test_user_details_do_not_leak_contact_info(self):
        self.as_user(self.member)
        data = self.client.get(reverse('project-detail', args=[self.project.id])).data
        self.assertEqual(set(data['manager_detail']), {'id', 'username', 'first_name', 'last_name', 'role'})
        self.assertEqual(set(data['members_detail'][0]), {'id', 'username', 'first_name', 'last_name', 'role'})
