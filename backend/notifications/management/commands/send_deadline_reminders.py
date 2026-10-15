"""
FR-057/058: notify assignees about tasks due soon or overdue.

This is inherently a scheduled job, not something a single web request can trigger on its
own - there's no user action that corresponds to "a day passed". Run it periodically (once
a day is enough) from cron, a systemd timer, or Celery beat, e.g.:

    0 7 * * *  cd /path/to/backend && python manage.py send_deadline_reminders

Each task is reminded at most once per category (checked via `already_notified`), so running
this daily is safe - it won't re-notify someone about the same task every day.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Category, NotificationSettings
from notifications.services import already_notified, notify
from tasks.models import Task, TaskStatus

FINISHED = (TaskStatus.COMPLETED, TaskStatus.CANCELLED)


class Command(BaseCommand):
    help = 'Send "due soon" and "overdue" notifications for assigned, unfinished tasks (FR-057/058).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--due-soon-days', type=int, default=None,
            help='A task becomes "due soon" this many days before its due date. '
                 'Defaults to the admin-configured value (FR-095, Administration settings).',
        )

    def handle(self, *args, **options):
        due_soon_days = options['due_soon_days']
        if due_soon_days is None:
            due_soon_days = NotificationSettings.current().due_soon_days  # FR-095
        today = timezone.localdate()
        horizon = today + timedelta(days=due_soon_days)

        open_assigned = Task.objects.filter(
            is_archived=False, assigned_to__isnull=False,
        ).exclude(status__in=FINISHED).select_related('assigned_to')

        due_soon_sent = overdue_sent = 0
        for task in open_assigned.filter(due_date__gte=today, due_date__lte=horizon):
            if not already_notified(task.assigned_to, task, Category.DUE_SOON):  # FR-057
                notify(
                    task.assigned_to, f'Task "{task.title}" is due on {task.due_date:%b %d}.',
                    task=task, category=Category.DUE_SOON,
                )
                due_soon_sent += 1

        for task in open_assigned.filter(due_date__lt=today):
            if not already_notified(task.assigned_to, task, Category.OVERDUE):  # FR-058
                notify(
                    task.assigned_to, f'Task "{task.title}" is overdue (was due {task.due_date:%b %d}).',
                    task=task, category=Category.OVERDUE,
                )
                overdue_sent += 1

        self.stdout.write(self.style.SUCCESS(
            f'Sent {due_soon_sent} due-soon and {overdue_sent} overdue reminder(s).'
        ))
