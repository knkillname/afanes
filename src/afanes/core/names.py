# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Name normalization and cross-platform filename derivation.

This module is a leaf: it imports only the standard library so both the
reference resolver and the vault writer can share one authoritative rule.
"""

import re
import unicodedata
from collections.abc import Iterable

# Public cross-platform filename policy. Callers and tests share these values
# instead of duplicating them.
FORBIDDEN_CHARACTERS = frozenset('<>:"/\\|?*')
RESERVED_DEVICE_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)
_CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE_PATTERN = re.compile(r"\s+")
MAX_NAME_BYTES = 200
FALLBACK_NAME = "Untitled"


def normalize_name(text: str) -> str:
    """Normalize a name for matching and uniqueness checks.

    The transformation applies NFC normalization, case folding, trimming,
    internal whitespace collapse, and removal of one optional trailing
    ``.md``. Applying it twice yields the same result.

    Parameters
    ----------
    text : str
        Name, filename stem, or link destination name to normalize. Empty
        input is valid and normalizes to an empty string.

    Returns
    -------
    str
        Case-folded, whitespace-collapsed name without a trailing extension.

    Notes
    -----
    A trailing ``.md`` is removed only after case folding, so ``Report.MD``
    and ``report.md`` normalize to the same key.
    """
    normalized = unicodedata.normalize("NFC", text).casefold()
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = _WHITESPACE_PATTERN.sub(" ", normalized).strip()
    while normalized.endswith(".md"):
        normalized = normalized[:-3].strip()
    return normalized


def safe_filename(title: str) -> str:
    """Derive a filename stem that is safe on macOS, Linux, and Windows.

    The transformation normalizes to NFC, replaces forbidden characters with
    spaces, removes control characters, collapses whitespace, avoids reserved
    device names, removes leading and trailing dots or spaces, and bounds the
    result to 200 UTF-8 bytes on a character boundary. An empty result becomes
    ``Untitled``.

    Parameters
    ----------
    title : str
        Display title supplied by the user or derived from note content.

    Returns
    -------
    str
        A deterministic, cross-platform filename stem without an extension.

    Notes
    -----
    The returned stem is the note's title and identity, so it is intentionally
    display-preserving rather than slugified. Collision handling belongs to
    :func:`unique_name`.
    """
    name = unicodedata.normalize("NFC", title)
    name = "".join(" " if character in FORBIDDEN_CHARACTERS else character for character in name)
    name = _CONTROL_PATTERN.sub("", name)
    name = _WHITESPACE_PATTERN.sub(" ", name).strip()
    name = _avoid_reserved_device_name(name)
    name = name.rstrip(". ")
    name = name.lstrip(". ")
    name = _truncate_to_utf8_bytes(name, MAX_NAME_BYTES)
    name = name.rstrip(". ").lstrip(". ")
    name = _avoid_reserved_device_name(name)
    name = _truncate_to_utf8_bytes(name, MAX_NAME_BYTES)
    if not name:
        return FALLBACK_NAME
    return name


def unique_name(name: str, taken: Iterable[str]) -> str:
    """Append the smallest available integer suffix when a name is taken.

    Parameters
    ----------
    name : str
        Candidate name, normally the output of :func:`safe_filename`.
    taken : Iterable[str]
        Names already used in the target namespace. Comparison uses
        :func:`normalize_name`, so case variants count as collisions.

    Returns
    -------
    str
        ``name`` unchanged when available, otherwise ``name 2``, ``name 3``,
        and so on, choosing the smallest free integer. The result never exceeds
        200 UTF-8 bytes.

    Notes
    -----
    The suffix base is truncated when needed so the complete result respects
    the byte limit. A gap in the suffix sequence is reused.
    """
    taken_keys = {normalize_name(item) for item in taken}
    if normalize_name(name) not in taken_keys:
        return name

    index = 2
    while True:
        suffix = f" {index}"
        available_bytes = MAX_NAME_BYTES - len(suffix.encode("utf-8"))
        base = _truncate_to_utf8_bytes(name, available_bytes).rstrip(". ")
        if not base:
            base = FALLBACK_NAME
        candidate = f"{base}{suffix}"
        if normalize_name(candidate) not in taken_keys:
            return candidate
        index += 1


def _avoid_reserved_device_name(name: str) -> str:
    """Insert ``-note`` into a reserved Windows device name."""
    head, separator, tail = name.partition(".")
    if head.strip().upper() in RESERVED_DEVICE_NAMES:
        return f"{head}-note{separator}{tail}"
    return name


def _truncate_to_utf8_bytes(text: str, limit: int) -> str:
    """Truncate text to a UTF-8 byte limit without splitting a character."""
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    return encoded[:limit].decode("utf-8", errors="ignore")
