"""
FR-059: notification preferences. Each category can be switched off independently;
everything defaults to on. Stored as a plain dict on User.notification_preferences
so adding a category later doesn't need a migration - `defaults()` just gains a key.
"""

CATEGORIES = {
    'assigned': 'A task is assigned to you',
    'status_changed': "A task's status changes",
    'mentioned': 'You are mentioned in a comment',
    'due_soon': 'A task you own is due soon',
    'overdue': 'A task you own becomes overdue',
}


def defaults():
    return {key: True for key in CATEGORIES}


def effective(user):
    """Stored preferences layered over the defaults, so a missing/new key is still 'on'."""
    stored = getattr(user, 'notification_preferences', None) or {}
    merged = defaults()
    for key in CATEGORIES:
        if key in stored:
            merged[key] = bool(stored[key])
    return merged


def wants(user, category):
    return effective(user).get(category, True)
