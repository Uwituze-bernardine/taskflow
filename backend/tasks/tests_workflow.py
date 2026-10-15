"""
FR-032 to FR-037 (status and workflow) and FR-038 to FR-042 (subtasks and dependencies).
"""
from django.urls import reverse

from notifications.models import Notification
from taskflow.test_utils import ApiTestCase
from tasks.models import CustomPriority, CustomTaskStatus, Task, TaskStatusHistory


class WorkflowTests(ApiTestCase):
    def url(self, name, task):
        return reverse(f'task-{name}', args=[task.id])

    def make(self, **extra):
        data = dict(title='Existing', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    def change(self, task, **body):
        return self.client.post(self.url('change-status', task), body, format='json')

    # ---- FR-033: predefined statuses ------------------------------------------------

    def test_workflow_lists_predefined_statuses_in_order(self):
        self.as_user(self.member)
        res = self.client.get(reverse('task-workflow'))
        keys = [o['key'] for o in res.data]
        self.assertEqual(keys, ['TODO', 'IN_PROGRESS', 'BLOCKED', 'UNDER_REVIEW', 'COMPLETED', 'CANCELLED'])
        self.assertTrue(all(o['builtin'] for o in res.data))

    # ---- FR-032/FR-034: authorized change + recorded history ------------------------

    def test_assignee_changes_status_and_it_is_recorded(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.member)
        res = self.change(task, status='IN_PROGRESS')
        self.assertEqual((res.status_code, res.data['status']), (200, 'IN_PROGRESS'), res.data)
        row = TaskStatusHistory.objects.get(task=task)
        self.assertEqual((row.from_status, row.to_status, row.from_label, row.to_label, row.changed_by), ('TODO', 'IN_PROGRESS', 'To Do', 'In Progress', self.member))
        self.assertTrue(Notification.objects.filter(recipient=self.member, task=task).exists())

    def test_only_managers_and_assignee_may_change_status(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.member2)
        self.assertEqual(self.change(task, status='IN_PROGRESS').status_code, 403)
        self.as_user(self.pm)
        self.assertEqual(self.change(task, status='IN_PROGRESS').status_code, 200)

    def test_same_status_again_is_a_no_op(self):
        task = self.make()
        self.as_user(self.pm)
        self.change(task, status='TODO')
        self.assertEqual(TaskStatusHistory.objects.filter(task=task).count(), 0)

    def test_must_choose_exactly_one_of_status_or_custom_status(self):
        task = self.make()
        self.as_user(self.pm)
        self.assertEqual(self.change(task).status_code, 400)
        self.assertEqual(self.change(task, status='IN_PROGRESS', custom_status=1).status_code, 400)

    # ---- FR-035: administrator-configured custom statuses ----------------------------

    def test_admin_creates_custom_status_others_cannot(self):
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('custom-status-list')).status_code, 200)
        denied = self.client.post(reverse('custom-status-list'), {'name': 'QA Testing', 'category': 'UNDER_REVIEW'})
        self.assertEqual(denied.status_code, 403)
        self.as_user(self.admin)
        res = self.client.post(reverse('custom-status-list'), {'name': 'QA Testing', 'category': 'UNDER_REVIEW', 'order': 1})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['task_count'], 0)

    def test_custom_status_name_cannot_clash(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.post(reverse('custom-status-list'), {'name': 'To Do', 'category': 'TODO'}).status_code, 400)
        CustomTaskStatus.objects.create(name='QA', category='UNDER_REVIEW')
        self.assertEqual(self.client.post(reverse('custom-status-list'), {'name': 'qa', 'category': 'TODO'}).status_code, 400)

    def test_task_can_be_moved_to_a_custom_status_and_it_appears_in_workflow(self):
        qa = CustomTaskStatus.objects.create(name='QA Testing', category='UNDER_REVIEW', order=1)
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        res = self.change(task, custom_status=qa.id)
        self.assertEqual((res.status_code, res.data['status'], res.data['custom_status'], res.data['status_label']), (200, 'UNDER_REVIEW', qa.id, 'QA Testing'))
        row = TaskStatusHistory.objects.get(task=task)
        self.assertEqual((row.to_status, row.to_label), ('UNDER_REVIEW', 'QA Testing'))
        self.as_user(self.member)
        keys = [o['key'] for o in self.client.get(reverse('task-workflow')).data]
        self.assertIn(f'custom:{qa.id}', keys)

    def test_inactive_custom_status_cannot_be_selected_or_listed(self):
        qa = CustomTaskStatus.objects.create(name='QA Testing', category='UNDER_REVIEW', is_active=False)
        task = self.make()
        self.as_user(self.pm)
        self.assertEqual(self.change(task, custom_status=qa.id).status_code, 400)
        self.as_user(self.member)
        keys = [o['key'] for o in self.client.get(reverse('task-workflow')).data]
        self.assertNotIn(f'custom:{qa.id}', keys)

    def test_custom_status_in_use_cannot_be_deleted_or_recategorized(self):
        qa = CustomTaskStatus.objects.create(name='QA Testing', category='UNDER_REVIEW')
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        self.change(task, custom_status=qa.id)
        self.as_user(self.admin)
        self.assertEqual(self.client.delete(reverse('custom-status-detail', args=[qa.id])).status_code, 400)
        self.assertEqual(self.client.patch(reverse('custom-status-detail', args=[qa.id]), {'category': 'TODO'}).status_code, 400)
        self.assertEqual(self.client.patch(reverse('custom-status-detail', args=[qa.id]), {'is_active': False}).status_code, 200)

    def test_unused_custom_status_can_be_deleted(self):
        qa = CustomTaskStatus.objects.create(name='Unused', category='TODO')
        self.as_user(self.admin)
        self.assertEqual(self.client.delete(reverse('custom-status-detail', args=[qa.id])).status_code, 204)

    # ---- FR-036: cannot complete with missing required info -------------------------

    def test_cannot_complete_unassigned_task(self):
        task = self.make()
        self.as_user(self.pm)
        res = self.change(task, status='COMPLETED')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Assign the task', str(res.data))

    def test_cannot_complete_with_open_subtasks(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        self.client.post(self.url('subtasks', task), {'title': 'Part 1'})
        res = self.change(task, status='COMPLETED')
        self.assertEqual(res.status_code, 400)
        self.assertIn('subtask', str(res.data))

    def test_completion_blockers_are_reported_on_the_task(self):
        task = self.make()
        self.as_user(self.pm)
        blockers = self.client.get(self.url('detail', task)).data['completion_blockers']
        self.assertIn('Assign the task to someone.', blockers)
        self.change(task, status='CANCELLED')
        # A finished task (completed or cancelled) has nothing left to block.
        self.assertEqual(self.client.get(self.url('detail', task)).data['completion_blockers'], [])

    def test_completing_a_task_with_subtasks_all_done_is_allowed(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        sub = self.client.post(self.url('subtasks', task), {'title': 'Part 1', 'assigned_to': self.member.id}).data
        done = self.change(type('T', (), {'id': sub['id']})(), status='COMPLETED')
        self.assertEqual(done.status_code, 200, done.data)
        self.assertEqual(self.change(task, status='COMPLETED').status_code, 200)

    # ---- FR-037: progress -------------------------------------------------------------

    def test_progress_without_subtasks_is_0_or_100(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        self.assertEqual(self.client.get(self.url('detail', task)).data['progress'], 0)
        self.change(task, status='COMPLETED')
        self.assertEqual(self.client.get(self.url('detail', task)).data['progress'], 100)

    def test_progress_reflects_subtask_completion(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        s1 = self.client.post(self.url('subtasks', task), {'title': 'A', 'assigned_to': self.member.id}).data
        self.client.post(self.url('subtasks', task), {'title': 'B'}).data
        s3 = self.client.post(self.url('subtasks', task), {'title': 'C'}).data
        Task.objects.filter(pk=s3['id']).update(status='CANCELLED')  # cancelled subtasks are not counted
        self.assertEqual(self.client.get(self.url('detail', task)).data['progress'], 0)
        completed = self.change(type('T', (), {'id': s1['id']})(), status='COMPLETED')
        self.assertEqual(completed.status_code, 200, completed.data)
        detail = self.client.get(self.url('detail', task)).data
        self.assertEqual((detail['progress'], detail['subtask_count'], detail['subtasks_done']), (50, 2, 1))

    # ---- FR-038/039/040: subtasks -----------------------------------------------------

    def test_add_subtask_and_assign_independently(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        res = self.client.post(self.url('subtasks', task), {
            'title': 'Design schema', 'assigned_to': self.member2.id, 'priority': 'LOW',
        })
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual((res.data['parent_task'], res.data['project'], res.data['assigned_to']), (task.id, self.project.id, self.member2.id))
        self.assertTrue(Notification.objects.filter(recipient=self.member2, task_id=res.data['id']).exists())

    def test_subtask_owner_and_managers_can_add_subtasks_others_cannot(self):
        task = self.make(assigned_to=self.member)
        for user in (self.pm, self.lead, self.member):  # manager, participant-with-role, and the assignee
            self.as_user(user)
            res = self.client.post(self.url('subtasks', task), {'title': f'by {user.username}'})
            self.assertEqual(res.status_code, 201, (user.username, res.data))
        self.as_user(self.member2)
        self.assertEqual(self.client.post(self.url('subtasks', task), {'title': 'nope'}).status_code, 403)

    def test_subtasks_cannot_have_their_own_subtasks(self):
        task = self.make()
        self.as_user(self.pm)
        sub = self.client.post(self.url('subtasks', task), {'title': 'S1'}).data
        # A subtask is not a valid "add subtask to" target: the permission check rejects it first.
        nested = self.client.post(self.url('subtasks', type('T', (), {'id': sub['id']})()), {'title': 'S2'})
        self.assertEqual(nested.status_code, 403)

    def test_subtask_project_defaults_to_its_parents_and_cannot_be_overridden(self):
        from projects.models import Project

        task = self.make()
        other = Project.objects.create(name='Other', manager=self.pm, created_by=self.pm, status='ACTIVE')
        self.as_user(self.pm)
        implicit = self.client.post(self.url('subtasks', task), {'title': 'ok'})
        self.assertEqual((implicit.status_code, implicit.data['project']), (201, self.project.id), implicit.data)
        mismatched = self.client.post(self.url('subtasks', task), {'title': 'cross', 'project': other.id})
        self.assertEqual(mismatched.status_code, 400)
        self.assertIn("parent's project", str(mismatched.data))

    def test_cannot_add_subtasks_to_a_finished_task(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        self.change(task, status='CANCELLED')
        self.assertEqual(self.client.post(self.url('subtasks', task), {'title': 'x'}).status_code, 400)

    def test_cannot_add_subtasks_to_an_archived_task(self):
        task = self.make()
        self.as_user(self.pm)
        self.client.delete(self.url('detail', task))  # archive
        # Archived is checked at the permission layer, alongside every other change to an archived task.
        self.assertEqual(self.client.post(self.url('subtasks', task), {'title': 'x'}).status_code, 403)

    def test_list_subtasks(self):
        task = self.make()
        self.as_user(self.pm)
        self.client.post(self.url('subtasks', task), {'title': 'A'})
        self.client.post(self.url('subtasks', task), {'title': 'B'})
        res = self.client.get(self.url('subtasks', task))
        self.assertEqual({t['title'] for t in res.data}, {'A', 'B'})

    def test_cancelling_a_task_cancels_its_open_subtasks(self):
        task = self.make(assigned_to=self.member)
        self.as_user(self.pm)
        s1 = self.client.post(self.url('subtasks', task), {'title': 'A', 'assigned_to': self.member.id}).data
        s2 = self.client.post(self.url('subtasks', task), {'title': 'B'}).data
        self.change(type('T', (), {'id': s1['id']})(), status='COMPLETED')
        self.change(task, status='CANCELLED')
        self.assertEqual(Task.objects.get(pk=s1['id']).status, 'COMPLETED')  # already done: left alone
        self.assertEqual(Task.objects.get(pk=s2['id']).status, 'CANCELLED')

    def test_parent_task_cannot_be_moved_to_a_different_project(self):
        from projects.models import Project

        task = self.make()
        self.as_user(self.pm)
        self.client.post(self.url('subtasks', task), {'title': 'A'})
        other = Project.objects.create(name='Other', manager=self.pm, created_by=self.pm, status='ACTIVE')
        self.assertEqual(self.client.patch(self.url('detail', task), {'project': other.id}).status_code, 400)

    # ---- FR-041/042: dependencies ------------------------------------------------------

    def test_add_and_remove_dependency(self):
        design = self.make(title='Design DB')
        api = self.make(title='Develop API', enforce_dependencies=True)
        self.as_user(self.pm)
        res = self.client.post(reverse('task-add-dependency', args=[api.id]), {'predecessor': design.id})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual([d['id'] for d in res.data['depends_on_detail']], [design.id])
        self.assertEqual([d['id'] for d in self.client.get(self.url('detail', design)).data['blocks_detail']], [api.id])

    def test_cannot_start_blocked_task_only_when_enforced(self):
        design = self.make(title='Design DB', assigned_to=self.member)
        api = self.make(title='Develop API', assigned_to=self.member, enforce_dependencies=True)
        self.as_user(self.pm)
        self.client.post(reverse('task-add-dependency', args=[api.id]), {'predecessor': design.id})
        self.as_user(self.member)
        blocked = self.change(api, status='IN_PROGRESS')
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('Design DB', str(blocked.data))
        self.assertEqual(self.change(design, status='COMPLETED').status_code, 200)
        self.assertEqual(self.change(api, status='IN_PROGRESS').status_code, 200)

    def test_dependency_not_enforced_by_default(self):
        design = self.make(title='Design DB', assigned_to=self.member)
        api = self.make(title='Develop API', assigned_to=self.member)  # enforce_dependencies=False
        self.as_user(self.pm)
        self.client.post(reverse('task-add-dependency', args=[api.id]), {'predecessor': design.id})
        self.as_user(self.member)
        self.assertEqual(self.change(api, status='IN_PROGRESS').status_code, 200)

    def test_dependency_must_be_same_project_not_self_not_archived(self):
        from projects.models import Project

        task = self.make()
        self.as_user(self.pm)
        self.assertIn('itself', str(self.client.post(reverse('task-add-dependency', args=[task.id]), {'predecessor': task.id}).data))
        other_proj = Project.objects.create(name='Other', manager=self.pm, created_by=self.pm, status='ACTIVE')
        elsewhere = Task.objects.create(title='Elsewhere', project=other_proj, created_by=self.pm)
        self.assertIn('same project', str(self.client.post(reverse('task-add-dependency', args=[task.id]), {'predecessor': elsewhere.id}).data))
        archived = self.make(title='Archived one', is_archived=True)
        self.assertIn('archived', str(self.client.post(reverse('task-add-dependency', args=[task.id]), {'predecessor': archived.id}).data))

    def test_circular_dependency_is_rejected(self):
        a = self.make(title='A')
        b = self.make(title='B')
        c = self.make(title='C')
        self.as_user(self.pm)
        self.client.post(reverse('task-add-dependency', args=[b.id]), {'predecessor': a.id})
        self.client.post(reverse('task-add-dependency', args=[c.id]), {'predecessor': b.id})
        res = self.client.post(reverse('task-add-dependency', args=[a.id]), {'predecessor': c.id})
        self.assertEqual(res.status_code, 400)
        self.assertIn('circular', str(res.data))

    def test_subtask_cannot_depend_on_its_own_parent_or_sibling_on_parent(self):
        task = self.make()
        self.as_user(self.pm)
        sub = Task.objects.create(title='Sub', project=self.project, created_by=self.pm, parent_task=task)
        res = self.client.post(reverse('task-add-dependency', args=[sub.id]), {'predecessor': task.id})
        self.assertEqual(res.status_code, 400)
        self.assertIn('parent', str(res.data))

    def test_dependency_candidates_excludes_invalid_options(self):
        task = self.make(title='API')
        design = self.make(title='Design')
        cancelled_other_proj_task = self.make(title='Cross', project=None)
        self.as_user(self.pm)
        self.client.post(reverse('task-add-dependency', args=[task.id]), {'predecessor': design.id})
        res = self.client.get(self.url('dependency-candidates', task))
        ids = {c['id'] for c in res.data}
        self.assertNotIn(task.id, ids)                       # not itself
        self.assertNotIn(design.id, ids)                      # already a predecessor
        self.assertNotIn(cancelled_other_proj_task.id, ids)   # different project

    def test_removing_dependency(self):
        design = self.make(title='Design DB')
        api = self.make(title='Develop API')
        self.as_user(self.pm)
        self.client.post(reverse('task-add-dependency', args=[api.id]), {'predecessor': design.id})
        res = self.client.delete(reverse('task-remove-dependency', args=[api.id, design.id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['depends_on_detail'], [])

    # ---- FR-025: dependency changes are audited ---------------------------------------

    def test_dependency_change_is_recorded_in_history(self):
        design = self.make(title='Design DB')
        api = self.make(title='Develop API')
        self.as_user(self.pm)
        self.client.post(reverse('task-add-dependency', args=[api.id]), {'predecessor': design.id})
        history = self.client.get(self.url('history', api)).data
        entry = next(h for h in history if h['changes'] and h['changes'][0]['field'] == 'depends_on')
        self.assertEqual((entry['changes'][0]['from'], entry['changes'][0]['to']), (None, 'Design DB'))


class CustomPriorityAndTagTests(ApiTestCase):
    """FR-093 configurable priorities, FR-094 tag registry."""

    def url(self, name, task):
        return reverse(f'task-{name}', args=[task.id])

    def make(self, **extra):
        data = dict(title='T', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    # ---- FR-093 ---------------------------------------------------------------------

    def test_admin_creates_custom_priority_others_cannot(self):
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('custom-priority-list')).status_code, 200)
        denied = self.client.post(reverse('custom-priority-list'), {'name': 'Showstopper', 'category': 'CRITICAL'})
        self.assertEqual(denied.status_code, 403)
        self.as_user(self.admin)
        res = self.client.post(reverse('custom-priority-list'), {'name': 'Showstopper', 'category': 'CRITICAL', 'order': 1})
        self.assertEqual((res.status_code, res.data['task_count']), (201, 0), res.data)

    def test_custom_priority_name_cannot_clash_with_builtin_or_existing(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.post(reverse('custom-priority-list'), {'name': 'High', 'category': 'HIGH'}).status_code, 400)
        CustomPriority.objects.create(name='Showstopper', category='CRITICAL')
        self.assertEqual(self.client.post(reverse('custom-priority-list'), {'name': 'showstopper', 'category': 'HIGH'}).status_code, 400)

    def test_task_takes_a_custom_priority_and_category_follows(self):
        showstopper = CustomPriority.objects.create(name='Showstopper', category='CRITICAL', order=1)
        self.as_user(self.pm)
        res = self.client.post(reverse('task-list'), {
            'title': 'Fix prod', 'project': self.project.id, 'custom_priority': showstopper.id,
        })
        self.assertEqual((res.status_code, res.data['priority'], res.data['priority_label']), (201, 'CRITICAL', 'Showstopper'), res.data)

    def test_inactive_custom_priority_cannot_be_selected(self):
        retired = CustomPriority.objects.create(name='Retired', category='LOW', is_active=False)
        self.as_user(self.pm)
        res = self.client.post(reverse('task-list'), {'title': 'X', 'project': self.project.id, 'custom_priority': retired.id})
        self.assertEqual(res.status_code, 400)

    def test_custom_priority_in_use_cannot_be_deleted_or_recategorized(self):
        showstopper = CustomPriority.objects.create(name='Showstopper', category='CRITICAL')
        self.make(custom_priority=showstopper, priority='CRITICAL')
        self.as_user(self.admin)
        self.assertEqual(self.client.delete(reverse('custom-priority-detail', args=[showstopper.id])).status_code, 400)
        self.assertEqual(self.client.patch(reverse('custom-priority-detail', args=[showstopper.id]), {'category': 'LOW'}).status_code, 400)
        self.assertEqual(self.client.patch(reverse('custom-priority-detail', args=[showstopper.id]), {'is_active': False}).status_code, 200)

    def test_unused_custom_priority_can_be_deleted(self):
        unused = CustomPriority.objects.create(name='Unused', category='LOW')
        self.as_user(self.admin)
        self.assertEqual(self.client.delete(reverse('custom-priority-detail', args=[unused.id])).status_code, 204)

    # ---- FR-094 ---------------------------------------------------------------------

    def test_admin_manages_tag_registry_others_read_only(self):
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('task-tag-list')).status_code, 200)
        self.assertEqual(self.client.post(reverse('task-tag-list'), {'name': 'urgent'}).status_code, 403)
        self.as_user(self.admin)
        res = self.client.post(reverse('task-tag-list'), {'name': ' Urgent '})
        self.assertEqual((res.status_code, res.data['name']), (201, 'urgent'))  # trimmed + lowercased
        self.assertEqual(self.client.post(reverse('task-tag-list'), {'name': 'URGENT'}).status_code, 400)

    def test_task_tags_remain_freeform_regardless_of_registry(self):
        # The registry is a curated suggestion list; it never constrains what a task stores.
        self.as_user(self.pm)
        res = self.client.post(reverse('task-list'), {
            'title': 'X', 'project': self.project.id, 'tags': ['anything-goes'],
        }, format='json')
        self.assertEqual((res.status_code, res.data['tags']), (201, ['anything-goes']))
