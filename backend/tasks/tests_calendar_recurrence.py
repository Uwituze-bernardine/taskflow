"""FR-061 to FR-065: calendar and scheduling, including recurring tasks (FR-064)."""
from django.urls import reverse

from taskflow.test_utils import ApiTestCase
from tasks.models import Task


class CalendarRecurrenceTests(ApiTestCase):
    def url(self, name, task):
        return reverse(f'task-{name}', args=[task.id])

    def make(self, **extra):
        data = dict(title='T', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    def change(self, task, **body):
        return self.client.post(self.url('change-status', task), body, format='json')

    # ---- FR-061/062: calendar view with due dates ------------------------------------

    def test_calendar_defaults_to_current_month_and_shows_due_dates(self):
        from django.utils import timezone

        today = timezone.localdate()
        in_month = self.make(title='In month', due_date=today.replace(day=min(today.day, 27)))
        self.make(title='No due date')  # never shows up on a calendar
        self.as_user(self.pm)
        res = self.client.get(reverse('task-calendar'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual({t['id'] for t in res.data}, {in_month.id})
        self.assertEqual(res.data[0]['due_date'], str(in_month.due_date))

    def test_calendar_respects_explicit_range(self):
        early = self.make(title='Early', due_date='2027-01-05')
        self.make(title='Later', due_date='2027-02-05')
        self.as_user(self.pm)
        res = self.client.get(reverse('task-calendar'), {'start': '2027-01-01', 'end': '2027-01-31'})
        self.assertEqual({t['id'] for t in res.data}, {early.id})

    def test_calendar_only_shows_tasks_i_can_see(self):
        from projects.models import Project

        mine = self.make(title='Mine', due_date='2027-03-01')
        other = Project.objects.create(name='Other', manager=self.other_pm, created_by=self.other_pm, status='ACTIVE')
        Task.objects.create(title='Elsewhere', project=other, created_by=self.other_pm, due_date='2027-03-01')
        self.as_user(self.pm)
        res = self.client.get(reverse('task-calendar'), {'start': '2027-03-01', 'end': '2027-03-31'})
        self.assertEqual({t['id'] for t in res.data}, {mine.id})

    # ---- FR-065: filter calendar items by project, status, assignee ------------------

    def test_calendar_filters_by_project_status_and_assignee(self):
        from projects.models import Project

        other = Project.objects.create(name='Other', manager=self.pm, created_by=self.pm, status='ACTIVE')
        a = self.make(title='A', due_date='2027-04-05', status='TODO', assigned_to=self.member)
        b = self.make(title='B', due_date='2027-04-06', status='IN_PROGRESS', assigned_to=self.member2, project=other)
        self.as_user(self.pm)
        base = {'start': '2027-04-01', 'end': '2027-04-30'}
        self.assertEqual({t['id'] for t in self.client.get(reverse('task-calendar'), {**base, 'project': self.project.id}).data}, {a.id})
        self.assertEqual({t['id'] for t in self.client.get(reverse('task-calendar'), {**base, 'status': 'IN_PROGRESS'}).data}, {b.id})
        self.assertEqual({t['id'] for t in self.client.get(reverse('task-calendar'), {**base, 'assigned_to': self.member.id}).data}, {a.id})

    # ---- FR-063: authorized users change task dates (via the normal edit endpoint) ---

    def test_manager_reschedules_task_others_cannot(self):
        task = self.make(due_date='2027-05-01')
        self.as_user(self.member)
        self.assertEqual(self.client.patch(self.url('detail', task), {'due_date': '2027-05-10'}).status_code, 403)
        self.as_user(self.pm)
        res = self.client.patch(self.url('detail', task), {'start_date': '2027-05-01', 'due_date': '2027-05-10'})
        self.assertEqual((res.status_code, res.data['due_date']), (200, '2027-05-10'), res.data)

    # ---- FR-064: recurring tasks -------------------------------------------------------

    def test_recurrence_requires_top_level_task_and_a_due_date(self):
        self.as_user(self.pm)
        no_due = self.client.post(reverse('task-list'), {'title': 'X', 'project': self.project.id, 'recurrence': 'WEEKLY'})
        self.assertEqual(no_due.status_code, 400)
        self.assertIn('due date', str(no_due.data))

        parent = self.make()
        sub = self.client.post(self.url('subtasks', parent), {
            'title': 'sub', 'recurrence': 'DAILY', 'due_date': '2027-06-01',
        })
        self.assertEqual(sub.status_code, 400)
        self.assertIn('Subtasks cannot repeat', str(sub.data))

    def test_completing_a_recurring_task_spawns_the_next_occurrence(self):
        task = self.make(
            title='Weekly sync', assigned_to=self.member, priority='HIGH', tags=['standup'],
            start_date='2027-01-04', due_date='2027-01-05', recurrence='WEEKLY', recurrence_interval=1,
        )
        self.as_user(self.member)
        res = self.change(task, status='COMPLETED')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('next_occurrence', res.data)
        nxt = res.data['next_occurrence']
        self.assertEqual((nxt['title'], nxt['status'], nxt['start_date'], nxt['due_date'], nxt['priority'], nxt['tags']),
                          ('Weekly sync', 'TODO', '2027-01-11', '2027-01-12', 'HIGH', ['standup']))
        self.assertEqual(nxt['assigned_to'], self.member.id)

        created = Task.objects.get(pk=nxt['id'])
        self.assertEqual(created.recurrence, 'WEEKLY')
        self.assertEqual(created.recurrence_of_id, task.id)  # points at the series root

    def test_recurrence_series_root_stays_consistent_across_generations(self):
        first = self.make(assigned_to=self.member, due_date='2027-02-01', recurrence='DAILY')
        self.as_user(self.member)
        second_id = self.change(first, status='COMPLETED').data['next_occurrence']['id']
        second = Task.objects.get(pk=second_id)
        third_id = self.change(second, status='COMPLETED').data['next_occurrence']['id']
        third = Task.objects.get(pk=third_id)
        self.assertEqual(third.recurrence_of_id, first.id)  # not second.id: always the original

    def test_new_assignee_of_next_occurrence_is_notified(self):
        from notifications.models import Notification

        task = self.make(assigned_to=self.member, due_date='2027-03-01', recurrence='DAILY')
        self.as_user(self.member)
        self.change(task, status='COMPLETED')
        nxt_id = Notification.objects.filter(recipient=self.member).latest('created_at').task_id
        self.assertNotEqual(nxt_id, task.id)

    def test_recurrence_stops_at_the_end_date(self):
        task = self.make(assigned_to=self.member, due_date='2027-04-01', recurrence='WEEKLY', recurrence_end_date='2027-04-05')
        self.as_user(self.member)
        res = self.change(task, status='COMPLETED')
        self.assertNotIn('next_occurrence', res.data)  # next would be 2027-04-08, past the end date
        self.assertEqual(Task.objects.filter(recurrence_of=task).count(), 0)

    def test_non_recurring_completion_has_no_next_occurrence(self):
        task = self.make(assigned_to=self.member, due_date='2027-05-01')
        self.as_user(self.member)
        res = self.change(task, status='COMPLETED')
        self.assertNotIn('next_occurrence', res.data)

    def test_cancelling_a_recurring_task_does_not_spawn_a_new_one(self):
        task = self.make(assigned_to=self.member, due_date='2027-06-01', recurrence='DAILY')
        self.as_user(self.pm)
        res = self.change(task, status='CANCELLED')
        self.assertNotIn('next_occurrence', res.data)

    def test_next_occurrence_due_date_preview_on_the_task(self):
        task = self.make(assigned_to=self.member, due_date='2027-07-01', recurrence='MONTHLY')
        self.as_user(self.pm)
        detail = self.client.get(self.url('detail', task)).data
        self.assertEqual(str(detail['next_occurrence_due_date']), '2027-08-01')
        self.assertTrue(detail['is_recurring'])
