"""End-to-end tests for the three-note vault, processing, and review."""

import asyncio
import datetime
from pathlib import Path

import pytest

import afanes.core.search
import afanes.core.settings
import afanes.core.vault
import afanes.ui.state
from afanes.core.editing import PageDraftFactory
from afanes.core.errors import ProcessingError
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.processing import ProcessingOutcome
from afanes.core.search import Browser, BrowserSection, ReviewPlanner
from afanes.core.steps import StepDocument
from afanes.core.vault import UnparsedPage, Vault
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType, Status

TODAY = datetime.datetime.now(tz=datetime.UTC).astimezone().date()
TWO_OPEN_STEPS = 2


def _write_note(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestReferenceLifecycle:
    def test_link_survives_a_move_and_follows_a_rename(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        ada = vault.create("Ada Lovelace", NoteType.REFERENCE, category=CategoryLabel("person"))
        note = vault.create("Prepare report", NoteType.NOTE, body="Ask [Ada Lovelace](<note:Ada Lovelace>).\n")

        reference = NoteReference(scheme=ReferenceScheme.NOTE, name="Ada Lovelace")
        assert vault.scan().catalog.resolve(reference).targets == (ada,)

        moved = vault.move(ada, Path("work"), confirm=True)
        assert vault.scan().catalog.resolve(reference).targets == (moved,)

        preview = vault.plan_rename(moved, "Ada King")
        report = vault.apply_rename(preview, confirm=True)

        assert report.failed == ()
        assert "[Ada King](<note:Ada King>)" in note.read_text(encoding="utf-8")
        assert vault.scan().catalog.resolve(NoteReference(ReferenceScheme.NOTE, "Ada King")).targets == (
            moved.with_name("Ada King.md"),
        )


class TestVaultLayoutAndTrash:
    def test_default_creation_uses_the_documented_layout(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)

        project = vault.create("Launch", NoteType.PROJECT)
        reference = vault.create("Reading", NoteType.REFERENCE)
        categorized = vault.create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))

        assert project.parent == root / "projects"
        assert reference.parent == root / "reference"
        assert categorized.parent == root / "reference" / "person"

    def test_trash_then_restore_updates_resolution(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        ada = vault.create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))
        referring = vault.create("Note", NoteType.NOTE, body="[Ada](<note:Ada>)\n")
        reference = NoteReference(scheme=ReferenceScheme.NOTE, name="Ada")

        count = vault.trash(ada, confirm=True)

        assert count == 1
        assert not ada.exists()
        assert (root / "trash" / "Ada.md").is_file()
        assert vault.scan().catalog.resolve(reference).outcome is ResolutionOutcome.UNRESOLVED

        restored = root / "reference" / "person" / "Ada.md"
        (root / "trash" / "Ada.md").replace(restored)

        assert vault.scan().catalog.resolve(reference).targets == (restored,)
        assert referring.exists()


