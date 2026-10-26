# filipino-talent.com

Free `yourname.filipino-talent.com` subdomains for Filipino remote workers.
This repository contains the whole service: the public site, the Google-authenticated
submit flow, the registry, the staff dashboard, and Cloudflare DNS automation.

The old `filipino-talent-backend` Worker/D1 repository is retired. There is no
Astro/Node runtime, Cloudflare Worker, or D1 database in this app.

## Stack

- Django 5.2 + Django templates
- SQLite (file at `data/db.sqlite3`)
- Gunicorn + WhiteNoise
- Google-only django-allauth
- Cloudflare DNS API (records tagged `managed-by:filipino-talent`)
- One Docker container, exposed on `127.0.0.1:${APP_PORT:-8020}`

## Quick start

```bash
cp .env.example .env
# edit .env: SECRET_KEY, Google OAuth, Cloudflare token/zone ID, ADMIN_EMAILS
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

Open http://localhost:8000.

For local development set `DEBUG=1`, `ALLOWED_HOSTS=localhost,127.0.0.1`,
`CSRF_TRUSTED_ORIGINS=http://localhost:8000`, and `SITE_URL=http://localhost:8000`
in `.env`. The SQLite file defaults to `./data/db.sqlite3` outside Docker.

## Google OAuth

1. In Google Cloud Console, configure an OAuth consent screen.
2. Create an OAuth client ID of type **Web application**.
3. Add authorized redirect URIs:
   - `https://filipino-talent.com/accounts/google/login/callback/`
   - `http://localhost:8000/accounts/google/login/callback/` for local dev
4. Put `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
5. Add your own Google email to `ADMIN_EMAILS` to unlock `/dashboard`.

Google is the only sign-in method. There are no local passwords, signup forms,
password resets, or verification emails.

## Cloudflare DNS

Create an API token with **Zone → DNS → Edit** for the `filipino-talent.com`
zone, then set `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID`. The app only
updates or deletes records whose comment is `managed-by:filipino-talent`.

New submissions publish immediately. If the Cloudflare call fails, the row stays
`pending` and can be retried from `/account` or `/dashboard`. Run the reconciler
manually or from host cron:

```bash
python manage.py sync_dns
python manage.py sync_dns --reconcile-live
```

Example host cron (optional):

```cron
*/15 * * * * cd /path/to/filipino-talent.com && docker compose exec -T web python manage.py sync_dns >> /var/log/filipino-talent-sync.log 2>&1
```

## Docker / VPS

```bash
cp .env.example .env
# edit .env
docker compose up -d --build
docker compose port web 8000   # 127.0.0.1:8020
curl http://127.0.0.1:8020/health
```

The container always listens on port `8000` internally. `APP_PORT` only changes
the host-facing port. The SQLite database lives in `./data` on the host.

### Cloudflare Tunnel

Do this in the Cloudflare Zero Trust dashboard, not in `docker-compose.yml`:

- Public hostname: `filipino-talent.com`
- Service: `HTTP`
- URL: `http://127.0.0.1:8020`

Add a redirect rule for `www.filipino-talent.com` → `https://filipino-talent.com`.
Django also redirects `www` as a fallback.

## Verify

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The suite covers validation rules, form behavior, submit/publish/remove flows,
rate limits, permissions, the staff dashboard, legacy import, and DNS retries.

## Import the legacy directory

Before shutting down the old API, import its public directory. On the VPS:

```bash
# fetches https://api.filipino-talent.com/domains
docker compose exec web python manage.py import_legacy

# or from a saved JSON file placed in ./data
docker compose exec web python manage.py import_legacy \
  --file /app/data/legacy-domains.json

# also upsert the DNS records (optional; existing records are already live)
docker compose exec web python manage.py import_legacy --sync-dns
```

For local development, run the same commands with `python manage.py ...`.

Legacy rows are imported as `live` with no user attached. Existing owners can
email `remove@filipino-talent.com` if they need a name released; new submissions
are tied to Google accounts and can be released from `/account`.

## Routes

| Route | Access | Purpose |
| --- | --- | --- |
| `/` | public | landing page |
| `/guide`, `/guide/<slug>` | public | guides |
| `/directory` | public | public registry |
| `/terms` | public | terms |
| `/api/domains` | public | JSON directory |
| `/submit` | Google login | submit a subdomain |
| `/account` | Google login | view, retry, release your subdomains |
| `/dashboard` | `ADMIN_EMAILS` | moderation |
| `/health` | public | container health check |

## Moderation

- `/dashboard` lists all submissions, filters by status, and supports publish,
  retry, remove, and reject.
- `/account` lets a signed-in user retry a pending publish or release a name.
- To free a name, the app deletes the tagged Cloudflare records first, then marks
  the row `removed` or `rejected`.
- Rate limits: per-IP/day, per-email/day, and a maximum number of active
  subdomains per user (`MAX_*` in `.env`).

## Backup

The only state is SQLite. Back it up while the app is running:

```bash
docker compose exec -T web python - <<'PY'
import sqlite3
from pathlib import Path

path = Path('/app/data/backup.sqlite3')
path.unlink(missing_ok=True)
src = sqlite3.connect('/app/data/db.sqlite3')
dst = sqlite3.connect(path)
src.backup(dst)
PY
docker cp filipino-talent-web:/app/data/backup.sqlite3 ./backup.sqlite3
```

Then copy `backup.sqlite3` off the VPS. To restore, stop the service, copy the
backup back, and start it again:

```bash
docker compose stop web
docker compose run --rm --entrypoint sh web -c \
  "rm -f /app/data/db.sqlite3-wal /app/data/db.sqlite3-shm"
docker cp ./backup.sqlite3 filipino-talent-web:/app/data/db.sqlite3
docker compose start web
```

## Retiring the old backend

1. Save the old public directory before the API is shut down.
2. Deploy this container and verify `/health`, Google login, and the directory.
3. Remove the Cloudflare Pages custom domain mapping for the apex and `www`.
4. Create the Cloudflare Tunnel public hostname for the apex domain
   (`http://127.0.0.1:8020`) and the `www` redirect.
5. Verify HTTPS, Google login, `/directory`, and a test submission.
6. Remove the old Worker route and the `api.filipino-talent.com` DNS record.
7. Archive the `filipino-talent-backend` GitHub repository.
8. After a retention period, delete the old D1 database and Worker.

## License

MIT. See [LICENSE](LICENSE). Inspired by [is-a.dev](https://www.is-a.dev).
