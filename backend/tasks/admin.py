from django.contrib import admin

from .models import CustomPriority, CustomTaskStatus, Task, TaskStatusHistory, TaskTag

admin.site.register(Task)
admin.site.register(TaskStatusHistory)
admin.site.register(CustomTaskStatus)
admin.site.register(CustomPriority)
admin.site.register(TaskTag)
