from django.conf import settings


def site(request):
    user = getattr(request, "user", None)
    is_admin = bool(
        user
        and user.is_authenticated
        and (
            user.is_superuser
            or (user.email or "").lower() in settings.ADMIN_EMAILS
        )
    )
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_URL": settings.SITE_URL,
        "ZONE": settings.ZONE,
        "GITHUB_URL": "https://github.com/xpall/filipino-talent.com",
        "IS_A_DEV_URL": "https://www.is-a.dev",
        "is_admin": is_admin,
        "current_path": request.path,
        "google_configured": bool(
            settings.SOCIALACCOUNT_PROVIDERS.get("google", {}).get("APP", {}).get("client_id")
            and settings.SOCIALACCOUNT_PROVIDERS.get("google", {}).get("APP", {}).get("secret")
        ),
    }
