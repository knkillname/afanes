# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tick, edit, and append project steps in a project body.

One step is rewritten per call and the write stays atomic. Path containment and
the atomic write primitive stay on :class:`afanes.core.vault.service.Vault`.
"""

import dataclasses
import datetime
import hashlib
from collections.abc import Callable, Iterable
from pathlib import Path

import afanes.core.atomic
import afanes.core.steps
import afanes.models.step
from afanes.core.errors import VaultError
from afanes.core.frontmatter import NoteDocument
from afanes.core.vault.service import Vault
from afanes.models.note import NoteType


@dataclasses.dataclass(frozen=True, slots=True)
class VaultSteps:
    """Tick, edit, and append steps of one project note.

    Attributes
    ----------
    vault : Vault
        Resolved vault that owns path containment and the storage layout.
    """

    vault: Vault

    def tick_step(
        self,
        note_path: Path,
        line_index: int,
        completed_on: datetime.date,
        *,
        confirm: bool = False,
    ) -> str:
        """Check one project step and record its actual date.

        Parameters
        ----------
        note_path : Path
            Path to an existing project note.
        line_index : int
            Zero-based body line of the step.
        completed_on : datetime.date
            Calendar date written as ``actual``.
        confirm : bool
            Explicit confirmation gate.

        Returns
        -------
        str
            SHA-256 digest of the written bytes.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not a project, or the line
            is not a step.
        StepEditError
            If the step cannot be rewritten safely.
        StepMetadataError
            If the metadata cannot be written as one valid comment.
        """
        return self._write_step(
            note_path,
            line_index,
            lambda document, step: document.tick(step, completed_on),
            confirm=confirm,
        )

    def untick_step(self, note_path: Path, line_index: int, *, confirm: bool = False) -> str:
        """Reopen one project step and remove its actual date.

        Parameters
        ----------
        note_path : Path
            Path to an existing project note.
        line_index : int
            Zero-based body line of the step.
        confirm : bool
            Explicit confirmation gate.

        Returns
        -------
        str
            SHA-256 digest of the written bytes.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not a project, or the line
            is not a step.
        StepEditError
            If the step cannot be rewritten safely.
        StepMetadataError
            If the metadata cannot be written as one valid comment.
        """
        return self._write_step(
            note_path,
            line_index,
            lambda document, step: document.untick(step),
            confirm=confirm,
        )

    def plan_step(
        self,
        note_path: Path,
        line_index: int,
        plan: datetime.date | None,
        *,
        confirm: bool = False,
    ) -> str:
        """Replace one project step's plan date.

        Parameters
        ----------
        note_path : Path
            Path to an existing project note.
        line_index : int
            Zero-based body line of the step.
        plan : datetime.date | None
            New plan date, or ``None`` to remove it.
        confirm : bool
            Explicit confirmation gate.

        Returns
        -------
        str
            SHA-256 digest of the written bytes.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not a project, or the line
            is not a step.
        StepEditError
            If the step cannot be rewritten safely.
        StepMetadataError
            If the metadata cannot be written as one valid comment.
        """
        return self._write_step(
            note_path,
            line_index,
            lambda document, step: document.with_plan(step, plan),
            confirm=confirm,
        )

    def set_step_owners(
        self,
        note_path: Path,
        line_index: int,
        owners: Iterable[str],
        *,
        confirm: bool = False,
    ) -> str:
        """Replace one project step's owner list.

        Parameters
        ----------
        note_path : Path
            Path to an existing project note.
        line_index : int
            Zero-based body line of the step.
        owners : Iterable[str]
            New owner names. An empty result makes the step the user's own
            work again.
        confirm : bool
            Explicit confirmation gate.

        Returns
        -------
        str
            SHA-256 digest of the written bytes.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not a project, or the line
            is not a step.
        StepEditError
            If the step cannot be rewritten safely.
        StepMetadataError
            If the metadata cannot be written as one valid comment.
        """
        return self._write_step(
            note_path,
            line_index,
            lambda document, step: document.with_owners(step, owners),
            confirm=confirm,
        )

    def append_step(
        self,
        note_path: Path,
        text: str,
        detail: str = "",
        *,
        confirm: bool = False,
    ) -> str:
        """Append one unchecked step to a project body.

        Parameters
        ----------
        note_path : Path
            Path to an existing project note.
        text : str
            Step text. It must contain a non-blank line.
        detail : str
            Optional prose written indented beneath the step.
        confirm : bool
            Explicit confirmation gate.

        Returns
        -------
        str
            SHA-256 digest of the written bytes.

        Raises
        ------
        VaultError
            If confirmation is missing or the note is not a project.
        StepEditError
            If the step text is blank.
        StepMetadataError
            If metadata cannot be written as one valid comment.
        """
        if not confirm:
            message = "Changing a step requires explicit confirmation"
            raise VaultError(message)
        source = self.vault.contained(note_path)
        document = NoteDocument.from_text(source.read_text(encoding="utf-8"))
        if document.note_type is not NoteType.PROJECT:
            message = "Only project notes contain steps"
            raise VaultError(message)
        step_document = afanes.core.steps.StepDocument(document.body)
        body = step_document.append(text, detail)
        text_out = document.with_body(body).to_text()
        afanes.core.atomic.write_text_atomic(source, text_out)
        return hashlib.sha256(text_out.encode("utf-8")).hexdigest()

    def _write_step(
        self,
        note_path: Path,
        line_index: int,
        transform: "Callable[[afanes.core.steps.StepDocument, afanes.models.step.ProjectStep], str]",
        *,
        confirm: bool,
    ) -> str:
        """Apply one line-level step transformation atomically."""
        if not confirm:
            message = "Changing a step requires explicit confirmation"
            raise VaultError(message)
        source = self.vault.contained(note_path)
        document = NoteDocument.from_text(source.read_text(encoding="utf-8"))
        if document.note_type is not NoteType.PROJECT:
            message = "Only project notes contain steps"
            raise VaultError(message)
        step_document = afanes.core.steps.StepDocument(document.body)
        step = next((value for value in step_document.steps if value.line_index == line_index), None)
        if step is None:
            message = "The step line no longer exists in this project"
            raise VaultError(message)
        body = transform(step_document, step)
        text_out = document.with_body(body).to_text()
        afanes.core.atomic.write_text_atomic(source, text_out)
        return hashlib.sha256(text_out.encode("utf-8")).hexdigest()
