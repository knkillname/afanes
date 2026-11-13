"""End-to-end tests for the three-note vault, processing, and review."""

import asyncio
import datetime
import typing
from pathlib import Path

import pytest

import afanes.core.search
import afanes.core.settings
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.core.vault.steps
import afanes.ui.state
from afanes.core.editing import PageDraftFactory
from afanes.core.errors import ProcessingError
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.processing import ProcessingOutcome
from afanes.core.project_body import ProseBlock, StepListBlock
from afanes.core.search import Browser, BrowserSection, ReviewPlanner
from afanes.core.steps import StepDocument
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import UnparsedPage
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType, Status
from afanes.models.step import StepEdit, StepEditKind
from tests.support import processing_request, versioned

TODAY = datetime.datetime.now(tz=datetime.UTC).astimezone().date()
TWO_OPEN_STEPS = 2


def _write_note(root: Path, relative: str, text: str) -> Path:
    versioned(root)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestReferenceLifecycle:
    def test_link_survives_a_move_and_follows_a_rename(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)
        ada = vault.create("Ada Lovelace", NoteType.REFERENCE, category=CategoryLabel("person"))
        note = vault.create("Prepare report", NoteType.NOTE, body="Ask [Ada Lovelace](<note:Ada Lovelace>).\n")

        reference = NoteReference(scheme=ReferenceScheme.NOTE, name="Ada Lovelace")
        assert vault.scan().catalog.resolve(reference).targets == (ada,)

        moved = afanes.core.vault.naming.VaultNaming(vault).move(ada, Path("work"), confirm=True)
        assert vault.scan().catalog.resolve(reference).targets == (moved,)

        preview = afanes.core.vault.naming.VaultNaming(vault).plan_rename(moved, "Ada King")
        report = afanes.core.vault.naming.VaultNaming(vault).apply_rename(preview, confirm=True)

        assert report.failed == ()
        assert "[Ada King](<note:Ada King>)" in note.read_text(encoding="utf-8")
        assert vault.scan().catalog.resolve(NoteReference(ReferenceScheme.NOTE, "Ada King")).targets == (
            moved.with_name("Ada King.md"),
        )


class TestVaultLayoutAndTrash:
    def test_default_creation_uses_the_documented_layout(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)

        project = vault.create("Launch", NoteType.PROJECT)
        reference = vault.create("Reading", NoteType.REFERENCE)
        categorized = vault.create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))

        assert project.parent == root / "projects"
        assert reference.parent == root / "reference"
        assert categorized.parent == root / "reference" / "person"

    def test_trash_then_restore_updates_resolution(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)
        ada = vault.create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))
        referring = vault.create("Note", NoteType.NOTE, body="[Ada](<note:Ada>)\n")
        reference = NoteReference(scheme=ReferenceScheme.NOTE, name="Ada")

        count = afanes.core.vault.naming.VaultNaming(vault).trash(ada, confirm=True)

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
        versioned(root)
        vault = Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Read the manual")

        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            processing_request(capture, ProcessingOutcome.REFERENCE)
        )
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert target == root / "reference" / "general" / "Read the manual.md"
        assert NoteDocument.from_text(target.read_text(encoding="utf-8")).note_type is NoteType.REFERENCE
        assert vault.scan().inbox_notes() == ()

    def test_capture_to_later(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Read the manual")

        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            processing_request(capture, ProcessingOutcome.LATER)
        )
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert NoteDocument.from_text(target.read_text(encoding="utf-8")).status is Status.LATER

    def test_capture_to_project_with_steps_from_the_body(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture(
            "Launch\n\n- [ ] Call the printer\n- [ ] Book the room\n"
        )

        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            processing_request(capture, ProcessingOutcome.PROJECT)
        )
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)
        note = vault.scan().find_note(target)

        assert note is not None
        assert [step.text for step in note.steps] == ["Call the printer", "Book the room"]
        assert note.next_step is not None
        assert note.next_step.text == "Call the printer"

    def test_capture_to_done_now(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Send the invoice")

        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            processing_request(capture, ProcessingOutcome.DONE_NOW, today=TODAY)
        )
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        steps = StepDocument(document.body).steps

        assert document.status is Status.DONE
        assert steps[0].checked is True
        assert steps[0].actual == TODAY

    def test_capture_to_append_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n")
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Call the plumber\n\nAsk about the boiler")

        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            processing_request(capture, ProcessingOutcome.APPEND_STEP, project="Home")
        )
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert target == project
        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert "- [ ] Call the plumber" in document.body
        assert "Ask about the boiler" in document.body
        assert not capture.exists()
        assert (root / "trash" / "Call the plumber.md").exists()

    def test_capture_to_trash_and_restore(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Obsolete")

        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            processing_request(capture, ProcessingOutcome.TRASH)
        )
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert target == root / "trash" / "Obsolete.md"
        assert not capture.exists()
        target.replace(root / "inbox" / "Obsolete.md")
        assert len(vault.scan().inbox_notes()) == 1


