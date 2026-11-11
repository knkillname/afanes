# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reference parsing, extraction, catalog building, and resolution."""

import dataclasses
import re
import urllib.parse
from collections.abc import Iterable, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Self

from markdown_it import MarkdownIt
from markdown_it.token import Token

import afanes.core.names
from afanes.core.errors import InvalidReferenceError, ReferenceRewriteError
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType

_SCHEME_PATTERN = re.compile(r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*):(?P<name>.*)$", re.DOTALL)
_LINK_DESTINATION_PATTERN = re.compile(r"\]\(\s*(?P<destination><[^>\n]*>|[^)\s]+)")
_REFERENCE_DEFINITION_PATTERN = re.compile(
    r"^ {0,3}\[(?P<label>[^\]\n]+)\]:[ \t]*(?P<destination><[^>\n]*>|[^\s]+)",
    re.MULTILINE,
)
# Public security policy: destinations with these schemes never become links.
UNSAFE_SCHEMES = frozenset({"javascript", "vbscript", "data", "file"})
_NON_LINK_TOKEN_TYPES = frozenset({"fence", "code_block", "html_block"})


class DestinationKind(StrEnum):
    """Classification of a Markdown link destination.

    Attributes
    ----------
    INTERNAL : str
        A destination in one of the three internal reference schemes.
    EXTERNAL : str
        An absolute URL outside the application.
    ATTACHMENT : str
        A relative file or attachment path.
    ANCHOR : str
        A heading fragment within the same note.
    UNSAFE : str
        An active scheme that must never become a navigable internal target.
    """

    INTERNAL = "internal"
    EXTERNAL = "external"
    ATTACHMENT = "attachment"
    ANCHOR = "anchor"
    UNSAFE = "unsafe"


class ResolutionOutcome(StrEnum):
    """Outcome of looking up a reference in the name catalog.

    Attributes
    ----------
    RESOLVED : str
        Exactly one note matches the scheme and name.
    UNRESOLVED : str
        No note matches; the reference remains valid and may heal later.
    AMBIGUOUS : str
        More than one note matches; no target is selected.
    """

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceResolution:
    """Result of resolving one reference against a catalog.

    Attributes
    ----------
    reference : NoteReference
        Reference that was looked up.
    outcome : ResolutionOutcome
        Whether the lookup found zero, one, or many candidates.
    targets : tuple[Path, ...]
        Matching note paths in deterministic order. Empty when unresolved and
        containing every candidate when ambiguous.
    """

    reference: NoteReference
    outcome: ResolutionOutcome
    targets: tuple[Path, ...] = ()


def scheme_for_note_type(note_type: NoteType) -> ReferenceScheme:
    """Map a note type to the scheme that addresses it.

    Parameters
    ----------
    note_type : NoteType
        Type declared by the target note.

    Returns
    -------
    ReferenceScheme
        ``person`` for person notes, ``project`` for project notes, and
        ``note`` for the document family.
    """
    if note_type is NoteType.PERSON:
        return ReferenceScheme.PERSON
    if note_type is NoteType.PROJECT:
        return ReferenceScheme.PROJECT
    return ReferenceScheme.NOTE


