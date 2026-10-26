from __future__ import annotations

from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def is_admin(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or (user.email or "").lower() in settings.ADMIN_EMAILS
        )
    )


def admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not is_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped
