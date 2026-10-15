from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class ActiveMemberJWTAuthentication(JWTAuthentication):
    """
    JWT auth that also enforces `is_active_member` (FR-004), so deactivating
    an account takes effect immediately, even for access tokens already issued.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.is_active_member:
            raise AuthenticationFailed(
                'This account has been deactivated.', code='user_deactivated'
            )
        return user
