# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pure page editing state shared by the interface and the vault services.

A :class:`PageDraft` holds one editing session: the raw Markdown body, the
frontmatter labels the editor owns, the baseline used for dirty detection, and
the mode (normal or raw rescue). It performs no file I/O; the vault remains the
only writer and the application state orchestrates both.
"""

import dataclasses
import datetime
from enum import StrEnum
from pathlib import Path
from typing import Self

import afanes.core.links
import afanes.core.names
from afanes.core.errors import AfanesError, NoteParseError
from afanes.core.frontmatter import NoteDocument
from afanes.core.vault.snapshot import PageContent, ParsedPage, UnparsedPage
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType, Status


class DraftMode(StrEnum):
    """Editing mode for one page draft.

    Attributes
    ----------
    NORMAL : str
        The note parsed successfully; body and labels are editable.
    RAW : str
        The note did not parse; the complete raw text is editable and labels
        are unavailable.
    """

    NORMAL = "normal"
    RAW = "raw"


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
    """

    note_type: NoteType
    category: CategoryLabel | None = None
    status: Status | None = None
    due_date_text: str = ""

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
            Labels populated from the document's type, category, status, and
            due date.

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
        )

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

    def with_type(self, note_type: NoteType) -> Self:
        """Return labels adjusted for a new note type.

        Parameters
        ----------
        note_type : NoteType
            New declared type.

        Returns
        -------
        PageLabels
            New labels. Category is kept only for references, due-date text is
            kept only for projects, and a status the new type does not allow is
            cleared.
        """
        category = self.category if note_type is NoteType.REFERENCE else None
        due_date_text = self.due_date_text if note_type is NoteType.PROJECT else ""
        status = self.status if self.status in note_type.allowed_statuses else None
        return dataclasses.replace(
            self,
            note_type=note_type,
            category=category,
            status=status,
            due_date_text=due_date_text,
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


@dataclasses.dataclass(frozen=True, slots=True)
class DraftCommon:
    """Editing state shared by normal and raw rescue drafts.

    Attributes
    ----------
    path : Path | None
        Absolute note path, or ``None`` for a new draft that has not been
        written yet.
    identity : str
        Filename stem that will identify the note.
    reference : NoteReference | None
        Reference that opened a new draft, or ``None`` for an existing page.
    baseline_body : str
        Body at the last read or write, used for dirty detection.
    baseline_labels : PageLabels | None
        Labels at the last read or write, used for dirty detection.
    baseline_raw_text : str
        Raw text at the last read or write, used for dirty detection in raw
        mode.
    baseline_hash : str
        Content hash captured at the last read or write.
    """

    path: Path | None
    identity: str
    reference: NoteReference | None
    baseline_body: str
    baseline_labels: PageLabels | None
    baseline_raw_text: str
    baseline_hash: str

    def with_path(self, path: Path | None) -> "DraftCommon":
        """Return shared state assigned to a different path.

        Parameters
        ----------
        path : Path | None
            New absolute path, or ``None`` to make the draft new.

        Returns
        -------
        DraftCommon
            New shared state with the path and identity updated.
        """
        identity = path.stem if path is not None else self.identity
        return dataclasses.replace(self, path=path, identity=identity)


@dataclasses.dataclass(frozen=True, slots=True)
class NormalDraft:
    """An editing session whose note parsed successfully.

    Attributes
    ----------
    common : DraftCommon
        Path, identity, reference, and baseline state.
    body : str
        Editable Markdown body, including its heading.
    labels : PageLabels
        Editable frontmatter labels.
    source : NoteDocument
        Parsed document whose unknown frontmatter keys and newline style are
        preserved.
    """

    common: DraftCommon
    body: str
    labels: PageLabels
    source: NoteDocument

    @classmethod
    def new(cls, reference: NoteReference) -> Self:
        """Build an empty draft for a page requested by a reference.

        Parameters
        ----------
        reference : NoteReference
            Missing reference that opened the draft.

        Returns
        -------
        NormalDraft
            Draft with the reference name as its heading, the scheme's type,
            and no other content. It is clean until the body or a label
            changes.

        Notes
        -----
        A ``note:`` reference creates an uncategorized reference note; a
        ``project:`` reference creates a project. There is no person case. The
        reference wording is preserved in the heading even when the identity is
        sanitized.
        """
        if reference.scheme is ReferenceScheme.PROJECT:
            note_type = NoteType.PROJECT
            category: CategoryLabel | None = None
        else:
            note_type = NoteType.REFERENCE
            category = None

        body = f"# {reference.name}\n\n"
        raw: dict[str, object] = {"type": note_type.value}
        if category is not None:
            raw["category"] = category.value
        document = NoteDocument(
            raw=raw,
            body=body,
            newline="\n",
            has_frontmatter=True,
            note_type=note_type,
            category=category,
            status=None,
        )
        labels = PageLabels.from_document(document)
        identity = afanes.core.names.safe_filename(reference.name)
        template = document.to_text()
        common = DraftCommon(
            path=None,
            identity=identity,
            reference=reference,
            baseline_body=body,
            baseline_labels=labels,
            baseline_raw_text=template,
            baseline_hash="",
        )
        return cls(common=common, body=body, labels=labels, source=document)

    @classmethod
    def from_parsed(cls, page: "ParsedPage", reference: NoteReference | None = None) -> Self:
        """Load a normal draft from a page that parsed successfully.

        Parameters
        ----------
        page : ParsedPage
            Parsed page returned by the vault.
        reference : NoteReference | None
            Reference that requested the page, when the page already existed.

        Returns
        -------
        NormalDraft
            Draft with editable body and labels and the page's baseline state.

        Raises
        ------
        NoteParseError
            If the parsed document has no declared type.
        """
        document = page.document
        labels = PageLabels.from_document(document)
        common = DraftCommon(
            path=page.path,
            identity=page.path.stem,
            reference=reference,
            baseline_body=document.body,
            baseline_labels=labels,
            baseline_raw_text=page.text,
            baseline_hash=page.content_hash,
        )
        return cls(common=common, body=document.body, labels=labels, source=document)

    @property
    def path(self) -> Path | None:
        """Return the absolute note path, or ``None`` for a new draft."""
        return self.common.path

    @property
    def identity(self) -> str:
        """Return the filename stem that identifies the note."""
        return self.common.identity

    @property
    def reference(self) -> NoteReference | None:
        """Return the reference that opened a new draft, if any."""
        return self.common.reference

    @property
    def mode(self) -> DraftMode:
        """Return the normal editing mode."""
        return DraftMode.NORMAL

    @property
    def raw_text(self) -> str:
        """Return the serialized text for surface uniformity with raw drafts."""
        return self.to_text()

    @property
    def baseline_body(self) -> str:
        """Return the body at the last read or write."""
        return self.common.baseline_body

    @property
    def baseline_labels(self) -> PageLabels | None:
        """Return the labels at the last read or write."""
        return self.common.baseline_labels

    @property
    def baseline_raw_text(self) -> str:
        """Return the raw text at the last read or write."""
        return self.common.baseline_raw_text

    @property
    def baseline_hash(self) -> str:
        """Return the content hash at the last read or write."""
        return self.common.baseline_hash

    @property
    def is_new(self) -> bool:
        """Return whether the draft has not been written to the vault yet."""
        return self.path is None

    @property
    def is_dirty(self) -> bool:
        """Return whether the body or labels differ from the last baseline."""
        return self.body != self.common.baseline_body or self.labels != self.common.baseline_labels

    @property
    def display_title(self) -> str:
        """Return the title derived from the current draft body."""
        return self.source.with_body(self.body).title or self.identity

    def as_new(self) -> Self:
        """Return a copy that is treated as an unwritten new draft.

        Returns
        -------
        NormalDraft
            Copy without a path or previous baseline, so the next save creates
            the page again. The body and labels are retained in memory.
        """
        common = dataclasses.replace(
            self.common,
            path=None,
            baseline_body="",
            baseline_labels=None,
            baseline_raw_text="",
            baseline_hash="",
        )
        return dataclasses.replace(self, common=common)

    def with_body(self, body: str) -> Self:
        """Return a draft with a replaced Markdown body.

        Parameters
        ----------
        body : str
            New complete body.

        Returns
        -------
        NormalDraft
            New draft; the original is unchanged.
        """
        return dataclasses.replace(self, body=body)

    def with_labels(self, labels: PageLabels) -> Self:
        """Return a draft with replaced labels.

        Parameters
        ----------
        labels : PageLabels
            New label values.

        Returns
        -------
        NormalDraft
            New draft; the original is unchanged.
        """
        return dataclasses.replace(self, labels=labels)

    def to_text(self) -> str:
        """Serialize the draft into complete note text.

        Returns
        -------
        str
            Frontmatter plus the edited body. Unknown keys, the newline style,
            and untouched values are preserved.

        Raises
        ------
        NoteParseError
            If the due date is invalid or the edited metadata is not valid for
            the note type.
        """
        if self.labels.due_date_error is not None:
            raise NoteParseError(self.labels.due_date_error)
        due_text = DueDateText.from_text(self.labels.due_date_text)

        raw = dict(self.source.raw)
        raw["type"] = self.labels.note_type.value
        if self.labels.note_type is not NoteType.REFERENCE or self.labels.category is None:
            raw.pop("category", None)
        else:
            raw["category"] = self.labels.category.value
        if self.labels.status is None:
            raw.pop("status", None)
        else:
            raw["status"] = self.labels.status.value
        due_date = due_text.date
        if self.labels.note_type is not NoteType.PROJECT or due_date is None:
            raw.pop("due_date", None)
        else:
            raw["due_date"] = due_date

        document = self.source.with_body(self.body).with_metadata(raw)
        return document.to_text()

    def after_write(self, text: str, *, content_hash: str, path: Path | None = None) -> Self:
        """Return a draft whose baseline matches a successful write.

        Parameters
        ----------
        text : str
            Complete text written to disk.
        content_hash : str
            Hash of the written bytes, for the next conflict check.
        path : Path | None
            Path assigned by a creation, or ``None`` to keep the current path.

        Returns
        -------
        NormalDraft
            New draft with updated baselines.
        """
        common = dataclasses.replace(
            self.common.with_path(path if path is not None else self.path),
            baseline_body=self.body,
            baseline_labels=self.labels,
            baseline_raw_text=text,
            baseline_hash=content_hash,
        )
        return dataclasses.replace(self, common=common)


@dataclasses.dataclass(frozen=True, slots=True)
class RawDraft:
    """An editing session whose note could not be parsed.

    Attributes
    ----------
    common : DraftCommon
        Path, identity, reference, and baseline state.
    raw_text : str
        Complete raw file text.
    """

    common: DraftCommon
    raw_text: str

    @classmethod
    def from_unparsed(cls, page: "UnparsedPage", reference: NoteReference | None = None) -> Self:
        """Load a raw rescue draft from a page that did not parse.

        Parameters
        ----------
        page : UnparsedPage
            Page returned by the vault with a parse failure.
        reference : NoteReference | None
            Reference that requested the page, when the page already existed.

        Returns
        -------
        RawDraft
            Draft whose complete text is editable and whose labels are
            unavailable.
        """
        common = DraftCommon(
            path=page.path,
            identity=page.path.stem,
            reference=reference,
            baseline_body="",
            baseline_labels=None,
            baseline_raw_text=page.text,
            baseline_hash=page.content_hash,
        )
        return cls(common=common, raw_text=page.text)

    @property
    def path(self) -> Path | None:
        """Return the absolute note path, or ``None`` for a new draft."""
        return self.common.path

    @property
    def identity(self) -> str:
        """Return the filename stem that identifies the note."""
        return self.common.identity

    @property
    def reference(self) -> NoteReference | None:
        """Return the reference that opened a new draft, if any."""
        return self.common.reference

    @property
    def mode(self) -> DraftMode:
        """Return the raw rescue editing mode."""
        return DraftMode.RAW

    @property
    def labels(self) -> None:
        """Return ``None`` because raw rescue drafts have no editable labels."""
        return None

    @property
    def source(self) -> None:
        """Return ``None`` because raw rescue drafts have no parsed source."""
        return None

    @property
    def body(self) -> str:
        """Return an empty body because raw rescue text is the whole content."""
        return ""

    @property
    def baseline_body(self) -> str:
        """Return the body at the last read or write."""
        return self.common.baseline_body

    @property
    def baseline_labels(self) -> PageLabels | None:
        """Return the labels at the last read or write."""
        return self.common.baseline_labels

    @property
    def baseline_raw_text(self) -> str:
        """Return the raw text at the last read or write."""
        return self.common.baseline_raw_text

    @property
    def baseline_hash(self) -> str:
        """Return the content hash at the last read or write."""
        return self.common.baseline_hash

    @property
    def is_new(self) -> bool:
        """Return whether the draft has not been written to the vault yet."""
        return self.path is None

    @property
    def is_dirty(self) -> bool:
        """Return whether the raw text differs from the last baseline."""
        return self.raw_text != self.common.baseline_raw_text

    @property
    def display_title(self) -> str:
        """Return the identity as the display title."""
        return self.identity

    def with_raw_text(self, text: str) -> Self:
        """Return a raw rescue draft with replaced file text.

        Parameters
        ----------
        text : str
            Complete raw file text.

        Returns
        -------
        RawDraft
            New draft; the original is unchanged.
        """
        return dataclasses.replace(self, raw_text=text)

    def as_new(self) -> Self:
        """Return a copy that is treated as an unwritten new draft.

        Returns
        -------
        RawDraft
            Copy without a path or previous baseline.
        """
        common = dataclasses.replace(
            self.common,
            path=None,
            baseline_body="",
            baseline_labels=None,
            baseline_raw_text="",
            baseline_hash="",
        )
        return dataclasses.replace(self, common=common)

    def to_text(self) -> str:
        """Return the complete raw file text."""
        return self.raw_text

    def after_write(self, text: str, *, content_hash: str, path: Path | None = None) -> "Self | NormalDraft":
        """Return a draft whose baseline matches a successful write.

        Parameters
        ----------
        text : str
            Complete text written to disk.
        content_hash : str
            Hash of the written bytes, for the next conflict check.
        path : Path | None
            Path assigned by a creation, or ``None`` to keep the current path.

        Returns
        -------
        RawDraft | NormalDraft
            Raw draft with the new baseline, or a normal draft when the written
            text now parses and declares a note type.
        """
        effective_path = path if path is not None else self.path
        common = self.common.with_path(effective_path)
        try:
            document: NoteDocument | None = NoteDocument.from_text(text)
        except (AfanesError, ValueError):
            document = None
        if document is None or document.note_type is None:
            common = dataclasses.replace(
                common,
                baseline_raw_text=text,
                baseline_hash=content_hash,
            )
            return dataclasses.replace(self, common=common, raw_text=text)
        labels = PageLabels.from_document(document)
        common = dataclasses.replace(
            common,
            baseline_body=document.body,
            baseline_labels=labels,
            baseline_raw_text=text,
            baseline_hash=content_hash,
        )
        return NormalDraft(common=common, body=document.body, labels=labels, source=document)


type PageDraft = NormalDraft | RawDraft


class PageDraftFactory:
    """Build a page draft from the vault's parsed or unparsed page union."""

    @staticmethod
    def from_page(content: PageContent, reference: NoteReference | None = None) -> PageDraft:
        """Load a draft from a note read by the vault.

        Parameters
        ----------
        content : PageContent
            Parsed or unparsed page returned by the vault.
        reference : NoteReference | None
            Reference that requested the page, when the page already existed.

        Returns
        -------
        PageDraft
            Normal draft when the note parsed, or raw rescue draft when it did
            not.

        Notes
        -----
        The factory lives in this module so ``vault.py`` stays independent of
        the draft classes and the import graph remains acyclic.
        """
        if isinstance(content, ParsedPage):
            return NormalDraft.from_parsed(content, reference)
        return RawDraft.from_unparsed(content, reference)
