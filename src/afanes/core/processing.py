# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Processing outcomes and the plans that describe one clarification step."""

import dataclasses
import datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Self

from afanes.core.errors import ProcessingError
from afanes.core.frontmatter import NoteDocument
from afanes.core.labels import PageLabels
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status


class ProcessingOutcome(StrEnum):
    """Outcomes available when clarifying an inbox capture.

    Attributes
    ----------
    TRASH : str
        Move the capture to the vault-local trash folder.
    LATER : str
        Keep the capture as a reference deferred for later attention.
    REFERENCE : str
        Keep the capture as an available reference.
    PROJECT : str
        Turn the capture into a project whose body holds the steps.
    APPEND_STEP : str
        Add the capture as a step of an existing project and trash it.
    DONE_NOW : str
        Write a completed one-step project.
    LOG : str
        Turn the capture into a dated log entry.
    """

    TRASH = "trash"
    LATER = "later"
    REFERENCE = "reference"
    PROJECT = "project"
    APPEND_STEP = "append_step"
    DONE_NOW = "done_now"
    LOG = "log"


_FIXED_OUTCOME_STATUS = MappingProxyType(
    {
        ProcessingOutcome.LATER: Status.LATER,
        ProcessingOutcome.REFERENCE: None,
        ProcessingOutcome.DONE_NOW: Status.DONE,
        ProcessingOutcome.LOG: None,
    }
)
_FIXED_STATUS_MESSAGE = MappingProxyType(
    {
        ProcessingOutcome.LATER: "Later uses the later status",
        ProcessingOutcome.REFERENCE: "Reference outcomes do not accept a status",
        ProcessingOutcome.DONE_NOW: "Done now uses the done status",
        ProcessingOutcome.LOG: "Log outcomes do not accept a status",
    }
)


@dataclasses.dataclass(frozen=True, slots=True)
class ProcessingTarget:
    """Type and status a processing outcome produces.

    Attributes
    ----------
    note_type : NoteType
        Type the note will have after applying the plan.
    status : Status | None
        Status the target will carry, or ``None`` when the key is removed.
    """

    note_type: NoteType
    status: Status | None

    @classmethod
    def from_outcome(cls, outcome: ProcessingOutcome, status: Status | None) -> Self:
        """Resolve the target type and status for a processing outcome.

        Parameters
        ----------
        outcome : ProcessingOutcome
            Selected clarification outcome.
        status : Status | None
            Requested target status, or ``None`` to use the outcome default.

        Returns
        -------
        ProcessingTarget
            Validated target type and status.

        Raises
        ------
        ProcessingError
            If the outcome does not produce a note, does not accept the
            requested status, or the status is not valid for the target type.
        """
        if outcome is ProcessingOutcome.LATER:
            return cls(note_type=NoteType.REFERENCE, status=cls._validate_status(outcome, status))
        if outcome is ProcessingOutcome.REFERENCE:
            return cls(note_type=NoteType.REFERENCE, status=cls._validate_status(outcome, status))
        if outcome is ProcessingOutcome.DONE_NOW:
            return cls(note_type=NoteType.PROJECT, status=cls._validate_status(outcome, status))
        if outcome is ProcessingOutcome.PROJECT:
            return cls(note_type=NoteType.PROJECT, status=cls._validate_status(outcome, status))
        if outcome is ProcessingOutcome.LOG:
            return cls(note_type=NoteType.LOG, status=cls._validate_status(outcome, status))
        message = f"Outcome {outcome.value!r} does not target a note"
        raise ProcessingError(message)

    @staticmethod
    def _validate_status(outcome: ProcessingOutcome, status: Status | None) -> Status | None:
        """Return the validated status for a note-producing outcome.

        Parameters
        ----------
        outcome : ProcessingOutcome
            Selected clarification outcome.
        status : Status | None
            Requested status, or ``None``.

        Returns
        -------
        Status | None
            Status written to the target, or ``None``.

        Raises
        ------
        ProcessingError
            If the outcome does not accept the requested status.
        """
        if outcome is ProcessingOutcome.PROJECT:
            target_status = status or Status.ACTIVE
            if target_status not in NoteType.PROJECT.allowed_statuses:
                message = "Status is not valid for a project"
                raise ProcessingError(message)
            return target_status
        if outcome not in _FIXED_OUTCOME_STATUS:
            message = f"Outcome {outcome.value!r} does not target a note"
            raise ProcessingError(message)
        expected = _FIXED_OUTCOME_STATUS[outcome]
        if status not in (None, expected):
            raise ProcessingError(_FIXED_STATUS_MESSAGE[outcome])
        return expected


