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
from enum import StrEnum
from pathlib import Path
from typing import Self

import afanes.core.links
import afanes.core.names
from afanes.core.errors import AfanesError, NoteParseError
from afanes.core.frontmatter import NoteDocument
from afanes.core.labels import PageLabels
from afanes.core.vault.snapshot import PageContent, ParsedPage, UnparsedPage
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType


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
        note_type = NoteType.PROJECT if reference.scheme is ReferenceScheme.PROJECT else NoteType.REFERENCE

        body = f"# {reference.name}\n\n"
        document = NoteDocument(
            raw={},
            body=body,
            newline="\n",
            has_frontmatter=True,
            note_type=None,
        )
        labels = PageLabels(note_type=note_type)
        document = labels.apply_to(document)
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
        if self.labels.date_error is not None:
            raise NoteParseError(self.labels.date_error)
        self._reject_log_date_change()
        document = self.labels.apply_to(self.source.with_body(self.body))
        return document.to_text()

    def _reject_log_date_change(self) -> None:
        """Refuse a log date edited through the draft.

        Raises
        ------
        NoteParseError
            If a log entry has no date or its date differs from its filename
            date. A log date change must use the dedicated date command.
        """
        note_date = self.labels.date
        if self.source.note_type is NoteType.LOG:
            if note_date is None:
                message = "A log entry needs a date"
                raise NoteParseError(message)
            if self.source.date is not None and note_date != self.source.date:
                message = "Change a log entry's date from the Date field"
                raise NoteParseError(message)

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
