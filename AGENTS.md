# AGENTS.md

Single Django project. There is no root manifest, workspace, CI, linter, or test
suite outside this repository. The old `filipino-talent-backend` Worker/D1 repo
is retired; do not reintroduce a Worker, D1, Astro, or Node runtime.

## Layout

- `config/` — Django settings, URLs, WSGI/ASGI.
- `core/` — public pages, Markdown guide rendering, health, context, middleware.
- `registry/` — `Submission` model, forms, views, Cloudflare DNS, management commands.
- `templates/` — Django templates ported from the old Astro site.
- `content/guides/` — Markdown guides with frontmatter.
- `static/` — `global.css` (ported design system), JS, favicon.
- `config-data/` — allowed CNAME targets and reserved subdomains (source of truth).
- `data/` — SQLite volume; gitignored.

## Commands

```bash
. .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py migrate
python manage.py runserver 8000
python manage.py collectstatic --noinput
python manage.py import_legacy
python manage.py sync_dns [--reconcile-live]
```

Docker:

```bash
docker compose up -d --build
docker compose logs -f web
docker compose exec web python manage.py sync_dns
```

## Architecture facts that are easy to get wrong

- One container: Gunicorn + SQLite + WhiteNoise. No Redis, Celery, Postgres, or
  Cloudflare Worker.
- Google is the only auth method via django-allauth. `/submit` and `/account`
  require login; `/dashboard` requires an email in `ADMIN_EMAILS`.
- Google ID-token decoding needs `PyJWT[crypto]`. Keep the
  `django-allauth[socialaccount]` extra in `requirements.txt`; plain
  `django-allauth` causes the callback to fail with `No module named 'jwt'`.
- Submissions publish immediately. If the Cloudflare API fails, the row stays
  `pending`; retry from `/account`, `/dashboard`, or `manage.py sync_dns`.
- `removed`/`rejected` rows free the name. Delete DNS first, then flip status.
- Cloudflare records are tagged `managed-by:filipino-talent`. Only tagged records
  are updated or deleted. Keep `MANAGED_COMMENT` intact.
- `config-data/allowed-targets.json` and `config-data/reserved.json` are the
  validation source of truth. The allowed list is injected into `submit.js` via
  `json_script`; there is no duplicated suffix list to maintain.
- SQLite is in WAL mode (`core/apps.py` connection signal). Keep `data/` on a
  local filesystem volume.
- TLS terminates at Cloudflare Tunnel. Keep `SECURE_PROXY_SSL_HEADER`; do not
  enable global HSTS (`SECURE_HSTS_SECONDS`) because it can force HTTPS on every
  user subdomain. Cloudflare handles HTTPS redirects.
- Port convention: container listens on `8000`; host port is `APP_PORT` (default
  `8020`). Cloudflare Tunnel is configured in the Cloudflare dashboard, not in
  Compose.
- Public URLs use no trailing slash and `APPEND_SLASH = False`. Keep `{% url %}`
  names in sync with `core/urls.py` and `registry/urls.py`.
- The terms copy intentionally says publishing is immediate and that Google
  verifies the account. Do not restore the old 15-minute/`verify@` wording.
