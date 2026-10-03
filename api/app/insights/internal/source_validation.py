"""Source-location validation for dashboards (spec FR-010).

An INTERNAL_PAGE dashboard lives inside the platform, so its location is a path
(``/ana/usage``). Every other source is embedded from outside and must be an
absolute ``https`` URL. Only the format is checked — nothing is fetched, so this
is no SSRF surface. Raises ValueError (routes map to 400).
"""
from typing import Optional
from urllib.parse import urlsplit

from ...internal.status import normalize

SOURCE_INTERNAL_PAGE = "INTERNAL_PAGE"
MAX_LENGTH = 2048


def validate_source_url(source_type: Optional[str], url: Optional[str]) -> None:
    value = (url or "").strip()
    if not value:
        raise ValueError("'source_url' cannot be blank")
    if len(value) > MAX_LENGTH:
        raise ValueError(f"'source_url' must be at most {MAX_LENGTH} characters")

    if normalize(source_type) == SOURCE_INTERNAL_PAGE:
        # A platform path: "/x", never protocol-relative ("//host") or a scheme.
        if not value.startswith("/") or value.startswith("//") or "://" in value:
            raise ValueError(
                "An Internal Page source must be a path inside the platform, e.g. /ana/usage")
        return

    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError("An external source must be an absolute https:// URL")
