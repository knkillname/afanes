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
from afanes.models.note import NoteType, ReferenceCategory

_SCHEME_PATTERN = re.compile(r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.\-]*):(?P<name>.*)$", re.DOTALL)
_LINK_DESTINATION_PATTERN = re.compile(r"\]\(\s*(?P<destination><[^>\n]*>|[^)\s]+)")
_REFERENCE_DEFINITION_PATTERN = re.compile(
    r"^ {0,3}\[(?P<label>[^\]\n]+)\]:[ \t]*(?P<destination><[^>\n]*>|[^\s]+)",
    re.MULTILINE,
)
# Public security policy: destinations with these schemes never become links.
UNSAFE_SCHEMES = frozenset({"javascript", "vbscript", "data", "file"})
_NON_LINK_TOKEN_TYPES = frozenset({"fence", "code_block", "html_block"})


@dataclasses.dataclass(frozen=True, slots=True)
class DestinationText:
    """One Markdown link destination.

    Attributes
    ----------
    raw : str
        Destination exactly as written, optionally wrapped in angle brackets.
    """

    raw: str

    @property
    def stripped(self) -> str:
        """Return the destination without surrounding whitespace or brackets.

        Returns
        -------
        str
            Trimmed destination. One leading ``<`` and one trailing ``>`` are
            removed when both are present.
        """
        value = self.raw.strip()
        if value.startswith("<") and value.endswith(">"):
            value = value[1:-1].strip()
        return value


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

    @classmethod
    def classify(cls, destination: str) -> "DestinationKind":
        """Classify a Markdown destination without resolving it.

        Parameters
        ----------
        destination : str
            Raw destination, optionally wrapped in angle brackets.

        Returns
        -------
        DestinationKind
            Internal reference, external URL, attachment path, anchor, or
            unsafe active scheme.

        Notes
        -----
        Only the three internal schemes produce :attr:`DestinationKind.INTERNAL`.
        Active schemes such as ``javascript:`` are classified as unsafe so no
        caller can turn them into a navigable internal target.
        """
        value = DestinationText(destination).stripped
        if value.startswith("#"):
            return cls.ANCHOR
        if value.startswith("//"):
            return cls.EXTERNAL

        match = _SCHEME_PATTERN.match(value)
        if match is None:
            return cls.ATTACHMENT

        scheme = match.group("scheme").casefold()
        if cls._internal_scheme(scheme) is not None:
            return cls.INTERNAL
        if scheme in UNSAFE_SCHEMES:
            return cls.UNSAFE
        return cls.EXTERNAL

    @staticmethod
    def _internal_scheme(token: str) -> ReferenceScheme | None:
        """Return the internal scheme for a token, or ``None``."""
        try:
            return ReferenceScheme(token)
        except ValueError:
            return None


class ReferenceParser:
    """Parse scheme destinations into reference value objects.

    Notes
    -----
    The parser is stateless apart from the compiled scheme pattern it carries.
    Reuse one parser for a batch of destinations or create one per call.
    """

    def __init__(self) -> None:
        """Create a parser backed by the canonical scheme pattern."""
        self._pattern = _SCHEME_PATTERN

    def parse(self, destination: str) -> NoteReference:
        """Parse one typed scheme destination.

        Parameters
        ----------
        destination : str
            Raw Markdown destination, with or without surrounding angle
            brackets. Percent escapes are decoded because the CommonMark parser
            normalizes spaces and non-ASCII characters in link destinations.

        Returns
        -------
        NoteReference
            Reference with the canonical scheme and the written name. The label
            is always ``None``; extraction adds it from the link text.

        Raises
        ------
        InvalidReferenceError
            If the destination has no scheme, uses a scheme outside ``person``,
            ``project``, and ``note``, or carries an empty name.
        """
        value = urllib.parse.unquote(DestinationText(destination).stripped)
        match = self._pattern.match(value)
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


