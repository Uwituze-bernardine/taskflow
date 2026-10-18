from django.db.models.signals import m2m_changed, post_save, pre_delete, pre_save
from django.dispatch import receiver

from tasks.models import Task

from . import services
from .middleware import get_current_user
from .models import AuditLog


def _actor(instance, created):
    """
    Views set `task._actor = request.user` before saving. (The middleware cannot know the
    user for JWT requests, so it is only a fallback.)
    """
    actor = getattr(instance, '_actor', None)
    if actor is None and created:
        actor = instance.created_by
    if actor is None:
        user = get_current_user()
        actor = user if user is not None and getattr(user, 'is_authenticated', False) else None
    return actor


@receiver(pre_save, sender=Task)
def remember_previous_state(sender, instance, **kwargs):
    instance._audit_old = None
    if instance.pk:
        old = (
            Task.objects.select_related(
                'assigned_to', 'project', 'parent_task', 'custom_status', 'custom_priority'
            )
            .filter(pk=instance.pk).first()
        )
        if old is not None:
            instance._audit_old = services.snapshot(old)


@receiver(post_save, sender=Task)
def log_task_changes(sender, instance, created, **kwargs):
    """FR-025 / FR-085 to FR-087: record what changed, who did it and when."""
    if created:
        AuditLog.objects.create(
            actor=_actor(instance, True), action='task.created', model_name='Task',
            object_id=str(instance.pk), changes={'title': instance.title},
        )
        return
    old = getattr(instance, '_audit_old', None)
    if old is None:
        return
    changes = services.diff(old, instance)
    if changes:
        AuditLog.objects.create(
            actor=_actor(instance, False), action='task.updated', model_name='Task',
            object_id=str(instance.pk), changes=changes,
        )


@receiver(pre_delete, sender=Task)
def log_task_deletion(sender, instance, **kwargs):
    """Keep a durable audit record when a task is permanently deleted."""
    AuditLog.objects.create(
        actor=_actor(instance, False), action='task.deleted', model_name='Task',
        object_id=str(instance.pk), changes={'title': instance.title},
    )


def _predecessor_titles(task):
    """Read straight from the database (an already-prefetched relation could be stale)."""
    return list(Task.objects.filter(blocks=task.pk).order_by('id').values_list('title', flat=True))


@receiver(m2m_changed, sender=Task.depends_on.through)
def log_dependency_changes(sender, instance, action, reverse, **kwargs):
    """FR-025: dependencies are an important change too."""
    if reverse or not isinstance(instance, Task):
        return
    if action in ('pre_add', 'pre_remove', 'pre_clear'):
        instance._audit_deps_before = _predecessor_titles(instance)
    elif action in ('post_add', 'post_remove', 'post_clear'):
        before = getattr(instance, '_audit_deps_before', None)
        after = _predecessor_titles(instance)
        if before is not None and before != after:
            AuditLog.objects.create(
                actor=_actor(instance, False), action='task.updated', model_name='Task',
                object_id=str(instance.pk),
                changes={'depends_on': {'from': ', '.join(before) or None, 'to': ', '.join(after) or None}},
            )
        instance._audit_deps_before = after
