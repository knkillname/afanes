# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Processing outcomes and the plan that describes one clarification step."""

import dataclasses
import datetime
from enum import StrEnum
from pathlib import Path

import afanes.models.note
from afanes.core.errors import ProcessingError
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
        _validate_common(self)
        _validate_outcome(self)


def _validate_common(plan: ProcessingPlan) -> None:
    """Validate path, hash, count, and reference invariants."""
    if not plan.source_path.is_absolute() or not plan.target_path.is_absolute():
        message = "Processing plan paths must be absolute"
        raise ProcessingError(message)
    if plan.source_path == plan.target_path:
        message = "Processing source and destination must differ"
        raise ProcessingError(message)
    if not plan.source_hash or not plan.processed_hash:
        message = "Processing plan hashes must not be empty"
        raise ProcessingError(message)
    if plan.reference_count < 0:
        message = "Processing reference count must not be negative"
        raise ProcessingError(message)
    if any(reference.scheme is not ReferenceScheme.PERSON for reference in plan.people):
        message = "Processing people must be person references"
        raise ProcessingError(message)
    if plan.project is not None and plan.project.scheme is not ReferenceScheme.PROJECT:
        message = "Processing project must be a project reference"
        raise ProcessingError(message)


def _validate_outcome(plan: ProcessingPlan) -> None:
    """Validate metadata against the selected outcome."""
    if plan.outcome is ProcessingOutcome.TRASH:
        if plan.people or plan.project is not None or plan.due_date is not None:
            message = "Trash does not accept assignment metadata"
            raise ProcessingError(message)
        return
    if plan.outcome in (ProcessingOutcome.LATER, ProcessingOutcome.REFERENCE):
        _validate_reference_outcome(plan)
        return
    if plan.outcome in (ProcessingOutcome.ACTION, ProcessingOutcome.PROJECT):
        _validate_actionable_outcome(plan)
        return
    message = f"Unsupported processing outcome: {plan.outcome!r}"
    raise ProcessingError(message)


def _validate_reference_outcome(plan: ProcessingPlan) -> None:
    """Validate Later and Reference metadata."""
    if plan.target_type is not NoteType.REFERENCE or plan.target_category is not None:
        message = "Reference outcomes must be uncategorized references"
        raise ProcessingError(message)
    if plan.due_date is not None or plan.project is not None:
        message = "Reference outcomes do not accept a due date or project"
        raise ProcessingError(message)
    expected_status = Status.LATER if plan.outcome is ProcessingOutcome.LATER else None
    if plan.target_status is not expected_status:
        message = "Reference outcome status does not match the outcome"
        raise ProcessingError(message)


def _validate_actionable_outcome(plan: ProcessingPlan) -> None:
    """Validate Action and Project metadata."""
    if plan.target_category is not None:
        message = "Processing outcomes do not assign a category"
        raise ProcessingError(message)
    if plan.target_status is None or plan.target_status not in afanes.models.note.allowed_statuses(plan.target_type):
        message = "Processing status is not valid for the target type"
        raise ProcessingError(message)
    if plan.outcome is ProcessingOutcome.ACTION:
        if plan.target_type is not NoteType.ACTION:
            message = "Action outcome must target an action note"
            raise ProcessingError(message)
        return
    if plan.target_type is not NoteType.PROJECT:
        message = "Project outcome must target a project note"
        raise ProcessingError(message)
    if plan.project is not None:
        message = "Project outcome must not declare a project reference"
        raise ProcessingError(message)
