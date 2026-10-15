from rest_framework import serializers

from .models import Notification, NotificationSettings
from .preferences import CATEGORIES


class NotificationSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'category', 'category_label', 'message', 'task', 'is_read', 'created_at']
        read_only_fields = fields


class NotificationPreferencesSerializer(serializers.Serializer):
    """FR-059: validates a PATCH to preferences - one boolean per category, unknown keys rejected."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key in CATEGORIES:
            self.fields[key] = serializers.BooleanField(required=False)

    def to_internal_value(self, data):
        unknown = set(data) - set(CATEGORIES)
        if unknown:
            raise serializers.ValidationError({key: 'Unknown preference.' for key in unknown})
        return super().to_internal_value(data)


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = ['due_soon_days']

    def validate_due_soon_days(self, value):
        if value < 1:
            raise serializers.ValidationError('Must be at least 1 day.')
        return value