@dataclasses.dataclass(frozen=True, slots=True)
class NameCatalog:
    """Deterministic catalog of note paths keyed by scheme and normalized name.

    Notes
    -----
    Build catalogs with :meth:`from_entries` rather than constructing the
    internal mapping by hand. A name may map to several paths when the vault
    contains duplicates; the catalog keeps every candidate so resolution can
    report ambiguity instead of choosing one. All note types in the document
    family share the ``note`` namespace.
    """

    _entries: dict[tuple[ReferenceScheme, str], tuple[Path, ...]]

    @classmethod
    def from_entries(
        cls,
        entries: Iterable[tuple[Path, NoteType]],
    ) -> Self:
        """Build a catalog from note paths and declared types.

        Parameters
        ----------
        entries : Iterable[tuple[Path, NoteType]]
            Note path and declared type for every note in the vault.

        Returns
        -------
        NameCatalog
            Catalog with normalized names, sorted candidate tuples, and
            deterministic iteration order. Names containing path syntax are
            ignored so they can never resolve.
        """
        grouped: dict[tuple[ReferenceScheme, str], list[Path]] = {}
        for path, note_type in entries:
            scheme = scheme_for_note_type(note_type)
            name = afanes.core.names.normalize_name(path.stem)
            if _has_path_syntax(name):
                continue
            grouped.setdefault((scheme, name), []).append(path)

        return cls(
            _entries={
                key: tuple(sorted(paths, key=_path_sort_key))
                for key, paths in sorted(grouped.items(), key=lambda item: (item[0][0].value, item[0][1]))
            }
        )

    def candidates(self, scheme: ReferenceScheme, name: str) -> tuple[Path, ...]:
        """Return every path matching a scheme and name.

        Parameters
        ----------
        scheme : ReferenceScheme
            Namespace to search.
        name : str
            Written name. Matching normalizes case, Unicode form, whitespace,
            and an optional ``.md`` extension.

        Returns
        -------
        tuple[Path, ...]
            Matching paths in deterministic order. Empty when the name is
            unknown or contains path syntax.
        """
        normalized = afanes.core.names.normalize_name(name)
        if _has_path_syntax(normalized):
            return ()
        return self._entries.get((scheme, normalized), ())

    def resolve(self, reference: NoteReference) -> ReferenceResolution:
        """Resolve a reference against this catalog.

        Parameters
        ----------
        reference : NoteReference
            Reference to resolve.

        Returns
        -------
        ReferenceResolution
            Resolved with one target, unresolved with none, or ambiguous with
            all candidates. Resolution never opens or stats a file.
        """
        targets = self.candidates(reference.scheme, reference.name)
        if not targets:
            return ReferenceResolution(reference=reference, outcome=ResolutionOutcome.UNRESOLVED)
        if len(targets) == 1:
            return ReferenceResolution(reference=reference, outcome=ResolutionOutcome.RESOLVED, targets=targets)
        return ReferenceResolution(reference=reference, outcome=ResolutionOutcome.AMBIGUOUS, targets=targets)


def parse_reference(destination: str) -> NoteReference:
    """Parse a typed scheme destination into a reference value object.

    Parameters
    ----------
    destination : str
        Raw Markdown destination, with or without surrounding angle brackets.
        Percent escapes are decoded because the CommonMark parser normalizes
        spaces and non-ASCII characters in link destinations.

    Returns
    -------
    NoteReference
        Reference with the canonical scheme and the written name. The label is
        always ``None``; extraction adds it from the link text.

    Raises
    ------
    InvalidReferenceError
        If the destination has no scheme, uses a scheme outside ``person``,
        ``project``, and ``note``, or carries an empty name.
    """
    value = _strip_destination(destination)
    value = urllib.parse.unquote(value)
    match = _SCHEME_PATTERN.match(value)
    if match is None:
        message = f"Not a scheme reference: {destination!r}"
        raise InvalidReferenceError(message)

    scheme_token = match.group("scheme")
    try:
        scheme = ReferenceScheme(scheme_token.casefold())
    except ValueError as exc:
        message = f"Unknown reference scheme: {scheme_token!r}"
        raise InvalidReferenceError(message) from exc

    name = match.group("name").strip()
    if not name:
        message = f"Reference name is empty: {destination!r}"
        raise InvalidReferenceError(message)
    return NoteReference(scheme=scheme, name=name)


