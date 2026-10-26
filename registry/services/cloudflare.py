"""Minimal Cloudflare DNS API client.

Only records tagged with ``MANAGED_COMMENT`` are ever updated or deleted.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from registry.services.rules import MANAGED_COMMENT

logger = logging.getLogger("registry")

API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareError(RuntimeError):
    pass


def _token() -> str:
    token = settings.CLOUDFLARE_API_TOKEN
    if not token:
        raise CloudflareError("CLOUDFLARE_API_TOKEN is not configured.")
    return token


def _zone_id() -> str:
    zone_id = settings.CLOUDFLARE_ZONE_ID
    if not zone_id:
        raise CloudflareError("CLOUDFLARE_ZONE_ID is not configured.")
    return zone_id


def _request(method: str, path: str, **kwargs) -> dict:
    url = f"{API_BASE}{path}"
    try:
        response = requests.request(
            method,
            url,
            headers={
                "Authorization": f"Bearer {_token()}",
                "Content-Type": "application/json",
            },
            timeout=20,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise CloudflareError(f"Cloudflare API request failed: {exc}") from exc

    try:
        body = response.json()
    except ValueError:
        body = {}

    if not response.ok or body.get("success") is False:
        detail = body.get("errors") or body
        raise CloudflareError(
            f"Cloudflare API {method} {path} failed: {response.status_code} {detail}"
        )
    return body.get("result") or {}


def list_managed_records(name: str | None = None) -> list[dict]:
    records: list[dict] = []
    page = 1
    while True:
        params = {"per_page": "100", "page": str(page)}
        if name:
            params["name"] = name
        batch = _request("GET", f"/zones/{_zone_id()}/dns_records", params=params)
        if not isinstance(batch, list):
            break
        records.extend(record for record in batch if record.get("comment") == MANAGED_COMMENT)
        if len(batch) < 100:
            break
        page += 1
    return records


def upsert_record(record: dict) -> str:
    existing = list_managed_records(record["name"])
    current = next((item for item in existing if item.get("type") == record["type"]), None)
    if not current:
        _request("POST", f"/zones/{_zone_id()}/dns_records", json=record)
        return "created"

    changed = (
        current.get("content") != record["content"]
        or int(current.get("ttl", 1)) != int(record["ttl"])
        or bool(current.get("proxied")) != bool(record["proxied"])
    )
    if changed:
        _request(
            "PUT",
            f"/zones/{_zone_id()}/dns_records/{current['id']}",
            json=record,
        )
        return "updated"
    return "unchanged"


def delete_records(name: str) -> int:
    records = list_managed_records(name)
    for record in records:
        _request("DELETE", f"/zones/{_zone_id()}/dns_records/{record['id']}")
    return len(records)
