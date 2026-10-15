from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    """FR-005: supported user roles."""
    ADMIN = 'ADMIN', 'System Administrator'
    PROJECT_MANAGER = 'PROJECT_MANAGER', 'Project Manager'
    TEAM_LEADER = 'TEAM_LEADER', 'Team Leader'
    TEAM_MEMBER = 'TEAM_MEMBER', 'Team Member'


class User(AbstractUser):
    """Custom user model. FR-001, FR-003, FR-004, FR-005, FR-007."""

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.TEAM_MEMBER
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    job_title = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active_member = models.BooleanField(
        default=True,
        help_text='Deactivate/reactivate without deleting the account (FR-004).',
    )
    notification_preferences = models.JSONField(
        default=dict, blank=True,
        help_text='Per-channel notification settings (FR-059).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        # A superuser created with `createsuperuser` should be a System
        # Administrator in this app's role model, not a default Team Member.
        if self._state.adding and self.is_superuser and self.role == Role.TEAM_MEMBER:
            self.role = Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_manager(self):
        return self.role in (Role.ADMIN, Role.PROJECT_MANAGER, Role.TEAM_LEADER)
