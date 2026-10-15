from django.contrib.auth import password_validation
from django.utils.crypto import get_random_string
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Role, User
from .permissions import IsAdmin
from .serializers import (
    AdminUserCreateSerializer, AdminUserUpdateSerializer, ChangePasswordSerializer,
    LoginSerializer, ProfileSerializer, RegisterSerializer, ResetPasswordSerializer,
    UserDirectorySerializer, UserSerializer,
)
from .services import revoke_user_tokens


class RegisterView(APIView):
    """FR-001: anyone can create an account (always as a Team Member)."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """FR-002: log in, returns JWT access/refresh tokens."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class LogoutView(APIView):
    """FR-002: log out by blacklisting the refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                pass  # already invalid/blacklisted: the goal (logged out) is met
        return Response(status=status.HTTP_205_RESET_CONTENT)


class UserViewSet(viewsets.ModelViewSet):
    """
    Administrator user management (FR-004, FR-006, FR-007) plus the
    current-user endpoints `me` (FR-003) and `me/change-password`.

    Listing/retrieving users is open to any signed-in user because the task
    assignee dropdown and @mentions need it - but non-admins only get a
    minimal directory of *active* users (no email/phone/status). Everything
    that changes a user is administrator-only.

    Accounts are never hard-deleted: they are deactivated instead, so task
    history and audit records stay intact.
    """
    queryset = User.objects.all().order_by('username')
    filterset_fields = ['role', 'is_active_member']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('me', 'change_password', 'list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdmin()]  # FR-006

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role != Role.ADMIN:
            qs = qs.filter(is_active_member=True)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminUserCreateSerializer
        if self.action == 'partial_update':
            return AdminUserUpdateSerializer
        if self.action in ('list', 'retrieve') and self.request.user.role != Role.ADMIN:
            return UserDirectorySerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(instance).data)

    # -- current user ------------------------------------------------------

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """FR-003: view / update own profile."""
        if request.method == 'PATCH':
            serializer = ProfileSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=['post'], url_path='me/change-password')
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'detail': 'Password updated.'})

    # -- admin actions -----------------------------------------------------

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """FR-004: deactivate an account and end all of its sessions."""
        user = self.get_object()
        if user == request.user:
            raise ValidationError({'detail': 'You cannot deactivate your own account.'})
        user.is_active_member = False
        user.save(update_fields=['is_active_member'])
        revoke_user_tokens(user)
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """FR-004: reactivate an account."""
        user = self.get_object()
        user.is_active_member = True
        user.save(update_fields=['is_active_member'])
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """
        FR-007: reset a user's password and end their sessions.
        If no password is supplied, a temporary one is generated and returned once.
        """
        user = self.get_object()
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_password = serializer.validated_data.get('new_password') or ''
        generated = not new_password
        if generated:
            new_password = get_random_string(
                12, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
            )
        else:
            try:
                password_validation.validate_password(new_password, user)
            except Exception as exc:
                raise ValidationError({'new_password': list(getattr(exc, 'messages', [str(exc)]))})
        user.set_password(new_password)
        user.save(update_fields=['password'])
        revoke_user_tokens(user)
        data = {'detail': 'Password reset.'}
        if generated:
            data['temporary_password'] = new_password
        return Response(data)
