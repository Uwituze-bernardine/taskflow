"""FR-054 to FR-060: notifications and reminders."""
from io import StringIO

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from taskflow.test_utils import ApiTestCase
from tasks.models import Task

from .models import Category, Notification


class NotificationTests(ApiTestCase):
    def make_task(self, **extra):
        data = dict(title='T', project=self.project, created_by=self.pm)
        data.update(extra)
        return Task.objects.create(**data)

    # ---- FR-054/055/056: categories fire from the right place -----------------------

    def test_assignment_notifies_with_the_assigned_category(self):
        task = self.make_task()
        self.as_user(self.pm)
        self.client.post(reverse('task-assign', args=[task.id]), {'user_id': self.member.id})
        note = Notification.objects.get(recipient=self.member, task=task)
        self.assertEqual(note.category, Category.ASSIGNED)

    def test_status_change_notifies_with_the_status_changed_category(self):
        task = self.make_task(assigned_to=self.member)
        self.as_user(self.member)
        self.client.post(reverse('task-change-status', args=[task.id]), {'status': 'IN_PROGRESS'})
        note = Notification.objects.get(recipient=self.member, task=task, category=Category.STATUS_CHANGED)
        self.assertIn('In Progress', note.message)

    def test_mention_notifies_with_the_mentioned_category(self):
        task = self.make_task()
        self.as_user(self.pm)
        self.client.post(reverse('comment-list'), {'task': task.id, 'body': f'hi @{self.member.username}'}, format='json')
        self.assertTrue(Notification.objects.filter(recipient=self.member, task=task, category=Category.MENTIONED).exists())

    # ---- FR-059: preferences ----------------------------------------------------------

    def test_default_preferences_are_all_on(self):
        self.as_user(self.member)
        res = self.client.get(reverse('notification-preferences'))
        self.assertTrue(all(res.data.values()))
        self.assertEqual(set(res.data), {'assigned', 'status_changed', 'mentioned', 'due_soon', 'overdue'})

    def test_turning_off_a_category_stops_it_and_leaves_others_on(self):
        self.as_user(self.member)
        res = self.client.patch(reverse('notification-preferences'), {'mentioned': False})
        self.assertEqual((res.status_code, res.data['mentioned'], res.data['assigned']), (200, False, True))

        task = self.make_task()
        self.as_user(self.pm)
        self.client.post(reverse('task-assign', args=[task.id]), {'user_id': self.member.id})
        self.client.post(reverse('comment-list'), {'task': task.id, 'body': f'hi @{self.member.username}'}, format='json')
        self.assertTrue(Notification.objects.filter(recipient=self.member, category=Category.ASSIGNED).exists())
        self.assertFalse(Notification.objects.filter(recipient=self.member, category=Category.MENTIONED).exists())

    def test_unknown_preference_key_rejected(self):
        self.as_user(self.member)
        res = self.client.patch(reverse('notification-preferences'), {'spam_me_always': True})
        self.assertEqual(res.status_code, 400)

    # ---- FR-060: history ---------------------------------------------------------------

    def test_notification_history_is_scoped_to_the_recipient(self):
        task = self.make_task()
        self.as_user(self.pm)
        self.client.post(reverse('task-assign', args=[task.id]), {'user_id': self.member.id})
        self.as_user(self.member)
        res = self.client.get(reverse('notification-list'))
        self.assertEqual(res.data['count'], 1)
        self.as_user(self.member2)
        self.assertEqual(self.client.get(reverse('notification-list')).data['count'], 0)

    def test_mark_read_and_mark_all_read_and_unread_count(self):
        task = self.make_task()
        self.as_user(self.pm)
        self.client.post(reverse('task-assign', args=[task.id]), {'user_id': self.member.id})
        self.client.post(reverse('task-assign', args=[task.id]), {'user_id': self.member.id})  # no-op, no dup note
        self.as_user(self.member)
        note_id = Notification.objects.get(recipient=self.member).id
        self.assertEqual(self.client.get(reverse('notification-unread-count')).data['count'], 1)
        self.client.post(reverse('notification-mark-read', args=[note_id]))
        self.assertEqual(self.client.get(reverse('notification-unread-count')).data['count'], 0)

        self.as_user(self.pm)
        self.client.post(reverse('task-change-status', args=[task.id]), {'status': 'IN_PROGRESS'})
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('notification-unread-count')).data['count'], 1)
        self.client.post(reverse('notification-mark-all-read'))
        self.assertEqual(self.client.get(reverse('notification-unread-count')).data['count'], 0)

    # ---- FR-057/058: reminder command --------------------------------------------------

    def test_reminder_command_sends_due_soon_and_overdue_once_each(self):
        today = timezone.localdate()
        soon = self.make_task(assigned_to=self.member, due_date=today + timezone.timedelta(days=1))
        late = self.make_task(assigned_to=self.member2, due_date=today - timezone.timedelta(days=3))
        self.make_task(assigned_to=self.member, due_date=today + timezone.timedelta(days=20))  # too far out
        self.make_task(assigned_to=self.member, due_date=today - timezone.timedelta(days=1), status='COMPLETED')  # finished

        call_command('send_deadline_reminders', stdout=StringIO())
        self.assertTrue(Notification.objects.filter(recipient=self.member, task=soon, category=Category.DUE_SOON).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.member2, task=late, category=Category.OVERDUE).exists())
        self.assertEqual(Notification.objects.filter(category=Category.DUE_SOON).count(), 1)
        self.assertEqual(Notification.objects.filter(category=Category.OVERDUE).count(), 1)

        call_command('send_deadline_reminders', stdout=StringIO())  # running again does not duplicate
        self.assertEqual(Notification.objects.filter(category=Category.DUE_SOON).count(), 1)
        self.assertEqual(Notification.objects.filter(category=Category.OVERDUE).count(), 1)

    def test_reminder_respects_preferences(self):
        self.as_user(self.member)
        self.client.patch(reverse('notification-preferences'), {'overdue': False})
        today = timezone.localdate()
        self.make_task(assigned_to=self.member, due_date=today - timezone.timedelta(days=1))
        call_command('send_deadline_reminders', stdout=StringIO())
        self.assertFalse(Notification.objects.filter(recipient=self.member, category=Category.OVERDUE).exists())

    def test_reminder_command_custom_horizon(self):
        today = timezone.localdate()
        far = self.make_task(assigned_to=self.member, due_date=today + timezone.timedelta(days=5))
        call_command('send_deadline_reminders', '--due-soon-days=7', stdout=StringIO())
        self.assertTrue(Notification.objects.filter(task=far, category=Category.DUE_SOON).exists())


