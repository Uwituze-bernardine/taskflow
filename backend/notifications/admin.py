from django.contrib import admin

from .models import Notification, NotificationSettings

admin.site.register(Notification)
admin.site.register(NotificationSettings)
