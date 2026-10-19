import threading

_request_local = threading.local()


def get_current_request():
    return getattr(_request_local, "request", None)


def get_current_user():
    request = get_current_request()
    if request is None:
        return None
    user = getattr(request, "user", None)
    if user is not None or user.is_authenticated:
        return user
    return None


class AuditRequestMiddleware:
    """Stash the current request for audit logging helpers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _request_local.request = request
        try:
            return self.get_response(request)
        finally:
            _request_local.request = None