class NotificationSettingsTests(ApiTestCase):
    """FR-095: system-wide notification configuration."""

    def test_default_due_soon_days_is_2(self):
        self.as_user(self.member)
        res = self.client.get(reverse('notification-settings'))
        self.assertEqual((res.status_code, res.data['due_soon_days']), (200, 2))

    def test_only_admin_can_change_it(self):
        self.as_user(self.pm)
        self.assertEqual(self.client.patch(reverse('notification-settings'), {'due_soon_days': 5}).status_code, 403)
        self.as_user(self.admin)
        res = self.client.patch(reverse('notification-settings'), {'due_soon_days': 5})
        self.assertEqual((res.status_code, res.data['due_soon_days']), (200, 5))
        self.as_user(self.member)
        self.assertEqual(self.client.get(reverse('notification-settings')).data['due_soon_days'], 5)

    def test_rejects_non_positive_value(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.patch(reverse('notification-settings'), {'due_soon_days': 0}).status_code, 400)

    def test_reminder_command_uses_configured_default_when_no_flag_given(self):
        from io import StringIO

        from django.core.management import call_command
        from django.utils import timezone

        from .models import Category, NotificationSettings, Notification
        from tasks.models import Task

        NotificationSettings.objects.update_or_create(pk=1, defaults={'due_soon_days': 10})
        task = Task.objects.create(
            title='Far out', project=self.project, created_by=self.pm, assigned_to=self.member,
            due_date=timezone.localdate() + timezone.timedelta(days=8),
        )
        call_command('send_deadline_reminders', stdout=StringIO())
        self.assertTrue(Notification.objects.filter(task=task, category=Category.DUE_SOON).exists())
