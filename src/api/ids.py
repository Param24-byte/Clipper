"""
Utility: generate ULID-style IDs.

Using python-ulid for lexicographically sortable, time-prefixed IDs.
These are stored as 26-char strings (no hyphens, URL-safe).
"""

from __future__ import annotations

from ulid import ULID


def new_id() -> str:
    """Return a new 26-character ULID string."""
    return str(ULID())
