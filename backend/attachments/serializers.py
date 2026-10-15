from rest_framework import serializers

from tasks.access import in_closed_project, visible_tasks
from users.serializers import UserDirectorySerializer
from .models import Attachment, AttachmentSettings


class AttachmentSettingsSerializer(serializers.ModelSerializer):
    extension_list = serializers.ReadOnlyField()

    class Meta:
        model = AttachmentSettings
        fields = ['allowed_extensions', 'max_size_mb', 'extension_list']

    def validate_allowed_extensions(self, value):
        exts = [e.strip().lower().lstrip('.') for e in value.split(',') if e.strip()]
        if not exts:
            raise serializers.ValidationError('At least one file extension must be allowed.')
        return ','.join(dict.fromkeys(exts))  # de-duplicate, keep order


class AttachmentSerializer(serializers.ModelSerializer):
    """
    `file` is write-only: downloads go through the authenticated `/download/` action (FR-050)
    rather than a raw URL in the response, so access stays checked on every download, not
    just at upload time.
    """
    uploaded_by_detail = UserDirectorySerializer(source='uploaded_by', read_only=True)
    file = serializers.FileField(write_only=True)
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            'id', 'task', 'file', 'filename', 'content_type',
            'uploaded_by', 'uploaded_by_detail', 'uploaded_at', 'size_bytes', 'can_delete',
        ]
        read_only_fields = ['id', 'filename', 'content_type', 'uploaded_by', 'uploaded_at', 'size_bytes']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated:
            fields['task'].queryset = visible_tasks(request.user)  # FR-049: only tasks I can see
        return fields

    def get_can_delete(self, obj):
        from projects.access import is_admin
        from tasks.access import can_manage_task

        request = self.context.get('request')
        user = request.user if request else None
        if not user:
            return False
        return obj.uploaded_by_id == user.id or is_admin(user) or can_manage_task(user, obj.task)

    def validate(self, attrs):
        task = attrs.get('task')
        file = attrs.get('file')
        if task is not None and in_closed_project(task):
            raise serializers.ValidationError(
                {'task': 'This task belongs to a closed or archived project and cannot receive new attachments.'}
            )
        if file is not None:
            settings_obj = AttachmentSettings.current()  # FR-052
            ext = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
            if ext not in settings_obj.extension_list:
                raise serializers.ValidationError(
                    {'file': f'File type ".{ext}" is not allowed. Allowed types: {settings_obj.allowed_extensions}.'}
                )
            max_bytes = settings_obj.max_size_mb * 1024 * 1024
            if file.size > max_bytes:
                raise serializers.ValidationError(
                    {'file': f'File exceeds the {settings_obj.max_size_mb}MB limit.'}
                )
        return attrs
