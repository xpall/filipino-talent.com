"""Pure validation and DNS record-building rules.

This module deliberately has no Django imports so it can be tested and reused
without an application context. The JSON files in ``config-data/`` are the
source of truth for reserved names and allowed CNAME targets.
"""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlparse

RECORD_TYPES = ("A", "AAAA", "CNAME", "TXT")

SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

MANAGED_COMMENT = "managed-by:filipino-talent"

GH_USER_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config-data"


def _load_json(name: str) -> dict:
    with (_CONFIG_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


RESERVED = _load_json("reserved.json")
ALLOWED_CNAME = _load_json("allowed-targets.json").get("cname", [])


def normalize_subdomain(value) -> str:
    return str(value or "").strip().lower()


def is_valid_subdomain_label(name) -> bool:
    return isinstance(name, str) and len(name) <= 63 and bool(SUBDOMAIN_RE.fullmatch(name))


def is_reserved(name: str, reserved: dict | None = None) -> bool:
    reserved = RESERVED if reserved is None else reserved
    if name in reserved.get("exact", []):
        return True
    for pattern in reserved.get("blockedPatterns", []):
        try:
            if re.search(pattern, name):
                return True
        except re.error:
            continue
    return False


def match_allowed_suffix(value: str, suffixes: list[str] | None = None) -> bool:
    suffixes = ALLOWED_CNAME if suffixes is None else suffixes
    host = str(value or "").strip().lower().rstrip(".")
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in suffixes)


def is_ipv4(value: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(str(value).strip()), ipaddress.IPv4Address)
    except ValueError:
        return False


def is_ipv6(value: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(str(value).strip()), ipaddress.IPv6Address)
    except ValueError:
        return False


def is_https_url(value: str) -> bool:
    try:
        return urlparse(str(value)).scheme == "https"
    except ValueError:
        return False


def validate_domain(
    name: str,
    doc: dict,
    *,
    reserved: dict | None = None,
    allowed_cname: list[str] | None = None,
) -> list[str]:
    """Validate a normalized subdomain document. Returns human-readable errors."""
    reserved = RESERVED if reserved is None else reserved
    allowed_cname = ALLOWED_CNAME if allowed_cname is None else allowed_cname
    errors: list[str] = []

    if not is_valid_subdomain_label(name):
        errors.append(
            f'"{name}" is not a valid subdomain (lowercase letters, digits and hyphens; 1-63 chars)'
        )
    if is_reserved(name, reserved):
        errors.append(f'"{name}" is a reserved subdomain')

    if not isinstance(doc, dict):
        errors.append("record must be a JSON object")
        return errors

    owner = doc.get("owner")
    if not isinstance(owner, dict):
        errors.append("owner object is required")
    else:
        github = owner.get("github")
        if github not in (None, ""):
            if not isinstance(github, str) or not GH_USER_RE.fullmatch(github):
                errors.append("owner.github must be a valid GitHub username")
        portfolio = owner.get("portfolio")
        if portfolio not in (None, "") and not is_https_url(portfolio):
            errors.append("owner.portfolio must be an https URL")

    records = doc.get("records")
    if not isinstance(records, dict):
        errors.append("records object is required")
        return errors

    present = [record_type for record_type in RECORD_TYPES if record_type in records]
    if not present:
        errors.append(f"at least one record type is required ({', '.join(RECORD_TYPES)})")

    unknown = [key for key in records if key not in RECORD_TYPES]
    if unknown:
        errors.append(f"unknown record type(s): {', '.join(unknown)}")

    for record_type in present:
        record = records[record_type]
        if not isinstance(record, dict):
            errors.append(f"{record_type} record must be an object")
            continue
        value = record.get("value")
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{record_type} record needs a non-empty "value"')
            continue
        if len(value) > 512:
            errors.append(f"{record_type} record value is too long (max 512)")

        if record_type == "A" and not is_ipv4(value):
            errors.append(f'A record value "{value}" is not a valid IPv4 address')
        if record_type == "AAAA" and not is_ipv6(value):
            errors.append(f'AAAA record value "{value}" is not a valid IPv6 address')
        if record_type == "CNAME":
            target = value.strip().lower().rstrip(".")
            if target.endswith("filipino-talent.com"):
                errors.append(f'CNAME "{value}" must not point back at filipino-talent.com')
            if not match_allowed_suffix(target, allowed_cname):
                errors.append(
                    f'CNAME "{value}" is not an allowed target. '
                    f"Allowed suffixes: {', '.join(allowed_cname)}"
                )
            if record.get("proxied"):
                errors.append("CNAME records cannot be proxied; the target host must terminate TLS")
        if record_type == "TXT" and record.get("proxied"):
            errors.append("TXT records cannot be proxied")

    return errors


def to_cloudflare_records(name: str, doc: dict, zone: str) -> list[dict]:
    records: list[dict] = []
    for record_type in RECORD_TYPES:
        record = doc.get("records", {}).get(record_type)
        if not record:
            continue
        records.append(
            {
                "type": record_type,
                "name": f"{name}.{zone}",
                "content": record["value"].strip(),
                "ttl": record.get("ttl", 1),
                "proxied": bool(record.get("proxied")) if record_type in ("A", "AAAA") else False,
                "comment": MANAGED_COMMENT,
            }
        )
    return records


def to_domain_doc(row) -> dict:
    """Build a domain document from a submission-like object or mapping."""
    get = row.get if isinstance(row, dict) else lambda key, default=None: getattr(row, key, default)
    owner = {}
    github = str(get("github_username", "") or "").strip()
    if github:
        owner["github"] = github
    portfolio = get("portfolio_url", "")
    if portfolio:
        owner["portfolio"] = str(portfolio).strip()
    record_type = str(get("record_type", "") or "").upper()
    record_value = str(get("record_value", "") or "").strip()
    return {"owner": owner, "records": {record_type: {"value": record_value}}}


HOST_CONNECT = [
    {"suffix": "github.io", "label": "GitHub Pages", "anchor": "github-pages"},
    {"suffix": "pages.dev", "label": "Cloudflare Pages", "anchor": "cloudflare-pages"},
    {"suffix": "vercel.app", "label": "Vercel", "anchor": "vercel"},
    {"suffix": "netlify.app", "label": "Netlify", "anchor": "netlify"},
]


def connect_guide_for_target(target: str) -> dict | None:
    host = str(target or "").strip().lower().rstrip(".")
    for entry in HOST_CONNECT:
        if host == entry["suffix"] or host.endswith(f".{entry['suffix']}"):
            return entry
    return None
