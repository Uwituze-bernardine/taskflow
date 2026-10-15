"""Central helper for creating notifications (FR-054 to FR-058), respecting preferences (FR-059)."""
from .models import Category
from .preferences import wants


def notify(user, message, task=None, category=Category.OTHER):
    from .models import Notification

    if not wants(user, category):
        return None
    return Notification.objects.create(recipient=user, message=message, task=task, category=category)


def already_notified(user, task, category):
    """
    True if `user` already has a notification of this `category` for this `task`.
    Used by the deadline-reminder command (FR-057/058) so re-running it doesn't spam
    the same reminder every time it's scheduled.
    """
    from .models import Notification

    return Notification.objects.filter(recipient=user, task=task, category=category).exists()