class TestInboxCapture:
    def test_capture_scan_list_and_preview_body(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)

        path = afanes.core.vault.pages.VaultPages(vault).capture("Call Ada\n\nAbout the report.")

        snapshot = vault.scan()
        assert [note.path for note in snapshot.inbox_notes()] == [path]
        assert snapshot.inbox_notes()[0].title == "Call Ada"
        assert "About the report." in vault.read_body(path)
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw["type"] == "note"
        assert document.date is not None
        assert "due_date" not in document.raw


class TestPageEditingLifecycle:
    def test_capture_link_follow_create_and_edit(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        versioned(root)
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
            await state.workspace.choose_vault(root)
            await state.navigation.open_page(capture)
            await state.navigation.follow_link("note:Ada")
            assert state.pages.page is not None
            assert state.pages.page.path == ada.resolve()
            await state.navigation.back()
            assert state.pages.page is not None
            assert state.pages.page.path == capture.resolve()
            await state.navigation.follow_link("note:Budget")
            await state.pages.set_page_body("# Budget\n\nDraft the budget.\n")
            await state.dialogs.set_page_type(NoteType.PROJECT)
            await state.dialogs.set_page_status(Status.ACTIVE)
            await state.dialogs.set_page_due_date("2026-12-01")
            assert await state.pages.autosave() is True
            assert await state.pages.done_editing() is True

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

    def test_project_requester_round_trip_preserves_the_note(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        path = _write_note(
            root,
            "projects/Home.md",
            "---\r\ntype: project\r\nstatus: active\r\ncustom: keep\r\n---\r\n\r\n# Home\r\n\r\n- [ ] Call\r\n",
        )
        body_before = NoteDocument.from_text(path.read_bytes().decode("utf-8")).body
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> None:
            await state.workspace.choose_vault(root)
            await state.navigation.open_page(path)
            assert state.pages.edit_page() is True
            await state.dialogs.set_page_asked_by("Priya Nair")
            assert await state.pages.autosave() is True

        try:
            asyncio.run(scenario())
        finally:
            state.reset()

        raw = path.read_bytes().decode("utf-8")
        written = NoteDocument.from_text(raw)
        assert written.asked_by == "Priya Nair"
        assert written.raw["custom"] == "keep"
        assert written.body == body_before
        assert written.newline == "\r\n"
        assert "\n" not in raw.replace("\r\n", "")

        async def clear() -> None:
            await state.workspace.choose_vault(root)
            await state.navigation.open_page(path)
            assert state.pages.edit_page() is True
            await state.dialogs.set_page_asked_by("")
            assert await state.pages.autosave() is True

        try:
            asyncio.run(clear())
        finally:
            state.reset()

        cleared = NoteDocument.from_text(path.read_bytes().decode("utf-8"))
        assert "asked_by" not in cleared.raw
        assert cleared.raw["custom"] == "keep"
        assert cleared.body == body_before
        assert cleared.newline == "\r\n"


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
            afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
                processing_request(path, ProcessingOutcome.PROJECT)
            )


class TestReviewWorkflow:
    def test_capture_project_tick_search_review_and_delegate(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "vault"
        versioned(root)
        vault = Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Launch the site")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            processing_request(capture, ProcessingOutcome.PROJECT)
        )
        project = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)
        afanes.core.vault.steps.VaultSteps(vault).append_step(project, "Call the printer", confirm=True)
        afanes.core.vault.steps.VaultSteps(vault).append_step(project, "Book the room", confirm=True)
        snapshot = vault.scan()
        note = snapshot.find_note(project)
        assert note is not None
        first = note.steps[0]
        second = note.steps[1]
        afanes.core.vault.steps.VaultSteps(vault).tick_step(project, first.line_index, TODAY, confirm=True)
        afanes.core.vault.steps.VaultSteps(vault).plan_step(
            project, second.line_index, TODAY - datetime.timedelta(days=1), confirm=True
        )

        assert len(Browser(vault.scan()).filter("printer").group(BrowserSection.PROJECTS).notes) == 1

        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        state.reset()

        async def scenario() -> None:
            await state.workspace.choose_vault(root)
            assert state.browser.due_count() == 1
            assert await state.review.start() is True
            assert await state.review.delegate("Ada") is True

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
        creation = afanes.core.vault.service.Vault.create_directory(tmp_path / "vault")
        vault = creation.vault
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Draft the plan")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            processing_request(capture, ProcessingOutcome.REFERENCE)
        )
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert target.is_file()
        assert vault.scan().inbox_notes() == ()
        assert [path.name for path in creation.seeded_directories] == [
            "inbox",
            "trash",
            "reference",
            "projects",
            "log",
        ]