class TestProcessingLifecycle:
    def test_capture_to_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        capture = vault.capture("Read the manual")

        plan = vault.plan_processing(capture, ProcessingOutcome.REFERENCE)
        target = vault.apply_processing(plan, confirm=True)

        assert target == root / "reference" / "Read the manual.md"
        assert NoteDocument.from_text(target.read_text(encoding="utf-8")).note_type is NoteType.REFERENCE
        assert vault.scan().inbox_notes() == ()

    def test_capture_to_later(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        capture = vault.capture("Read the manual")

        plan = vault.plan_processing(capture, ProcessingOutcome.LATER)
        target = vault.apply_processing(plan, confirm=True)

        assert NoteDocument.from_text(target.read_text(encoding="utf-8")).status is Status.LATER

    def test_capture_to_project_with_steps_from_the_body(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        capture = vault.capture("Launch\n\n- [ ] Call the printer\n- [ ] Book the room\n")

        plan = vault.plan_processing(capture, ProcessingOutcome.PROJECT)
        target = vault.apply_processing(plan, confirm=True)
        note = vault.scan().find_note(target)

        assert note is not None
        assert [step.text for step in note.steps] == ["Call the printer", "Book the room"]
        assert note.next_step is not None
        assert note.next_step.text == "Call the printer"

    def test_capture_to_done_now(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        capture = vault.capture("Send the invoice")

        plan = vault.plan_processing(capture, ProcessingOutcome.DONE_NOW, today=TODAY)
        target = vault.apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        steps = StepDocument(document.body).steps

        assert document.status is Status.DONE
        assert steps[0].checked is True
        assert steps[0].actual == TODAY

    def test_capture_to_append_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n")
        capture = vault.capture("Call the plumber\n\nAsk about the boiler")

        plan = vault.plan_processing(capture, ProcessingOutcome.APPEND_STEP, project="Home")
        target = vault.apply_processing(plan, confirm=True)

        assert target == project
        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert "- [ ] Call the plumber" in document.body
        assert "Ask about the boiler" in document.body
        assert not capture.exists()
        assert (root / "trash" / "Call the plumber.md").exists()

    def test_capture_to_trash_and_restore(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        capture = vault.capture("Obsolete")

        plan = vault.plan_processing(capture, ProcessingOutcome.TRASH)
        target = vault.apply_processing(plan, confirm=True)

        assert target == root / "trash" / "Obsolete.md"
        assert not capture.exists()
        target.replace(root / "inbox" / "Obsolete.md")
        assert len(vault.scan().inbox_notes()) == 1


class TestInboxCapture:
    def test_capture_scan_list_and_preview_body(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)

        path = vault.capture("Call Ada\n\nAbout the report.")

        snapshot = vault.scan()
        assert [note.path for note in snapshot.inbox_notes()] == [path]
        assert snapshot.inbox_notes()[0].title == "Call Ada"
        assert "About the report." in vault.read_body(path)
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw == {"type": "note"}


class TestPageEditingLifecycle:
    def test_capture_link_follow_create_and_edit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        ada = vault.create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))
        capture = vault.create(
            "Planning",
            NoteType.NOTE,
            body="[Ada](<note:Ada>) and [Budget](<note:Budget>)\n",
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
            await state.follow_link("note:Ada")
            assert state.page is not None
            assert state.page.path == ada.resolve()
            await state.back()
            assert state.page is not None
            assert state.page.path == capture.resolve()
            await state.follow_link("note:Budget")
            await state.set_page_body("# Budget\n\nDraft the budget.\n")
            await state.set_page_type(NoteType.PROJECT)
            await state.set_page_status(Status.ACTIVE)
            await state.set_page_due_date("2026-12-01")
            assert await state.autosave() is True
            assert await state.done_editing() is True

        try:
            asyncio.run(scenario())
        finally:
            state.reset()

        budget = root / "projects" / "Budget.md"
        document = NoteDocument.from_text(budget.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.PROJECT
        assert document.status is Status.ACTIVE
        assert document.due_date == datetime.date(2026, 12, 1)
        assert document.body == "# Budget\n\nDraft the budget.\n"
        assert vault.scan().catalog.resolve(NoteReference(ReferenceScheme.PROJECT, "Budget")).targets == (budget,)


class TestHardBreak:
    def test_old_note_lands_in_unreadable_and_is_not_rewritten(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        text = '---\ntype: action\npeople:\n  - "person:Ada"\nproject: "project:Turing"\n---\n\n# Old\n'
        path = _write_note(root, "actions/Old.md", text)
        before = path.read_bytes()
        vault = Vault(root)

        snapshot = vault.scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == 1
        page = vault.read_page(path)
        assert isinstance(page, UnparsedPage)
        draft = PageDraftFactory.from_page(page)
        assert draft.mode.value == "raw"
        assert path.read_bytes() == before

    def test_person_link_is_unreadable(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_note(root, "note/Ada.md", "---\ntype: reference\n---\n[Ada](person:Ada)\n")

        snapshot = Vault(root).scan()

        assert snapshot.notes == ()
        assert "retired" in snapshot.failures[0].message
        assert path.exists()


class TestMisplacedNote:
    def test_misplaced_note_needs_attention_and_cannot_be_processed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_note(root, "notes/Later.md", "---\ntype: note\n---\n# Later\n")
        vault = Vault(root)

        listing = Browser(vault.scan()).groups()

        assert listing.group(BrowserSection.NEEDS_ATTENTION).notes[0].path == path
        with pytest.raises(ProcessingError):
            vault.plan_processing(path, ProcessingOutcome.PROJECT)


class TestReviewWorkflow:
    def test_capture_project_tick_search_review_and_delegate(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        capture = vault.capture("Launch the site")
        plan = vault.plan_processing(capture, ProcessingOutcome.PROJECT)
        project = vault.apply_processing(plan, confirm=True)
        vault.append_step(project, "Call the printer", confirm=True)
        vault.append_step(project, "Book the room", confirm=True)
        snapshot = vault.scan()
        note = snapshot.find_note(project)
        assert note is not None
        first = note.steps[0]
        second = note.steps[1]
        vault.tick_step(project, first.line_index, TODAY, confirm=True)
        vault.plan_step(project, second.line_index, TODAY - datetime.timedelta(days=1), confirm=True)

        assert len(Browser(vault.scan()).filter("printer").group(BrowserSection.PROJECTS).notes) == 1

        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> None:
            await state.choose_vault(root)
            assert state.review_due_count == 1
            assert await state.start_review() is True
            assert await state.review_delegate("Ada") is True

        try:
            asyncio.run(scenario())
        finally:
            state.reset()

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        steps = StepDocument(document.body).steps
        assert steps[0].checked is True
        assert steps[1].owners == ("Ada",)
        assert steps[1].checked is False
        assert ReviewPlanner(vault.scan(), today=TODAY).due_count() == 0


class TestCreatedVaultWorkflow:
    def test_create_capture_process_and_read_back(
        self,
        tmp_path: Path,
    ) -> None:
        creation = afanes.core.vault.Vault.create_directory(tmp_path / "vault")
        vault = creation.vault
        capture = vault.capture("Draft the plan")
        plan = vault.plan_processing(capture, ProcessingOutcome.REFERENCE)
        target = vault.apply_processing(plan, confirm=True)

        assert target.is_file()
        assert vault.scan().inbox_notes() == ()
        assert [path.name for path in creation.seeded_directories] == [
            "inbox",
            "trash",
            "reference",
            "projects",
        ]


class TestWorkspaceLiveness:
    def test_external_edits_reach_the_browser_and_project_rows(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = Vault(root)
        vault.create("Launch", NoteType.PROJECT, body="# Launch\n\n- [ ] Old step\n")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> tuple[list[str], int, str | None]:
            await state.choose_vault(root)
            capture = await state.capture("Old title")
            assert capture is not None
            _write_note(root, "inbox/Old title.md", "---\ntype: note\n---\n\n# New title\n")
            _write_note(
                root,
                "projects/Launch.md",
                "---\ntype: project\n---\n\n# Launch\n\n- [ ] Fresh step\n- [ ] Second step\n",
            )
            assert await state.refresh_workspace() is True
            listing = state.browser_listing
            assert listing is not None
            inbox = [note.title for note in listing.group(BrowserSection.INBOX).notes]
            summaries = [summary for group in state.project_groups for summary in group.projects]
            launch = next(summary for summary in summaries if summary.note.name == "Launch")
            next_text = None if launch.next_step is None else launch.next_step.text
            return inbox, launch.open_count, next_text

        try:
            inbox, open_count, next_text = asyncio.run(scenario())
        finally:
            state.reset()

        assert inbox == ["New title"]
        assert open_count == TWO_OPEN_STEPS
        assert next_text == "Fresh step"


class TestDocumentedExamples:
    def test_readme_project_example_parses(self) -> None:
        readme = Path(__file__).resolve().parents[2] / "README.md"
        text = readme.read_text(encoding="utf-8")
        marker = "---\ntype: project\nstatus: active\ndue_date: 2026-11-30\n---\n"
        start = text.index(marker)
        end = text.index("```", start)
        document = NoteDocument.from_text(text[start:end])
        steps = StepDocument(document.body).steps

        assert document.note_type is NoteType.PROJECT
        assert document.due_date == datetime.date(2026, 11, 30)
        assert [step.text for step in steps] == [
            "Draft the checklist",
            "Ask [Ada Lovelace](<note:Ada Lovelace>) to review it",
            "Open the tracking page",
        ]
        assert steps[1].owners == ("Ada Lovelace",)
        assert steps[2].checked is True
        assert steps[2].actual == datetime.date(2026, 11, 15)
