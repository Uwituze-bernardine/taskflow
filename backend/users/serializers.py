from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers

from .models import Role, User


def _unique_email(value, instance=None):
    qs = User.objects.filter(email__iexact=value)
    if instance is not None:
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise serializers.ValidationError('A user with this email already exists.')
    return value


class UserSerializer(serializers.ModelSerializer):
    """Read representation used everywhere a user is returned."""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'avatar', 'job_title', 'phone', 'is_active_member',
            'notification_preferences', 'date_joined',
        ]
        read_only_fields = fields


class UserDirectorySerializer(serializers.ModelSerializer):
    """
    What non-administrators see when they list users (assignee pickers, @mentions).
    Contact details, account status and preferences stay admin-only.
    """

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """
    FR-001: public self-registration.
    The role is NOT accepted here: everyone who signs up is a Team Member.
    Only an administrator can grant a higher role (FR-004/FR-006).
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'email': {'required': True, 'allow_blank': False},
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': True, 'allow_blank': False},
        }

    def validate_email(self, value):
        return _unique_email(value)

    def validate(self, attrs):
        candidate = User(**{k: v for k, v in attrs.items() if k != 'password'})
        password_validation.validate_password(attrs['password'], candidate)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data, role=Role.TEAM_MEMBER)
        user.set_password(password)
        user.save()
        return user


class AdminUserCreateSerializer(RegisterSerializer):
    """FR-004: an administrator creates an account and chooses its role."""
    role = serializers.ChoiceField(choices=Role.choices, default=Role.TEAM_MEMBER)

    class Meta(RegisterSerializer.Meta):
        fields = RegisterSerializer.Meta.fields + ['role', 'job_title', 'phone']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """FR-004 / FR-007: administrators manage other users' details and role."""

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'role', 'job_title', 'phone']

    def validate_email(self, value):
        return _unique_email(value, self.instance)

    def validate_role(self, value):
        request = self.context.get('request')
        if request and self.instance == request.user and value != Role.ADMIN:
            raise serializers.ValidationError(
                'You cannot remove your own administrator role.'
            )
        return value


class ProfileSerializer(serializers.ModelSerializer):
    """
    FR-003: what a user may change about themselves.
    Role, username and active status are deliberately not editable here.
    """

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'job_title', 'phone']
        extra_kwargs = {'email': {'allow_blank': False}}

    def validate_email(self, value):
        if self.instance and value.casefold() == self.instance.email.casefold():
            return value
        return _unique_email(value, self.instance)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value, self.context['request'].user)
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """FR-007: admin sets a password, or omits it to get a generated temporary one."""
    new_password = serializers.CharField(write_only=True, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    """FR-002: login."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['username'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Invalid username or password.')
        if not user.is_active_member:
            raise serializers.ValidationError('This account has been deactivated.')
        attrs['user'] = user
        return attrs
