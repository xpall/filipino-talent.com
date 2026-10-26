from __future__ import annotations

import json
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from registry.models import Submission
from registry.services import cloudflare
from registry.services.rules import (
    ALLOWED_CNAME,
    RESERVED,
    is_valid_subdomain_label,
    to_cloudflare_records,
    to_domain_doc,
    validate_domain,
)

LEGACY_URL = "https://api.filipino-talent.com/domains"


class Command(BaseCommand):
    help = "Import the old public directory from api.filipino-talent.com/domains."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=LEGACY_URL, help="Legacy JSON endpoint")
        parser.add_argument("--file", help="Read the legacy JSON from a file instead of a URL")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--sync-dns",
            action="store_true",
            help="Also upsert each imported record through the Cloudflare API.",
        )

    def handle(self, *args, **options):
        if options["file"]:
            try:
                payload = json.loads(Path(options["file"]).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise CommandError(f"Could not read {options['file']}: {exc}") from exc
        else:
            try:
                response = requests.get(options["url"], timeout=20)
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise CommandError(f"Could not fetch {options['url']}: {exc}") from exc

        domains = payload.get("domains") if isinstance(payload, dict) else payload
        if not isinstance(domains, list):
            raise CommandError("Expected a JSON object with a 'domains' array.")

        created = updated = skipped = failed = 0

        for item in domains:
            if not isinstance(item, dict) or not item.get("subdomain"):
                skipped += 1
                continue
            subdomain = str(item["subdomain"]).strip().lower()
            portfolio_url = str(item.get("portfolio_url") or "").strip()
            record_type = str(item.get("record_type") or "CNAME").upper()
            record_value = str(item.get("record_value") or "").strip()
            github_username = str(item.get("github_username") or "").strip()
            if not portfolio_url or not record_value:
                self.stderr.write(f"skip {subdomain}: missing portfolio_url or record_value")
                skipped += 1
                continue

            created_at = parse_datetime(str(item.get("created_at") or "")) or timezone.now()
            if timezone.is_naive(created_at):
                created_at = timezone.make_aware(created_at)

            doc = to_domain_doc(
                {
                    "github_username": github_username,
                    "portfolio_url": portfolio_url,
                    "record_type": record_type,
                    "record_value": record_value,
                }
            )
            validation_errors = validate_domain(
                subdomain, doc, reserved=RESERVED, allowed_cname=ALLOWED_CNAME
            )
            if not is_valid_subdomain_label(subdomain):
                self.stderr.write(f"skip {subdomain}: invalid subdomain label")
                skipped += 1
                continue
            if validation_errors:
                self.stderr.write(
                    f"warning {subdomain}: imported anyway; does not pass current "
                    f"validation: {'; '.join(validation_errors)}"
                )

            existing = Submission.objects.filter(subdomain__iexact=subdomain).first()
            if existing:
                if existing.user_id is not None:
                    self.stdout.write(f"skip {subdomain}: already owned in the new app")
                    skipped += 1
                    continue
                if existing.status in (Submission.Status.REMOVED, Submission.Status.REJECTED):
                    self.stdout.write(f"skip {subdomain}: already removed/rejected")
                    skipped += 1
                    continue
                if options["dry_run"]:
                    self.stdout.write(f"would update {subdomain}")
                    updated += 1
                    continue
                existing.portfolio_url = portfolio_url
                existing.github_username = github_username
                existing.record_type = record_type
                existing.record_value = record_value
                existing.status = Submission.Status.LIVE
                existing.published_at = existing.published_at or created_at
                existing.last_error = ""
                existing.save(
                    update_fields=[
                        "portfolio_url",
                        "github_username",
                        "record_type",
                        "record_value",
                        "status",
                        "published_at",
                        "last_error",
                        "updated_at",
                    ]
                )
                updated += 1
            else:
                if options["dry_run"]:
                    self.stdout.write(f"would create {subdomain}")
                    created += 1
                    continue
                submission = Submission.objects.create(
                    user=None,
                    subdomain=subdomain,
                    legal_name="",
                    email="",
                    portfolio_url=portfolio_url,
                    github_username=github_username,
                    record_type=record_type,
                    record_value=record_value,
                    status=Submission.Status.LIVE,
                    notes=(
                        "Imported from legacy public directory"
                        + (
                            f"; validation warnings: {'; '.join(validation_errors)}"
                            if validation_errors
                            else ""
                        )
                    ),
                    created_at=created_at,
                    published_at=created_at,
                )
                created += 1
                existing = submission

            if options["sync_dns"] and not options["dry_run"]:
                if validation_errors:
                    self.stderr.write(
                        f"dns skipped for {subdomain}: fix the validation warnings first"
                    )
                    failed += 1
                    continue
                try:
                    for record in to_cloudflare_records(
                        subdomain, doc, settings.ZONE
                    ):
                        cloudflare.upsert_record(record)
                except cloudflare.CloudflareError as exc:
                    existing.last_error = str(exc)
                    existing.save(update_fields=["last_error", "updated_at"])
                    self.stderr.write(f"dns failed for {subdomain}: {exc}")
                    failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"import complete: created={created} updated={updated} "
                f"skipped={skipped} dns_failed={failed}"
            )
        )
