from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from .admin import AuditLogAdmin
from .models import AuditLog


class AuditLogAdminTests(SimpleTestCase):
    def test_superuser_cannot_delete_audit_entries(self):
        request = RequestFactory().get('/admin/audit/auditlog/')
        request.user = type('User', (), {'is_superuser': True})()
        model_admin = AuditLogAdmin(AuditLog, admin.site)
        self.assertFalse(model_admin.has_delete_permission(request))
