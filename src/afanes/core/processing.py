# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Processing outcomes and the plan that describes one clarification step."""

import dataclasses
import datetime
from enum import StrEnum
from pathlib import Path
from typing import Self

from afanes.core.errors import ProcessingError
from afanes.core.frontmatter import NoteDocument
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status


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
    ACTION : str
        Turn the capture into a single action.
    PROJECT : str
        Turn the capture into a project outcome.
    """

    TRASH = "trash"
    LATER = "later"
    REFERENCE = "reference"
    ACTION = "action"
    PROJECT = "project"


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
            If the outcome does not accept the requested status or the status
            is not valid for the target type.
        """
        if outcome is ProcessingOutcome.LATER:
            if status not in (None, Status.LATER):
                message = "Later uses the later status"
                raise ProcessingError(message)
            return cls(note_type=NoteType.REFERENCE, status=Status.LATER)
        if outcome is ProcessingOutcome.REFERENCE:
            if status is not None:
                message = "Reference outcomes do not accept a status"
                raise ProcessingError(message)
            return cls(note_type=NoteType.REFERENCE, status=None)
        if outcome is ProcessingOutcome.ACTION:
            target_status = status or Status.ACTIVE
            if target_status not in NoteType.ACTION.allowed_statuses:
                message = "Status is not valid for an action"
                raise ProcessingError(message)
            return cls(note_type=NoteType.ACTION, status=target_status)
        if outcome is ProcessingOutcome.PROJECT:
            target_status = status or Status.ACTIVE
            if target_status not in NoteType.PROJECT.allowed_statuses:
                message = "Status is not valid for a project"
                raise ProcessingError(message)
            return cls(note_type=NoteType.PROJECT, status=target_status)
        message = f"Unsupported processing outcome: {outcome!r}"
        raise ProcessingError(message)


@dataclasses.dataclass(frozen=True, slots=True)
class ProcessingPlan:
    """One validated clarification step for an inbox capture.

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
    target_category : ReferenceCategory | None
        Reference category for the target, always ``None`` for processing
        outcomes in this change.
    target_status : Status | None
        Status the target will carry, or ``None`` when the key is removed.
    due_date : datetime.date | None
        Optional calendar due date for an action or project.
    people : tuple[NoteReference, ...]
        Person references assigned by the plan.
    project : NoteReference | None
        Project reference assigned to an action.
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
    unresolved_references : tuple[NoteReference, ...]
        Planned person or project references that do not resolve yet.

    Notes
    -----
    Build plans through ``Vault.plan_processing``. Direct construction is
    validated for local invariants so a malformed plan cannot reach the apply
    step.
    """

    source_path: Path
    target_path: Path
    outcome: ProcessingOutcome
    target_type: NoteType
    target_category: ReferenceCategory | None
    target_status: Status | None
    due_date: datetime.date | None
    people: tuple[NoteReference, ...]
    project: NoteReference | None
    source_hash: str
    processed_hash: str
    reference_count: int
    affected_notes: tuple[Path, ...]
    changes_scheme: bool
    unresolved_references: tuple[NoteReference, ...]

    def __post_init__(self) -> None:
        """Validate the plan's local invariants.

        Raises
        ------
        ProcessingError
            If a path is not absolute, a hash is empty, a reference has the
            wrong scheme, the destination equals the source, or the metadata
            does not match the selected outcome.
        """
        self._validate_common()
        self._validate_outcome()

    def processed_text(self, document: NoteDocument) -> str:
        """Apply this plan's classification to a parsed document.

        Parameters
        ----------
        document : NoteDocument
            Current capture document. Its unknown keys, body, and newline style
            are preserved.

        Returns
        -------
        str
            Classified Markdown text. Trash plans return the document
            unchanged because the file is moved without rewriting it.
        """
        if self.outcome is ProcessingOutcome.TRASH:
            return document.to_text()

        raw = dict(document.raw)
        raw["type"] = self.target_type.value
        if self.target_category is None:
            raw.pop("category", None)
        else:
            raw["category"] = self.target_category.value
        if self.target_status is None:
            raw.pop("status", None)
        else:
            raw["status"] = self.target_status.value
        if self.due_date is None:
            raw.pop("due_date", None)
        else:
            raw["due_date"] = self.due_date.isoformat()
        if self.people:
            raw["people"] = [f"{reference.scheme.value}:{reference.name}" for reference in self.people]
        else:
            raw.pop("people", None)
        if self.project is None:
            raw.pop("project", None)
        else:
            raw["project"] = f"{self.project.scheme.value}:{self.project.name}"
        return document.with_metadata(raw).to_text()

    def _validate_common(self) -> None:
        """Validate path, hash, count, and reference invariants."""
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
        if any(reference.scheme is not ReferenceScheme.PERSON for reference in self.people):
            message = "Processing people must be person references"
            raise ProcessingError(message)
        if self.project is not None and self.project.scheme is not ReferenceScheme.PROJECT:
            message = "Processing project must be a project reference"
            raise ProcessingError(message)

    def _validate_outcome(self) -> None:
        """Validate metadata against the selected outcome."""
        if self.outcome is ProcessingOutcome.TRASH:
            if self.people or self.project is not None or self.due_date is not None:
                message = "Trash does not accept assignment metadata"
                raise ProcessingError(message)
            return
        if self.outcome in (ProcessingOutcome.LATER, ProcessingOutcome.REFERENCE):
            self._validate_reference_outcome()
            return
        if self.outcome in (ProcessingOutcome.ACTION, ProcessingOutcome.PROJECT):
            self._validate_actionable_outcome()
            return
        message = f"Unsupported processing outcome: {self.outcome!r}"
        raise ProcessingError(message)

    def _validate_reference_outcome(self) -> None:
        """Validate Later and Reference metadata."""
        if self.target_type is not NoteType.REFERENCE or self.target_category is not None:
            message = "Reference outcomes must be uncategorized references"
            raise ProcessingError(message)
        if self.due_date is not None or self.project is not None:
            message = "Reference outcomes do not accept a due date or project"
            raise ProcessingError(message)
        expected_status = Status.LATER if self.outcome is ProcessingOutcome.LATER else None
        if self.target_status is not expected_status:
            message = "Reference outcome status does not match the outcome"
            raise ProcessingError(message)

    def _validate_actionable_outcome(self) -> None:
        """Validate Action and Project metadata."""
        if self.target_category is not None:
            message = "Processing outcomes do not assign a category"
            raise ProcessingError(message)
        if self.target_status is None or self.target_status not in self.target_type.allowed_statuses:
            message = "Processing status is not valid for the target type"
            raise ProcessingError(message)
        if self.outcome is ProcessingOutcome.ACTION:
            if self.target_type is not NoteType.ACTION:
                message = "Action outcome must target an action note"
                raise ProcessingError(message)
            return
        if self.target_type is not NoteType.PROJECT:
            message = "Project outcome must target a project note"
            raise ProcessingError(message)
        if self.project is not None:
            message = "Project outcome must not declare a project reference"
            raise ProcessingError(message)
