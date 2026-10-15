import threading

_local = threading.local()


def get_current_user():
    return getattr(_local, 'user', None)


class CurrentUserMiddleware:
    """Stashes the requesting user so model signals can attribute changes (FR-086)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.user = getattr(request, 'user', None)
        try:
            response = self.get_response(request)
        finally:
            _local.user = None
        return response
