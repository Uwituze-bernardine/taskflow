from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'actor', 'actor_username', 'action', 'model_name', 'object_id', 'changes', 'timestamp']
        read_only_fields = fields