@dataclasses.dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One note offered to a name catalog.

    Attributes
    ----------
    path : Path
        Note path. Its stem is the identity indexed by the catalog.
    note_type : NoteType
        Declared note type.
    category : ReferenceCategory | None
        Reference category, or ``None`` for an uncategorized reference or a
        non-reference note.
    """

    path: Path
    note_type: NoteType
    category: ReferenceCategory | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceKey:
    """Normalized lookup key for one reference.

    Attributes
    ----------
    scheme : ReferenceScheme
        Namespace the reference addresses.
    name : str
        Name normalized with :func:`afanes.core.names.normalize_name`.
    """

    scheme: ReferenceScheme
    name: str

    @classmethod
    def from_reference(cls, reference: NoteReference) -> Self:
        """Build a normalized key from a written reference.

        Parameters
        ----------
        reference : NoteReference
            Reference to normalize. The label is ignored.

        Returns
        -------
        ReferenceKey
            Scheme plus normalized name, suitable as a catalog key and for
            equality checks during reference rewriting.
        """
        return cls(scheme=reference.scheme, name=afanes.core.names.normalize_name(reference.name))


@dataclasses.dataclass(frozen=True, slots=True)
class NameCatalog:
    """Deterministic catalog of note paths keyed by scheme and normalized name.

    Notes
    -----
    Build catalogs with :meth:`from_entries` rather than constructing the
    internal mapping by hand. A name may map to several paths when the vault
    contains duplicates; the catalog keeps every candidate so resolution can
    report ambiguity instead of choosing one. ``note``, ``action``, and
    uncategorized references share the ``note`` namespace; a categorized
    reference belongs only to its category scheme.
    """

    _entries: dict[ReferenceKey, tuple[Path, ...]]

    @staticmethod
    def _has_path_syntax(name: str) -> bool:
        """Return whether a name contains a path separator or traversal segment."""
        return "/" in name or "\\" in name or name.strip() == ".."

    @staticmethod
    def _path_sort_key(path: Path) -> str:
        """Return a platform-independent deterministic sort key."""
        return path.as_posix()

    @classmethod
    def from_entries(
        cls,
        entries: Iterable[CatalogEntry],
    ) -> Self:
        """Build a catalog from note entries.

        Parameters
        ----------
        entries : Iterable[CatalogEntry]
            Note path, declared type, and optional reference category for
            every note in the vault.

        Returns
        -------
        NameCatalog
            Catalog with normalized names, sorted candidate tuples, and
            deterministic iteration order. Names containing path syntax are
            ignored so they can never resolve. Each note is indexed under
            exactly one scheme.
        """
        grouped: dict[ReferenceKey, list[Path]] = {}
        for entry in entries:
            scheme = ReferenceScheme.for_note(entry.note_type, entry.category)
            name = afanes.core.names.normalize_name(entry.path.stem)
            if NameCatalog._has_path_syntax(name):
                continue
            grouped.setdefault(ReferenceKey(scheme=scheme, name=name), []).append(entry.path)

        return cls(
            _entries={
                key: tuple(sorted(paths, key=NameCatalog._path_sort_key))
                for key, paths in sorted(grouped.items(), key=lambda item: (item[0].scheme.value, item[0].name))
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
        if NameCatalog._has_path_syntax(normalized):
            return ()
        return self._entries.get(ReferenceKey(scheme=scheme, name=normalized), ())

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


@dataclasses.dataclass(frozen=True, slots=True)
class SourceSpan:
    """Half-open source range in a Markdown document.

    Attributes
    ----------
    start : int
        Offset of the first character in the span.
    end : int
        Offset one past the last character in the span.
    """

    start: int
    end: int

    def contains(self, position: int) -> bool:
        """Return whether a source offset falls inside this span.

        Parameters
        ----------
        position : int
            Source offset to test.

        Returns
        -------
        bool
            ``True`` when ``start <= position < end``.
        """
        return self.start <= position < self.end


@dataclasses.dataclass(frozen=True, slots=True)
class MarkdownEdit:
    """One replacement span in a Markdown document.

    Attributes
    ----------
    start : int
        Source offset where the replaced text begins.
    end : int
        Source offset where the replaced text ends.
    replacement : str
        Text written in place of ``start:end``.
    """

    start: int
    end: int
    replacement: str


@dataclasses.dataclass(frozen=True, slots=True)
class EditBatch:
    """Edits collected by one rewriting pass.

    Attributes
    ----------
    edits : tuple[MarkdownEdit, ...]
        Replacements in source order.
    count : int
        Number of destinations the batch changes.
    """

    edits: tuple[MarkdownEdit, ...]
    count: int

    def extend(self, other: "EditBatch") -> "EditBatch":
        """Return a batch with another batch's edits appended.

        Parameters
        ----------
        other : EditBatch
            Batch to append after this one.

        Returns
        -------
        EditBatch
            Combined edits and counts. The operands are unchanged.
        """
        return EditBatch(edits=(*self.edits, *other.edits), count=self.count + other.count)


@dataclasses.dataclass(frozen=True, slots=True)
class LinkLabel:
    """Rendered label of one Markdown link and the next token index.

    Attributes
    ----------
    text : str
        Concatenated text, code, and image content inside the link label.
    next_index : int
        Index of the first token after the closing link token.
    """

    text: str
    next_index: int


@dataclasses.dataclass(frozen=True, slots=True)
class MarkdownRewrite:
    """Result of rewriting references in one Markdown body.

    Attributes
    ----------
    text : str
        Rewritten Markdown.
    count : int
        Number of destinations changed.
    """

    text: str
    count: int


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
        self._reference_parser = ReferenceParser()

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
            references.extend(self._references_in_children(token.children))
        return references

    def _references_in_children(self, children: Sequence[Token]) -> list[NoteReference]:
        """Extract references from one inline token's children."""
        references: list[NoteReference] = []
        index = 0
        while index < len(children):
            token = children[index]
            if token.type != "link_open":
                index += 1
                continue

            href = token.attrGet("href")
            if not isinstance(href, str) or DestinationKind.classify(href) is not DestinationKind.INTERNAL:
                index += 1
                continue

            label = self._link_label(children, index + 1)
            index = label.next_index
            reference = self._reference_parser.parse(href)
            references.append(dataclasses.replace(reference, label=label.text or None))
        return references

    @staticmethod
    def _link_label(
        children: Sequence[Token],
        start: int,
    ) -> LinkLabel:
        """Collect the rendered label of a link and the index after it."""
        parts: list[str] = []
        index = start
        while index < len(children):
            token = children[index]
            if token.type == "link_close":
                return LinkLabel(text="".join(parts), next_index=index + 1)
            if token.type in {"text", "code_inline", "image"}:
                parts.append(token.content)
            index += 1
        return LinkLabel(text="".join(parts), next_index=index)


