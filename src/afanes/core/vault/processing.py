# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Planning and applying one clarification step for an inbox capture.

Plans capture the current content hashes so apply can detect an external edit.
Path containment and atomic writes stay on :class:`afanes.core.vault.service.Vault`.
"""

import dataclasses
import datetime
import hashlib
from pathlib import Path

import afanes.core.atomic
import afanes.core.steps
import afanes.core.vault.snapshot
from afanes.core.errors import AfanesError, NameCollisionError, ProcessingError
from afanes.core.frontmatter import NoteDocument
from afanes.core.processing import AppendStepPlan, ProcessingOutcome, ProcessingPlan, ProcessingTarget
from afanes.core.template_cards import TemplateCard
from afanes.core.vault.naming import VaultNaming
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import VaultNote, VaultPath, VaultSnapshot
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status


@dataclasses.dataclass(frozen=True, slots=True)
class VaultProcessing:
    """Plan and apply clarification steps for inbox captures.

    Attributes
    ----------
    vault : Vault
        Resolved vault that owns path containment and the storage layout.
    """

    vault: Vault

    def plan_processing(
        self,
        note_path: Path,
        outcome: ProcessingOutcome,
        *,
        status: Status | None = None,
        due_date: datetime.date | None = None,
        project: str | None = None,
        card: TemplateCard | None = None,
        today: datetime.date | None = None,
        snapshot: VaultSnapshot | None = None,
    ) -> ProcessingPlan | AppendStepPlan:
        """Plan one clarification step for an inbox capture.

        Parameters
        ----------
        note_path : Path
            Capture path, relative or absolute, under the vault's ``inbox/``.
        outcome : ProcessingOutcome
            Selected clarification outcome.
        status : Status | None
            Requested target status. Projects default to ``active``; Later is
            always ``later``; Reference has no status; Done now is ``done``.
        due_date : datetime.date | None
            Optional calendar due date for a new project or a done-now project.
        project : str | None
            Target project identity for Append step. Text that matches no
            project is rejected.
        card : TemplateCard | None
            Template card chosen for Reference or Later. ``None`` is the Empty
            option and produces a ``general`` reference with no starter body.
        today : datetime.date | None
            Calendar date recorded as ``actual`` by Done now. ``None`` uses the
            current local date.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        ProcessingPlan | AppendStepPlan
            A single-note plan, or an append plan when the outcome is Append
            step.

        Raises
        ------
        ProcessingError
            If the note is outside ``inbox/``, is missing from the vault, the
            requested metadata is not valid for the outcome, or an append
            target matches no project.
        NameCollisionError
            If the destination filename, target scheme name, or append target
            is ambiguous.
        NoteParseError
            If the capture cannot be parsed.
        VaultPathError
            If a path escapes the vault.

        Notes
        -----
        Planning performs blocking reads but never writes. The plan captures
        the current source hash so apply can detect an external edit. Reference
        and Later always carry a category: the chosen card's label, or
        ``general`` for Empty. Only those outcomes accept a card.
        """
        if card is not None and outcome not in (ProcessingOutcome.REFERENCE, ProcessingOutcome.LATER):
            message = "Only Reference and Later accept a template card"
            raise ProcessingError(message)
        if card is not None and card.note_type is not NoteType.REFERENCE:
            message = "Reference and Later need a reference card"
            raise ProcessingError(message)
        source = self.vault.contained(note_path)
        self._require_inbox_note(source)

        vault = snapshot or self.vault.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise ProcessingError(message)

        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        source_scheme = ReferenceScheme.for_note(note.note_type)
        non_note = self._plan_non_note(
            source,
            vault,
            note,
            outcome,
            status=status,
            due_date=due_date,
            project=project,
            source_hash=source_hash,
        )
        if non_note is not None:
            return non_note

        target = ProcessingTarget.from_outcome(outcome, status)
        target_type = target.note_type
        target_status = target.status
        if due_date is not None and outcome not in (ProcessingOutcome.PROJECT, ProcessingOutcome.DONE_NOW):
            message = "Only projects accept a due date"
            raise ProcessingError(message)

        category: CategoryLabel | None = None
        scaffold: str | None = None
        if outcome in (ProcessingOutcome.REFERENCE, ProcessingOutcome.LATER):
            category = card.category if card is not None else CategoryLabel("general")
            scaffold = card.body if card is not None and card.body.strip() else None
        target_date: NoteDate | None = None
        if outcome is ProcessingOutcome.LOG:
            target_date = note.date or NoteDate.from_date(
                datetime.datetime.fromtimestamp(source.stat().st_mtime, tz=datetime.UTC).astimezone().date()
            )
            target_directory = self.vault.log_directory(target_date)
            target_name = target_date.text
        else:
            target_directory = self.vault.directory_for(target_type, category)
            target_name = source.stem
        target_path = target_directory / f"{target_name}{afanes.core.vault.snapshot.NOTE_SUFFIX}"
        target_scheme = ReferenceScheme.for_note(target_type)
        existing = vault.catalog.candidates(target_scheme, target_name)
        if any(not VaultPath.same(path, source) for path in existing):
            message = f"A {target_scheme.value} note named {target_name!r} already exists"
            raise NameCollisionError(message)
        if target_path.exists() and not VaultPath.same(target_path, source):
            message = f"Destination already exists: {target_path}"
            raise NameCollisionError(message)

        affected = vault.affected_sites(source)
        body_override = self._done_now_override(source, outcome, today=today)
        plan = ProcessingPlan(
            source_path=source,
            target_path=target_path,
            outcome=outcome,
            target_type=target_type,
            target_status=target_status,
            due_date=due_date,
            body_override=body_override,
            category=category,
            scaffold=scaffold,
            source_hash=source_hash,
            processed_hash=source_hash,
            reference_count=sum(site.reference_count for site in affected),
            affected_notes=tuple(site.path for site in affected),
            changes_scheme=source_scheme is not target_scheme,
            target_date=target_date,
        )
        document = NoteDocument.from_text(source.read_text(encoding="utf-8"))
        processed_text = plan.processed_text(document)
        return dataclasses.replace(
            plan,
            processed_hash=hashlib.sha256(processed_text.encode("utf-8")).hexdigest(),
        )

    def _plan_non_note(
        self,
        source: Path,
        vault: VaultSnapshot,
        note: VaultNote,
        outcome: ProcessingOutcome,
        *,
        status: Status | None,
        due_date: datetime.date | None,
        project: str | None,
        source_hash: str,
    ) -> ProcessingPlan | AppendStepPlan | None:
        """Plan Append step or Trash, or return ``None`` for a note outcome."""
        if outcome is ProcessingOutcome.APPEND_STEP:
            if status is not None or due_date is not None:
                message = "Append step does not accept status or due date metadata"
                raise ProcessingError(message)
            if project is None:
                message = "Append step needs a target project"
                raise ProcessingError(message)
            return self.plan_append_step(source, project, snapshot=vault)
        if outcome is ProcessingOutcome.TRASH:
            if status is not None or due_date is not None:
                message = "Trash does not accept assignment metadata"
                raise ProcessingError(message)
            trash_preview = VaultNaming(self.vault).plan_trash(source, snapshot=vault)
            return ProcessingPlan(
                source_path=source,
                target_path=trash_preview.trash_path,
                outcome=outcome,
                target_type=note.note_type,
                target_status=note.status,
                due_date=None,
                body_override=None,
                category=None,
                scaffold=None,
                source_hash=source_hash,
                processed_hash=source_hash,
                reference_count=trash_preview.reference_count,
                affected_notes=trash_preview.affected_notes,
                changes_scheme=False,
            )
        return None

    def _done_now_override(
        self,
        source: Path,
        outcome: ProcessingOutcome,
        *,
        today: datetime.date | None,
    ) -> str | None:
        """Return the completed body for Done now, or ``None`` otherwise."""
        if outcome is not ProcessingOutcome.DONE_NOW:
            return None
        document = NoteDocument.from_text(source.read_text(encoding="utf-8"))
        completed_on = today or datetime.datetime.now(tz=datetime.UTC).astimezone().date()
        return self._done_now_body(document, source.stem, completed_on)

    def plan_append_step(
        self,
        capture_path: Path,
        project_name: str,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> AppendStepPlan:
        """Plan appending one inbox capture to an existing project.

        Parameters
        ----------
        capture_path : Path
            Capture path, relative or absolute, under the vault's ``inbox/``.
        project_name : str
            Project identity. Matching is case-insensitive and ignores repeated
            whitespace, following reference resolution.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        AppendStepPlan
            Capture, target project, step text, detail, and both content hashes.

        Raises
        ------
        ProcessingError
            If the capture is outside the inbox, is missing, or the name matches
            no project.
        NameCollisionError
            If the name matches more than one project.
        VaultPathError
            If a path escapes the vault.
        """
        source = self.vault.contained(capture_path)
        self._require_inbox_note(source)
        vault = snapshot or self.vault.scan()
        if vault.find_note(source) is None:
            message = f"Note is not part of the vault: {capture_path}"
            raise ProcessingError(message)
        target_name = project_name.strip()
        if not target_name:
            message = "Append step needs a target project"
            raise ProcessingError(message)
        candidates = vault.catalog.candidates(ReferenceScheme.PROJECT, target_name)
        if not candidates:
            message = f"No project is named {target_name!r}"
            raise ProcessingError(message)
        if len(candidates) > 1:
            message = f"More than one project is named {target_name!r}"
            raise NameCollisionError(message)

        project_path = candidates[0]
        capture_data = source.read_bytes()
        project_data = project_path.read_bytes()
        document = NoteDocument.from_text(capture_data.decode("utf-8"))
        step_text, detail = self._capture_step(document.body, source.stem)
        return AppendStepPlan(
            capture_path=source,
            project_path=project_path,
            step_text=step_text,
            detail=detail,
            capture_hash=hashlib.sha256(capture_data).hexdigest(),
            project_hash=hashlib.sha256(project_data).hexdigest(),
        )

    def apply_processing(
        self,
        plan: ProcessingPlan | AppendStepPlan,
        *,
        confirm: bool = False,
    ) -> Path:
        """Apply a processing plan after explicit confirmation.

        Parameters
        ----------
        plan : ProcessingPlan | AppendStepPlan
            Plan produced by :meth:`plan_processing` or
            :meth:`plan_append_step`.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        Path
            Absolute destination path after the move, or the target project
            path for an append.

        Raises
        ------
        ProcessingError
            If confirmation is missing, the source is no longer an inbox
            capture, the source or target changed after planning, the processed
            text does not match the plan, or a move fails.
        NameCollisionError
            If the destination appears after planning.
        VaultPathError
            If a plan path escapes the vault.

        Notes
        -----
        A single-note plan writes the classified frontmatter atomically to the
        source before the rename. Append writes the target project first and
        trashes the capture second, so a failure never loses the step. A failed
        move leaves the capture in ``inbox/`` and the same plan can be retried.
        """
        if not confirm:
            message = "Processing requires explicit confirmation"
            raise ProcessingError(message)
        if isinstance(plan, AppendStepPlan):
            return self._apply_append_step(plan)

        source = self.vault.contained(plan.source_path)
        self._require_inbox_note(source)
        if not source.is_file():
            message = f"Capture no longer exists: {plan.source_path}"
            raise ProcessingError(message)

        target = self._processing_destination(plan)
        self._write_processing(plan, source)
        moved = self._move_processing(source, target)
        if plan.outcome is ProcessingOutcome.LOG:
            self._rewrite_log_conversion(plan)
        return moved

    def _apply_append_step(self, plan: AppendStepPlan) -> Path:
        """Write the step to the project, then trash the capture."""
        capture = self.vault.contained(plan.capture_path)
        project = self.vault.contained(plan.project_path)
        self._require_inbox_note(capture)
        if not capture.is_file():
            message = f"Capture no longer exists: {plan.capture_path}"
            raise ProcessingError(message)
        capture_data = capture.read_bytes()
        if hashlib.sha256(capture_data).hexdigest() != plan.capture_hash:
            message = "Source note changed after planning"
            raise ProcessingError(message)
        if not project.is_file():
            message = f"Target project no longer exists: {plan.project_path}"
            raise ProcessingError(message)

        project_data = project.read_bytes()
        document = NoteDocument.from_text(project_data.decode("utf-8"))
        step_document = afanes.core.steps.StepDocument(document.body)
        already_present = any(step.text == plan.step_text for step in step_document.steps)
        if not already_present:
            if hashlib.sha256(project_data).hexdigest() != plan.project_hash:
                message = "Target project changed after planning"
                raise ProcessingError(message)
            body = step_document.append(plan.step_text, plan.detail)
            afanes.core.atomic.write_text_atomic(project, document.with_body(body).to_text())
        try:
            VaultNaming(self.vault).trash(capture, confirm=True)
        except (AfanesError, OSError) as exc:
            message = "The step was written, but the capture could not be moved to trash; retry the same plan"
            raise ProcessingError(message) from exc
        return project

    @staticmethod
    def _done_now_body(document: NoteDocument, fallback_title: str, completed_on: datetime.date) -> str:
        """Return a project body whose step is completed today."""
        step_document = afanes.core.steps.StepDocument(document.body)
        steps = step_document.steps
        if steps:
            target = next((step for step in steps if not step.checked), steps[0])
            return step_document.tick(target, completed_on)
        title = document.title or fallback_title
        appended = step_document.append(title)
        completed = afanes.core.steps.StepDocument(appended)
        return completed.tick(completed.steps[-1], completed_on)

    @staticmethod
    def _capture_step(body: str, fallback_title: str) -> tuple[str, str]:
        """Split a capture body into a step text and indented detail."""
        lines = body.splitlines()
        first = next((index for index, line in enumerate(lines) if line.strip()), None)
        if first is None:
            return fallback_title, ""
        text = lines[first].strip().lstrip("#").strip() or fallback_title
        detail = "\n".join(lines[first + 1 :]).strip("\n")
        return text, detail

    def _processing_destination(self, plan: ProcessingPlan) -> Path:
        """Resolve and validate the destination path for a plan."""
        target = self.vault.contained(plan.target_path)
        if target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)
        return target

    def _write_processing(self, plan: ProcessingPlan, source: Path) -> None:
        """Write the classified frontmatter, or confirm it is already written."""
        data = source.read_bytes()
        current_hash = hashlib.sha256(data).hexdigest()
        if plan.outcome is ProcessingOutcome.TRASH:
            if current_hash != plan.source_hash:
                message = "Source note changed after planning"
                raise ProcessingError(message)
            return
        if current_hash == plan.processed_hash:
            return
        if current_hash != plan.source_hash:
            message = "Source note changed after planning"
            raise ProcessingError(message)
        document = NoteDocument.from_text(data.decode("utf-8"))
        text = plan.processed_text(document)
        processed_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if processed_hash != plan.processed_hash:
            message = "Processed note does not match the plan"
            raise ProcessingError(message)
        afanes.core.atomic.write_text_atomic(source, text)

    def _move_processing(self, source: Path, target: Path) -> Path:
        """Move a processed note to its destination."""
        if target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.replace(target)
        except OSError as exc:
            message = f"Could not move the note to its destination: {source}"
            raise ProcessingError(message) from exc
        return target

    def _rewrite_log_conversion(self, plan: ProcessingPlan) -> None:
        """Rewrite `note:` references to the new `log:` date destination.

        Parameters
        ----------
        plan : ProcessingPlan
            Applied log plan carrying the source name and target date.

        Notes
        -----
        The move happens first, so the scan sees the entry at its new path. A
        changed referring note is skipped by the repair hash guard and is
        reported by the repair service; the log entry itself remains valid.
        """
        if plan.target_date is None:
            return
        old = NoteReference(ReferenceScheme.NOTE, plan.source_path.stem)
        new = NoteReference(ReferenceScheme.LOG, plan.target_date.text)
        naming = VaultNaming(self.vault)
        preview = naming.plan_reference_repair(
            old,
            new,
            allow_scheme_change=True,
        )
        naming.apply_reference_repair(preview, confirm=True)

    def _require_inbox_note(self, source: Path) -> None:
        """Require a source path to be under the vault's inbox directory."""
        relative = source.relative_to(self.vault.root)
        if (
            len(relative.parts) < afanes.core.vault.snapshot.MIN_INBOX_PART_COUNT
            or relative.parts[0].casefold() != afanes.core.vault.snapshot.INBOX_DIRECTORY.name.casefold()
        ):
            message = "Only notes in the inbox can be processed"
            raise ProcessingError(message)
