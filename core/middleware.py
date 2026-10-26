from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class WWWRedirectMiddleware:
    """Canonicalize www.filipino-talent.com to the apex domain.

    Cloudflare is expected to handle this too; this is a fallback for direct
    requests that reach the container.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        canonical = urlsplit(settings.SITE_URL).hostname or ""
        if host == f"www.{canonical}":
            target = request.build_absolute_uri(request.get_full_path())
            parts = urlsplit(target)
            target = parts._replace(scheme=urlsplit(settings.SITE_URL).scheme, netloc=canonical).geturl()
            return HttpResponsePermanentRedirect(target)
        return self.get_response(request)


class TrailingSlashRedirectMiddleware:
    """Normalize legacy trailing-slash URLs to the canonical no-slash routes.

    The previous Astro/Cloudflare Pages site used directory-style URLs such as
    ``/submit/``. Django routes are canonical without the slash. ``/accounts/``
    is exempt because django-allauth requires its trailing slashes.
    """

    exempt_prefixes = ("/accounts/", "/admin/", "/static/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if (
            path != "/"
            and path.endswith("/")
            and not path.startswith(self.exempt_prefixes)
        ):
            target = path.rstrip("/") or "/"
            query = request.META.get("QUERY_STRING")
            if query:
                target = f"{target}?{query}"

            response = HttpResponsePermanentRedirect(target)
            if request.method not in ("GET", "HEAD"):
                response.status_code = 308
            return response
        return self.get_response(request)