@dataclasses.dataclass(frozen=True, slots=True)
class ProcessingPlan:
    """One validated clarification step that writes a single note.

    Attributes
    ----------
    source_path : Path
        Absolute path to the capture in ``inbox/``.
    target_path : Path
        Absolute destination inside the vault.
    outcome : ProcessingOutcome
        Selected clarification outcome.
    target_type : NoteType
        Type the note will have after applying the plan.
    target_status : Status | None
        Status the target will carry, or ``None`` when the key is removed.
    due_date : datetime.date | None
        Optional calendar due date for a project.
    body_override : str | None
        Complete replacement body, or ``None`` to preserve the capture body.
    category : CategoryLabel | None
        Reference category applied to the note, or ``None`` for outcomes that
        do not produce a reference.
    scaffold : str | None
        Starter body appended below the capture text, or ``None`` when the
        chosen card has no starter body.
    source_hash : str
        SHA-256 of the source bytes captured while planning.
    processed_hash : str
        SHA-256 of the classified note text, or the source hash for Trash.
    reference_count : int
        Number of inbound references to the source.
    affected_notes : tuple[Path, ...]
        Notes containing at least one inbound reference.
    changes_scheme : bool
        Whether the outcome moves the note to a different reference scheme.
    target_date : NoteDate | None
        Date written by a log outcome, or ``None`` for every other outcome.

    Notes
    -----
    Build plans through ``VaultProcessing.plan_processing``. Direct construction is
    validated for local invariants so a malformed plan cannot reach the apply
    step. Append step uses :class:`AppendStepPlan` instead.
    """

    source_path: Path
    target_path: Path
    outcome: ProcessingOutcome
    target_type: NoteType
    target_status: Status | None
    due_date: datetime.date | None
    body_override: str | None
    category: CategoryLabel | None
    scaffold: str | None
    source_hash: str
    processed_hash: str
    reference_count: int
    affected_notes: tuple[Path, ...]
    changes_scheme: bool
    target_date: NoteDate | None = None

    def __post_init__(self) -> None:
        """Validate the plan's local invariants.

        Raises
        ------
        ProcessingError
            If a path is not absolute, a hash is empty, the destination equals
            the source, or the metadata does not match the selected outcome.
        """
        self._validate_common()
        self._validate_outcome()

    def processed_text(self, document: NoteDocument) -> str:
        """Apply this plan's classification to a parsed document.

        Parameters
        ----------
        document : NoteDocument
            Current capture document. Its unknown keys and newline style are
            preserved.

        Returns
        -------
        str
            Classified Markdown text. Trash plans return the document
            unchanged because the file is moved without rewriting it.
        """
        if self.outcome is ProcessingOutcome.TRASH:
            return document.to_text()

        labels = PageLabels.from_document(document).with_type(self.target_type)
        labels = labels.with_status(self.target_status)
        labels = labels.with_category(self.category)
        labels = labels.with_due_date_text("" if self.due_date is None else self.due_date.isoformat())
        if self.target_date is not None:
            labels = labels.with_date_text(self.target_date.text)
        body = document.body if self.body_override is None else self.body_override
        if self.scaffold is not None:
            body = self._append_scaffold(body, document.newline)
        return labels.apply_to(document.with_body(body)).to_text()

    def _append_scaffold(self, body: str, newline: str) -> str:
        """Append the starter body below the capture text.

        Parameters
        ----------
        body : str
            Capture body, or the body override, in the document's newline style.
        newline : str
            Newline sequence used by the document.

        Returns
        -------
        str
            Body whose original text remains a prefix, followed by the starter
            body and a final newline. An empty scaffold leaves the body
            unchanged.
        """
        scaffold = (self.scaffold or "").replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        if not scaffold:
            return body
        normalized = scaffold.replace("\n", newline)
        prefix = body.rstrip("\r\n")
        if not prefix:
            return f"{normalized}{newline}"
        return f"{prefix}{newline}{newline}{normalized}{newline}"

    def _validate_common(self) -> None:
        """Validate path, hash, and count invariants."""
        if not self.source_path.is_absolute() or not self.target_path.is_absolute():
            message = "Processing plan paths must be absolute"
            raise ProcessingError(message)
        if self.source_path == self.target_path:
            message = "Processing source and destination must differ"
            raise ProcessingError(message)
        if not self.source_hash or not self.processed_hash:
            message = "Processing plan hashes must not be empty"
            raise ProcessingError(message)
        if self.reference_count < 0:
            message = "Processing reference count must not be negative"
            raise ProcessingError(message)

    def _validate_outcome(self) -> None:
        """Validate metadata against the selected outcome."""
        if self.outcome is ProcessingOutcome.APPEND_STEP:
            message = "Append step uses an append plan"
            raise ProcessingError(message)
        if self.outcome is ProcessingOutcome.TRASH:
            if self.due_date is not None:
                message = "Trash does not accept assignment metadata"
                raise ProcessingError(message)
            if self.category is not None or self.scaffold is not None:
                message = "Trash does not accept a category or starter body"
                raise ProcessingError(message)
            return
        if self.outcome in (ProcessingOutcome.LATER, ProcessingOutcome.REFERENCE):
            self._validate_reference_outcome()
            return
        if self.outcome is ProcessingOutcome.LOG:
            self._validate_log_outcome()
            return
        self._validate_project_outcome()

    def _validate_log_outcome(self) -> None:
        """Validate Log entry metadata."""
        if self.target_type is not NoteType.LOG:
            message = "Log outcomes must target a log note"
            raise ProcessingError(message)
        if self.target_status is not None:
            message = "Log outcomes do not accept a status"
            raise ProcessingError(message)
        if self.target_date is None:
            message = "Log outcomes need a date"
            raise ProcessingError(message)
        if self.due_date is not None:
            message = "Log outcomes do not accept a due date"
            raise ProcessingError(message)
        if self.category is not None or self.scaffold is not None:
            message = "Log outcomes do not accept a category or starter body"
            raise ProcessingError(message)

    def _validate_reference_outcome(self) -> None:
        """Validate Later and Reference metadata."""
        if self.target_type is not NoteType.REFERENCE:
            message = "Reference outcomes must target a reference note"
            raise ProcessingError(message)
        if self.due_date is not None:
            message = "Reference outcomes do not accept a due date"
            raise ProcessingError(message)
        if self.category is None:
            message = "Reference outcomes need a category"
            raise ProcessingError(message)
        expected_status = Status.LATER if self.outcome is ProcessingOutcome.LATER else None
        if self.target_status is not expected_status:
            message = "Reference outcome status does not match the outcome"
            raise ProcessingError(message)

    def _validate_project_outcome(self) -> None:
        """Validate Project and Done now metadata."""
        if self.target_type is not NoteType.PROJECT:
            message = "Project outcomes must target a project note"
            raise ProcessingError(message)
        if self.target_status is None or self.target_status not in self.target_type.allowed_statuses:
            message = "Processing status is not valid for the target type"
            raise ProcessingError(message)
        if self.outcome is ProcessingOutcome.DONE_NOW and self.target_status is not Status.DONE:
            message = "Done now must complete the project"
            raise ProcessingError(message)
        if self.category is not None or self.scaffold is not None:
            message = "Project outcomes do not accept a category or starter body"
            raise ProcessingError(message)


