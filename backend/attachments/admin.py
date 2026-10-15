from django.contrib import admin

from .models import Attachment, AttachmentSettings

admin.site.register(Attachment)
admin.site.register(AttachmentSettings)
