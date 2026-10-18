from rest_framework import serializers

from tasks.access import in_closed_project, visible_tasks
from users.serializers import UserDirectorySerializer
from .mentions import extract_mentions
from .models import Comment, CommentRevision

DELETED_BODY = 'This comment was deleted.'


class CommentRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentRevision
        fields = ['body', 'edited_by', 'saved_at']
        read_only_fields = fields


class CommentSerializer(serializers.ModelSerializer):
    author_detail = UserDirectorySerializer(source='author', read_only=True)
    mentioned_users_detail = UserDirectorySerializer(source='mentioned_users', many=True, read_only=True)
    is_edited = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    revisions = CommentRevisionSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'task', 'author', 'author_detail', 'body',
            'mentioned_users_detail', 'is_edited', 'is_deleted',
            'can_edit', 'can_delete', 'created_at', 'edited_at', 'revisions',
        ]
        # `mentioned_users` is derived server-side from the body (FR-045), never set by the client.
        read_only_fields = ['id', 'author', 'is_deleted', 'created_at', 'edited_at']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request is not None and request.user.is_authenticated:
            fields['task'].queryset = visible_tasks(request.user)  # FR-043: only tasks I can see
        return fields

    def get_is_edited(self, obj):
        return obj.edited_at is not None

    def get_can_edit(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        return bool(user and not obj.is_deleted and obj.author_id == user.id and not in_closed_project(obj.task))

    def get_can_delete(self, obj):
        from projects.access import is_admin
        from tasks.access import can_manage_task

        request = self.context.get('request')
        user = request.user if request else None
        if not user or obj.is_deleted:
            return False
        return obj.author_id == user.id or is_admin(user) or can_manage_task(user, obj.task)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:  # FR-047: the fact of the comment stays; its content doesn't.
            data['body'] = DELETED_BODY
            data['mentioned_users_detail'] = []
            data['revisions'] = []
        return data

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('A comment cannot be empty.')
        if len(value) > 5000:
            raise serializers.ValidationError('Comments are limited to 5000 characters.')
        return value

    def validate(self, attrs):
        task = attrs.get('task', getattr(self.instance, 'task', None))
        if self.instance is None and in_closed_project(task):
            raise serializers.ValidationError(
                {'task': 'This task belongs to a closed or archived project and cannot receive new comments.'}
            )
        return attrs

    def create(self, validated_data):
        comment = Comment.objects.create(**validated_data)
        comment.mentioned_users.set(extract_mentions(comment.body, comment.task))  # FR-045
        return comment

    def update(self, instance, validated_data):
        instance.body = validated_data.get('body', instance.body)
        instance.edited_at = validated_data.get('edited_at', instance.edited_at)
        instance.save(update_fields=['body', 'edited_at'])
        instance.mentioned_users.set(extract_mentions(instance.body, instance.task))  # FR-045: re-derive on edit
        return instance
