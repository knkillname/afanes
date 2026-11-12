"""End-to-end test for creation, linking, moving, and renaming notes."""

import asyncio
import os
from pathlib import Path

import pytest

import afanes.core.search
import afanes.core.settings
import afanes.core.vault
import afanes.ui.state
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.processing import ProcessingOutcome
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

ONE_REFERENCE = 1
FIRST_MODIFIED_NS = 1_700_000_000_000_000_000
SECOND_MODIFIED_NS = 1_700_000_001_000_000_000


class TestReferenceLifecycle:
    def test_link_survives_a_move_and_follows_a_rename(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        ada = afanes.core.vault.Vault(root).create(
            "Ada Lovelace",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
        )
        note = afanes.core.vault.Vault(root).create(
            "Prepare report",
            NoteType.NOTE,
            body="Ask [Ada Lovelace](<person:Ada Lovelace>).\n",
        )

        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada Lovelace")
        before = afanes.core.vault.Vault(root).scan()
        resolved = before.catalog.resolve(reference)
        assert resolved.outcome is ResolutionOutcome.RESOLVED
        assert resolved.targets == (ada,)

        moved = afanes.core.vault.Vault(root).move(ada, Path("work"), confirm=True)
        after_move = afanes.core.vault.Vault(root).scan()
        resolved_after_move = after_move.catalog.resolve(reference)
        assert resolved_after_move.outcome is ResolutionOutcome.RESOLVED
        assert resolved_after_move.targets == (moved,)

        preview = afanes.core.vault.Vault(root).plan_rename(moved, "Ada King")
        assert preview.reference_count == ONE_REFERENCE
        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert report.failed == ()
        assert "[Ada King](<person:Ada King>)" in note.read_text(encoding="utf-8")

        after_rename = afanes.core.vault.Vault(root).scan()
        renamed = after_rename.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King"))
        assert renamed.outcome is ResolutionOutcome.RESOLVED
        assert renamed.targets[0].parent.name == "work"


class TestVaultLayoutAndTrash:
    def test_default_creation_uses_the_documented_layout(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        action = vault.create("Call Ada", NoteType.ACTION)
        project = vault.create("Launch", NoteType.PROJECT)
        reference = vault.create("Reading", NoteType.REFERENCE)
        person = vault.create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)

        assert action.parent == root / "actions"
        assert project.parent == root / "projects"
        assert reference.parent == root / "reference"
        assert person.parent == root / "reference" / "people"

    def test_trash_then_restore_updates_resolution(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        person = vault.create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)
        referring = vault.create("Note", NoteType.NOTE, body="[Ada](person:Ada)\n")
        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")

        count = vault.trash(person, confirm=True)

        assert count == ONE_REFERENCE
        assert not person.exists()
        assert (root / "trash" / "Ada.md").is_file()
        assert vault.scan().catalog.resolve(reference).outcome is ResolutionOutcome.UNRESOLVED

        restored = root / "reference" / "people" / "Ada.md"
        (root / "trash" / "Ada.md").replace(restored)

        assert vault.scan().catalog.resolve(reference).targets == (restored,)
        assert referring.exists()


class TestProcessingLifecycle:
    def test_capture_to_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Call Ada")

        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)
        target = vault.apply_processing(plan, confirm=True)
        snapshot = vault.scan()

        assert target == root / "actions" / "Call Ada.md"
        assert snapshot.inbox_notes() == ()
        assert [note.path for note in snapshot.notes] == [target]
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.body == "# Call Ada"
        assert document.title == "Call Ada"

    def test_capture_to_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Reading list")

        plan = vault.plan_processing(capture, ProcessingOutcome.REFERENCE)
        target = vault.apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))

        assert target == root / "reference" / "Reading list.md"
        assert document.note_type is NoteType.REFERENCE
        assert document.status is None
        assert document.title == "Reading list"
        assert vault.scan().inbox_notes() == ()

    def test_capture_to_later(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Maybe later")

        plan = vault.plan_processing(capture, ProcessingOutcome.LATER)
        target = vault.apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))

        assert document.status is Status.LATER
        assert vault.scan().inbox_notes() == ()

    def test_capture_to_project_with_a_linked_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Launch")

        plan = vault.plan_processing(capture, ProcessingOutcome.PROJECT)
        project = vault.apply_processing(plan, confirm=True)
        step = root / "actions" / "Draft brief.md"
        step.parent.mkdir(parents=True, exist_ok=True)
        step.write_text(
            '---\ntype: action\nstatus: active\nproject: "project:Launch"\n---\nDraft brief\n',
            encoding="utf-8",
        )

        snapshot = vault.scan()
        project_reference = NoteReference(scheme=ReferenceScheme.PROJECT, name="Launch")

        assert snapshot.catalog.resolve(project_reference).targets == (project,)
        assert [note.name for note in snapshot.notes] == ["Draft brief", "Launch"]

    def test_capture_to_trash_and_restore(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Discard me")

        plan = vault.plan_processing(capture, ProcessingOutcome.TRASH)
        trashed = vault.apply_processing(plan, confirm=True)

        assert not capture.exists()
        assert trashed == root / "trash" / "Discard me.md"
        assert vault.scan().inbox_notes() == ()

        restored = root / "inbox" / "Discard me.md"
        trashed.replace(restored)

        assert [note.path for note in vault.scan().inbox_notes()] == [restored]


class TestInboxCapture:
    def test_capture_scan_list_and_preview_body(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        first = afanes.core.vault.Vault(root).capture("First thought\nwith detail")
        second = afanes.core.vault.Vault(root).capture("Second thought")
        os.utime(first, ns=(FIRST_MODIFIED_NS, FIRST_MODIFIED_NS))
        os.utime(second, ns=(SECOND_MODIFIED_NS, SECOND_MODIFIED_NS))

        snapshot = afanes.core.vault.Vault(root).scan()
        inbox = snapshot.inbox_notes()
        documents = [NoteDocument.from_text(note.path.read_text(encoding="utf-8")) for note in inbox]

        assert [note.name for note in inbox] == ["Second thought", "First thought"]
        assert [note.title for note in inbox] == ["Second thought", "First thought"]
        assert [note.relative_path.as_posix() for note in inbox] == [
            "inbox/Second thought.md",
            "inbox/First thought.md",
        ]
        assert [document.body for document in documents] == [
            "# Second thought",
            "# First thought\nwith detail",
        ]
        assert [document.raw for document in documents] == [{"type": "note"}, {"type": "note"}]
        assert all(note.path.parent.name == "inbox" for note in inbox)


class TestPageEditingLifecycle:
    def test_capture_link_follow_create_and_edit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        ada = vault.create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)
        capture = vault.create(
            "Planning",
            NoteType.NOTE,
            body="[Ada](<person:Ada>) and [Budget](<note:Budget>)\n",
        )
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> None:
            await state.choose_vault(root)
            await state.open_page(capture)
            await state.follow_link("person:Ada")
            assert state.page is not None
            assert state.page.path == ada.resolve()
            await state.back()
            assert state.page is not None
            assert state.page.path == capture.resolve()
            await state.follow_link("note:Budget")
            await state.set_page_body("# Budget\n\nDraft the budget.\n")
            await state.set_page_type(NoteType.ACTION)
            await state.set_page_status(Status.ACTIVE)
            await state.set_page_due_date("2026-12-01")
            await state.set_page_people(("Ada",))
            await state.set_page_project("Release 1.0")
            assert await state.autosave() is True
            assert await state.done_editing() is True

        try:
            asyncio.run(scenario())
        finally:
            state.reset()

        budget = root / "actions" / "Budget.md"
        document = NoteDocument.from_text(budget.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.ACTION
        assert document.status is Status.ACTIVE
        assert document.raw["due_date"] == "2026-12-01"
        assert document.raw["people"] == ["person:Ada"]
        assert document.raw["project"] == "project:Release 1.0"
        assert document.body == "# Budget\n\nDraft the budget.\n"

        snapshot = afanes.core.vault.Vault(root).scan()
        assert snapshot.catalog.resolve(NoteReference(ReferenceScheme.NOTE, "Budget")).targets == (budget,)
        assert snapshot.catalog.resolve(NoteReference(ReferenceScheme.PERSON, "Ada")).targets == (ada,)
        assert [note.path for note in snapshot.inbox_notes()] == [capture]


def _write_note(
    root: Path,
    relative: str,
    *,
    note_type: str,
    status: str | None = None,
    project: str | None = None,
    due_date: str | None = None,
    body: str = "",
) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    if project is not None:
        lines.append(f'project: "{project}"')
    lines.extend(["---", body])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class TestReviewActionCreation:
    def test_review_action_creation_writes_only_the_new_action(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        project = _write_note(root, "projects/Launch.md", note_type="project", status="active", body="# Launch")
        action = _write_note(
            root,
            "actions/Draft brief.md",
            note_type="action",
            status="active",
            project="project:Launch",
            body="# Draft brief",
        )
        before = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: tmp_path / "settings.json")
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> Path | None:
            await state.choose_vault(root)
            await state.start_review()
            return await state.create_review_action("Send the supplier the address")

        try:
            created = asyncio.run(scenario())
        finally:
            state.reset()

        assert created is not None
        after = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        new_files = set(after) - set(before)
        assert new_files == {"actions/Send the supplier the address.md"}
        assert project.read_bytes() == before["projects/Launch.md"]
        assert action.read_bytes() == before["actions/Draft brief.md"]
        project_document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        action_document = NoteDocument.from_text(created.read_text(encoding="utf-8"))
        assert project_document.status is Status.ACTIVE
        assert action_document.status is Status.ACTIVE
        assert action_document.raw["project"] == "project:Launch"


class TestReviewWorkspaceWorkflow:
    def test_browse_process_and_create_a_next_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        release = _write_note(
            root, "projects/Release 1.0.md", note_type="project", status="active", body="# Release 1.0"
        )
        _write_note(
            root,
            "actions/Draft checklist.md",
            note_type="action",
            status="active",
            due_date="2026-11-15",
            project="project:Release 1.0",
            body="# Draft checklist",
        )
        stalled = _write_note(
            root, "projects/Office move.md", note_type="project", status="active", body="# Office move"
        )
        _write_note(root, "projects/Finished.md", note_type="project", status="done", body="# Finished")
        _write_note(root, "inbox/Call the printer.md", note_type="note", body="# Call the printer")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: tmp_path / "settings.json")
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> None:
            await state.choose_vault(root)
            listing = state.browser_listing
            assert listing is not None
            project_paths = [note.path for note in listing.group(afanes.core.search.BrowserSection.PROJECTS).notes]
            assert project_paths == [root / "projects/Finished.md", stalled, release]
            assert await state.open_page(release) is True
            assert state.page is not None
            assert state.page.path == release
            assert await state.start_review() is True
            plan = await state.plan_processing(ProcessingOutcome.ACTION)
            assert plan is not None
            assert await state.apply_processing() == root / "actions/Call the printer.md"
            assert state.review_session is not None
            current = state.review_session.current
            assert current is not None
            assert current.project is not None
            assert current.project.note.path == stalled
            assert await state.create_review_action("Send the supplier the address") is not None

        try:
            asyncio.run(scenario())
        finally:
            state.reset()

        assert (root / "actions" / "Call the printer.md").is_file()
        assert (root / "actions" / "Send the supplier the address.md").is_file()
        assert not (root / "inbox" / "Call the printer.md").exists()
        assert NoteDocument.from_text(stalled.read_text(encoding="utf-8")).status is Status.ACTIVE

        snapshot = afanes.core.vault.Vault(root).scan()
        assert snapshot.inbox_notes() == ()
        summaries = {summary.note.name: summary for summary in afanes.core.search.ProjectBoard(snapshot).summaries()}
        assert summaries["Release 1.0"].next_action is not None
        assert summaries["Release 1.0"].next_action.name == "Draft checklist"
        assert summaries["Office move"].next_action is not None
        assert summaries["Office move"].next_action.name == "Send the supplier the address"
        assert set(summaries) == {"Release 1.0", "Office move", "Finished"}


class TestCreatedVaultWorkflow:
    def test_create_capture_process_and_read_back(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        target = tmp_path / "notes" / "vault"
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> Path:
            assert await state.create_vault(target) is True
            captured = await state.capture("Call the printer")
            assert captured is not None
            assert captured.parent == target.resolve() / "inbox"
            assert await state.begin_processing(captured) is True
            assert await state.plan_processing(ProcessingOutcome.ACTION) is not None
            processed = await state.apply_processing()
            assert processed is not None
            return processed

        try:
            action = asyncio.run(scenario())
        finally:
            state.reset()

        assert action == target.resolve() / "actions" / "Call the printer.md"
        document = NoteDocument.from_text(action.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.ACTION
        snapshot = afanes.core.vault.Vault.open(target).scan()
        assert snapshot.inbox_notes() == ()
        assert [note.path for note in snapshot.notes] == [action]