def classify_destination(destination: str) -> DestinationKind:
    """Classify a Markdown destination without resolving it.

    Parameters
    ----------
    destination : str
        Raw destination, optionally wrapped in angle brackets.

    Returns
    -------
    DestinationKind
        Internal reference, external URL, attachment path, anchor, or unsafe
        active scheme.

    Notes
    -----
    Only the three internal schemes produce :attr:`DestinationKind.INTERNAL`.
    Active schemes such as ``javascript:`` are classified as unsafe so no
    caller can turn them into a navigable internal target.
    """
    value = _strip_destination(destination)
    if value.startswith("#"):
        return DestinationKind.ANCHOR
    if value.startswith("//"):
        return DestinationKind.EXTERNAL

    match = _SCHEME_PATTERN.match(value)
    if match is None:
        return DestinationKind.ATTACHMENT

    scheme = match.group("scheme").casefold()
    if _internal_scheme(scheme) is not None:
        return DestinationKind.INTERNAL
    if scheme in UNSAFE_SCHEMES:
        return DestinationKind.UNSAFE
    return DestinationKind.EXTERNAL


class ReferenceReader:
    """Extract internal references from Markdown with one configured parser.

    Notes
    -----
    Reuse one reader for a batch of documents. The parser is not shared across
    threads or scans; create a reader per batch.
    """

    def __init__(self) -> None:
        """Create a reader backed by a CommonMark parser."""
        self._parser = MarkdownIt("commonmark")

    def extract(self, markdown: str) -> list[NoteReference]:
        """Extract every internal reference from Markdown body text.

        Parameters
        ----------
        markdown : str
            Note body without frontmatter.

        Returns
        -------
        list[NoteReference]
            References in document order, each carrying its link label when
            the label is not empty.

        Raises
        ------
        InvalidReferenceError
            If an internal destination is malformed, for example ``note:``
            with an empty name.

        Notes
        -----
        Extraction uses a CommonMark parser, so references inside fenced code,
        indented code, inline code, HTML comments, and images are ignored.
        Image destinations never become references.
        """
        references: list[NoteReference] = []
        for token in self._parser.parse(markdown):
            if token.type != "inline" or token.children is None:
                continue
            references.extend(_references_in_children(token.children))
        return references


def reference_key(reference: NoteReference) -> tuple[ReferenceScheme, str]:
    """Return the normalized lookup key for a reference.

    Parameters
    ----------
    reference : NoteReference
        Reference to normalize.

    Returns
    -------
    tuple[ReferenceScheme, str]
        Scheme plus normalized name, suitable as a catalog key.
    """
    return (reference.scheme, afanes.core.names.normalize_name(reference.name))


def rewrite_body_references(markdown: str, old: NoteReference, new: NoteReference) -> tuple[str, int]:
    """Rewrite body destinations that resolve to one reference name.

    Parameters
    ----------
    markdown : str
        Note body without frontmatter.
    old : NoteReference
        Reference whose scheme and name identify the destinations to change.
        The label is ignored; only labels exactly equal to ``old.name`` are
        updated.
    new : NoteReference
        Replacement scheme and name. Only ``new.name`` is written into the
        destination; the old label is kept unless it equals ``old.name``.

    Returns
    -------
    tuple[str, int]
        Rewritten Markdown and the number of destinations changed.

    Raises
    ------
    ReferenceRewriteError
        If the result still contains a reference to the old scheme and name,
        or if verification cannot parse the rewritten body.

    Notes
    -----
    Fenced code, indented code, inline code, HTML comments, and images are
    skipped. Angle-bracketed destinations stay angle-bracketed; bare
    destinations percent-encode characters that CommonMark cannot carry.
    Reference-style definitions are rewritten, but their usage labels are not.
    """
    old_key = reference_key(old)
    masked = _masked_spans(markdown)
    inline_edits, inline_count = _collect_inline_edits(markdown, masked, old, new)
    definition_edits, definition_count = _collect_definition_edits(markdown, masked, old, new)
    edits = inline_edits + definition_edits
    replacements = inline_count + definition_count

    if not edits:
        return markdown, 0

    rewritten = _apply_edits(markdown, edits)
    try:
        remaining = ReferenceReader().extract(rewritten)
    except InvalidReferenceError as exc:
        message = "Rewritten body is no longer valid Markdown"
        raise ReferenceRewriteError(message) from exc

    if any(reference_key(reference) == old_key for reference in remaining):
        message = "Rewritten body still contains the old reference"
        raise ReferenceRewriteError(message)
    return rewritten, replacements