class TestWorkspaceLiveness:
    def test_external_edits_reach_the_browser_and_project_rows(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "vault"
        versioned(root)
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
            await state.workspace.choose_vault(root)
            capture = await state.session.capture("Old title")
            assert capture is not None
            _write_note(root, "inbox/Old title.md", "---\ntype: note\n---\n\n# New title\n")
            _write_note(
                root,
                "projects/Launch.md",
                "---\ntype: project\n---\n\n# Launch\n\n- [ ] Fresh step\n- [ ] Second step\n",
            )
            assert await state.workspace.refresh_workspace() is True
            listing = state.browser.listing()
            assert listing is not None
            inbox = [note.title for note in listing.group(BrowserSection.INBOX).notes]
            summaries = [summary for group in state.browser.project_groups() for summary in group.projects]
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
    def test_project_example_parses(self) -> None:
        page = Path(__file__).resolve().parents[2] / "docs" / "reference" / "vault-format.md"
        text = page.read_text(encoding="utf-8")
        marker = (
            "---\ntype: project\nstatus: active\ndate: 2025-10-12\ndue_date: 2026-11-30\n"
            "asked_by: Priya Nair\nowner: Sam Rivera\n---\n"
        )
        start = text.index(marker)
        end = text.index("```", start)
        document = NoteDocument.from_text(text[start:end])
        steps = StepDocument(document.body).steps

        assert document.note_type is NoteType.PROJECT
        assert document.due_date == datetime.date(2026, 11, 30)
        assert document.asked_by == "Priya Nair"
        assert document.owner == "Sam Rivera"
        assert [step.text for step in steps] == [
            "Draft the checklist",
            "Ask [Ada Lovelace](<note:Ada Lovelace>) to review it",
            "Open the tracking page",
        ]
        assert steps[1].owners == ("Ada Lovelace",)
        assert steps[2].checked is True
        assert steps[2].actual == datetime.date(2026, 11, 15)

    def test_capture_example_parses(self) -> None:
        page = Path(__file__).resolve().parents[2] / "docs" / "getting-started" / "capture-clarify-review.md"
        text = page.read_text(encoding="utf-8")
        marker = "---\ntype: note\n---\n"
        start = text.index(marker)
        end = text.index("```", start)
        document = NoteDocument.from_text(text[start:end])

        assert document.note_type is NoteType.NOTE
        assert document.title == "Call Ada"
        assert document.status is None
        assert "about the invoice" in document.body

    def test_step_metadata_example_parses(self) -> None:
        page = Path(__file__).resolve().parents[2] / "docs" / "guide" / "projects-and-steps.md"
        text = page.read_text(encoding="utf-8")
        marker = "- [ ] Call the plumber"
        start = text.index(marker)
        end = text.index("\n", start)
        steps = StepDocument(text[start:end]).steps

        assert len(steps) == 1
        step = steps[0]
        assert step.text == "Call the plumber"
        assert step.checked is False
        assert step.owners == ("Ada",)
        assert step.plan == datetime.date(2026, 11, 20)
        assert step.actual == datetime.date(2026, 11, 14)
        assert step.tags == ("phone",)


class TestStepAwareProjectPageIntegration:
    @pytest.fixture(autouse=True)
    def _reset(self) -> typing.Iterator[None]:
        afanes.ui.state.app_state.reset()
        yield
        afanes.ui.state.app_state.reset()

    def _open_project(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        body: str,
    ) -> tuple[Path, afanes.ui.state.controller.AppState]:
        root = tmp_path / "vault"
        path = _write_note(
            root,
            "projects/Home.md",
            f"---\ntype: project\nstatus: active\n---\n{body}",
        )
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(root)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        return path, state

    def test_prose_and_steps_keep_document_order(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _path, state = self._open_project(
            tmp_path,
            monkeypatch,
            "# Home\n\nIntro.\n\n- [ ] Call\n\nOutro.\n",
        )

        blocks = state.pages.page_body_blocks

        assert isinstance(blocks[0], ProseBlock)
        assert isinstance(blocks[1], ProseBlock)
        assert isinstance(blocks[2], StepListBlock)
        assert isinstance(blocks[3], ProseBlock)
        assert "Intro." in blocks[1].source
        assert blocks[2].entries[0].step.text == "Call"
        assert "Outro." in blocks[3].source

    def test_step_link_opens_its_target(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "vault"
        ada = _write_note(root, "reference/Ada.md", "---\ntype: reference\n---\n# Ada\n")
        _path, state = self._open_project(
            tmp_path,
            monkeypatch,
            "# Home\n\n- [ ] Call [Ada](<note:Ada>)\n",
        )

        asyncio.run(state.navigation.follow_link("note:Ada"))

        assert state.pages.page is not None
        assert state.pages.page.path == ada.resolve()

    def test_owner_and_plan_edit_one_line(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path, state = self._open_project(
            tmp_path,
            monkeypatch,
            "# Home\n\n- [ ] One <!-- {actual: 2026-11-14, tags: [phone], priority: high} -->\n- [ ] Two\n",
        )
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        steps = StepDocument(document.body).steps
        second_line = document.body.splitlines()[3]

        assert (
            asyncio.run(
                state.pages.edit_page_step_metadata(
                    StepEdit(line_index=steps[0].line_index, kind=StepEditKind.PLAN, plan=datetime.date(2026, 12, 1))
                )
            )
            is True
        )
        assert (
            asyncio.run(
                state.pages.edit_page_step_metadata(
                    StepEdit(line_index=steps[0].line_index, kind=StepEditKind.OWNERS, owners=("Ada", "Grace"))
                )
            )
            is True
        )

        written = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        rewritten = StepDocument(written.body).steps[0]
        assert rewritten.plan == datetime.date(2026, 12, 1)
        assert rewritten.owners == ("Ada", "Grace")
        assert rewritten.actual == datetime.date(2026, 11, 14)
        assert rewritten.tags == ("phone",)
        assert rewritten.metadata.raw["priority"] == "high"
        assert written.body.splitlines()[3] == second_line

    def test_due_date_write_preserves_the_body(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path, state = self._open_project(
            tmp_path,
            monkeypatch,
            "# Home\n\n- [ ] Call\n",
        )
        body_before = NoteDocument.from_text(path.read_text(encoding="utf-8")).body

        assert asyncio.run(state.dialogs.save_page_due_date("2026-12-01")) is True

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.due_date == datetime.date(2026, 12, 1)
        assert document.body == body_before

    def test_external_edit_reloads_the_blocks(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _path, state = self._open_project(
            tmp_path,
            monkeypatch,
            "# Home\n\n- [ ] One\n",
        )
        _write_note(
            tmp_path / "vault",
            "projects/Home.md",
            "---\ntype: project\nstatus: active\n---\n# Home\n\n- [ ] One\n- [ ] Two\n",
        )

        assert asyncio.run(state.workspace.refresh_workspace()) is True

        blocks = state.pages.page_body_blocks
        step_block = next(block for block in blocks if isinstance(block, StepListBlock))
        assert [entry.step.text for entry in step_block.entries] == ["One", "Two"]