class MarkdownBody:
    """One Markdown body that owns reference rewriting.

    Parameters
    ----------
    markdown : str
        Note body without frontmatter.

    Notes
    -----
    The object is immutable after construction. Rewriting performs no file I/O
    and keeps every operation on the body it owns.
    """

    def __init__(self, markdown: str) -> None:
        """Store the Markdown body this object owns.

        Parameters
        ----------
        markdown : str
            Note body without frontmatter.
        """
        self._markdown = markdown

    def rewrite_references(self, old: NoteReference, new: NoteReference) -> MarkdownRewrite:
        """Rewrite destinations that resolve to one reference name.

        Parameters
        ----------
        old : NoteReference
            Reference whose scheme and name identify the destinations to
            change. The label is ignored; only labels exactly equal to
            ``old.name`` are updated.
        new : NoteReference
            Replacement scheme and name. Only ``new.name`` is written into the
            destination; the old label is kept unless it equals ``old.name``.

        Returns
        -------
        MarkdownRewrite
            Rewritten Markdown and the number of destinations changed.

        Raises
        ------
        ReferenceRewriteError
            If the result still contains a reference to the old scheme and
            name, or if verification cannot parse the rewritten body.

        Notes
        -----
        Fenced code, indented code, inline code, HTML comments, and images are
        skipped. Angle-bracketed destinations stay angle-bracketed; bare
        destinations percent-encode characters that CommonMark cannot carry.
        Reference-style definitions are rewritten, but their usage labels are
        not.
        """
        old_key = ReferenceKey.from_reference(old)
        masked = self._masked_spans()
        batch = self._collect_inline_edits(masked, old, new).extend(self._collect_definition_edits(masked, old, new))

        if not batch.edits:
            return MarkdownRewrite(text=self._markdown, count=0)

        rewritten = self._apply_edits(batch.edits)
        try:
            remaining = ReferenceReader().extract(rewritten)
        except InvalidReferenceError as exc:
            message = "Rewritten body is no longer valid Markdown"
            raise ReferenceRewriteError(message) from exc

        if any(ReferenceKey.from_reference(reference) == old_key for reference in remaining):
            message = "Rewritten body still contains the old reference"
            raise ReferenceRewriteError(message)
        return MarkdownRewrite(text=rewritten, count=batch.count)

    def _collect_inline_edits(
        self,
        masked: Sequence[SourceSpan],
        old: NoteReference,
        new: NoteReference,
    ) -> EditBatch:
        """Collect destination and default-label edits for inline links."""
        old_key = ReferenceKey.from_reference(old)
        edits: list[MarkdownEdit] = []
        replacements = 0
        for match in _LINK_DESTINATION_PATTERN.finditer(self._markdown):
            if self._is_masked(masked, match.start()) or self._is_escaped(match.start()):
                continue
            label_start = self._find_label_start(match.start())
            if label_start is None or self._is_escaped(label_start):
                continue
            if self._is_image_label(label_start):
                continue

            replacement = self._rewritten_destination(match.group("destination"), old_key, new)
            if replacement is None:
                continue

            edits.append(MarkdownEdit(match.start("destination"), match.end("destination"), replacement))
            replacements += 1
            if self._markdown[label_start + 1 : match.start()] == old.name and old.name != new.name:
                edits.append(MarkdownEdit(label_start + 1, match.start(), new.name))
        return EditBatch(edits=tuple(edits), count=replacements)

    def _collect_definition_edits(
        self,
        masked: Sequence[SourceSpan],
        old: NoteReference,
        new: NoteReference,
    ) -> EditBatch:
        """Collect destination edits for reference-style link definitions."""
        old_key = ReferenceKey.from_reference(old)
        edits: list[MarkdownEdit] = []
        replacements = 0
        for match in _REFERENCE_DEFINITION_PATTERN.finditer(self._markdown):
            if self._is_masked(masked, match.start()):
                continue
            replacement = self._rewritten_destination(match.group("destination"), old_key, new)
            if replacement is None:
                continue
            edits.append(MarkdownEdit(match.start("destination"), match.end("destination"), replacement))
            replacements += 1
        return EditBatch(edits=tuple(edits), count=replacements)

    @staticmethod
    def _rewritten_destination(
        destination: str,
        old_key: ReferenceKey,
        new: NoteReference,
    ) -> str | None:
        """Return a replacement destination when it names the old reference."""
        try:
            reference = ReferenceParser().parse(destination)
        except InvalidReferenceError:
            return None
        if ReferenceKey.from_reference(reference) != old_key:
            return None

        stripped = destination.strip()
        if stripped.startswith("<") and stripped.endswith(">"):
            return f"<{new.scheme.value}:{new.name}>"
        encoded_name = urllib.parse.quote(new.name, safe="")
        return f"{new.scheme.value}:{encoded_name}"

    def _apply_edits(self, edits: Sequence[MarkdownEdit]) -> str:
        """Apply non-overlapping edits from the end of the document backwards."""
        rewritten = self._markdown
        for edit in sorted(edits, key=lambda item: item.start, reverse=True):
            rewritten = f"{rewritten[: edit.start]}{edit.replacement}{rewritten[edit.end :]}"
        return rewritten

    def _is_escaped(self, position: int) -> bool:
        """Return whether the character at a position is backslash-escaped."""
        backslashes = 0
        cursor = position - 1
        while cursor >= 0 and self._markdown[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        return backslashes % 2 == 1

    def _is_image_label(self, label_start: int) -> bool:
        """Return whether a label is preceded by an unescaped image marker."""
        if label_start == 0 or self._markdown[label_start - 1] != "!":
            return False
        return not self._is_escaped(label_start - 1)

    def _find_label_start(self, close_index: int) -> int | None:
        """Find the opening bracket that matches a link label's closing bracket."""
        depth = 0
        index = close_index
        while index >= 0:
            if self._is_escaped(index):
                index -= 1
                continue
            character = self._markdown[index]
            if character == "]":
                depth += 1
            elif character == "[":
                depth -= 1
                if depth == 0:
                    return index
            index -= 1
        return None

    def _masked_spans(self) -> list[SourceSpan]:
        """Return merged source spans where link syntax has no effect."""
        spans = self._merge_spans(self._block_spans())
        index = 0
        while index < len(self._markdown):
            containing = self._containing_span(spans, index)
            if containing is not None:
                index = containing.end
                continue

            if self._markdown.startswith("<!--", index):
                comment_end = self._markdown.find("-->", index + 4)
                end = len(self._markdown) if comment_end == -1 else comment_end + 3
                spans.append(SourceSpan(index, end))
                index = end
                continue

            if self._markdown[index] == "`" and not self._is_escaped(index):
                run = self._backtick_run(index)
                closing = self._find_closing_backticks(index + run, run)
                if closing is None:
                    index += run
                    continue
                spans.append(SourceSpan(index, closing + run))
                index = closing + run
                continue

            index += 1

        return self._merge_spans(spans)

    def _block_spans(self) -> list[SourceSpan]:
        """Return source spans of parser-identified code and HTML blocks."""
        offsets = self._line_offsets()
        last = len(offsets) - 1
        spans: list[SourceSpan] = []
        parser = MarkdownIt("commonmark")
        for token in parser.parse(self._markdown):
            if token.type not in _NON_LINK_TOKEN_TYPES or token.map is None:
                continue
            start_line, end_line = token.map
            spans.append(SourceSpan(offsets[min(start_line, last)], offsets[min(end_line, last)]))
        return spans

    def _line_offsets(self) -> list[int]:
        """Return the source offset of every line boundary."""
        offsets = [0]
        for line in self._markdown.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        return offsets

    def _backtick_run(self, start: int) -> int:
        """Return the length of a run of backticks starting at a position."""
        end = start
        while end < len(self._markdown) and self._markdown[end] == "`":
            end += 1
        return end - start

    def _find_closing_backticks(self, start: int, length: int) -> int | None:
        """Find a backtick run of exactly ``length`` at or after ``start``."""
        index = start
        while index < len(self._markdown):
            if self._markdown[index] != "`":
                index += 1
                continue
            run = self._backtick_run(index)
            if run == length:
                return index
            index += run
        return None

    @staticmethod
    def _merge_spans(spans: Iterable[SourceSpan]) -> list[SourceSpan]:
        """Sort and merge overlapping source spans."""
        merged: list[SourceSpan] = []
        for span in sorted(spans, key=lambda item: (item.start, item.end)):
            if span.end <= span.start:
                continue
            if merged and span.start <= merged[-1].end:
                merged[-1] = SourceSpan(merged[-1].start, max(merged[-1].end, span.end))
            else:
                merged.append(span)
        return merged

    @staticmethod
    def _containing_span(spans: Sequence[SourceSpan], position: int) -> SourceSpan | None:
        """Return the merged span containing a position, if any."""
        for span in spans:
            if span.contains(position):
                return span
        return None

    @staticmethod
    def _is_masked(spans: Sequence[SourceSpan], position: int) -> bool:
        """Return whether a position falls inside a masked span."""
        return MarkdownBody._containing_span(spans, position) is not None