def _has_path_syntax(name: str) -> bool:
    """Return whether a name contains a path separator or is a traversal segment."""
    return "/" in name or "\\" in name or name.strip() == ".."


def _internal_scheme(token: str) -> ReferenceScheme | None:
    """Return the internal scheme for a token, or ``None``."""
    try:
        return ReferenceScheme(token)
    except ValueError:
        return None


def _strip_destination(destination: str) -> str:
    """Trim whitespace and one pair of angle brackets."""
    value = destination.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    return value


def _references_in_children(children: Sequence[Token]) -> list[NoteReference]:
    """Extract references from one inline token's children."""
    references: list[NoteReference] = []
    index = 0
    while index < len(children):
        token = children[index]
        if token.type != "link_open":
            index += 1
            continue

        href = token.attrGet("href")
        if not isinstance(href, str) or classify_destination(href) is not DestinationKind.INTERNAL:
            index += 1
            continue

        label, index = _link_label(children, index + 1)
        reference = parse_reference(href)
        references.append(dataclasses.replace(reference, label=label or None))
    return references


def _link_label(
    children: Sequence[Token],
    start: int,
) -> tuple[str, int]:
    """Collect the rendered label of a link and the index after it."""
    parts: list[str] = []
    index = start
    while index < len(children):
        token = children[index]
        if token.type == "link_close":
            return "".join(parts), index + 1
        if token.type in {"text", "code_inline", "image"}:
            parts.append(token.content)
        index += 1
    return "".join(parts), index


def _path_sort_key(path: Path) -> str:
    """Return a platform-independent deterministic sort key."""
    return path.as_posix()


@dataclasses.dataclass(frozen=True, slots=True)
class _Edit:
    """One replacement span in a Markdown document."""

    start: int
    end: int
    replacement: str


def _collect_inline_edits(
    markdown: str,
    masked: Sequence[tuple[int, int]],
    old: NoteReference,
    new: NoteReference,
) -> tuple[list[_Edit], int]:
    """Collect destination and default-label edits for inline links."""
    old_key = reference_key(old)
    edits: list[_Edit] = []
    replacements = 0
    for match in _LINK_DESTINATION_PATTERN.finditer(markdown):
        if _is_masked(masked, match.start()) or _is_escaped(markdown, match.start()):
            continue
        label_start = _find_label_start(markdown, match.start())
        if label_start is None or _is_escaped(markdown, label_start):
            continue
        if _is_image_label(markdown, label_start):
            continue

        replacement = _rewritten_destination(match.group("destination"), old_key, new)
        if replacement is None:
            continue

        edits.append(_Edit(match.start("destination"), match.end("destination"), replacement))
        replacements += 1
        if markdown[label_start + 1 : match.start()] == old.name and old.name != new.name:
            edits.append(_Edit(label_start + 1, match.start(), new.name))
    return edits, replacements


def _collect_definition_edits(
    markdown: str,
    masked: Sequence[tuple[int, int]],
    old: NoteReference,
    new: NoteReference,
) -> tuple[list[_Edit], int]:
    """Collect destination edits for reference-style link definitions."""
    old_key = reference_key(old)
    edits: list[_Edit] = []
    replacements = 0
    for match in _REFERENCE_DEFINITION_PATTERN.finditer(markdown):
        if _is_masked(masked, match.start()):
            continue
        replacement = _rewritten_destination(match.group("destination"), old_key, new)
        if replacement is None:
            continue
        edits.append(_Edit(match.start("destination"), match.end("destination"), replacement))
        replacements += 1
    return edits, replacements


def _rewritten_destination(
    destination: str,
    old_key: tuple[ReferenceScheme, str],
    new: NoteReference,
) -> str | None:
    """Return a replacement destination when it names the old reference."""
    try:
        reference = parse_reference(destination)
    except InvalidReferenceError:
        return None
    if reference_key(reference) != old_key:
        return None

    stripped = destination.strip()
    if stripped.startswith("<") and stripped.endswith(">"):
        return f"<{new.scheme.value}:{new.name}>"
    encoded_name = urllib.parse.quote(new.name, safe="")
    return f"{new.scheme.value}:{encoded_name}"


