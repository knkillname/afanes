# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frontmatter-aware note documents.

The module exposes one cohesive value object, :class:`NoteDocument`, which
owns fence parsing, safe YAML loading, serialization, and validation of the seven
recognized frontmatter keys. Keeping those behaviors together preserves the
document's invariants: metadata, body, newline style, declared type, category,
status, due date, requester, and note date always travel as one unit.
"""

import dataclasses
import datetime
from typing import Self

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token
from yaml import YAMLError

from afanes.core.errors import NoteParseError, RetiredValueError
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status

# Public canonical frontmatter delimiter.
FRONTMATTER_FENCE = "---"

# Public retired frontmatter keys. They are rejected instead of migrated.
RETIRED_KEYS = frozenset({"people", "project"})
# Public retired note type value.
RETIRED_NOTE_TYPES = frozenset({"action", "person"})


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
    category : CategoryLabel | None
        Free-form reference category, or ``None`` for an uncategorized
        reference or a non-reference note.
    status : Status | None
        Validated workflow status, or ``None`` when the key is absent.
    due_date : datetime.date | None
        Calendar due date for a project, or ``None`` when absent.
    asked_by : str | None
        Plain name of the person or group that requested the project, or
        ``None`` when absent.
    owner : str | None
        Plain name of the person or team accountable for the project, or
        ``None`` when absent.
    date : NoteDate | None
        ISO partial date, or ``None`` when absent or malformed.
    date_error : str | None
        Validation message for a malformed ``date``, or ``None`` when the value
        is absent or valid.

    Notes
    -----
    Use :meth:`from_text` to build a validated document from source. The raw
    mapping is kept so a rewrite can preserve unknown keys; callers receive a
    fresh copy from the parser. A malformed ``date`` is preserved in the raw
    mapping, reported through :attr:`date_error`, and treated as absent by the
    scan instead of making the note unreadable.
    """

    raw: dict[str, object]
    body: str
    newline: str
    has_frontmatter: bool
    note_type: NoteType | None
    category: CategoryLabel | None = None
    status: Status | None = None
    due_date: datetime.date | None = None
    asked_by: str | None = None
    owner: str | None = None
    date: NoteDate | None = None
    date_error: str | None = None

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
            Raw metadata, body, newline style, declared type, category, status,
            due date, requester, owner, and note date.

        Raises
        ------
        NoteParseError
            If the opening fence is never closed, the YAML is malformed or is
            not a mapping, a key is not a string, the declared type or status
            is unknown, the category is invalid or misplaced, the due date is
            invalid or misplaced, the asked-by or owner name is invalid or
            misplaced, or the status is not valid for the type.
        RetiredValueError
            If the note declares ``type: action``, ``type: person``, or a
            ``people`` or ``project`` key.

        Notes
        -----
        Frontmatter exists only when the first line is exactly ``---``. A body
        that later begins with ``---`` is ordinary content and is preserved. A
        malformed ``date`` does not raise; it is preserved in :attr:`raw`,
        reported through :attr:`date_error`, and treated as absent.
        """
        split = cls._split_frontmatter(text)
        newline = "\r\n" if "\r\n" in text else "\n"
        cls._reject_retired_keys(split.raw)
        note_type = cls._declared_note_type(split.raw)
        category = cls._declared_category(split.raw, note_type)
        status = cls._declared_status(split.raw, note_type)
        due_date = cls._declared_due_date(split.raw, note_type)
        asked_by = cls._declared_asked_by(split.raw, note_type)
        owner = cls._declared_owner(split.raw, note_type)
        note_date, date_error = cls._declared_date(split.raw)
        return cls(
            raw=split.raw,
            body=split.body,
            newline=newline,
            has_frontmatter=split.has_frontmatter,
            note_type=note_type,
            category=category,
            status=status,
            due_date=due_date,
            asked_by=asked_by,
            owner=owner,
            date=note_date,
            date_error=date_error,
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
            category, status, or due date, or malformed values.
        RetiredValueError
            If the replacement metadata declares a retired type or key.

        Notes
        -----
        Unknown keys are preserved. Category values preserve their written
        form; retired keys are never accepted back. A malformed ``date`` is
        preserved and reported through :attr:`date_error` rather than raising.
        """
        new_raw = dict(raw)
        self._reject_retired_keys(new_raw)
        note_type = self._declared_note_type(new_raw)
        category = self._declared_category(new_raw, note_type)
        status = self._declared_status(new_raw, note_type)
        due_date = self._declared_due_date(new_raw, note_type)
        asked_by = self._declared_asked_by(new_raw, note_type)
        owner = self._declared_owner(new_raw, note_type)
        note_date, date_error = self._declared_date(new_raw)
        return dataclasses.replace(
            self,
            raw=new_raw,
            note_type=note_type,
            category=category,
            status=status,
            due_date=due_date,
            asked_by=asked_by,
            owner=owner,
            date=note_date,
            date_error=date_error,
        )

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
    def _reject_retired_keys(raw: dict[str, object]) -> None:
        """Reject the frontmatter keys retired by the three-type model."""
        for key in sorted(RETIRED_KEYS & raw.keys()):
            if key == "people":
                message = (
                    "The 'people' key was retired; link people in the body with "
                    "[Name](<note:Name>) or list them as step owners"
                )
            else:
                message = (
                    "The 'project' key was retired; move the work into the project body "
                    "as a step or link it in the body"
                )
            raise RetiredValueError(message)

    @staticmethod
    def _declared_note_type(raw: dict[str, object]) -> NoteType | None:
        """Return the declared note type, or ``None`` when absent."""
        if "type" not in raw:
            return None
        value = raw["type"]
        if not isinstance(value, str):
            message = "Frontmatter type must be a string"
            raise NoteParseError(message)
        if value in RETIRED_NOTE_TYPES:
            if value == "action":
                message = "The 'action' note type was retired; make a one-step project instead"
            else:
                message = "The 'person' note type was retired; create a reference with a category label instead"
            raise RetiredValueError(message)
        try:
            return NoteType(value)
        except ValueError as exc:
            message = f"Unknown note type: {value!r}"
            raise NoteParseError(message) from exc

    @staticmethod
    def _declared_category(
        raw: dict[str, object],
        note_type: NoteType | None,
    ) -> CategoryLabel | None:
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
            category = CategoryLabel(value.strip())
        except ValueError as exc:
            message = f"Invalid reference category: {value!r}"
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
    def _declared_due_date(
        raw: dict[str, object],
        note_type: NoteType | None,
    ) -> datetime.date | None:
        """Return the validated calendar due date, or ``None`` when absent."""
        if "due_date" not in raw:
            return None
        value = raw["due_date"]
        if value is None:
            return None
        if note_type is not NoteType.PROJECT:
            message = "Frontmatter due_date is only valid on project notes"
            raise NoteParseError(message)
        due_date = NoteDocument._calendar_date(value)
        raw["due_date"] = due_date
        return due_date

    @staticmethod
    def _declared_asked_by(
        raw: dict[str, object],
        note_type: NoteType | None,
    ) -> str | None:
        """Return the validated requester name, or ``None`` when absent."""
        if "asked_by" not in raw:
            return None
        value = raw["asked_by"]
        if not isinstance(value, str):
            message = "Frontmatter asked_by must be a string"
            raise NoteParseError(message)
        name = value.strip()
        if not name:
            message = "Frontmatter asked_by must be a non-empty string"
            raise NoteParseError(message)
        if note_type is not NoteType.PROJECT:
            message = "Frontmatter asked_by is only valid on project notes"
            raise NoteParseError(message)
        raw["asked_by"] = name
        return name

    @staticmethod
    def _declared_owner(
        raw: dict[str, object],
        note_type: NoteType | None,
    ) -> str | None:
        """Return the validated project owner name, or ``None`` when absent."""
        if "owner" not in raw:
            return None
        value = raw["owner"]
        if not isinstance(value, str):
            message = "Frontmatter owner must be a string"
            raise NoteParseError(message)
        name = value.strip()
        if not name:
            message = "Frontmatter owner must be a non-empty string"
            raise NoteParseError(message)
        if note_type is not NoteType.PROJECT:
            message = "Frontmatter owner is only valid on project notes"
            raise NoteParseError(message)
        raw["owner"] = name
        return name

    @staticmethod
    def _declared_date(raw: dict[str, object]) -> tuple[NoteDate | None, str | None]:
        """Return the parsed note date and any malformed-value warning.

        Parameters
        ----------
        raw : dict[str, object]
            Frontmatter mapping exactly as loaded. A valid value is normalized
            in place; a malformed value is left untouched.

        Returns
        -------
        tuple[NoteDate | None, str | None]
            Parsed date and ``None``, or ``None`` and an actionable warning.
            An absent or null key returns ``(None, None)``.
        """
        if "date" not in raw or raw["date"] is None:
            return None, None
        value = raw["date"]
        note_date: NoteDate | None = None
        warning: str | None = None
        if isinstance(value, bool):
            warning = "A note date must be a date written as YYYY, YYYY-MM, or YYYY-MM-DD"
        elif isinstance(value, datetime.datetime):
            warning = "A note date is a calendar date, not a timestamp"
        else:
            try:
                if isinstance(value, datetime.date):
                    note_date = NoteDate.from_date(value)
                elif isinstance(value, int):
                    note_date = NoteDate.from_year(value)
                elif isinstance(value, str):
                    note_date = NoteDate.from_text(value)
                else:
                    warning = "A note date must be a date written as YYYY, YYYY-MM, or YYYY-MM-DD"
            except ValueError as exc:
                warning = str(exc)
        if warning is None and note_date is not None:
            raw["date"] = note_date.to_yaml_value()
            return note_date, None
        return None, warning

    @staticmethod
    def _calendar_date(value: object) -> datetime.date:
        """Convert one frontmatter value into a calendar date.

        Parameters
        ----------
        value : object
            Raw loaded value, normally a YAML date or an ISO date string.

        Returns
        -------
        datetime.date
            Calendar date with no time or timezone.

        Raises
        ------
        NoteParseError
            If the value is a timestamp, is not a date, or is not a valid
            ``YYYY-MM-DD`` calendar date.
        """
        if isinstance(value, datetime.datetime):
            message = "A due date is a calendar date, not a timestamp"
            raise NoteParseError(message)
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value.strip())
            except ValueError as exc:
                message = f"Invalid due date: {value!r}; use YYYY-MM-DD"
                raise NoteParseError(message) from exc
        message = "Frontmatter due_date must be a date written as YYYY-MM-DD"
        raise NoteParseError(message)

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
