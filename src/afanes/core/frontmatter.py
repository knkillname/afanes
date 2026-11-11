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
from yaml import YAMLError

import afanes.core.links
from afanes.core.errors import InvalidReferenceError, NoteParseError
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType

# Public canonical frontmatter delimiter.
FRONTMATTER_FENCE = "---"


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
            not a mapping, a key is not a string, or the declared type is
            unknown.
        InvalidReferenceError
            If ``people`` or ``project`` is not made of valid scheme
            references.

        Notes
        -----
        Frontmatter exists only when the first line is exactly ``---``. A body
        that later begins with ``---`` is ordinary content and is preserved.
        """
        raw, body, has_frontmatter = cls._split_frontmatter(text)
        newline = "\r\n" if "\r\n" in text else "\n"
        return cls(
            raw=raw,
            body=body,
            newline=newline,
            has_frontmatter=has_frontmatter,
            note_type=cls._declared_note_type(raw),
            references=cls._references_from_raw(raw),
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
        old_key = afanes.core.links.reference_key(old)
        count = 0

        people = raw.get("people")
        if isinstance(people, list):
            rewritten_people: list[object] = []
            for value in people:
                reference = self._person_reference(value)
                if afanes.core.links.reference_key(reference) == old_key:
                    rewritten_people.append(self._frontmatter_value(new))
                    count += 1
                else:
                    rewritten_people.append(value)
            raw["people"] = rewritten_people

        project = raw.get("project")
        if isinstance(project, str):
            reference = self._project_reference(project)
            if afanes.core.links.reference_key(reference) == old_key:
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
    def _split_frontmatter(text: str) -> tuple[dict[str, object], str, bool]:
        """Split source into raw frontmatter, body, and a presence flag."""
        lines = text.splitlines(keepends=True)
        if not lines or NoteDocument._without_ending(lines[0]) != FRONTMATTER_FENCE:
            return {}, text, False

        for index in range(1, len(lines)):
            if NoteDocument._without_ending(lines[index]) != FRONTMATTER_FENCE:
                continue
            source = "".join(lines[1:index])
            raw = NoteDocument._load_yaml(source)
            return raw, "".join(lines[index + 1 :]), True

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
        reference = afanes.core.links.parse_reference(value)
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
        reference = afanes.core.links.parse_reference(value)
        if reference.scheme is not ReferenceScheme.PROJECT:
            message = f"Frontmatter project value is not a project reference: {value!r}"
            raise InvalidReferenceError(message)
        return reference

    @staticmethod
    def _frontmatter_value(reference: NoteReference) -> str:
        """Render a reference as a frontmatter value without angle brackets."""
        return f"{reference.scheme.value}:{reference.name}"
