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
import afanes.models.note
from afanes.core.errors import AfanesError, NoteParseError
from afanes.core.frontmatter import NoteDocument
from afanes.core.vault import PageContent
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status


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


def parse_due_date(text: str) -> datetime.date | None:
    """Parse a due-date field as an ISO calendar date.

    Parameters
    ----------
    text : str
        Field text. Blank means no due date.

    Returns
    -------
    datetime.date | None
        Parsed date, or ``None`` when the field is blank.

    Raises
    ------
    NoteParseError
        If the non-blank text is not a valid ``YYYY-MM-DD`` date.
    """
    trimmed = text.strip()
    if not trimmed:
        return None
    try:
        return datetime.date.fromisoformat(trimmed)
    except ValueError as exc:
        message = "Enter the due date as YYYY-MM-DD or leave it empty"
        raise NoteParseError(message) from exc


def due_date_text_from_raw(value: object) -> str:
    """Return an editable due-date string from a loaded frontmatter value.

    Parameters
    ----------
    value : object
        Raw value of the ``due_date`` key. YAML normally loads an ISO date as a
        :class:`datetime.date`; strings and other values are preserved for
        display so the user can correct them.

    Returns
    -------
    str
        ISO date text for a date value, the original string, an empty string
        for ``None``, or a display string for any other value.
    """
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)


