# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Editable page labels and their validation.

The module owns the due-date text value and the label set the page editor
mutates. It performs no file I/O and never reaches into the vault.
"""

import dataclasses
import datetime
from typing import Self

from afanes.core.errors import NoteParseError
from afanes.core.frontmatter import NoteDocument
from afanes.models.link import ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status


@dataclasses.dataclass(frozen=True, slots=True)
class DueDateText:
    """Editable due-date text and its interpretation.

    Attributes
    ----------
    text : str
        Text exactly as shown in the editor.
    date : datetime.date | None
        Parsed calendar date, or ``None`` when the text is blank or invalid.
    error : str | None
        Actionable validation message for an invalid non-blank value, or
        ``None`` when the text is valid or blank.
    """

    text: str
    date: datetime.date | None
    error: str | None

    @classmethod
    def from_text(cls, text: str) -> Self:
        """Interpret editable due-date text.

        Parameters
        ----------
        text : str
            Field text. Blank means no due date.

        Returns
        -------
        DueDateText
            Parsed date for a valid ``YYYY-MM-DD`` value, or ``None`` plus an
            actionable error for an invalid value.

        Notes
        -----
        The original text is preserved so an invalid value is never silently
        discarded from the editor.
        """
        trimmed = text.strip()
        if not trimmed:
            return cls(text=text, date=None, error=None)
        try:
            return cls(text=text, date=datetime.date.fromisoformat(trimmed), error=None)
        except ValueError:
            return cls(
                text=text,
                date=None,
                error="Enter the due date as YYYY-MM-DD or leave it empty",
            )

    @classmethod
    def from_raw(cls, value: object) -> Self:
        """Interpret a loaded frontmatter value.

        Parameters
        ----------
        value : object
            Raw value of the ``due_date`` key. YAML normally loads an ISO date
            as a :class:`datetime.date`; strings and other values are preserved
            for display so the user can correct them.

        Returns
        -------
        DueDateText
            Text and interpretation derived from the raw value. ``None``
            becomes blank text; a date becomes ISO text; any other value is
            preserved for correction.
        """
        if value is None:
            return cls.from_text("")
        if isinstance(value, datetime.datetime):
            return cls.from_text(value.isoformat())
        if isinstance(value, datetime.date):
            return cls.from_text(value.isoformat())
        if isinstance(value, str):
            return cls.from_text(value)
        return cls.from_text(str(value))


@dataclasses.dataclass(frozen=True, slots=True)
class PageLabels:
    """Frontmatter labels owned by the page editor.

    Attributes
    ----------
    note_type : NoteType
        Declared note type.
    category : CategoryLabel | None
        Free-form reference category, or ``None`` for an uncategorized
        reference or a non-reference note.
    status : Status | None
        Workflow status, or ``None`` when the key is absent.
    due_date_text : str
        Due-date field text exactly as shown in the editor.
    asked_by_text : str
        Requester field text exactly as shown in the editor.
    date_text : str
        Note-date field text exactly as shown in the editor.
    """

    note_type: NoteType
    category: CategoryLabel | None = None
    status: Status | None = None
    due_date_text: str = ""
    asked_by_text: str = ""
    date_text: str = ""

    @classmethod
    def from_document(cls, document: NoteDocument) -> Self:
        """Build labels from a parsed note.

        Parameters
        ----------
        document : NoteDocument
            Parsed note with a declared type.

        Returns
        -------
        PageLabels
            Labels populated from the document's type, category, status, due
            date, and requester.

        Raises
        ------
        NoteParseError
            If the document has no declared type.
        """
        if document.note_type is None:
            message = "Note has no type"
            raise NoteParseError(message)
        due_date = document.raw.get("due_date")
        return cls(
            note_type=document.note_type,
            category=document.category,
            status=document.status,
            due_date_text=DueDateText.from_raw(due_date).text,
            asked_by_text=document.asked_by or "",
            date_text=PageLabels._date_text(document.raw.get("date")),
        )

    @staticmethod
    def _date_text(value: object) -> str:
        """Return the editable text for a raw note date.

        Parameters
        ----------
        value : object
            Raw value from the parsed frontmatter mapping.

        Returns
        -------
        str
            ISO text for a valid date, the original text for a malformed
            string, or the ISO representation of a date/time value. ``None``
            becomes blank.
        """
        if value is None:
            return ""
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        return str(value)

    @property
    def date(self) -> NoteDate | None:
        """Return the parsed note date, or ``None`` when absent or invalid.

        Returns
        -------
        NoteDate | None
            Parsed ISO partial date, or ``None``.
        """
        text = self.date_text.strip()
        if not text:
            return None
        try:
            return NoteDate.from_text(text)
        except ValueError:
            return None

    @property
    def date_error(self) -> str | None:
        """Return the date validation message, or ``None`` when valid.

        Returns
        -------
        str | None
            Actionable message for a malformed non-blank date.
        """
        text = self.date_text.strip()
        if not text:
            return None
        try:
            NoteDate.from_text(text)
        except ValueError as exc:
            return str(exc)
        return None

    @property
    def scheme(self) -> ReferenceScheme:
        """Return the reference scheme this label set belongs to.

        Returns
        -------
        ReferenceScheme
            Scheme derived from the type. Category never changes it.
        """
        return ReferenceScheme.for_note(self.note_type)

    @property
    def due_date(self) -> datetime.date | None:
        """Return the parsed due date, or ``None`` when absent or invalid.

        Returns
        -------
        datetime.date | None
            Parsed calendar date, or ``None``.
        """
        return DueDateText.from_text(self.due_date_text).date

    @property
    def due_date_error(self) -> str | None:
        """Return the due-date validation message, or ``None`` when valid.

        Returns
        -------
        str | None
            Actionable message for an invalid non-blank due date.
        """
        return DueDateText.from_text(self.due_date_text).error

    def apply_to(self, document: NoteDocument) -> NoteDocument:
        """Return a document with these labels written into its frontmatter.

        Parameters
        ----------
        document : NoteDocument
            Parsed note whose body, newline style, and unknown keys are kept.

        Returns
        -------
        NoteDocument
            New document with the editable labels applied and revalidated.
            Existing keys keep their positions and new keys append in the
            documented order: type, date, category, status, due_date, asked_by.

        Raises
        ------
        NoteParseError
            If the resulting metadata is not valid for the note type.
        RetiredValueError
            If the document declares a retired type or key.

        Notes
        -----
        Validation and serialization stay in ``NoteDocument``. A malformed
        non-blank note date already present in the document is left untouched
        so it can be corrected later; a blank date removes the key. Category,
        status, due date, and requester are removed when the note type does not
        allow them.
        """
        raw = dict(document.raw)
        raw["type"] = self.note_type.value
        self._apply_date(raw)
        if self.note_type is NoteType.REFERENCE and self.category is not None:
            raw["category"] = self.category.value
        else:
            raw.pop("category", None)
        if self.status is None:
            raw.pop("status", None)
        else:
            raw["status"] = self.status.value
        due_date = self.due_date
        if self.note_type is NoteType.PROJECT and due_date is not None:
            raw["due_date"] = due_date
        else:
            raw.pop("due_date", None)
        asked_by = self.asked_by_text.strip()
        if self.note_type is NoteType.PROJECT and asked_by:
            raw["asked_by"] = asked_by
        else:
            raw.pop("asked_by", None)
        return document.with_metadata(raw)

    def _apply_date(self, raw: dict[str, object]) -> None:
        """Write the note date into a raw frontmatter mapping.

        Parameters
        ----------
        raw : dict[str, object]
            Mapping copied from the source document. The method mutates it.
        """
        if not self.date_text.strip():
            raw.pop("date", None)
            return
        note_date = self.date
        if note_date is not None:
            raw["date"] = note_date.to_yaml_value()

    def with_type(self, note_type: NoteType) -> Self:
        """Return labels adjusted for a new note type.

        Parameters
        ----------
        note_type : NoteType
            New declared type.

        Returns
        -------
        PageLabels
            New labels. Category is kept only for references, due-date and
            requester text are kept only for projects, and a status the new
            type does not allow is cleared.
        """
        category = self.category if note_type is NoteType.REFERENCE else None
        due_date_text = self.due_date_text if note_type is NoteType.PROJECT else ""
        asked_by_text = self.asked_by_text if note_type is NoteType.PROJECT else ""
        status = self.status if self.status in note_type.allowed_statuses else None
        return dataclasses.replace(
            self,
            note_type=note_type,
            category=category,
            status=status,
            due_date_text=due_date_text,
            asked_by_text=asked_by_text,
        )

    def with_category(self, category: CategoryLabel | None) -> Self:
        """Return labels with a reference category.

        Parameters
        ----------
        category : CategoryLabel | None
            New category, or ``None`` for an uncategorized reference.

        Returns
        -------
        PageLabels
            New labels. The category is forced to ``None`` for a non-reference
            type.
        """
        effective = category if self.note_type is NoteType.REFERENCE else None
        return dataclasses.replace(self, category=effective)

    def with_status(self, status: Status | None) -> Self:
        """Return labels with a validated workflow status.

        Parameters
        ----------
        status : Status | None
            New status, or ``None`` to clear it.

        Returns
        -------
        PageLabels
            New labels with the status applied.

        Raises
        ------
        NoteParseError
            If the status is not valid for the current type.
        """
        if status is not None and status not in self.note_type.allowed_statuses:
            message = f"Status {status.value!r} is not valid for a {self.note_type.value} note"
            raise NoteParseError(message)
        return dataclasses.replace(self, status=status)

    def with_due_date_text(self, text: str) -> Self:
        """Return labels with new due-date field text.

        Parameters
        ----------
        text : str
            Text exactly as typed. It is validated when the draft is saved.

        Returns
        -------
        PageLabels
            New labels carrying the text, or blank labels for a non-project
            note.
        """
        if self.note_type is not NoteType.PROJECT:
            return dataclasses.replace(self, due_date_text="")
        return dataclasses.replace(self, due_date_text=text)

    def with_asked_by_text(self, text: str) -> Self:
        """Return labels with new requester field text.

        Parameters
        ----------
        text : str
            Text exactly as typed. It is trimmed when the draft is saved.

        Returns
        -------
        PageLabels
            New labels carrying the text, or blank labels for a non-project
            note.
        """
        if self.note_type is not NoteType.PROJECT:
            return dataclasses.replace(self, asked_by_text="")
        return dataclasses.replace(self, asked_by_text=text)

    def with_date_text(self, text: str) -> Self:
        """Return labels with new note-date field text.

        Parameters
        ----------
        text : str
            Text exactly as typed. It is validated when the draft is saved.

        Returns
        -------
        PageLabels
            New labels carrying the text. The date is available for every note
            type, so the text is never cleared by this method.
        """
        return dataclasses.replace(self, date_text=text)
