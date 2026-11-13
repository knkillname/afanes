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
from afanes.core.processing import AppendStepPlan, ProcessingOutcome, ProcessingPlan
from afanes.models.note import NoteDate, NoteType, Status

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
    date: str | None = None,
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
    if date is not None:
        lines.append(f"date: {date}")
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
    def test_project_plan_writes_role_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Call")
        service = afanes.core.vault.processing.VaultProcessing(vault)

        plan = service.plan_processing(
            capture,
            ProcessingOutcome.PROJECT,
            owner="  Sam Rivera  ",
            asked_by="  Priya Nair  ",
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.owner == "Sam Rivera"
        assert plan.asked_by == "Priya Nair"
        target = service.apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.owner == "Sam Rivera"
        assert document.asked_by == "Priya Nair"

    def test_done_now_plan_writes_role_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Call")
        service = afanes.core.vault.processing.VaultProcessing(vault)

        plan = service.plan_processing(
            capture,
            ProcessingOutcome.DONE_NOW,
            today=datetime.date(2026, 11, 14),
            owner="Sam Rivera",
            asked_by="Priya Nair",
        )

        assert isinstance(plan, ProcessingPlan)
        target = service.apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.owner == "Sam Rivera"
        assert document.asked_by == "Priya Nair"

    @pytest.mark.parametrize(
        "outcome",
        [ProcessingOutcome.REFERENCE, ProcessingOutcome.LATER, ProcessingOutcome.LOG, ProcessingOutcome.TRASH],
    )
    def test_non_project_outcomes_reject_role_names(self, tmp_path: Path, outcome: ProcessingOutcome) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Buy milk")
        service = afanes.core.vault.processing.VaultProcessing(vault)

        with pytest.raises(ProcessingError, match="Only projects"):
            service.plan_processing(capture, outcome, owner="Sam Rivera")

    def test_blank_role_values_write_no_keys(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Call")
        service = afanes.core.vault.processing.VaultProcessing(vault)

        plan = service.plan_processing(
            capture,
            ProcessingOutcome.PROJECT,
            owner="   ",
            asked_by="   ",
        )
        target = service.apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert "owner" not in document.raw
        assert "asked_by" not in document.raw

    def test_append_step_does_not_inherit_the_project_owner(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        project = _write_note(root / "projects" / "Home.md", "project", "# Home\n")
        project.write_text(
            "---\ntype: project\nowner: Sam Rivera\n---\n\n# Home\n",
            encoding="utf-8",
        )
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Call the plumber")
        service = afanes.core.vault.processing.VaultProcessing(vault)

        plan = service.plan_processing(capture, ProcessingOutcome.APPEND_STEP, project="Home")
        service.apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        steps = afanes.core.steps.StepDocument(document.body).steps
        assert document.owner == "Sam Rivera"
        assert steps[0].owners == ()
        assert "owners" not in steps[0].metadata.raw

    def test_append_step_rejects_role_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n")
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Buy milk")
        service = afanes.core.vault.processing.VaultProcessing(vault)

        with pytest.raises(ProcessingError, match="Only projects"):
            service.plan_processing(capture, ProcessingOutcome.APPEND_STEP, project="Home", asked_by="Sam Rivera")
        assert project.is_file()

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


class TestLogProcessing:
    def test_plan_and_apply_a_dated_capture(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        capture = _write_note(
            root / "inbox" / "Call the plumber.md",
            body="Call the plumber\n\nAbout the leak.\n",
            date="2025-10-12",
        )
        vault = afanes.core.vault.service.Vault(root)
        processing = afanes.core.vault.processing.VaultProcessing(vault)

        plan = processing.plan_processing(capture, ProcessingOutcome.LOG)
        target = processing.apply_processing(plan, confirm=True)

        expected = root / "log" / "2025" / "10" / "2025-10-12.md"
        assert target == expected
        assert expected.is_file()
        assert not capture.exists()
        document = NoteDocument.from_text(expected.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.LOG
        assert document.date == NoteDate.from_text("2025-10-12")
        assert "category" not in document.raw
        assert "status" not in document.raw
        assert "due_date" not in document.raw
        assert "asked_by" not in document.raw

    def test_undated_capture_uses_the_last_modified_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        capture = _write_note(root / "inbox" / "Call the plumber.md", body="Call the plumber\n")
        modified = datetime.datetime(2025, 10, 12, 12, tzinfo=datetime.UTC)
        _set_modified_ns(capture, int(modified.timestamp() * 1_000_000_000))
        vault = afanes.core.vault.service.Vault(root)
        processing = afanes.core.vault.processing.VaultProcessing(vault)

        plan = processing.plan_processing(capture, ProcessingOutcome.LOG)
        target = processing.apply_processing(plan, confirm=True)

        assert target == root / "log" / "2025" / "10" / "2025-10-12.md"

    def test_occupied_date_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        capture = _write_note(
            root / "inbox" / "Call the plumber.md",
            body="Call the plumber\n",
            date="2025-10-12",
        )
        _write_note(root / "log" / "2025" / "10" / "2025-10-12.md", "log", date="2025-10-12")
        vault = afanes.core.vault.service.Vault(root)
        processing = afanes.core.vault.processing.VaultProcessing(vault)

        with pytest.raises(NameCollisionError):
            processing.plan_processing(capture, ProcessingOutcome.LOG)

    def test_inbound_note_references_are_rewritten(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        capture = _write_note(
            root / "inbox" / "Call the plumber.md",
            body="# Call the plumber\n",
            date="2025-10-12",
        )
        referrer = _write_note(
            root / "reference" / "Entry.md",
            "reference",
            body="[Call](<note:Call the plumber>)\n",
        )
        vault = afanes.core.vault.service.Vault(root)
        processing = afanes.core.vault.processing.VaultProcessing(vault)

        plan = processing.plan_processing(capture, ProcessingOutcome.LOG)
        processing.apply_processing(plan, confirm=True)

        assert "log:2025-10-12" in referrer.read_text(encoding="utf-8")
