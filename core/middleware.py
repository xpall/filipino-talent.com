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
