from django.urls import reverse

from notifications.models import Notification
from projects.models import Project
from taskflow.test_utils import ApiTestCase
from tasks.models import Task, TaskStatusHistory


class TaskTests(ApiTestCase):
    def payload(self, **extra):
        data = {'title': 'Write spec', 'description': 'Details', 'project': self.project.id,
                'priority': 'HIGH', 'due_date': '2026-12-01'}
        data.update(extra)
        return data

    def make(self, **extra):
        data = dict(title='Existing', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    def url(self, name, task):
        return reverse(f'task-{name}', args=[task.id])

    def create(self, user, **extra):
        self.as_user(user)
        return self.client.post(reverse('task-list'), self.payload(**extra), format='json')

    # ---- FR-015..FR-021: creating -------------------------------------------------

    def test_pm_creates_task_with_all_fields(self):
        res = self.create(self.pm, tags=['api', 'backend'], start_date='2026-11-01')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['created_by'], self.pm.id)
        self.assertEqual((res.data['status'], res.data['priority']), ('TODO', 'HIGH'))
        self.assertEqual((res.data['project_name'], res.data['due_date']), ('Apollo', '2026-12-01'))
        self.assertEqual(res.data['tags'], ['api', 'backend'])

    def test_who_can_create(self):
        self.assertEqual(self.create(self.lead).status_code, 201)      # team leader in the project
        self.assertEqual(self.create(self.admin).status_code, 201)
        member = self.create(self.member)
        self.assertEqual(member.status_code, 403)
        self.assertIn('team leaders', str(member.data))
        self.assertEqual(self.create(self.other_pm).status_code, 403)  # right role, not on the project

    def test_standalone_task_without_project(self):
        res = self.create(self.other_pm, project=None)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertIsNone(res.data['project'])

    def test_status_cannot_be_chosen_on_create(self):
        self.assertEqual(self.create(self.pm, status='COMPLETED').data['status'], 'TODO')

    def test_closed_project_rejects_new_tasks(self):
        self.project.status = 'CLOSED'
        self.project.save()
        self.assertEqual(self.create(self.pm).status_code, 400)

    def test_validation(self):
        self.assertEqual(self.create(self.pm, start_date='2026-12-05', due_date='2026-12-01').status_code, 400)
        self.assertEqual(self.create(self.pm, title='').status_code, 400)
        self.assertEqual(self.create(self.pm, tags=['a', ' A ', 'B', '']).data['tags'], ['a', 'B'])

    # ---- FR-018 / FR-026: assignee rules ---------------------------------------------

    def test_create_with_assignee_notifies_them(self):
        res = self.create(self.pm, assigned_to=self.member.id)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(Notification.objects.filter(recipient=self.member, task_id=res.data['id']).exists())

    def test_assignee_must_be_project_member_and_active(self):
        self.assertEqual(self.create(self.pm, assigned_to=self.outsider.id).status_code, 400)
        self.member2.is_active_member = False
        self.member2.save()
        self.assertEqual(self.create(self.pm, assigned_to=self.member2.id).status_code, 400)
        self.assertEqual(self.create(self.pm, assigned_to=self.pm.id).status_code, 201)  # the manager counts

    # ---- FR-024: viewing ------------------------------------------------------------

    def test_visibility(self):
        task = self.make()
        for user in (self.pm, self.lead, self.member, self.admin):
            self.as_user(user)
            self.assertEqual(self.client.get(self.url('detail', task)).status_code, 200, user.username)
        for user in (self.outsider, self.other_pm):
            self.as_user(user)
            self.assertEqual(self.client.get(self.url('detail', task)).status_code, 404, user.username)
            self.assertNotIn(task.id, self.ids(self.client.get(reverse('task-list'))))

    def test_standalone_task_visible_only_to_creator_assignee_and_admin(self):
        task = self.make(project=None, created_by=self.other_pm, assigned_to=self.outsider)
        for user, code in ((self.other_pm, 200), (self.outsider, 200), (self.admin, 200), (self.member, 404), (self.pm, 404)):
            self.as_user(user)
            self.assertEqual(self.client.get(self.url('detail', task)).status_code, code, user.username)

    def test_detail_reports_what_the_current_user_may_do(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        flags = self.client.get(self.url('detail', task)).data['permissions']
        self.assertTrue(flags['edit'] and flags['assign'] and flags['archive'] and flags['change_status'])
        self.as_user(self.member)
        flags = self.client.get(self.url('detail', task)).data['permissions']
        self.assertEqual((flags['edit'], flags['assign'], flags['change_status']), (False, False, True))
        self.as_user(self.member2)  # on the project, but neither assigned nor a manager
        self.assertFalse(self.client.get(self.url('detail', task)).data['permissions']['change_status'])

    # ---- FR-022: editing ------------------------------------------------------------

    def test_managers_can_edit_others_cannot(self):
        task = self.make(assigned_to=self.member)
        for user in (self.pm, self.lead, self.admin):
            self.as_user(user)
            res = self.client.patch(self.url('detail', task), {'title': f'by {user.username}', 'priority': 'LOW'})
            self.assertEqual(res.status_code, 200, (user.username, res.data))
        for user in (self.member, self.member2):  # even the assignee cannot edit the task itself
            self.as_user(user)
            self.assertEqual(self.client.patch(self.url('detail', task), {'title': 'x'}).status_code, 403, user.username)

    def test_status_and_archive_flag_are_not_editable_through_patch(self):
        task = self.make()
        self.as_user(self.pm)
        self.client.patch(self.url('detail', task), {'status': 'COMPLETED', 'is_archived': True})
        task.refresh_from_db()
        self.assertEqual((task.status, task.is_archived), ('TODO', False))

    def test_cannot_move_task_into_a_project_you_cannot_use(self):
        other = Project.objects.create(name='Other', manager=self.other_pm, created_by=self.other_pm, status='ACTIVE')
        task = self.make()
        self.as_user(self.pm)
        self.assertEqual(self.client.patch(self.url('detail', task), {'project': other.id}).status_code, 403)

    def test_tasks_of_closed_projects_are_read_only(self):
        task = self.make(assigned_to=self.member)
        self.project.status = 'CLOSED'
        self.project.save()
        self.as_user(self.pm)
        self.assertEqual(self.client.patch(self.url('detail', task), {'title': 'x'}).status_code, 403)
        self.as_user(self.member)
        self.assertEqual(self.client.post(self.url('change-status', task), {'status': 'IN_PROGRESS'}).status_code, 403)
        self.assertEqual(self.client.get(self.url('detail', task)).status_code, 200)

    # ---- FR-023: archive / delete ---------------------------------------------------

    def test_delete_archives_and_restore_brings_back(self):
        task = self.make()
        self.as_user(self.member)
        self.assertEqual(self.client.delete(self.url('detail', task)).status_code, 403)
        self.as_user(self.pm)
        self.assertEqual(self.client.delete(self.url('detail', task)).status_code, 204)
        self.assertTrue(Task.objects.get(pk=task.pk).is_archived)
        self.assertNotIn(task.id, self.ids(self.client.get(reverse('task-list'))))
        self.assertIn(task.id, self.ids(self.client.get(reverse('task-list'), {'archived': 'true'})))
        res = self.client.post(self.url('restore', task))
        self.assertEqual((res.status_code, res.data['is_archived']), (200, False))
        self.assertIn(task.id, self.ids(self.client.get(reverse('task-list'))))

    def test_archive_action(self):
        task = self.make()
        self.as_user(self.pm)
        self.assertTrue(self.client.post(self.url('archive', task)).data['is_archived'])

    def test_permanent_delete_is_admin_only(self):
        task = self.make()
        self.as_user(self.pm)
        self.assertEqual(self.client.delete(self.url('detail', task) + '?permanent=true').status_code, 403)
        self.as_user(self.admin)
        self.assertEqual(self.client.delete(self.url('detail', task) + '?permanent=true').status_code, 204)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    # ---- FR-026/027/028/031: assignment ---------------------------------------------

    def test_assign_notifies_and_reassign_notifies_the_new_person(self):
        task = self.make()
        self.as_user(self.pm)
        res = self.client.post(self.url('assign', task), {'user_id': self.member.id})
        self.assertEqual((res.status_code, res.data['assigned_to']), (200, self.member.id), res.data)
        self.assertEqual(Notification.objects.filter(recipient=self.member, task=task).count(), 1)
        res = self.client.post(self.url('assign', task), {'user_id': self.member2.id})
        self.assertEqual(res.data['assigned_to'], self.member2.id)
        self.assertEqual(Notification.objects.filter(recipient=self.member2, task=task).count(), 1)

    def test_assigning_to_the_same_person_again_is_a_no_op(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        self.client.post(self.url('assign', task), {'user_id': self.member.id})
        self.assertEqual(Notification.objects.filter(recipient=self.member, task=task).count(), 0)

    def test_unassign(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        res = self.client.post(self.url('assign', task), {'user_id': None}, format='json')
        self.assertEqual((res.status_code, res.data['assigned_to']), (200, None))

    def test_unauthorized_users_cannot_assign(self):  # FR-031
        task = self.make(assigned_to=self.member)
        for user in (self.member, self.member2):
            self.as_user(user)
            res = self.client.post(self.url('assign', task), {'user_id': user.id})
            self.assertEqual(res.status_code, 403, user.username)
            self.assertIn('not authorized', str(res.data))
        self.as_user(self.lead)
        self.assertEqual(self.client.post(self.url('assign', task), {'user_id': self.member2.id}).status_code, 200)

    def test_assign_rejects_bad_targets(self):
        task = self.make()
        self.as_user(self.pm)
        for bad in (self.outsider.id, 99999, 'abc'):
            self.assertEqual(self.client.post(self.url('assign', task), {'user_id': bad}).status_code, 400, bad)

    def test_editing_the_assignee_via_patch_also_notifies(self):
        task = self.make()
        self.as_user(self.pm)
        self.client.patch(self.url('detail', task), {'assigned_to': self.member.id})
        self.assertEqual(Notification.objects.filter(recipient=self.member, task=task).count(), 1)

    # ---- FR-032/034/036: status ----------------------------------------------------

    def test_assignee_changes_status_and_it_is_recorded(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.member)
        res = self.client.post(self.url('change-status', task), {'status': 'IN_PROGRESS'})
        self.assertEqual((res.status_code, res.data['status']), (200, 'IN_PROGRESS'), res.data)
        row = TaskStatusHistory.objects.get(task=task)
        self.assertEqual((row.from_status, row.to_status, row.changed_by), ('TODO', 'IN_PROGRESS', self.member))
        self.assertTrue(Notification.objects.filter(recipient=self.member, task=task).exists())

    def test_only_managers_and_assignee_may_change_status(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.member2)
        self.assertEqual(self.client.post(self.url('change-status', task), {'status': 'IN_PROGRESS'}).status_code, 403)
        self.as_user(self.pm)
        self.assertEqual(self.client.post(self.url('change-status', task), {'status': 'IN_PROGRESS'}).status_code, 200)

    def test_cannot_complete_unassigned_task_and_same_status_is_a_no_op(self):
        task = self.make()
        self.as_user(self.pm)
        self.assertEqual(self.client.post(self.url('change-status', task), {'status': 'COMPLETED'}).status_code, 400)
        self.client.post(self.url('change-status', task), {'status': 'TODO'})
        self.assertEqual(TaskStatusHistory.objects.filter(task=task).count(), 0)

    # ---- FR-025: history -----------------------------------------------------------

    def test_history_records_who_changed_what(self):
        res = self.create(self.pm)
        tid = res.data['id']
        task = Task.objects.get(pk=tid)
        self.as_user(self.lead)
        self.client.patch(self.url('detail', task), {'priority': 'LOW', 'title': 'New title'})
        self.as_user(self.pm)
        self.client.post(self.url('assign', task), {'user_id': self.member.id})
        self.as_user(self.member)
        self.client.post(self.url('change-status', task), {'status': 'IN_PROGRESS'})

        self.as_user(self.member)  # anyone who can see the task can read its history
        history = self.client.get(self.url('history', task)).data
        self.assertEqual([h['action'] for h in history], ['task.updated', 'task.updated', 'task.updated', 'task.created'])
        status, assign, edit, created = history
        self.assertEqual(status['actor']['name'], 'Member Test')
        self.assertEqual(status['changes'], [{'field': 'status', 'label': 'Status', 'from': 'To Do', 'to': 'In Progress'}])
        self.assertEqual(assign['actor']['name'], 'Pm Test')
        self.assertEqual((assign['changes'][0]['from'], assign['changes'][0]['to']), (None, 'Member Test'))
        self.assertEqual(edit['actor']['name'], 'Lead Test')
        by_field = {c['field']: c for c in edit['changes']}
        self.assertEqual((by_field['priority']['from'], by_field['priority']['to']), ('High', 'Low'))
        self.assertEqual((by_field['title']['from'], by_field['title']['to']), ('Write spec', 'New title'))
        self.assertEqual(created['actor']['name'], 'Pm Test')

    def test_unchanged_saves_are_not_logged_and_archiving_is(self):
        task = self.make()
        self.as_user(self.pm)
        self.client.patch(self.url('detail', task), {'title': task.title})
        self.assertEqual(len(self.client.get(self.url('history', task)).data), 1)  # only "created"
        self.client.post(self.url('archive', task))
        latest = self.client.get(self.url('history', task)).data[0]
        self.assertEqual((latest['changes'][0]['label'], latest['changes'][0]['to']), ('Archived', 'Yes'))

    def test_history_is_hidden_from_people_who_cannot_see_the_task(self):
        task = self.make()
        self.as_user(self.outsider)
        self.assertEqual(self.client.get(self.url('history', task)).status_code, 404)

    # ---- FR-029 / FR-030 ------------------------------------------------------------

    def test_my_tasks(self):
        mine = self.make(assigned_to=self.member)
        self.make(assigned_to=self.member2)
        self.make(assigned_to=self.member, is_archived=True)
        self.as_user(self.member)
        self.assertEqual(self.ids(self.client.get(reverse('task-mine'))), {mine.id})

    def test_managers_see_their_teams_assigned_tasks(self):
        a = self.make(assigned_to=self.member)
        b = self.make(assigned_to=self.member2)
        self.make()  # unassigned: not "assigned to a team member"
        other = Project.objects.create(name='Other', manager=self.other_pm, created_by=self.other_pm, status='ACTIVE')
        elsewhere = Task.objects.create(title='Elsewhere', project=other, created_by=self.other_pm, assigned_to=self.outsider)
        expectations = {
            self.pm: {a.id, b.id},           # manages the project
            self.lead: {a.id, b.id},         # is a member of it
            self.admin: {a.id, b.id, elsewhere.id},
            self.other_pm: {elsewhere.id},   # only their own project's team
        }
        for user, expected in expectations.items():
            self.as_user(user)
            res = self.client.get(reverse('task-team'))
            self.assertEqual((res.status_code, self.ids(res)), (200, expected), user.username)

    def test_team_members_cannot_use_the_team_view(self):
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('task-team')).status_code, 403)

    # ---- misc -----------------------------------------------------------------------

    def test_search_by_id_and_text(self):
        task = self.make(title='Alpha')
        self.make(title='Beta')
        self.as_user(self.pm)
        self.assertEqual(self.ids(self.client.get(reverse('task-list'), {'search': str(task.id)})), {task.id})
        self.assertEqual(self.ids(self.client.get(reverse('task-list'), {'search': 'alph'})), {task.id})

    def test_sorting_by_priority_and_due_date_is_meaningful(self):
        low = self.make(title='low', priority='LOW', due_date='2026-01-02')
        crit = self.make(title='crit', priority='CRITICAL')  # no due date
        high = self.make(title='high', priority='HIGH', due_date='2026-01-01')
        self.as_user(self.pm)

        def order(param):
            rows = self.client.get(reverse('task-list'), {'ordering': param}).data['results']
            return [r['id'] for r in rows]

        self.assertEqual(order('-priority'), [crit.id, high.id, low.id])
        self.assertEqual(order('priority'), [low.id, high.id, crit.id])
        self.assertEqual(order('due_date'), [high.id, low.id, crit.id])   # undated task last
        self.assertEqual(order('-due_date'), [low.id, high.id, crit.id])

    def test_task_details_do_not_leak_contact_info(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.member2)
        detail = self.client.get(self.url('detail', task)).data['assigned_to_detail']
        self.assertEqual(set(detail), {'id', 'username', 'first_name', 'last_name', 'role'})

    def test_custom_statuses_are_admin_only_to_change(self):
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('custom-status-list')).status_code, 200)
        self.assertEqual(self.client.post(reverse('custom-status-list'), {'name': 'QA', 'order': 1}).status_code, 403)
        self.as_user(self.admin)
        self.assertEqual(self.client.post(reverse('custom-status-list'), {'name': 'QA', 'order': 1}).status_code, 201)