def _apply_edits(markdown: str, edits: Sequence[_Edit]) -> str:
    """Apply non-overlapping edits from the end of the document backwards."""
    rewritten = markdown
    for edit in sorted(edits, key=lambda item: item.start, reverse=True):
        rewritten = f"{rewritten[: edit.start]}{edit.replacement}{rewritten[edit.end :]}"
    return rewritten


def _is_escaped(markdown: str, position: int) -> bool:
    """Return whether the character at a position is backslash-escaped."""
    backslashes = 0
    cursor = position - 1
    while cursor >= 0 and markdown[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def _is_image_label(markdown: str, label_start: int) -> bool:
    """Return whether a label is preceded by an unescaped image marker."""
    if label_start == 0 or markdown[label_start - 1] != "!":
        return False
    return not _is_escaped(markdown, label_start - 1)


def _find_label_start(markdown: str, close_index: int) -> int | None:
    """Find the opening bracket that matches a link label's closing bracket."""
    depth = 0
    index = close_index
    while index >= 0:
        if _is_escaped(markdown, index):
            index -= 1
            continue
        character = markdown[index]
        if character == "]":
            depth += 1
        elif character == "[":
            depth -= 1
            if depth == 0:
                return index
        index -= 1
    return None


def _masked_spans(markdown: str) -> list[tuple[int, int]]:
    """Return merged source spans where link syntax has no effect."""
    block_spans = _block_spans(markdown)
    spans = _merge_spans(block_spans)
    index = 0
    while index < len(markdown):
        containing = _containing_span(spans, index)
        if containing is not None:
            index = containing[1]
            continue

        if markdown.startswith("<!--", index):
            comment_end = markdown.find("-->", index + 4)
            end = len(markdown) if comment_end == -1 else comment_end + 3
            spans.append((index, end))
            index = end
            continue

        if markdown[index] == "`" and not _is_escaped(markdown, index):
            run = _backtick_run(markdown, index)
            closing = _find_closing_backticks(markdown, index + run, run)
            if closing is None:
                index += run
                continue
            spans.append((index, closing + run))
            index = closing + run
            continue

        index += 1

    return _merge_spans(spans)


def _block_spans(markdown: str) -> list[tuple[int, int]]:
    """Return source spans of parser-identified code and HTML blocks."""
    offsets = _line_offsets(markdown)
    last = len(offsets) - 1
    spans: list[tuple[int, int]] = []
    parser = MarkdownIt("commonmark")
    for token in parser.parse(markdown):
        if token.type not in _NON_LINK_TOKEN_TYPES or token.map is None:
            continue
        start_line, end_line = token.map
        spans.append((offsets[min(start_line, last)], offsets[min(end_line, last)]))
    return spans


def _line_offsets(markdown: str) -> list[int]:
    """Return the source offset of every line boundary."""
    offsets = [0]
    for line in markdown.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _backtick_run(markdown: str, start: int) -> int:
    """Return the length of a run of backticks starting at a position."""
    end = start
    while end < len(markdown) and markdown[end] == "`":
        end += 1
    return end - start


def _find_closing_backticks(markdown: str, start: int, length: int) -> int | None:
    """Find a backtick run of exactly ``length`` at or after ``start``."""
    index = start
    while index < len(markdown):
        if markdown[index] != "`":
            index += 1
            continue
        run = _backtick_run(markdown, index)
        if run == length:
            return index
        index += run
    return None


def _merge_spans(spans: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Sort and merge overlapping source spans."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _containing_span(spans: Sequence[tuple[int, int]], position: int) -> tuple[int, int] | None:
    """Return the merged span containing a position, if any."""
    for start, end in spans:
        if start <= position < end:
            return (start, end)
    return None


def _is_masked(spans: Sequence[tuple[int, int]], position: int) -> bool:
    """Return whether a position falls inside a masked span."""
    return _containing_span(spans, position) is not None
