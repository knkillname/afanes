# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Trash origin and retention metadata read from and written to frontmatter.

The editor is intentionally independent of :class:`afanes.core.frontmatter.NoteDocument`.
A trashed note can carry a frontmatter value that the active note model rejects,
yet its birthplace is still known and the note must remain restorable. The
module owns only the two trash keys and preserves every other byte-shaped part
of the document: body, newline style, key order, and unknown keys.
"""

import dataclasses
import datetime
from pathlib import Path, PurePosixPath
from typing import Self

import yaml
from yaml import YAMLError

import afanes.core.names
import afanes.core.vault.snapshot
from afanes.core.errors import NoteParseError
from afanes.core.frontmatter import FRONTMATTER_FENCE, NoteDocument

# Public trash metadata keys and retention policy.
TRASHED_FROM_KEY = "trashed_from"
TRASHED_ON_KEY = "trashed_on"
TRASH_RETENTION_DAYS = 30

_FORBIDDEN_BIRTHPLACE_ROOTS = frozenset(
    {
        afanes.core.vault.snapshot.TRASH_DIRECTORY.name.casefold(),
        afanes.core.vault.snapshot.TEMPLATES_DIRECTORY.name.casefold(),
    }
)


@dataclasses.dataclass(frozen=True, slots=True)
class TrashMetadata:
    """Origin and retention day recorded on one trashed note.

    Attributes
    ----------
    birthplace : pathlib.Path
        Vault-relative path the note occupied before it was moved to Trash.
    trashed_on : datetime.date | None
        Local calendar day the note was trashed, or ``None`` when the written
        value was missing or unusable.

    Notes
    -----
    Build instances through :meth:`from_raw`. A missing or unsafe birthplace
    makes the trash file unmanaged; a missing day is recoverable and is stamped
    on the next maintenance pass.
    """

    birthplace: Path
    trashed_on: datetime.date | None

    @classmethod
    def from_raw(cls, raw: dict[str, object]) -> Self | None:
        """Read trash metadata from a loaded frontmatter mapping.

        Parameters
        ----------
        raw : dict[str, object]
            Frontmatter mapping exactly as loaded.

        Returns
        -------
        TrashMetadata | None
            Metadata when ``trashed_from`` is a safe vault-relative note path;
            otherwise ``None``, which marks the file unmanaged. A missing or
            malformed ``trashed_on`` leaves the day as ``None``.

        Notes
        -----
        The birthplace is validated without touching the filesystem. Absolute
        paths, ancestor traversal, hidden folders, notes under ``trash/`` or
        ``templates/``, and names that violate the cross-platform filename
        policy are refused. :class:`afanes.core.vault.trash_catalog.TrashCatalog`
        additionally resolves the path against the vault root.
        """
        value = raw.get(TRASHED_FROM_KEY)
        if not isinstance(value, str):
            return None
        birthplace = cls._birthplace(value)
        if birthplace is None:
            return None
        return cls(birthplace=birthplace, trashed_on=cls._day(raw.get(TRASHED_ON_KEY)))

    @classmethod
    def _birthplace(cls, value: str) -> Path | None:
        """Return a safe vault-relative path, or ``None`` when unusable."""
        text = value.strip().replace("\\", "/")
        pure = PurePosixPath(text)
        parts = pure.parts
        unsafe = (
            not text
            or text.startswith(("/", "~"))
            or pure.is_absolute()
            or not parts
            or any(part in ("", ".", "..") for part in parts)
            or parts[0].casefold() in _FORBIDDEN_BIRTHPLACE_ROOTS
            or any(part.startswith(".") for part in parts)
            or pure.suffix.casefold() != afanes.core.vault.snapshot.NOTE_SUFFIX
        )
        policy = afanes.core.names.NamePolicy
        if unsafe or any(policy.safe_filename(part) != part for part in parts):
            return None
        return Path(*parts)

    @staticmethod
    def _day(value: object) -> datetime.date | None:
        """Return a calendar date from a YAML date or ISO date string."""
        if isinstance(value, datetime.datetime):
            return None
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value.strip())
            except ValueError:
                return None
        return None

    @property
    def birthplace_text(self) -> str:
        """Return the birthplace as the POSIX text stored in frontmatter.

        Returns
        -------
        str
            Vault-relative path with forward slashes.
        """
        return self.birthplace.as_posix()

    def is_expired(self, today: datetime.date) -> bool:
        """Return whether the retention period has elapsed.

        Parameters
        ----------
        today : datetime.date
            Current local calendar day supplied by the caller.

        Returns
        -------
        bool
            ``True`` when a usable trashed day is at least the retention period
            before ``today``.

        Notes
        -----
        An entry without a usable day is never expired. A future date is kept
        and does not expire until the calendar catches up.
        """
        if self.trashed_on is None:
            return False
        age = (today - self.trashed_on).days
        return age >= TRASH_RETENTION_DAYS

    def with_day(self, day: datetime.date) -> Self:
        """Return a copy carrying a replacement trashed day.

        Parameters
        ----------
        day : datetime.date
            Local calendar day to record.

        Returns
        -------
        TrashMetadata
            New metadata; the original is unchanged.
        """
        return dataclasses.replace(self, trashed_on=day)

    def to_raw(self) -> dict[str, object]:
        """Return the two keys as a YAML-ready mapping.

        Returns
        -------
        dict[str, object]
            Mapping with ``trashed_from`` and, when usable, ``trashed_on``.
        """
        raw: dict[str, object] = {TRASHED_FROM_KEY: self.birthplace_text}
        if self.trashed_on is not None:
            raw[TRASHED_ON_KEY] = self.trashed_on
        return raw


@dataclasses.dataclass(frozen=True, slots=True)
class TrashDocument:
    """A trashed note split into raw frontmatter and Markdown body.

    Attributes
    ----------
    raw : dict[str, object]
        Frontmatter mapping exactly as loaded, including unknown keys.
    body : str
        Markdown body after the closing fence, or the complete source when no
        frontmatter is present.
    newline : str
        Newline sequence used by the document: LF or CRLF.
    has_frontmatter : bool
        Whether the source began with a complete ``---`` fence block.

    Notes
    -----
    This value object exists so trash metadata can be read and written without
    validating the rest of the note. Build instances through :meth:`from_text`.
    """

    raw: dict[str, object]
    body: str
    newline: str
    has_frontmatter: bool

    @classmethod
    def from_text(cls, text: str) -> Self:
        """Split complete note text into frontmatter and body.

        Parameters
        ----------
        text : str
            Complete file text.

        Returns
        -------
        TrashDocument
            Raw metadata and the untouched body.

        Raises
        ------
        NoteParseError
            If the opening fence is never closed, or the frontmatter is not
            valid YAML or not a string-keyed mapping.
        """
        lines = text.splitlines(keepends=True)
        newline = "\r\n" if "\r\n" in text else "\n"
        if not lines or cls._without_ending(lines[0]) != FRONTMATTER_FENCE:
            return cls(raw={}, body=text, newline=newline, has_frontmatter=False)
        for index in range(1, len(lines)):
            if cls._without_ending(lines[index]) != FRONTMATTER_FENCE:
                continue
            source = "".join(lines[1:index])
            return cls(
                raw=cls._load_yaml(source),
                body="".join(lines[index + 1 :]),
                newline=newline,
                has_frontmatter=True,
            )
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

    @property
    def metadata(self) -> TrashMetadata | None:
        """Return the trash metadata carried by this document.

        Returns
        -------
        TrashMetadata | None
            Parsed metadata, or ``None`` when the document has no safe
            birthplace and is therefore unmanaged.
        """
        return TrashMetadata.from_raw(self.raw)

    @property
    def title(self) -> str | None:
        """Return the display title derived from the first level-1 heading.

        Returns
        -------
        str | None
            Trimmed heading text, or ``None`` when the body has no level-1
            heading or its first heading is blank.

        Notes
        -----
        Title extraction reuses :class:`afanes.core.frontmatter.NoteDocument`
        with an empty metadata mapping, so it never validates the trashed
        note's declared type or other frontmatter fields.
        """
        document = NoteDocument(
            raw={},
            body=self.body,
            newline=self.newline,
            has_frontmatter=False,
            note_type=None,
        )
        return document.title

    def with_metadata(self, metadata: TrashMetadata) -> str:
        """Return the document text with the two trash keys written.

        Parameters
        ----------
        metadata : TrashMetadata
            Origin and retention day to record. Existing values are replaced in
            place; missing keys append at the end of the mapping.

        Returns
        -------
        str
            Complete note text with the original body, newline style, key
            order, and unknown keys preserved.
        """
        raw = dict(self.raw)
        raw[TRASHED_FROM_KEY] = metadata.birthplace_text
        if metadata.trashed_on is None:
            raw.pop(TRASHED_ON_KEY, None)
        else:
            raw[TRASHED_ON_KEY] = metadata.trashed_on
        return self._render(raw)

    def without_metadata(self) -> str:
        """Return the document text with the two trash keys removed.

        Returns
        -------
        str
            Complete note text with the original body, newline style, key
            order, and unknown keys preserved. A document that carries neither
            key is returned unchanged.
        """
        if TRASHED_FROM_KEY not in self.raw and TRASHED_ON_KEY not in self.raw:
            return self._source_text()
        raw = dict(self.raw)
        raw.pop(TRASHED_FROM_KEY, None)
        raw.pop(TRASHED_ON_KEY, None)
        return self._render(raw)

    def _source_text(self) -> str:
        """Serialize the document without changing its metadata."""
        return self._render(dict(self.raw))

    def _render(self, raw: dict[str, object]) -> str:
        """Serialize a raw mapping and body with the document's newline style."""
        if not raw and not self.has_frontmatter:
            return self.body
        yaml_text = yaml.safe_dump(
            raw,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )
        yaml_text = yaml_text.replace("\r\n", "\n")
        if not yaml_text.endswith("\n"):
            yaml_text = f"{yaml_text}\n"
        yaml_text = yaml_text.replace("\n", self.newline)
        return f"{FRONTMATTER_FENCE}{self.newline}{yaml_text}{FRONTMATTER_FENCE}{self.newline}{self.body}"
