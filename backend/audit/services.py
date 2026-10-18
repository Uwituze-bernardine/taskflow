"""Helpers that turn task changes into readable, durable history entries."""
from .models import AuditLog

TRACKED_FIELDS = [
    'title', 'description', 'priority', 'custom_priority', 'status', 'assigned_to', 'project', 'parent_task',
    'start_date', 'due_date', 'tags', 'enforce_dependencies', 'is_archived',
    'recurrence', 'recurrence_interval', 'recurrence_end_date',
]
FIELD_LABELS = {
    'title': 'Title', 'description': 'Description', 'priority': 'Priority', 'status': 'Status',
    'custom_priority': 'Custom priority',
    'assigned_to': 'Assignee', 'project': 'Project', 'parent_task': 'Parent task',
    'start_date': 'Start date', 'due_date': 'Due date', 'tags': 'Tags',
    'enforce_dependencies': 'Enforce dependencies', 'is_archived': 'Archived',
    'depends_on': 'Depends on',
    'recurrence': 'Recurrence', 'recurrence_interval': 'Recurrence interval',
    'recurrence_end_date': 'Recurrence end date',
}
_FK_FIELDS = ('assigned_to', 'project', 'parent_task', 'custom_priority')


def _raw(task, field):
    if field == 'status':  # a change of custom status alone (same category) is still a change
        return (task.status, task.custom_status_id)
    return getattr(task, f'{field}_id') if field in _FK_FIELDS else getattr(task, field)


def _display(task, field):
    """A human-readable value stored in the log so history stays readable if names change later."""
    if field == 'status':
        return task.status_label
    value = getattr(task, field)
    if value is None or value == '' or value == []:
        return None
    if field == 'assigned_to':
        return value.get_full_name() or value.username
    if field == 'project':
        return value.name
    if field == 'parent_task':
        return value.title
    if field == 'custom_priority':
        return value.name
    if field == 'priority':
        return dict(task._meta.get_field(field).flatchoices).get(value, value)
    if field in ('start_date', 'due_date', 'recurrence_end_date'):
        return value.isoformat()
    if field == 'recurrence':
        return dict(task._meta.get_field(field).flatchoices).get(value, value)
    if field in ('enforce_dependencies', 'is_archived'):
        return 'Yes' if value else 'No'
    if field == 'tags':
        return ', '.join(value)
    text = str(value)
    return text if len(text) <= 120 else text[:117] + '…'


def snapshot(task):
    return {f: (_raw(task, f), _display(task, f)) for f in TRACKED_FIELDS}


def diff(old_snapshot, task):
    """{field: {'from': display, 'to': display}} for every tracked field that changed."""
    changes = {}
    for field in TRACKED_FIELDS:
        old_raw, old_display = old_snapshot[field]
        new_raw = _raw(task, field)
        if old_raw != new_raw:
            changes[field] = {'from': old_display, 'to': _display(task, field)}
    return changes


def task_history(task):
    """FR-025: chronological (newest first) list of what changed, when and by whom."""
    entries = AuditLog.objects.filter(model_name='Task', object_id=str(task.pk)).select_related('actor')
    result = []
    for entry in entries:
        changes = []
        if entry.action == 'task.updated':
            for field, values in (entry.changes or {}).items():
                changes.append({
                    'field': field,
                    'label': FIELD_LABELS.get(field, field),
                    'from': values.get('from'),
                    'to': values.get('to'),
                })
        actor = entry.actor
        result.append({
            'id': entry.id,
            'timestamp': entry.timestamp,
            'action': entry.action,
            'actor': {'id': actor.id, 'name': actor.get_full_name() or actor.username} if actor else None,
            'changes': changes,
        })
    return result
