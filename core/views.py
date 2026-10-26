from __future__ import annotations

import logging
from pathlib import Path

import frontmatter
import markdown
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe

from registry.models import Submission

logger = logging.getLogger("registry")

CONTENT_DIR = Path(settings.BASE_DIR) / "content" / "guides"

HOME_HOSTS = [
    {
        "name": "GitHub Pages",
        "target": "username.github.io",
        "note": "Free forever, works with a repo",
        "href": "/guide/github-pages",
    },
    {
        "name": "Cloudflare Pages",
        "target": "project.pages.dev",
        "note": "Free, fast, custom domains",
        "href": "/guide/cloudflare-pages",
    },
    {
        "name": "Vercel",
        "target": "project.vercel.app",
        "note": "Great for Next.js portfolios",
        "href": "/guide/vercel",
    },
    {
        "name": "Netlify",
        "target": "site.netlify.app",
        "note": "Free tier, drag-and-drop deploy",
        "href": "/guide/netlify",
    },
]

GUIDE_SLUGS = {
    path.stem
    for path in CONTENT_DIR.glob("*.md")
    if path.stem != "index"
}
MARKDOWN_EXTENSIONS = [
    "extra",
    "tables",
    "fenced_code",
    "sane_lists",
    "toc",
    "attr_list",
    "md_in_html",
    "pymdownx.superfences",
    "pymdownx.tilde",
    "pymdownx.tasklist",
]


def _render_guide(filename: str) -> tuple[dict, str]:
    post = frontmatter.load(CONTENT_DIR / filename)
    body = markdown.markdown(
        post.content,
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs={"pymdownx.tasklist": {"custom_checkbox": True}},
    )
    return post.metadata, mark_safe(body)


def home(request):
    context = {
        "domain_count": Submission.objects.filter(status=Submission.Status.LIVE).count(),
        "hosts": HOME_HOSTS,
    }
    return render(request, "home.html", context)


def guide_index(request):
    metadata, content = _render_guide("index.md")
    return render(
        request,
        "guide/index.html",
        {
            "page_title": metadata.get("title", "Guide"),
            "page_description": metadata.get("description", ""),
            "content": content,
        },
    )


def guide_connect(request):
    return render(request, "guide/connect.html")


def guide_page(request, slug: str):
    if slug not in GUIDE_SLUGS:
        from django.http import Http404

        raise Http404("Guide not found")
    metadata, content = _render_guide(f"{slug}.md")
    return render(
        request,
        "guide/page.html",
        {
            "page_title": metadata.get("title", "Guide"),
            "page_description": metadata.get("description", ""),
            "content": content,
        },
    )


def terms(request):
    return render(request, "terms.html")


def health(request):
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"ok": True})
    except Exception:  # pragma: no cover - health endpoint
        logger.exception("health check failed")
        return JsonResponse({"ok": False}, status=503)


def robots(request):
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /account",
            "Disallow: /dashboard",
            "Disallow: /submit",
            "",
        ]
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