@dataclasses.dataclass(frozen=True, slots=True)
class PageLabels:
    """Frontmatter labels owned by the page editor.

    Attributes
    ----------
    note_type : NoteType
        Declared note type.
    category : ReferenceCategory | None
        Reference category, or ``None`` for an uncategorized reference or a
        non-reference note.
    status : Status | None
        Workflow status, or ``None`` when the key is absent.
    due_date_text : str
        Due-date field text exactly as shown in the editor.
    people : tuple[str, ...]
        Person identities assigned to the note, in display order.
    project : str | None
        Project identity assigned to the note, or ``None``.
    """

    note_type: NoteType
    category: ReferenceCategory | None = None
    status: Status | None = None
    due_date_text: str = ""
    people: tuple[str, ...] = ()
    project: str | None = None

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
            Labels populated from the document's type, category, status,
            due date, and frontmatter references.

        Raises
        ------
        NoteParseError
            If the document has no declared type.
        """
        if document.note_type is None:
            message = "Note has no type"
            raise NoteParseError(message)
        people = tuple(
            reference.name for reference in document.references if reference.scheme is ReferenceScheme.PERSON
        )
        project = next(
            (reference.name for reference in document.references if reference.scheme is ReferenceScheme.PROJECT),
            None,
        )
        return cls(
            note_type=document.note_type,
            category=document.category,
            status=document.status,
            due_date_text=due_date_text_from_raw(document.raw.get("due_date")),
            people=people,
            project=project,
        )

    @property
    def scheme(self) -> ReferenceScheme:
        """Return the reference scheme this label set belongs to.

        Returns
        -------
        ReferenceScheme
            Scheme derived from the type and category.
        """
        return afanes.core.links.scheme_for_note(self.note_type, self.category)

    @property
    def due_date(self) -> datetime.date | None:
        """Return the parsed due date, or ``None`` when absent or invalid.

        Returns
        -------
        datetime.date | None
            Parsed calendar date, or ``None``.
        """
        try:
            return parse_due_date(self.due_date_text)
        except NoteParseError:
            return None

    @property
    def due_date_error(self) -> str | None:
        """Return the due-date validation message, or ``None`` when valid.

        Returns
        -------
        str | None
            Actionable message for an invalid non-blank due date.
        """
        try:
            parse_due_date(self.due_date_text)
        except NoteParseError as exc:
            return str(exc)
        return None

    def with_type(self, note_type: NoteType) -> Self:
        """Return labels adjusted for a new note type.

        Parameters
        ----------
        note_type : NoteType
            New declared type.

        Returns
        -------
        PageLabels
            New labels. Category is kept only for references, and a status the
            new type does not allow is cleared.
        """
        category = self.category if note_type is NoteType.REFERENCE else None
        status = self.status if self.status in afanes.models.note.allowed_statuses(note_type) else None
        return dataclasses.replace(self, note_type=note_type, category=category, status=status)

    def with_category(self, category: ReferenceCategory | None) -> Self:
        """Return labels with a reference category.

        Parameters
        ----------
        category : ReferenceCategory | None
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
        if status is not None and status not in afanes.models.note.allowed_statuses(self.note_type):
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
            New labels carrying the text.
        """
        return dataclasses.replace(self, due_date_text=text)

    def with_people(self, people: tuple[str, ...]) -> Self:
        """Return labels with normalized person identities.

        Parameters
        ----------
        people : tuple[str, ...]
            Person identities. Surrounding whitespace is trimmed and blank
            entries are dropped; order is preserved.

        Returns
        -------
        PageLabels
            New labels with the person list replaced.
        """
        cleaned = tuple(name.strip() for name in people if name.strip())
        return dataclasses.replace(self, people=cleaned)

    def with_project(self, project: str | None) -> Self:
        """Return labels with a normalized project identity.

        Parameters
        ----------
        project : str | None
            Project identity, or ``None`` to clear it. Surrounding whitespace
            is trimmed and a blank value clears the project.

        Returns
        -------
        PageLabels
            New labels with the project replaced.
        """
        trimmed = None if project is None else project.strip() or None
        return dataclasses.replace(self, project=trimmed)


@dataclasses.dataclass(frozen=True, slots=True)
class PageDraft:
    """One editing session for a note page.

    Attributes
    ----------
    path : Path | None
        Absolute note path, or ``None`` for a new draft that has not been
        written yet.
    identity : str
        Filename stem that will identify the note.
    reference : NoteReference | None
        Reference that opened a new draft, or ``None`` for an existing page.
    mode : DraftMode
        Normal editing or raw rescue mode.
    body : str
        Editable Markdown body, including its heading. Empty in raw mode.
    labels : PageLabels | None
        Editable frontmatter labels, or ``None`` in raw mode.
    source : NoteDocument | None
        Parsed document whose unknown frontmatter keys and newline style are
        preserved, or ``None`` in raw mode.
    raw_text : str
        Complete raw file text in raw mode, or the text last read in normal
        mode.
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
    mode: DraftMode
    body: str
    labels: PageLabels | None
    source: NoteDocument | None
    raw_text: str
    baseline_body: str
    baseline_labels: PageLabels | None
    baseline_raw_text: str
    baseline_hash: str

    @classmethod
    def new(cls, reference: NoteReference) -> Self:
        """Build an empty draft for a page requested by a reference.

        Parameters
        ----------
        reference : NoteReference
            Missing reference that opened the draft.

        Returns
        -------
        PageDraft
            Draft with the reference name as its heading, the scheme's type,
            and no other content. It is clean until the body or a label
            changes.

        Notes
        -----
        ``note:`` and ``person:`` references create a reference note;
        ``person:`` additionally sets category ``person``. ``project:``
        references create a project. The reference wording is preserved in the
        heading even when the identity is sanitized.
        """
        if reference.scheme is ReferenceScheme.PERSON:
            note_type = NoteType.REFERENCE
            category: ReferenceCategory | None = ReferenceCategory.PERSON
        elif reference.scheme is ReferenceScheme.PROJECT:
            note_type = NoteType.PROJECT
            category = None
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
            references=(),
            category=category,
            status=None,
        )
        labels = PageLabels.from_document(document)
        identity = afanes.core.names.safe_filename(reference.name)
        template = document.to_text()
        return cls(
            path=None,
            identity=identity,
            reference=reference,
            mode=DraftMode.NORMAL,
            body=body,
            labels=labels,
            source=document,
            raw_text=template,
            baseline_body=body,
            baseline_labels=labels,
            baseline_raw_text=template,
            baseline_hash="",
        )

    @classmethod
    def from_page(cls, content: PageContent, reference: NoteReference | None = None) -> Self:
        """Load a draft from a note read by the vault.

        Parameters
        ----------
        content : PageContent
            Raw text, hash, and parsed document returned by the vault.
        reference : NoteReference | None
            Reference that requested the page, when the page already existed.

        Returns
        -------
        PageDraft
            Normal draft when the note parsed, or raw rescue draft when it did
            not.

        Raises
        ------
        NoteParseError
            If the parsed document has no declared type.
        """
        if content.document is None:
            return cls(
                path=content.path,
                identity=content.path.stem,
                reference=reference,
                mode=DraftMode.RAW,
                body="",
                labels=None,
                source=None,
                raw_text=content.text,
                baseline_body="",
                baseline_labels=None,
                baseline_raw_text=content.text,
                baseline_hash=content.content_hash,
            )

        labels = PageLabels.from_document(content.document)
        return cls(
            path=content.path,
            identity=content.path.stem,
            reference=reference,
            mode=DraftMode.NORMAL,
            body=content.document.body,
            labels=labels,
            source=content.document,
            raw_text=content.text,
            baseline_body=content.document.body,
            baseline_labels=labels,
            baseline_raw_text=content.text,
            baseline_hash=content.content_hash,
        )

    @property
    def is_new(self) -> bool:
        """Return whether the draft has not been written to the vault yet.

        Returns
        -------
        bool
            ``True`` when the draft has no path.
        """
        return self.path is None

    @property
    def is_dirty(self) -> bool:
        """Return whether the draft differs from its last read or write.

        Returns
        -------
        bool
            ``True`` when the editable body or labels changed in normal mode,
            or the raw text changed in raw mode.
        """
        if self.mode is DraftMode.RAW:
            return self.raw_text != self.baseline_raw_text
        return self.body != self.baseline_body or self.labels != self.baseline_labels

    @property
    def display_title(self) -> str:
        """Return the title derived from the current draft body.

        Returns
        -------
        str
            First level-1 heading text, or :attr:`identity` when the body has
            no level-1 heading or the draft is in raw mode.
        """
        if self.mode is DraftMode.RAW or self.source is None:
            return self.identity
        return self.source.with_body(self.body).title or self.identity

    def as_new(self) -> Self:
        """Return a copy that is treated as an unwritten new draft.

        Returns
        -------
        PageDraft
            Copy without a path or previous baseline, so the next save creates
            the page again.

        Notes
        -----
        Used when a just-created page is removed after the user cancels the
        unsafe-link repair. The body and labels are retained in memory.
        """
        return dataclasses.replace(
            self,
            path=None,
            baseline_body="",
            baseline_labels=None,
            baseline_raw_text="",
            baseline_hash="",
        )

    def with_body(self, body: str) -> Self:
        """Return a draft with a replaced Markdown body.

        Parameters
        ----------
        body : str
            New complete body.

        Returns
        -------
        PageDraft
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
        PageDraft
            New draft; the original is unchanged.

        Raises
        ------
        NoteParseError
            If the draft is in raw rescue mode and has no labels.
        """
        if self.labels is None:
            message = "Raw rescue pages do not have editable labels"
            raise NoteParseError(message)
        return dataclasses.replace(self, labels=labels)

    def with_raw_text(self, text: str) -> Self:
        """Return a raw rescue draft with replaced file text.

        Parameters
        ----------
        text : str
            Complete raw file text.

        Returns
        -------
        PageDraft
            New draft; the original is unchanged.
        """
        return dataclasses.replace(self, raw_text=text)

    def to_text(self) -> str:
        """Serialize the draft into complete note text.

        Returns
        -------
        str
            Raw text in rescue mode, or frontmatter plus the edited body in
            normal mode. Unknown keys, the newline style, and untouched values
            are preserved.

        Raises
        ------
        NoteParseError
            If the due date is invalid, the labels are missing, or the edited
            metadata is not valid for the note type.
        """
        if self.mode is DraftMode.RAW:
            return self.raw_text
        labels = self.labels
        source = self.source
        if labels is None or source is None:
            message = "Normal drafts require labels and a source document"
            raise NoteParseError(message)
        if labels.due_date_error is not None:
            raise NoteParseError(labels.due_date_error)

        raw = dict(source.raw)
        raw["type"] = labels.note_type.value
        if labels.category is None:
            raw.pop("category", None)
        else:
            raw["category"] = labels.category.value
        if labels.status is None:
            raw.pop("status", None)
        else:
            raw["status"] = labels.status.value
        due_date = labels.due_date
        if due_date is None:
            raw.pop("due_date", None)
        else:
            raw["due_date"] = due_date.isoformat()
        if labels.people:
            raw["people"] = [f"{ReferenceScheme.PERSON.value}:{name}" for name in labels.people]
        else:
            raw.pop("people", None)
        if labels.project is None:
            raw.pop("project", None)
        else:
            raw["project"] = f"{ReferenceScheme.PROJECT.value}:{labels.project}"

        document = source.with_body(self.body).with_metadata(raw)
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
        PageDraft
            New draft with updated baselines. A raw rescue draft whose text now
            parses upgrades to normal mode; otherwise it stays raw.

        Notes
        -----
        The method performs no I/O and never validates the text unless it is
        deciding whether a raw draft can upgrade.
        """
        effective_path = path if path is not None else self.path
        if self.mode is DraftMode.RAW:
            document: NoteDocument | None
            try:
                document = NoteDocument.from_text(text)
            except (AfanesError, ValueError):
                document = None
            if document is None or document.note_type is None:
                return dataclasses.replace(
                    self,
                    path=effective_path,
                    raw_text=text,
                    baseline_raw_text=text,
                    baseline_hash=content_hash,
                )
            labels = PageLabels.from_document(document)
            return dataclasses.replace(
                self,
                path=effective_path,
                identity=effective_path.stem if effective_path is not None else self.identity,
                mode=DraftMode.NORMAL,
                body=document.body,
                labels=labels,
                source=document,
                raw_text=text,
                baseline_body=document.body,
                baseline_labels=labels,
                baseline_raw_text=text,
                baseline_hash=content_hash,
            )
        return dataclasses.replace(
            self,
            path=effective_path,
            identity=effective_path.stem if effective_path is not None else self.identity,
            baseline_body=self.body,
            baseline_labels=self.labels,
            baseline_raw_text=text,
            baseline_hash=content_hash,
        )
