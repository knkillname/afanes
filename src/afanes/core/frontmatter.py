# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frontmatter-aware note documents.

The module exposes one cohesive value object, :class:`NoteDocument`, which
owns fence parsing, safe YAML loading, serialization, and reference rewriting.
Keeping those behaviors together preserves the document's invariants: metadata,
body, newline style, declared type, and references always travel as one unit.
"""

import dataclasses
from typing import Self

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token
from yaml import YAMLError

from afanes.core.errors import InvalidReferenceError, NoteParseError
from afanes.core.links import ReferenceKey, ReferenceParser
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

# Public canonical frontmatter delimiter.
FRONTMATTER_FENCE = "---"


@dataclasses.dataclass(frozen=True, slots=True)
class FrontmatterSplit:
    """Source split produced by the frontmatter fence parser.

    Attributes
    ----------
    raw : dict[str, object]
        Loaded frontmatter mapping, empty when no fence block is present.
    body : str
        Markdown body after the closing fence, or the complete source when no
        frontmatter is present.
    has_frontmatter : bool
        Whether the source began with a complete fence block.
    """

    raw: dict[str, object]
    body: str
    has_frontmatter: bool


@dataclasses.dataclass(frozen=True, slots=True)
class NoteDocument:
    """One note split into frontmatter metadata and Markdown body.

    Attributes
    ----------
    raw : dict[str, object]
        Frontmatter mapping exactly as loaded, including unknown keys.
    body : str
        Markdown body after the closing fence, with its original newlines.
    newline : str
        Newline sequence used by the document: LF or CRLF.
    has_frontmatter : bool
        Whether the source began with a complete ``---`` fence block.
    note_type : NoteType | None
        Declared type, or ``None`` when the note has no ``type`` key.
    references : tuple[NoteReference, ...]
        References declared by the ``people`` and ``project`` values.
    category : ReferenceCategory | None
        Reference category, or ``None`` for an uncategorized reference or a
        non-reference note.
    status : Status | None
        Validated workflow status, or ``None`` when the key is absent.

    Notes
    -----
    Use :meth:`from_text` to build a validated document from source. The raw
    mapping is kept so a rewrite can preserve unknown keys; callers receive a
    fresh copy from the parser.
    """

    raw: dict[str, object]
    body: str
    newline: str
    has_frontmatter: bool
    note_type: NoteType | None
    references: tuple[NoteReference, ...]
    category: ReferenceCategory | None = None
    status: Status | None = None

    @classmethod
    def from_text(cls, text: str) -> Self:
        """Parse a Markdown note with optional YAML frontmatter.

        Parameters
        ----------
        text : str
            Complete note source. A leading UTF-8 BOM is not interpreted as a
            fence and is left in the body.

        Returns
        -------
        NoteDocument
            Raw metadata, body, newline style, declared type, and frontmatter
            references.

        Raises
        ------
        NoteParseError
            If the opening fence is never closed, the YAML is malformed or is
            not a mapping, a key is not a string, the declared type is unknown,
            the category is invalid or misplaced, or the status is unknown or
            not valid for the declared type.
        InvalidReferenceError
            If ``people`` or ``project`` is not made of valid scheme
            references.

        Notes
        -----
        Frontmatter exists only when the first line is exactly ``---``. A body
        that later begins with ``---`` is ordinary content and is preserved.
        """
        split = cls._split_frontmatter(text)
        newline = "\r\n" if "\r\n" in text else "\n"
        note_type = cls._declared_note_type(split.raw)
        category = cls._declared_category(split.raw, note_type)
        status = cls._declared_status(split.raw, note_type)
        return cls(
            raw=split.raw,
            body=split.body,
            newline=newline,
            has_frontmatter=split.has_frontmatter,
            note_type=note_type,
            references=cls._references_from_raw(split.raw),
            category=category,
            status=status,
        )

    def to_text(self) -> str:
        """Serialize the document back to Markdown.

        Returns
        -------
        str
            Markdown with the document's original newline style. A document
            that had no frontmatter is returned as its body alone.

        Notes
        -----
        Rewriting the frontmatter block re-emits it from the raw mapping, so
        YAML comments inside that block are not preserved. Unknown keys and
        their order are preserved.
        """
        if not self.has_frontmatter:
            return self.body

        yaml_text = yaml.safe_dump(
            self.raw,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
        yaml_text = yaml_text.replace("\r\n", "\n")
        if not yaml_text.endswith("\n"):
            yaml_text = f"{yaml_text}\n"
        yaml_text = yaml_text.replace("\n", self.newline)
        return f"{FRONTMATTER_FENCE}{self.newline}{yaml_text}{FRONTMATTER_FENCE}{self.newline}{self.body}"

    def with_body(self, body: str) -> Self:
        """Return a copy with a replaced Markdown body.

        Parameters
        ----------
        body : str
            New body text. Frontmatter metadata and newline style are kept.

        Returns
        -------
        NoteDocument
            New document instance; the original is unchanged.
        """
        return dataclasses.replace(self, body=body)

    def with_heading(self, text: str) -> Self:
        """Return a copy with its first level-1 heading replaced.

        Parameters
        ----------
        text : str
            New heading text. Surrounding whitespace is trimmed and the heading
            is written in ATX form.

        Returns
        -------
        NoteDocument
            New document with the first level-1 heading replaced. Content
            before and after the heading is preserved.

        Raises
        ------
        NoteParseError
            If the body has no level-1 heading.

        Notes
        -----
        Heading detection uses the CommonMark parser, so a line inside a code
        block is not a heading. A setext heading is replaced with an ATX
        heading at the same line position, and the document's newline style is
        preserved.
        """
        tokens = MarkdownIt("commonmark").parse(self.body)
        for token in tokens:
            if token.type != "heading_open" or token.tag != "h1":
                continue
            line_map = token.map
            if line_map is None:
                break
            start, end = line_map
            lines = self.body.splitlines(keepends=True)
            if start < 0 or end > len(lines) or start >= end:
                break
            trailing = lines[end - 1].endswith(("\n", "\r"))
            replacement = f"# {text.strip()}"
            if trailing:
                replacement += self.newline
            lines[start:end] = [replacement]
            return self.with_body("".join(lines))
        message = "Note has no level-1 heading"
        raise NoteParseError(message)

    @property
    def title(self) -> str | None:
        """Return the display title derived from the first level-1 heading.

        Returns
        -------
        str | None
            Trimmed plain text of the first level-1 heading in :attr:`body`, or
            ``None`` when the body has no level-1 heading or its first level-1
            heading has blank text.

        Notes
        -----
        The title is derived from the body on every access and is never stored
        in frontmatter. Setext headings count, and inline formatting is
        flattened to text. A heading inside a fenced or indented code block is
        ignored. A blank first heading does not fall through to a later
        heading. The value is display-only; it does not participate in
        identity, uniqueness, or reference resolution.
        """
        return self._body_title()

    def with_metadata(self, raw: dict[str, object]) -> Self:
        """Return a copy with replaced frontmatter, revalidated.

        Parameters
        ----------
        raw : dict[str, object]
            New frontmatter mapping. The mapping is copied before validation;
            the caller's dictionary is not retained.

        Returns
        -------
        NoteDocument
            New document with the replacement metadata and the original body,
            newline style, and frontmatter presence.

        Raises
        ------
        NoteParseError
            If the replacement metadata has an unknown type, an invalid
            category or status, or malformed values.
        InvalidReferenceError
            If ``people`` or ``project`` is not made of valid scheme
            references.

        Notes
        -----
        Unknown keys are preserved. Category and status values are normalized
        to their canonical lowercase forms.
        """
        new_raw = dict(raw)
        note_type = self._declared_note_type(new_raw)
        category = self._declared_category(new_raw, note_type)
        status = self._declared_status(new_raw, note_type)
        references = self._references_from_raw(new_raw)
        return dataclasses.replace(
            self,
            raw=new_raw,
            note_type=note_type,
            category=category,
            status=status,
            references=references,
        )

    def rewrite_references(self, old: NoteReference, new: NoteReference) -> tuple[Self, int]:
        """Rewrite matching frontmatter reference values.

        Parameters
        ----------
        old : NoteReference
            Scheme and name to replace. The label is ignored.
        new : NoteReference
            Replacement scheme and name.

        Returns
        -------
        tuple[NoteDocument, int]
            Document with updated raw metadata and references, plus the number
            of values changed. When nothing matches, the original document is
            returned with zero.

        Raises
        ------
        InvalidReferenceError
            If an existing value is not a valid reference for its key. Parsed
            documents normally cannot reach this state.

        Notes
        -----
        Only the ``people`` and ``project`` values change. Unknown keys and
        their order are preserved. Frontmatter values never use angle brackets.
        """
        raw = dict(self.raw)
        old_key = ReferenceKey.from_reference(old)
        count = 0

        people = raw.get("people")
        if isinstance(people, list):
            rewritten_people: list[object] = []
            for value in people:
                reference = self._person_reference(value)
                if ReferenceKey.from_reference(reference) == old_key:
                    rewritten_people.append(self._frontmatter_value(new))
                    count += 1
                else:
                    rewritten_people.append(value)
            raw["people"] = rewritten_people

        project = raw.get("project")
        if isinstance(project, str):
            reference = self._project_reference(project)
            if ReferenceKey.from_reference(reference) == old_key:
                raw["project"] = self._frontmatter_value(new)
                count += 1

        if count == 0:
            return self, 0
        return dataclasses.replace(
            self,
            raw=raw,
            references=self._references_from_raw(raw),
        ), count

    @staticmethod
    def _split_frontmatter(text: str) -> FrontmatterSplit:
        """Split source into raw frontmatter, body, and a presence flag."""
        lines = text.splitlines(keepends=True)
        if not lines or NoteDocument._without_ending(lines[0]) != FRONTMATTER_FENCE:
            return FrontmatterSplit(raw={}, body=text, has_frontmatter=False)

        for index in range(1, len(lines)):
            if NoteDocument._without_ending(lines[index]) != FRONTMATTER_FENCE:
                continue
            source = "".join(lines[1:index])
            raw = NoteDocument._load_yaml(source)
            return FrontmatterSplit(raw=raw, body="".join(lines[index + 1 :]), has_frontmatter=True)

        message = "Frontmatter opening fence is never closed"
        raise NoteParseError(message)

    @staticmethod
    def _without_ending(line: str) -> str:
        """Remove a trailing CRLF or LF from one line."""
        return line.rstrip("\r\n")

    @staticmethod
    def _load_yaml(source: str) -> dict[str, object]:
        """Load a frontmatter block as a string-keyed mapping."""
        try:
            loaded = yaml.safe_load(source)
        except YAMLError as exc:
            message = "Frontmatter is not valid YAML"
            raise NoteParseError(message) from exc

        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            message = "Frontmatter must be a YAML mapping"
            raise NoteParseError(message)

        raw: dict[str, object] = {}
        for key, value in loaded.items():
            if not isinstance(key, str):
                message = "Frontmatter keys must be strings"
                raise NoteParseError(message)
            raw[key] = value
        return raw

    @staticmethod
    def _declared_note_type(raw: dict[str, object]) -> NoteType | None:
        """Return the declared note type, or ``None`` when absent."""
        if "type" not in raw:
            return None
        value = raw["type"]
        if not isinstance(value, str):
            message = "Frontmatter type must be a string"
            raise NoteParseError(message)
        try:
            return NoteType(value)
        except ValueError as exc:
            message = f"Unknown note type: {value!r}"
            raise NoteParseError(message) from exc

    @staticmethod
    def _declared_category(
        raw: dict[str, object],
        note_type: NoteType | None,
    ) -> ReferenceCategory | None:
        """Return the validated reference category, or ``None`` when absent."""
        if "category" not in raw:
            return None
        value = raw["category"]
        if not isinstance(value, str) or not value.strip():
            message = "Frontmatter category must be a non-empty string"
            raise NoteParseError(message)
        if note_type is not NoteType.REFERENCE:
            message = "Frontmatter category is only valid on reference notes"
            raise NoteParseError(message)
        try:
            category = ReferenceCategory(value.strip().casefold())
        except ValueError as exc:
            message = f"Unknown reference category: {value!r}"
            raise NoteParseError(message) from exc
        raw["category"] = category.value
        return category

    @staticmethod
    def _declared_status(
        raw: dict[str, object],
        note_type: NoteType | None,
    ) -> Status | None:
        """Return the validated workflow status, or ``None`` when absent."""
        if "status" not in raw:
            return None
        value = raw["status"]
        if value is None:
            return None
        if not isinstance(value, str):
            message = "Frontmatter status must be a string"
            raise NoteParseError(message)
        try:
            status = Status(value)
        except ValueError as exc:
            message = f"Unknown note status: {value!r}"
            raise NoteParseError(message) from exc
        if note_type is None:
            message = "Frontmatter status requires a note type"
            raise NoteParseError(message)
        if status not in note_type.allowed_statuses:
            message = f"Status {value!r} is not valid for {note_type.value} notes"
            raise NoteParseError(message)
        raw["status"] = status.value
        return status

    @staticmethod
    def _references_from_raw(raw: dict[str, object]) -> tuple[NoteReference, ...]:
        """Validate and collect references declared by frontmatter values."""
        references: list[NoteReference] = []

        if "people" in raw:
            people = raw["people"]
            if not isinstance(people, list):
                message = "Frontmatter people must be a list of person references"
                raise InvalidReferenceError(message)
            references.extend(NoteDocument._person_reference(value) for value in people)

        project = raw.get("project")
        if project is not None:
            references.append(NoteDocument._project_reference(project))

        return tuple(references)

    @staticmethod
    def _person_reference(value: object) -> NoteReference:
        """Validate one person reference value."""
        if not isinstance(value, str):
            message = "Frontmatter people entries must be strings"
            raise InvalidReferenceError(message)
        reference = ReferenceParser().parse(value)
        if reference.scheme is not ReferenceScheme.PERSON:
            message = f"Frontmatter people entry is not a person reference: {value!r}"
            raise InvalidReferenceError(message)
        return reference

    @staticmethod
    def _project_reference(value: object) -> NoteReference:
        """Validate the single project reference value."""
        if not isinstance(value, str):
            message = "Frontmatter project must be a string"
            raise InvalidReferenceError(message)
        reference = ReferenceParser().parse(value)
        if reference.scheme is not ReferenceScheme.PROJECT:
            message = f"Frontmatter project value is not a project reference: {value!r}"
            raise InvalidReferenceError(message)
        return reference

    @staticmethod
    def _frontmatter_value(reference: NoteReference) -> str:
        """Render a reference as a frontmatter value without angle brackets."""
        return f"{reference.scheme.value}:{reference.name}"

    def _body_title(self) -> str | None:
        """Return the plain text of the first level-1 heading in the body.

        Returns
        -------
        str | None
            Trimmed heading text, or ``None`` when the first level-1 heading is
            absent or blank.

        Notes
        -----
        Extraction uses the CommonMark parser, so headings inside code blocks
        are not considered. Inline markup is flattened to text and a multi-line
        setext heading is joined with single spaces.
        """
        tokens = MarkdownIt("commonmark").parse(self.body)
        for index, token in enumerate(tokens):
            if token.type != "heading_open" or token.tag != "h1":
                continue
            inline = tokens[index + 1] if index + 1 < len(tokens) else None
            text = self._inline_text(inline) if inline is not None and inline.type == "inline" else ""
            return text.strip() or None
        return None

    @staticmethod
    def _inline_text(token: Token) -> str:
        """Flatten one inline token's children to plain text.

        Parameters
        ----------
        token : Token
            Inline token holding the heading's children.

        Returns
        -------
        str
            Concatenated text of text, code, and image children, with line
            breaks rendered as single spaces.

        Notes
        -----
        Formatting markers and raw inline HTML are omitted because the result
        is a display title, not a Markdown fragment.
        """
        if token.children is None:
            return token.content
        parts: list[str] = []
        for child in token.children:
            if child.type in {"text", "code_inline", "image"}:
                parts.append(child.content)
            elif child.type in {"softbreak", "hardbreak"}:
                parts.append(" ")
        return "".join(parts)
