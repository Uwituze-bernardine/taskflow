import binascii

from django.contrib.auth import password_validation
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.crypto import get_random_string
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .emails import send_password_reset_email, send_verification_email
from .models import Role, User
from .permissions import IsAdmin
from .serializers import (
    AdminUserCreateSerializer, AdminUserUpdateSerializer, ChangePasswordSerializer,
    EmailSerializer, EmailVerificationSerializer, LoginSerializer, PasswordResetConfirmSerializer,
    ProfileSerializer, RegisterSerializer, ResetPasswordSerializer, UserDirectorySerializer,
    UserSerializer,
)
from .services import revoke_user_tokens
from .tokens import email_verification_token


class RegisterView(APIView):
    """FR-001: anyone can create an account (always as a Team Member)."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'registration'

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(user)
        return Response(
            {'detail': 'Account created. Check your email for a verification link before signing in.'},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_verification'

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _user_from_uid(serializer.validated_data['uid'])
        if user is None:
            raise ValidationError({'detail': 'This verification link is invalid or expired.'})
        if user.email_verified:
            return Response({'detail': 'This email address is already verified.'})
        if not email_verification_token.check_token(user, serializer.validated_data['token']):
            raise ValidationError({'detail': 'This verification link is invalid or expired.'})
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        return Response({'detail': 'Email verified. You can now sign in.'})


class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_email'

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data['email'],
            is_active_member=True,
            email_verified=False,
        ).first()
        if user:
            send_verification_email(user)
        return Response({
            'detail': 'If this address belongs to an unverified account, a verification email has been sent.'
        })


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_email'

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data['email'],
            is_active_member=True,
            email_verified=True,
        ).first()
        if user:
            send_password_reset_email(user)
        return Response({
            'detail': 'If an active account uses that email, password reset instructions have been sent.'
        })


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_verification'

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _user_from_uid(serializer.validated_data['uid'])
        if (
            user is None
            or not user.is_active_member
            or not user.email_verified
            or not default_token_generator.check_token(user, serializer.validated_data['token'])
        ):
            raise ValidationError({'detail': 'This password reset link is invalid or expired.'})
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        revoke_user_tokens(user)
        return Response({'detail': 'Password reset. You can now sign in.'})


def _user_from_uid(uid):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError, binascii.Error):
        return None
    return User.objects.filter(pk=user_id).first()


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
    @transaction.atomic
    def me(self, request):
        """FR-003: view / update own profile."""
        if request.method == 'PATCH':
            previous_email = request.user.email
            serializer = ProfileSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            if request.user.email.casefold() != previous_email.casefold():
                send_verification_email(request.user)
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
