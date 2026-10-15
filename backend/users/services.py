from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken, OutstandingToken,
)


def revoke_user_tokens(user):
    """
    Blacklist every refresh token issued to `user`, forcing a fresh login.
    Used when an account is deactivated or its password is reset (FR-004, FR-007).
    """
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
