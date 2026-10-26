from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from registry.models import Submission
from registry.services import cloudflare
from registry.services.publish import PublishError, publish_submission, unpublish_submission
from registry.services.rules import (
    ALLOWED_CNAME,
    RESERVED,
    to_cloudflare_records,
    to_domain_doc,
    validate_domain,
)


class Command(BaseCommand):
    help = "Retry pending publishes, clean removed records, and optionally reconcile live rows."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--reconcile-live",
            action="store_true",
            help="Upsert every live row's DNS record (idempotent).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        failures = 0
        published = cleaned = reconciled = 0

        pending = Submission.objects.filter(status=Submission.Status.PENDING)
        for submission in pending:
            if dry_run:
                self.stdout.write(f"would publish {submission.subdomain}")
                continue
            try:
                publish_submission(submission)
                published += 1
            except PublishError as exc:
                submission.last_error = str(exc)
                submission.save(update_fields=["last_error", "updated_at"])
                self.stderr.write(f"publish failed for {submission.subdomain}: {exc}")
                failures += 1

        cleanup = Submission.objects.filter(
            status__in=[Submission.Status.REMOVED, Submission.Status.REJECTED],
            dns_cleaned_at__isnull=True,
        )
        for submission in cleanup:
            if dry_run:
                self.stdout.write(f"would clean {submission.subdomain}")
                continue
            try:
                unpublish_submission(submission, submission.status)
                cleaned += 1
            except PublishError as exc:
                submission.last_error = str(exc)
                submission.save(update_fields=["last_error", "updated_at"])
                self.stderr.write(f"cleanup failed for {submission.subdomain}: {exc}")
                failures += 1

        if options["reconcile_live"]:
            live = Submission.objects.filter(status=Submission.Status.LIVE)
            for submission in live:
                doc = to_domain_doc(submission)
                errors = validate_domain(
                    submission.subdomain,
                    doc,
                    reserved=RESERVED,
                    allowed_cname=ALLOWED_CNAME,
                )
                if errors:
                    self.stderr.write(
                        f"reconcile skipped for {submission.subdomain}: {'; '.join(errors)}"
                    )
                    if not dry_run:
                        submission.last_error = (
                            "Reconcile skipped: " + "; ".join(errors)
                        )
                        submission.save(update_fields=["last_error", "updated_at"])
                    failures += 1
                    continue
                if dry_run:
                    self.stdout.write(f"would reconcile {submission.subdomain}")
                    continue
                try:
                    for record in to_cloudflare_records(
                        submission.subdomain, doc, settings.ZONE
                    ):
                        cloudflare.upsert_record(record)
                    reconciled += 1
                except cloudflare.CloudflareError as exc:
                    submission.last_error = str(exc)
                    submission.save(update_fields=["last_error", "updated_at"])
                    self.stderr.write(
                        f"reconcile failed for {submission.subdomain}: {exc}"
                    )
                    failures += 1

        self.stdout.write(
            f"sync complete: published={published} cleaned={cleaned} "
            f"reconciled={reconciled} failures={failures} at={timezone.now().isoformat()}"
        )
        if failures:
            raise CommandError(f"sync_dns completed with {failures} failure(s)")
