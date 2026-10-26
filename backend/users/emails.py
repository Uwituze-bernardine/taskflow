from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import email_verification_token


def _account_link(path, user, token):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return f'{settings.FRONTEND_URL.rstrip("/")}/{path}?uid={uid}&token={token}'


def send_verification_email(user):
    link = _account_link('verify-email', user, email_verification_token.make_token(user))
    return send_mail(
        'Verify your TaskFlow email address',
        f'Hello {user.first_name or user.username},\n\n'
        f'Verify your email address to activate your TaskFlow sign-in:\n{link}\n\n'
        'If you did not create this account, you can ignore this message.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_password_reset_email(user):
    link = _account_link('reset-password', user, default_token_generator.make_token(user))
    return send_mail(
        'Reset your TaskFlow password',
        f'Hello {user.first_name or user.username},\n\n'
        f'Reset your TaskFlow password using this link:\n{link}\n\n'
        'If you did not request a password reset, you can ignore this message.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
