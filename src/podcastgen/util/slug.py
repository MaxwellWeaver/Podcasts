"""Slug helpers — wraps python-slugify with project conventions."""

from __future__ import annotations

import hashlib
import secrets

from slugify import slugify as _slugify


def slugify(text: str, max_length: int = 80) -> str:
    """Lowercase, hyphenated slug suitable for filenames."""
    return _slugify(text, max_length=max_length, lowercase=True, separator="-")


def short_uuid(n: int = 8) -> str:
    """Short URL-safe random token. Used to make episode filenames unguessable."""
    return secrets.token_urlsafe(n)[:n].lower().replace("_", "a").replace("-", "b")


def url_hash(url: str) -> str:
    """Stable short hash of a URL for the dedup ledger."""
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]
