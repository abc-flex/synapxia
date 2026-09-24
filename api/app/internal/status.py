"""Status-code normalization shared by every domain's status policy.

Legacy/seeded rows may carry the `list_items` sort prefix (e.g. `3-PUBLISHED`)
instead of the bare code. Policies compare on the bare code so such a row is
still recognised — the UI already tolerates both spellings.
"""
import re
from typing import Optional

_SORT_PREFIX = re.compile(r"^\d+-")


def normalize(status: Optional[str]) -> str:
    """The bare status code: trimmed, upper-cased, sort-prefix stripped."""
    return _SORT_PREFIX.sub("", (status or "").strip().upper())
