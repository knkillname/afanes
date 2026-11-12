"""Tests for processing plans and their apply path."""

import datetime
import os
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.links
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.core.vault.snapshot
import afanes.core.vault.steps
from afanes.core.errors import NameCollisionError, ProcessingError
from afanes.core.frontmatter import NoteDocument
from afanes.core.processing import AppendStepPlan, ProcessingOutcome
from afanes.models.note import NoteType, Status

ONE = 1
TWO = 2
THREE_REFERENCES = 3


def _write_note(
    path: Path,
    note_type: str = "note",
    body: str = "",
    *,
    category: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if note_type == "person":
        note_type = "reference"
        category = "person"
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _set_modified_ns(path: Path, modified_ns: int) -> None:
    os.utime(path, ns=(modified_ns, modified_ns))


class TestProcessingEdgeCases:
    def test_done_now_ticks_an_existing_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Plan\n\n- [ ] One\n- [ ] Two\n")

        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            capture, ProcessingOutcome.DONE_NOW, today=datetime.date(2026, 11, 14)
        )
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        steps = afanes.core.steps.StepDocument(document.body).steps

        assert steps[0].checked is True
        assert steps[1].checked is False

    def test_append_aborts_when_the_capture_changed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n")
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Call")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            capture, ProcessingOutcome.APPEND_STEP, project="Home"
        )
        capture.write_text("---\ntype: note\n---\n# Changed\n", encoding="utf-8")

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert capture.exists()
        assert "- [ ] Call" not in project.read_text(encoding="utf-8")

    def test_apply_rejects_a_missing_capture(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Call")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(capture, ProcessingOutcome.PROJECT)
        capture.unlink()

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

    def test_capture_step_falls_back_to_the_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n")
        capture = vault.create("Blank", NoteType.NOTE)
        capture.write_text("---\ntype: note\n---\n", encoding="utf-8")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            capture, ProcessingOutcome.APPEND_STEP, project="Home"
        )

        assert isinstance(plan, AppendStepPlan)
        assert plan.step_text == "Blank"
        assert project.is_file()


class TestProcessingGuards:
    def test_plan_rejects_a_capture_missing_from_the_snapshot(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Buy milk")
        snapshot = afanes.core.vault.snapshot.VaultSnapshot(
            root=root.resolve(),
            notes=(),
            failures=(),
            catalog=afanes.core.links.NameCatalog.from_entries([]),
        )

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
                capture, ProcessingOutcome.PROJECT, snapshot=snapshot
            )

    def test_plan_rejects_an_unindexed_destination_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Ada")
        broken = root / "projects" / "Ada.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("---\ntype: refrence\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.processing.VaultProcessing(vault).plan_processing(capture, ProcessingOutcome.PROJECT)

    def test_append_rejects_status_or_due_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Buy milk")
        service = afanes.core.vault.processing.VaultProcessing(vault)

        with pytest.raises(ProcessingError):
            service.plan_processing(capture, ProcessingOutcome.APPEND_STEP, status=Status.ACTIVE)
        with pytest.raises(ProcessingError):
            service.plan_processing(capture, ProcessingOutcome.TRASH, due_date=datetime.date(2026, 11, 20))

    def test_append_rejects_a_capture_missing_from_the_snapshot(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Buy milk")
        snapshot = afanes.core.vault.snapshot.VaultSnapshot(
            root=root.resolve(),
            notes=(),
            failures=(),
            catalog=afanes.core.links.NameCatalog.from_entries([]),
        )

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).plan_append_step(capture, "Home", snapshot=snapshot)

    def test_append_rejects_a_blank_project_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Buy milk")

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).plan_append_step(capture, "   ")

    def test_apply_append_rejects_a_deleted_capture(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        pages = afanes.core.vault.pages.VaultPages(vault)
        service = afanes.core.vault.processing.VaultProcessing(vault)
        capture = pages.capture("Buy milk")
        pages.create_page("Home", NoteType.PROJECT, body="# Home\n")
        plan = service.plan_append_step(capture, "Home")
        capture.unlink()

        with pytest.raises(ProcessingError):
            service.apply_processing(plan, confirm=True)

    def test_trash_aborts_when_the_capture_changed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        service = afanes.core.vault.processing.VaultProcessing(vault)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Buy milk")
        plan = service.plan_processing(capture, ProcessingOutcome.TRASH)
        capture.write_text("---\ntype: note\n---\n\nChanged\n", encoding="utf-8")

        with pytest.raises(ProcessingError):
            service.apply_processing(plan, confirm=True)