@dataclasses.dataclass(frozen=True, slots=True)
class AppendStepPlan:
    """One validated append of an inbox capture into an existing project.

    Attributes
    ----------
    capture_path : Path
        Absolute path to the capture in ``inbox/``.
    project_path : Path
        Absolute path to the target project note.
    step_text : str
        First non-blank capture line, written as the step text.
    detail : str
        Remaining capture body, written indented beneath the step.
    capture_hash : str
        SHA-256 of the capture bytes captured while planning.
    project_hash : str
        SHA-256 of the project bytes captured while planning.

    Notes
    -----
    Build plans through ``VaultProcessing.plan_append_step``. Apply writes the project
    first and trashes the capture second, so a failure never loses the step.
    """

    capture_path: Path
    project_path: Path
    step_text: str
    detail: str
    capture_hash: str
    project_hash: str

    def __post_init__(self) -> None:
        """Validate the append plan's local invariants.

        Raises
        ------
        ProcessingError
            If a path is not absolute, a hash is empty, the step is blank, or
            the capture and project are the same file.
        """
        if not self.capture_path.is_absolute() or not self.project_path.is_absolute():
            message = "Append plan paths must be absolute"
            raise ProcessingError(message)
        if self.capture_path == self.project_path:
            message = "Append plan capture and project must differ"
            raise ProcessingError(message)
        if not self.step_text.strip():
            message = "An appended step needs text"
            raise ProcessingError(message)
        if not self.capture_hash or not self.project_hash:
            message = "Append plan hashes must not be empty"
            raise ProcessingError(message)
