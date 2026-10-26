from __future__ import annotations

import logging

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from registry.models import Submission
from registry.services import cloudflare
from registry.services.rules import (
    ALLOWED_CNAME,
    RESERVED,
    to_cloudflare_records,
    to_domain_doc,
    validate_domain,
)

logger = logging.getLogger("registry")


class PublishError(RuntimeError):
    pass


def publish_submission(submission: Submission) -> None:
    """Create/update the tagged Cloudflare records and mark the row live.

    Raises ``PublishError`` if the document is invalid or the Cloudflare API
    fails. The row is left in its current status so it can be retried.
    """
    name = submission.subdomain
    doc = to_domain_doc(submission)
    errors = validate_domain(name, doc, reserved=RESERVED, allowed_cname=ALLOWED_CNAME)
    if errors:
        raise PublishError("; ".join(errors))

    records = to_cloudflare_records(name, doc, settings.ZONE)
    if not records:
        raise PublishError("No DNS records to publish.")

    try:
        for record in records:
            result = cloudflare.upsert_record(record)
            logger.info("dns %s %s %s", result, record["type"], record["name"])
    except cloudflare.CloudflareError as exc:
        raise PublishError(str(exc)) from exc

    submission.status = Submission.Status.LIVE
    submission.published_at = submission.published_at or timezone.now()
    submission.removed_at = None
    submission.dns_cleaned_at = None
    submission.last_error = ""
    try:
        submission.save(
            update_fields=[
                "status",
                "published_at",
                "removed_at",
                "dns_cleaned_at",
                "last_error",
                "updated_at",
            ]
        )
    except IntegrityError as exc:
        raise PublishError(
            "Another active request already uses this subdomain. "
            "The DNS record was updated; fix the duplicate in the dashboard."
        ) from exc


def unpublish_submission(
    submission: Submission,
    status: str = Submission.Status.REMOVED,
) -> None:
    """Delete the tagged records for a subdomain and set the final status."""
    name = f"{submission.subdomain}.{settings.ZONE}"
    try:
        deleted = cloudflare.delete_records(name)
        logger.info("dns deleted=%s name=%s", deleted, name)
    except cloudflare.CloudflareError as exc:
        raise PublishError(str(exc)) from exc

    submission.status = status
    submission.removed_at = submission.removed_at or timezone.now()
    submission.dns_cleaned_at = timezone.now()
    submission.last_error = ""
    submission.save(
        update_fields=[
            "status",
            "removed_at",
            "dns_cleaned_at",
            "last_error",
            "updated_at",
        ]
    )
