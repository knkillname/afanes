"""Tests for the single application state controller."""

import asyncio
import dataclasses
import datetime
import json
import os
import threading
from pathlib import Path

import pytest

import afanes.core.connections
import afanes.core.settings
import afanes.core.templates
import afanes.core.vault.log_conversions
import afanes.core.vault.naming
import afanes.core.vault.naming_reports
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.schema
import afanes.core.vault.service
import afanes.core.vault.snapshot
import afanes.ui.state
import afanes.ui.state.lock
import afanes.ui.state.navigation
import afanes.ui.state.session
import afanes.ui.state.status
import afanes.ui.strings
from afanes.core.editing import NormalDraft
from afanes.core.errors import (
    ConfigurationError,
    TemplateContentError,
    VaultError,
    VaultSchemaWriteError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.core.log import LogMode
from afanes.core.processing import AppendStepPlan, ProcessingOutcome, ProcessingPlan
from afanes.core.project_body import ProseBlock, StepListBlock
from afanes.core.settings import Settings, SettingsStore
from afanes.core.steps import StepDocument
from afanes.models.link import ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status
from afanes.models.step import ProjectStep, StepEdit, StepEditKind
from tests.support import ensure_vault as _ensure_vault
from tests.support import versioned as _versioned

OLD_NS = 1_700_000_000_000_000_000
NEW_NS = 1_700_000_001_000_000_000
TWO_PENDING = 2


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(
        afanes.core.settings.SettingsStore,
        "settings_path",
        classmethod(lambda _cls: path),
    )


def _write_settings(path: Path, vault: Path) -> None:
    payload = {"version": afanes.core.settings.SETTINGS_VERSION, "vault": str(vault)}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_note(path: Path, content: str) -> Path:
    _ensure_vault(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _adoptable(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for folder in afanes.core.vault.schema.DEFAULT_FOLDERS:
        (root / folder).mkdir()
    return root


def _note_text(body: str) -> str:
    return f"---\ntype: note\n---\n{body}"


def _typed_note(note_type: str, body: str, *, category: str | None = None) -> str:
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    lines.extend(["---", body])
    return "\n".join(lines)


def _write_typed_note(
    path: Path,
    note_type: str,
    *,
    status: str | None = None,
    project: str | None = None,
    due_date: str | None = None,
    body: str = "",
) -> Path:
    _ensure_vault(path)
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


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


class TestProcessingState:
    def test_begin_processing_loads_the_capture(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> tuple[bool, Path]:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            opened = await state.processing.begin(capture)
            return opened, capture

        opened, capture = asyncio.run(scenario())

        assert opened is True
        assert state.processing.note == capture
        assert state.processing.body == "# Buy milk"
        assert state.session.selected == capture

    def test_build_plan_passes_role_names(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> ProcessingPlan | None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            assert await state.processing.begin(capture) is True
            plan = await state.processing.build_plan(
                ProcessingOutcome.PROJECT,
                owner="Sam Rivera",
                asked_by="Priya Nair",
            )
            assert isinstance(plan, ProcessingPlan)
            return plan

        plan = asyncio.run(scenario())

        assert plan is not None
        assert plan.owner == "Sam Rivera"
        assert plan.asked_by == "Priya Nair"

    def test_begin_processing_rejects_a_missing_capture(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.processing.begin(vault / "inbox" / "Missing.md")

        opened = asyncio.run(scenario())

        assert opened is False
        assert state.status.message == afanes.ui.strings.PROCESSING_MISSING

    def test_begin_processing_performs_no_writes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> dict[str, bytes]:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            before = _tree_state(vault)
            await state.processing.begin(capture)
            return before

        before = asyncio.run(scenario())

        assert _tree_state(vault) == before

    def test_begin_processing_loads_the_valid_cards(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        card = vault / "templates" / "person.md"
        card.parent.mkdir(parents=True)
        card.write_text(
            "---\ntype: reference\ncategory: person\ntitle: Person\n---\n\n## Contact\n",
            encoding="utf-8",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            assert await state.processing.begin(capture) is True

        asyncio.run(scenario())

        assert [item.title for item in state.processing.cards] == ["Person"]
        assert state.processing.card_issues == ()

    def test_begin_processing_without_a_folder_offers_no_cards(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            assert await state.processing.begin(capture) is True

        asyncio.run(scenario())

        assert state.processing.cards == ()
        assert state.processing.card_issues == ()

    def test_begin_processing_reports_invalid_cards(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        broken = vault / "templates" / "broken.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("---\ntype: reference\n---\n", encoding="utf-8")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            assert await state.processing.begin(capture) is True

        asyncio.run(scenario())

        assert state.processing.cards == ()
        assert [issue.relative_path.as_posix() for issue in state.processing.card_issues] == ["broken.md"]

    def test_build_plan_uses_the_selected_card(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        card = vault / "templates" / "person.md"
        card.parent.mkdir(parents=True)
        card.write_text(
            "---\ntype: reference\ncategory: person\ntitle: Person\n---\n\n## Contact\n",
            encoding="utf-8",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            assert await state.processing.begin(capture) is True
            selected = state.processing.cards[0]
            plan = await state.processing.build_plan(ProcessingOutcome.REFERENCE, card=selected)
            assert isinstance(plan, ProcessingPlan)
            assert plan.category == CategoryLabel("person")
            assert plan.scaffold == "## Contact"

        asyncio.run(scenario())

    def test_build_plan_empty_uses_general(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            assert await state.processing.begin(capture) is True
            plan = await state.processing.build_plan(ProcessingOutcome.REFERENCE)
            assert isinstance(plan, ProcessingPlan)
            assert plan.category == CategoryLabel("general")
            assert plan.scaffold is None

        asyncio.run(scenario())

    def test_plan_processing_builds_a_plan_without_writing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            await state.processing.begin(capture)
            plan = await state.processing.build_plan(ProcessingOutcome.PROJECT)
            assert plan is not None
            assert state.processing.plan is plan

        asyncio.run(scenario())

        assert not (vault / "projects" / "Buy milk.md").exists()

    def test_plan_processing_failure_sets_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            await state.processing.begin(capture)
            plan = await state.processing.build_plan(
                ProcessingOutcome.REFERENCE,
                due_date=datetime.date(2026, 11, 20),
            )
            assert plan is None

        asyncio.run(scenario())

        assert state.processing.plan is None
        assert state.status.message is not None
        assert state.status.message.startswith("Could not prepare")

    def test_apply_processing_moves_the_capture(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            await state.processing.begin(capture)
            await state.processing.build_plan(ProcessingOutcome.PROJECT)
            target = await state.processing.apply()
            assert target is not None
            return target

        target = asyncio.run(scenario())

        assert target == vault / "projects" / "Buy milk.md"
        assert target.exists()
        assert state.processing.result == target
        assert state.processing.note is None
        assert state.processing.plan is None
        assert state.session.notes == ()

    def test_apply_processing_leaves_the_open_page_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        note = _write_note(vault / "reference" / "Ada.md", _typed_note("reference", "# Ada\n"))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            await state.processing.begin(capture)
            await state.processing.build_plan(ProcessingOutcome.PROJECT)
            assert await state.processing.apply() is not None

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.path == note.resolve()
        assert state.pages.editing is False
        assert state.processing.result is not None

    def test_apply_processing_failure_keeps_the_plan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        capture_path: Path | None = None

        async def scenario() -> None:
            nonlocal capture_path
            await state.workspace.choose_vault(vault)
            capture_path = await state.session.capture("Buy milk")
            assert capture_path is not None
            await state.processing.begin(capture_path)
            await state.processing.build_plan(ProcessingOutcome.PROJECT)

        asyncio.run(scenario())

        def fail_apply(_vault: object, _plan: object, **_kwargs: object) -> Path:
            message = "write failed"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.processing.VaultProcessing, "apply_processing", fail_apply)
        result = asyncio.run(state.processing.apply())

        assert result is None
        assert state.processing.plan is not None
        assert state.status.message is not None
        assert capture_path is not None
        assert capture_path.exists()

    def test_cancel_processing_clears_the_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            await state.processing.begin(capture)
            await state.processing.build_plan(ProcessingOutcome.PROJECT)
            state.processing.cancel()

        asyncio.run(scenario())

        assert state.processing.note is None
        assert state.processing.body is None
        assert state.processing.plan is None
        assert state.processing.result is None
        assert state.status.message is None

    def test_finish_processing_clears_the_success_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            await state.processing.begin(capture)
            await state.processing.build_plan(ProcessingOutcome.PROJECT)
            await state.processing.apply()
            state.processing.finish()

        asyncio.run(scenario())

        assert state.processing.result is None
        assert state.processing.note is None


class TestTemplateCards:
    def test_reads_valid_cards(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        card = vault / "templates" / "person.md"
        card.parent.mkdir(parents=True)
        card.write_text("---\ntype: reference\ncategory: person\ntitle: Person\n---\n", encoding="utf-8")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> afanes.core.template_cards.TemplateCardListing | None:
            await state.workspace.choose_vault(vault)
            return await state.session.template_cards()

        listing = asyncio.run(scenario())

        assert listing is not None
        assert [item.title for item in listing.cards] == ["Person"]
        assert listing.issues == ()

    def test_a_missing_folder_is_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> afanes.core.template_cards.TemplateCardListing | None:
            await state.workspace.choose_vault(vault)
            return await state.session.template_cards()

        listing = asyncio.run(scenario())

        assert listing is not None
        assert listing.cards == ()
        assert listing.issues == ()

    def test_invalid_cards_are_reported(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        broken = vault / "templates" / "broken.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("---\ntype: reference\n---\n", encoding="utf-8")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> afanes.core.template_cards.TemplateCardListing | None:
            await state.workspace.choose_vault(vault)
            return await state.session.template_cards()

        listing = asyncio.run(scenario())

        assert listing is not None
        assert [issue.relative_path.as_posix() for issue in listing.issues] == ["broken.md"]

    def test_without_a_vault_returns_none(self) -> None:
        state = afanes.ui.state.app_state

        assert asyncio.run(state.session.template_cards()) is None


class TestCreateReference:
    def test_creates_and_opens_the_note_in_edit_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        state.browser.query = "stale"

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_reference("Priya Nair", CategoryLabel("person"), "## Contact\n")

        created = asyncio.run(scenario())

        path = vault / "reference" / "person" / "Priya Nair.md"
        assert created is True
        assert path.is_file()
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.category == CategoryLabel("person")
        assert document.body == "# Priya Nair\n\n## Contact\n"
        assert state.pages.editing is True
        assert state.pages.page is not None
        assert state.pages.page.path == path.resolve()
        assert state.browser.query == ""

    def test_empty_uses_the_general_category(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_reference("Inbox thought", CategoryLabel("general"), None)

        created = asyncio.run(scenario())

        path = vault / "reference" / "general" / "Inbox thought.md"
        assert created is True
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.category == CategoryLabel("general")
        assert document.body == "# Inbox thought\n"

    def test_a_blank_name_writes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_reference("  ", CategoryLabel("general"), None)

        created = asyncio.run(scenario())

        assert created is False
        assert not (vault / "reference" / "general").exists()
        assert state.status.message == afanes.ui.strings.BROWSER_NAME_REQUIRED

    def test_a_collision_writes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Ada.md", _typed_note("reference", "# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_reference("Ada", CategoryLabel("general"), None)

        created = asyncio.run(scenario())

        assert created is False
        assert not (vault / "reference" / "general" / "Ada.md").exists()
        assert not (vault / "reference" / "general" / "Ada 2.md").exists()

    def test_a_dirty_current_page_is_saved_first(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "reference" / "Ada.md", _typed_note("reference", "# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)
            state.pages.edit_page()
            await state.pages.set_page_body("# Ada\n\nChanged.\n")
            return await state.navigation.create_reference("Priya", CategoryLabel("person"), "## Contact\n")

        created = asyncio.run(scenario())

        assert created is True
        assert "# Ada\n\nChanged.\n" in note.read_text(encoding="utf-8")
        assert state.pages.page is not None
        assert state.pages.page.path == (vault / "reference" / "person" / "Priya.md").resolve()

    def test_a_refresh_failure_is_reported_after_the_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        original = afanes.core.vault.service.Vault.scan

        def failing_scan(current: afanes.core.vault.service.Vault) -> afanes.core.vault.snapshot.VaultSnapshot:
            if (current.root / "reference" / "person" / "Priya.md").exists():
                message = "scan failed"
                raise VaultError(message)
            return original(current)

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            monkeypatch.setattr(afanes.core.vault.service.Vault, "scan", failing_scan)
            return await state.navigation.create_reference("Priya", CategoryLabel("person"), None)

        created = asyncio.run(scenario())

        assert created is True
        assert (vault / "reference" / "person" / "Priya.md").is_file()
        assert state.status.message is not None
        assert state.status.message.startswith("Could not refresh")


class TestAssignmentCandidates:
    def test_returns_candidates_from_the_last_scan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects/Ada.md",
            "---\ntype: project\nstatus: active\n---\n# Ada, Countess of Lovelace\n",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.choose_vault(vault))
        candidates = state.session.assignment_candidates(ReferenceScheme.PROJECT, "countess")

        assert [note.name for note in candidates] == ["Ada"]
        assert candidates[0].title == "Ada, Countess of Lovelace"

    def test_returns_nothing_without_a_vault(self) -> None:
        state = afanes.ui.state.app_state

        assert state.session.assignment_candidates(ReferenceScheme.PROJECT, "ada") == ()

    def test_candidates_follow_a_refresh(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> tuple[afanes.core.vault.snapshot.VaultNote, ...]:
            await state.workspace.choose_vault(vault)
            _write_note(
                vault / "projects/Launch.md",
                "---\ntype: project\nstatus: active\n---\n# Launch the product\n",
            )
            await state.workspace.refresh()
            return state.session.assignment_candidates(ReferenceScheme.PROJECT, "product")

        candidates = asyncio.run(scenario())

        assert [note.name for note in candidates] == ["Launch"]


class TestStartup:
    def test_without_settings_shows_welcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root is None
        assert state.session.notes == ()
        assert state.status.message is None

    def test_malformed_settings_show_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        settings.write_text("{not json", encoding="utf-8")
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.SETTINGS_UNREADABLE
        assert settings.read_text(encoding="utf-8") == "{not json"

    def test_missing_vault_shows_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        missing = tmp_path / "missing"
        settings = tmp_path / "settings.json"
        _write_settings(settings, missing)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_MISSING
        assert not missing.exists()

    def test_file_vault_shows_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.write_text("not a directory", encoding="utf-8")
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_NOT_DIRECTORY

    def test_valid_settings_opens_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("First")
        second = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("Second")
        os.utime(first, ns=(OLD_NS, OLD_NS))
        os.utime(second, ns=(NEW_NS, NEW_NS))
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root == vault.resolve()
        assert [note.name for note in state.session.notes] == ["Second", "First"]
        assert state.status.message is None

    def test_starting_does_not_create_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state
        before = _tree_state(vault)

        asyncio.run(state.workspace.start())

        assert not (vault / "inbox").exists()
        assert _tree_state(vault) == before

    def test_unreadable_notes_are_reported(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("Good")
        bad = _write_note(vault / "inbox" / "Bad.md", "---\ntype: [unclosed\n---\n")
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert [note.name for note in state.session.notes] == ["Good"]
        assert [failure.path.as_posix() for failure in state.session.failures] == ["inbox/Bad.md"]
        assert bad.read_text(encoding="utf-8") == "---\ntype: [unclosed\n---\n"


class TestChooseVault:
    def test_choose_vault_saves_settings_and_lists_notes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("Buy milk")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.choose_vault(vault))

        assert state.session.vault_root == vault.resolve()
        assert [note.name for note in state.session.notes] == ["Buy milk"]
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(vault.resolve())

    def test_choose_vault_rejects_a_missing_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        missing = tmp_path / "missing"
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.choose_vault(missing))

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_MISSING
        assert not settings.exists()

    def test_choose_vault_rejects_a_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.write_text("not a directory", encoding="utf-8")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.choose_vault(vault))

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_NOT_DIRECTORY

    def test_choose_vault_reports_a_save_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def fail_save(_store: SettingsStore, _settings: Settings) -> None:
            message = "simulated"
            raise ConfigurationError(message)

        monkeypatch.setattr(afanes.core.settings.SettingsStore, "save", fail_save)

        asyncio.run(state.workspace.choose_vault(vault))

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_SELECTION_FAILED.format(detail="simulated")

    def test_choose_vault_does_not_write_to_the_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        before = _tree_state(vault)

        asyncio.run(state.workspace.choose_vault(vault))

        assert _tree_state(vault) == before


class TestChangeVault:
    def test_change_vault_switches_and_preserves_the_previous(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = tmp_path / "first"
        second = tmp_path / "second"
        _versioned(first)
        _versioned(second)
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(first)).capture("First note")
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(second)).capture("Second note")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state
        first_before = _tree_state(first)

        async def scenario() -> None:
            await state.workspace.choose_vault(first)
            await state.workspace.change_vault(second)

        asyncio.run(scenario())

        assert state.session.vault_root == second.resolve()
        assert [note.name for note in state.session.notes] == ["Second note"]
        assert _tree_state(first) == first_before
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(second.resolve())

    def test_change_vault_failure_keeps_the_current_vault(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = tmp_path / "first"
        _versioned(first)
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(first)).capture("First note")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(first)
            await state.workspace.change_vault(tmp_path / "missing")

        asyncio.run(scenario())

        assert state.session.vault_root == first.resolve()
        assert state.status.message == afanes.ui.strings.VAULT_MISSING
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(first.resolve())


class TestAdoption:
    def test_welcome_offers_adoption_for_a_remembered_folder(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = _adoptable(tmp_path / "vault")
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root is None
        assert state.session.adoption_target == vault.resolve()
        assert state.status.message == afanes.ui.strings.VAULT_SCHEMA_ADOPT_MESSAGE
        assert not (vault / "afanes.yaml").exists()

    def test_welcome_refuses_a_folder_without_the_defaults(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root is None
        assert state.session.adoption_target is None
        assert state.status.message == afanes.ui.strings.VAULT_SCHEMA_UNAVAILABLE
        assert list(vault.iterdir()) == []

    def test_change_vault_offers_adoption_and_keeps_the_current_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = _versioned(tmp_path / "first")
        second = _adoptable(tmp_path / "second")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(first)
            await state.workspace.change_vault(second)

        asyncio.run(scenario())

        assert state.session.vault_root == first.resolve()
        assert state.session.adoption_target == second.resolve()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(first.resolve())
        assert not (second / "afanes.yaml").exists()

    def test_declining_adoption_keeps_the_current_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = _versioned(tmp_path / "first")
        second = _adoptable(tmp_path / "second")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(first)
            await state.workspace.change_vault(second)

        asyncio.run(scenario())
        state.workspace.cancel_adoption()

        assert state.session.adoption_target is None
        assert state.session.vault_root == first.resolve()
        assert not (second / "afanes.yaml").exists()

    def test_confirming_adoption_writes_only_the_settings_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = _versioned(tmp_path / "first")
        second = _adoptable(tmp_path / "second")
        note = second / "inbox" / "Buy milk.md"
        note.write_text(_note_text("# Buy milk"), encoding="utf-8")
        before = _tree_state(second)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(first)
            await state.workspace.change_vault(second)
            await state.workspace.adopt_vault()

        asyncio.run(scenario())

        after = _tree_state(second)
        assert state.session.vault_root == second.resolve()
        assert state.session.adoption_target is None
        assert [item.name for item in state.session.notes] == ["Buy milk"]
        assert set(after) - set(before) == {"afanes.yaml"}
        assert all(after[path] == content for path, content in before.items())
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(second.resolve())

    def test_adoption_write_failure_keeps_the_offer(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = _versioned(tmp_path / "first")
        second = _adoptable(tmp_path / "second")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def fail_adopt(_store: afanes.core.vault.schema.VaultSchemaStore) -> None:
            message = "disk full"
            raise VaultSchemaWriteError(message)

        monkeypatch.setattr(afanes.core.vault.schema.VaultSchemaStore, "adopt", fail_adopt)

        async def scenario() -> None:
            await state.workspace.choose_vault(first)
            await state.workspace.change_vault(second)
            await state.workspace.adopt_vault()

        asyncio.run(scenario())

        assert state.session.vault_root == first.resolve()
        assert state.session.adoption_target == second.resolve()
        assert state.status.message == "disk full"
        assert not (second / "afanes.yaml").exists()

    def test_adoption_remember_failure_still_opens_the_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = _versioned(tmp_path / "first")
        second = _adoptable(tmp_path / "second")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def fail_save(_store: SettingsStore, _settings: Settings) -> None:
            message = "settings are read-only"
            raise ConfigurationError(message)

        monkeypatch.setattr(SettingsStore, "save", fail_save)

        async def scenario() -> None:
            await state.workspace.choose_vault(first)
            await state.workspace.change_vault(second)
            await state.workspace.adopt_vault()

        asyncio.run(scenario())

        assert state.session.vault_root == second.resolve()
        assert state.session.adoption_target is None
        assert state.status.message == afanes.ui.strings.VAULT_SCHEMA_ADOPTED_NOT_REMEMBERED.format(
            detail="settings are read-only",
        )

    def test_invalid_schema_is_reported_and_preserved(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = vault / "afanes.yaml"
        path.write_text("schema_version: 1\nextra: true\n", encoding="utf-8")
        before = path.read_bytes()
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root is None
        assert state.session.adoption_target is None
        assert "exactly schema_version" in (state.status.message or "")
        assert path.read_bytes() == before

    def test_newer_schema_is_refused_with_an_update_message(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "afanes.yaml").write_text("schema_version: 2\n", encoding="utf-8")
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())

        assert state.session.vault_root is None
        assert state.session.adoption_target is None
        assert "update Afanes" in (state.status.message or "")

    def test_a_read_only_unversioned_folder_is_refused_without_an_offer(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = _adoptable(tmp_path / "vault")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        monkeypatch.setattr(
            afanes.core.vault.schema.os,
            "access",
            lambda _path, mode: mode == os.R_OK,
        )
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.choose_vault(vault))

        assert state.session.vault_root is None
        assert state.session.adoption_target is None
        assert state.status.message == afanes.ui.strings.VAULT_SCHEMA_UNAVAILABLE
        assert not (vault / "afanes.yaml").exists()

    def test_an_unversioned_supplied_folder_is_not_offered_adoption(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = _adoptable(tmp_path / "vault")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.open_vault_for_run(vault))

        assert state.session.vault_root is None
        assert state.session.adoption_target is None
        assert state.status.message == afanes.ui.strings.VAULT_SCHEMA_UNAVAILABLE
        assert not (vault / "afanes.yaml").exists()

    def test_adoption_requires_a_pending_offer(self) -> None:
        state = afanes.ui.state.app_state

        assert asyncio.run(state.workspace.adopt_vault()) is False


class TestLogMode:
    def test_default_mode_is_entries(self) -> None:
        state = afanes.ui.state.app_state

        assert state.browser.log_mode is LogMode.ENTRIES
        assert state.browser.log_year is None
        assert state.browser.log_month is None
        assert state.browser.log_selected is None

    def test_reset_restores_the_log_defaults(self) -> None:
        state = afanes.ui.state.app_state
        state.browser.set_log_mode(LogMode.EVERYTHING)
        state.browser.show_log_month(2025, 10)
        state.browser.select_log_entry(Path("/vault/log/2025/10/2025-10-12.md"))

        state.reset()

        assert state.browser.log_mode is LogMode.ENTRIES
        assert state.browser.log_year is None
        assert state.browser.log_month is None
        assert state.browser.log_selected is None

    def test_mode_is_remembered_for_the_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> LogMode:
            await state.workspace.choose_vault(vault)
            await state.workspace.set_log_mode("everything")
            await state.workspace.choose_vault(vault)
            return state.browser.log_mode

        assert asyncio.run(scenario()) is LogMode.EVERYTHING

    def test_unknown_mode_falls_back_to_entries(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> LogMode:
            await state.workspace.choose_vault(vault)
            await state.workspace.set_log_mode("unknown")
            return state.browser.log_mode

        assert asyncio.run(scenario()) is LogMode.ENTRIES


class TestLogEntryCreation:
    def test_creates_and_opens_a_log_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.open_or_create_log_entry(
                NoteDate.from_text("2025-10-12"),
                "A quiet Tuesday",
                "## What happened\n",
            )

        assert asyncio.run(scenario()) is True
        path = vault / "log" / "2025" / "10" / "2025-10-12.md"
        assert path.is_file()
        assert state.pages.page is not None
        assert state.pages.page.path == path
        assert state.pages.editing is True
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.date == NoteDate.from_text("2025-10-12")
        assert "## What happened" in document.body

    def test_occupied_date_opens_the_existing_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> tuple[bool, bool]:
            await state.workspace.choose_vault(vault)
            first = await state.navigation.open_or_create_log_entry(
                NoteDate.from_text("2025-10-12"),
                "First",
                None,
            )
            second = await state.navigation.open_or_create_log_entry(
                NoteDate.from_text("2025-10-12"),
                "Second",
                None,
            )
            return first, second

        assert asyncio.run(scenario()) == (True, True)
        path = vault / "log" / "2025" / "10" / "2025-10-12.md"
        assert path.is_file()
        assert "First" in path.read_text(encoding="utf-8")
        assert "Second" not in path.read_text(encoding="utf-8")

    def test_blank_title_is_reported(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.open_or_create_log_entry(
                NoteDate.from_text("2025-10-12"),
                "   ",
                None,
            )

        assert asyncio.run(scenario()) is False
        assert state.status.message is not None
        assert not (vault / "log" / "2025" / "10" / "2025-10-12.md").exists()


class TestCapture:
    def test_capture_writes_and_promotes_the_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.workspace.choose_vault(vault)
            return await state.session.capture("Buy milk")

        path = asyncio.run(scenario())

        assert path is not None
        assert path.name == "Buy milk.md"
        assert state.session.notes[0].path == path
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.NOTE
        assert document.date is not None
        assert state.status.message is None

    def test_empty_capture_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.workspace.choose_vault(vault)
            return await state.session.capture(" \n\t")

        path = asyncio.run(scenario())

        assert path is None
        assert state.status.message == afanes.ui.strings.CAPTURE_EMPTY
        assert state.session.notes == ()

    def test_successful_capture_clears_the_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("")
            await state.session.capture("Buy milk")

        asyncio.run(scenario())

        assert state.status.message is None
        assert len(state.session.notes) == 1

    def test_capture_failure_reports_and_keeps_the_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def fail_capture(_self: afanes.core.vault.pages.VaultPages, _text: str) -> Path:
            message = "disk full"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.pages.VaultPages, "capture", fail_capture)

        async def scenario() -> Path | None:
            await state.workspace.choose_vault(vault)
            return await state.session.capture("Buy milk")

        path = asyncio.run(scenario())

        assert path is None
        assert state.status.message == afanes.ui.strings.CAPTURE_FAILED.format(detail="disk full")
        assert state.session.notes == ()

    def test_repeated_captures_get_distinct_names(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")
            await state.session.capture("Buy milk")

        asyncio.run(scenario())

        assert [note.name for note in state.session.notes] == ["Buy milk 2", "Buy milk"]

    def test_capture_works_with_an_unreadable_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Bad.md", "---\ntype: [unclosed\n---\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.workspace.choose_vault(vault)
            return await state.session.capture("Buy milk")

        path = asyncio.run(scenario())

        assert path is not None
        assert [note.name for note in state.session.notes] == ["Buy milk"]
        assert len(state.session.failures) == 1

    def test_capture_does_not_infer_structure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.workspace.choose_vault(vault)
            return await state.session.capture("Ask Ada about 2026-11-20")

        path = asyncio.run(scenario())

        assert path is not None
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw["type"] == "note"
        assert document.date is not None
        assert document.due_date is None
        assert document.category is None

    def test_capture_does_not_modify_other_notes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        existing = _write_note(vault / "work" / "Existing.md", _note_text("Do not touch"))
        before = existing.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")

        asyncio.run(scenario())

        assert existing.read_bytes() == before


class TestPreview:
    def test_select_note_loads_body_without_frontmatter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("First line\nsecond line")
            await state.session.select_note(state.session.notes[0].path)

        asyncio.run(scenario())

        assert state.session.selected == state.session.notes[0].path
        assert state.session.preview_body == "# First line\nsecond line"
        assert "type: note" not in (state.session.preview_body or "")

    def test_preview_performs_no_write(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        before: list[tuple[bytes, int]] = []

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")
            path = state.session.notes[0].path
            before.append((path.read_bytes(), path.stat().st_mtime_ns))
            await state.session.select_note(path)

        asyncio.run(scenario())

        path = state.session.notes[0].path
        assert (path.read_bytes(), path.stat().st_mtime_ns) == before[0]

    def test_preview_failure_clears_the_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")
            state.session.notes[0].path.unlink()
            await state.session.select_note(state.session.notes[0].path)

        asyncio.run(scenario())

        assert state.session.selected is None
        assert state.session.preview_body is None
        assert state.status.message is not None
        assert state.status.message.startswith("Could not read this note:")


class TestSessionConnections:
    def test_builds_one_index_per_snapshot(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "notes" / "Ada.md", _note_text("# Ada"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        calls = 0
        original = afanes.core.connections.Connections

        def counting_connections(
            snapshot: afanes.core.vault.snapshot.VaultSnapshot,
        ) -> afanes.core.connections.Connections:
            nonlocal calls
            calls += 1
            return original(snapshot)

        monkeypatch.setattr(afanes.core.connections, "Connections", counting_connections)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            first = state.session.connections
            second = state.session.connections
            assert first is second

        asyncio.run(scenario())

        assert calls == 1

    def test_rebuilds_after_a_new_snapshot(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "notes" / "Ada.md", _note_text("# Ada"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            first = state.session.connections
            _write_note(vault / "notes" / "Grace.md", _note_text("# Grace"))
            await state.workspace.refresh()
            second = state.session.connections
            assert second is not first

        asyncio.run(scenario())

    def test_reset_clears_the_index(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "notes" / "Ada.md", _note_text("# Ada"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            assert state.session.connections is not None
            state.reset()
            assert state.session.connections is None

        asyncio.run(scenario())


class TestRefresh:
    def test_refresh_adds_an_external_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("External note")
            await state.workspace.refresh()

        asyncio.run(scenario())

        assert [note.name for note in state.session.notes] == ["External note"]

    def test_refresh_removes_a_deleted_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")
            state.session.notes[0].path.unlink()
            await state.workspace.refresh()

        asyncio.run(scenario())

        assert state.session.notes == ()

    def test_refresh_updates_the_selected_preview(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Old body")
            path = state.session.notes[0].path
            await state.session.select_note(path)
            path.write_text(_note_text("New body\n"), encoding="utf-8")
            await state.workspace.refresh()

        asyncio.run(scenario())

        assert state.session.preview_body == "New body\n"

    def test_refresh_clears_a_disappeared_selection(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")
            path = state.session.notes[0].path
            await state.session.select_note(path)
            path.unlink()
            await state.workspace.refresh()

        asyncio.run(scenario())

        assert state.session.selected is None
        assert state.session.preview_body is None

    def test_refresh_without_a_vault_is_a_no_op(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.refresh())

        assert state.session.notes == ()
        assert state.status.message is None


class TestRefreshIfChanged:
    def _session(self, root: Path) -> afanes.ui.state.session.VaultSession:
        vault = afanes.core.vault.service.Vault.open(root)
        session = afanes.ui.state.session.VaultSession(
            afanes.ui.state.status.UiStatus(),
            afanes.ui.state.lock.CommandLock(),
        )
        session.vault = vault
        session.apply_snapshot(vault.scan())
        return session

    def test_unchanged_vault_returns_none_without_a_scan(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox" / "Ada.md", _note_text("# Ada"))
        session = self._session(root)
        calls = 0
        original = afanes.core.vault.service.Vault.scan

        def counting_scan(vault: afanes.core.vault.service.Vault) -> afanes.core.vault.snapshot.VaultSnapshot:
            nonlocal calls
            calls += 1
            return original(vault)

        monkeypatch.setattr(afanes.core.vault.service.Vault, "scan", counting_scan)

        result = asyncio.run(session.refresh_if_changed())

        assert result is None
        assert calls == 0

    def test_a_changed_vault_triggers_exactly_one_scan(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox" / "Ada.md", _note_text("# Ada"))
        session = self._session(root)
        calls = 0
        original = afanes.core.vault.service.Vault.scan

        def counting_scan(vault: afanes.core.vault.service.Vault) -> afanes.core.vault.snapshot.VaultSnapshot:
            nonlocal calls
            calls += 1
            return original(vault)

        monkeypatch.setattr(afanes.core.vault.service.Vault, "scan", counting_scan)
        _write_note(root / "inbox" / "Grace.md", _note_text("# Grace"))

        result = asyncio.run(session.refresh_if_changed())

        assert result is not None
        assert calls == 1
        assert {note.name for note in session.notes} == {"Ada", "Grace"}

    def test_no_vault_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        session = afanes.ui.state.session.VaultSession(
            afanes.ui.state.status.UiStatus(),
            afanes.ui.state.lock.CommandLock(),
        )

        assert asyncio.run(session.refresh_if_changed()) is None


class TestRefreshWorkspace:
    def test_without_a_vault_returns_false(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        assert asyncio.run(state.workspace.refresh_workspace()) is False

    def test_busy_lock_skips_the_tick(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        entered = threading.Event()
        release = threading.Event()
        original = afanes.core.vault.service.Vault.scan

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)

            def blocking_scan(current: afanes.core.vault.service.Vault) -> afanes.core.vault.snapshot.VaultSnapshot:
                entered.set()
                release.wait(timeout=5)
                return original(current)

            monkeypatch.setattr(afanes.core.vault.service.Vault, "scan", blocking_scan)
            first = asyncio.create_task(state.workspace.refresh())
            try:
                await asyncio.to_thread(entered.wait, 5)
                return await state.workspace.refresh_workspace()
            finally:
                release.set()
                await first

        assert asyncio.run(scenario()) is False

    def test_does_not_set_the_busy_indicator(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        observed: list[bool] = []
        original = afanes.core.vault.service.Vault.scan

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)

            def recording_scan(current: afanes.core.vault.service.Vault) -> afanes.core.vault.snapshot.VaultSnapshot:
                observed.append(state.status.busy)
                return original(current)

            monkeypatch.setattr(afanes.core.vault.service.Vault, "scan", recording_scan)
            _write_note(vault / "inbox" / "External.md", _note_text("# External"))
            return await state.workspace.refresh_workspace()

        assert asyncio.run(scenario()) is True
        assert observed == [False]

    def test_pending_processing_plan_is_untouched(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        plan: ProcessingPlan | AppendStepPlan | None = None

        async def scenario() -> None:
            nonlocal plan
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Buy milk")
            assert capture is not None
            await state.processing.begin(capture)
            plan = await state.processing.build_plan(ProcessingOutcome.PROJECT)
            _write_note(vault / "inbox" / "External.md", _note_text("# External"))
            changed = await state.workspace.refresh_workspace()
            assert changed is True

        asyncio.run(scenario())

        assert plan is not None
        assert state.processing.note is not None
        assert state.processing.plan is plan
        assert state.processing.body == "# Buy milk"
        assert "External" in {note.name for note in state.session.notes}

    def test_clean_page_reloads_an_external_edit(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Old body")
            assert capture is not None
            await state.navigation.open_page(capture)
            _write_note(capture, _note_text("New body\n"))
            assert await state.workspace.refresh_workspace() is True

        asyncio.run(scenario())

        assert state.pages.page_body == "New body\n"
        assert state.pages.conflict is None
        assert state.pages.editing is False

    def test_dirty_draft_keeps_its_text_and_raises_changed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Old body")
            assert capture is not None
            await state.navigation.open_page(capture)
            state.pages.edit_page()
            await state.pages.set_page_body("Mine\n")
            _write_note(capture, _note_text("Theirs\n"))
            assert await state.workspace.refresh_workspace() is True

        asyncio.run(scenario())

        assert state.pages.page_body == "Mine\n"
        assert state.pages.conflict == "changed"
        assert state.status.message == afanes.ui.strings.PAGE_CONFLICT_CHANGED

    def test_missing_file_raises_missing_and_keeps_the_draft(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Old body")
            assert capture is not None
            await state.navigation.open_page(capture)
            state.pages.edit_page()
            await state.pages.set_page_body("Mine\n")
            capture.unlink()
            assert await state.workspace.refresh_workspace() is True

        asyncio.run(scenario())

        assert state.pages.page_body == "Mine\n"
        assert state.pages.conflict == "missing"
        assert state.status.message == afanes.ui.strings.PAGE_CONFLICT_MISSING

    def test_conflict_resolves_with_the_existing_actions(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Old body")
            assert capture is not None
            await state.navigation.open_page(capture)
            state.pages.edit_page()
            await state.pages.set_page_body("Mine\n")
            _write_note(capture, _note_text("Theirs\n"))
            await state.workspace.refresh_workspace()
            assert await state.dialogs.overwrite_page() is True

        asyncio.run(scenario())

        assert state.pages.conflict is None
        assert state.pages.page_body == "Mine\n"
        assert state.status.message is None

    def test_a_command_message_survives_the_background_apply(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> str | None:
            await state.workspace.choose_vault(vault)
            state.status.message = "Saved by a command"
            _write_note(vault / "inbox" / "External.md", _note_text("# External"))
            assert await state.workspace.refresh_workspace() is True
            return state.status.message

        assert asyncio.run(scenario()) == "Saved by a command"

    def test_a_capture_still_clears_the_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            state.status.message = "Old message"
            assert await state.session.capture("Buy milk") is not None

        asyncio.run(scenario())

        assert state.status.message is None

    def test_background_refresh_writes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def mtimes() -> dict[str, int]:
            return {
                path.relative_to(vault).as_posix(): path.stat().st_mtime_ns
                for path in vault.rglob("*")
                if path.is_file()
            }

        async def scenario() -> tuple[dict[str, bytes], dict[str, bytes], dict[str, int], dict[str, int]]:
            await state.workspace.choose_vault(vault)
            capture = await state.session.capture("Old body")
            assert capture is not None
            _write_note(capture, _note_text("Theirs\n"))
            before_files = _tree_state(vault)
            before_mtimes = mtimes()
            assert await state.workspace.refresh_workspace() is True
            return before_files, _tree_state(vault), before_mtimes, mtimes()

        before_files, after_files, before_mtimes, after_mtimes = asyncio.run(scenario())

        assert before_files
        assert after_files == before_files
        assert after_mtimes == before_mtimes


class TestConcurrency:
    def test_commands_are_serialized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        entered = threading.Event()
        release = threading.Event()
        original = afanes.core.vault.pages.VaultPages.capture

        def blocking_capture(pages: afanes.core.vault.pages.VaultPages, text: str) -> Path:
            entered.set()
            release.wait(timeout=5)
            return original(pages, text)

        monkeypatch.setattr(afanes.core.vault.pages.VaultPages, "capture", blocking_capture)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            first = asyncio.create_task(state.session.capture("Buy milk"))
            assert await asyncio.to_thread(entered.wait, 2) is True
            assert state.status.busy is True
            second = asyncio.create_task(state.workspace.refresh())
            await asyncio.sleep(0)
            assert second.done() is False
            release.set()
            await asyncio.gather(first, second)
            assert state.status.busy is False

        asyncio.run(scenario())

        assert [note.name for note in state.session.notes] == ["Buy milk"]


class TestPageSession:
    def test_open_page_loads_a_read_only_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        before = path.read_bytes()

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.open_page(path)

        opened = asyncio.run(scenario())

        assert opened is True
        assert state.pages.page is not None
        assert state.pages.page.path == path.resolve()
        assert state.pages.editing is False
        assert state.pages.page_title == "Ada"
        assert path.read_bytes() == before

    def test_opening_a_second_page_pushes_history(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(first)
            await state.navigation.open_page(second)
            assert state.navigation.history == (first.resolve(),)
            assert state.pages.page is not None
            assert state.pages.page.path == second.resolve()
            await state.navigation.back()
            assert state.pages.page is not None
            assert state.pages.page.path == first.resolve()
            assert state.navigation.history == ()
            await state.navigation.back()
            assert state.pages.page is None

        asyncio.run(scenario())

    def test_back_discards_an_untouched_new_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(first)
            await state.navigation.follow_link("note:Missing")
            assert state.pages.page is not None
            assert state.pages.page.is_new
            assert state.pages.editing is True
            await state.navigation.back()
            assert state.pages.page is not None
            assert state.pages.page.path == first.resolve()
            assert not (vault / "reference" / "Missing.md").exists()

        asyncio.run(scenario())

    def test_history_is_bounded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        paths = [
            _write_note(vault / "notes" / f"Note {index:02d}.md", _note_text(f"# Note {index:02d}\n"))
            for index in range(55)
        ]
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            for path in paths:
                await state.navigation.open_page(path)

        asyncio.run(scenario())

        assert len(state.navigation.history) == afanes.ui.state.navigation.PAGE_HISTORY_LIMIT
        assert state.navigation.history[0] == paths[4].resolve()
        assert state.navigation.history[-1] == paths[53].resolve()

    def test_back_skips_a_missing_history_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(first)
            await state.navigation.open_page(second)
            first.unlink()
            await state.navigation.back()

        asyncio.run(scenario())

        assert state.pages.page is None
        assert state.status.message is not None

    def test_done_editing_commits_the_body(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            assert state.pages.edit_page() is True
            await state.pages.set_page_body("# Ada\n\nNew body.\n")
            committed = await state.pages.done_editing()
            assert committed is True

        asyncio.run(scenario())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.body == "# Ada\n\nNew body.\n"
        assert state.pages.editing is False
        assert state.pages.page is not None
        assert state.pages.page.is_dirty is False

    def test_reset_clears_the_page_and_history(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(first)

        asyncio.run(scenario())
        state.reset()

        assert state.pages.page is None
        assert state.navigation.history == ()
        assert state.pages.editing is False


class TestPageLabels:
    def test_type_change_with_referrers_waits_for_confirmation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        referrer = _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)
            applied = await state.dialogs.set_page_type(NoteType.PROJECT)
            assert applied is False
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.scheme is ReferenceScheme.NOTE
            assert state.dialogs.pending_labels is not None
            assert state.dialogs.pending_labels.scheme is ReferenceScheme.PROJECT
            assert len(state.dialogs.type_change_sites) == 1
            assert state.dialogs.type_change_sites[0].path == referrer.resolve()
            assert await state.dialogs.apply_type_change() is True
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.note_type is NoteType.PROJECT
            assert page.labels.category is None
            assert state.dialogs.pending_labels is None

        asyncio.run(scenario())

    def test_cancelling_a_type_change_keeps_the_original_labels(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)
            await state.dialogs.set_page_type(NoteType.PROJECT)
            await state.dialogs.cancel_type_change()
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.scheme is ReferenceScheme.NOTE
            assert state.dialogs.pending_labels is None
            assert state.dialogs.type_change_sites == ()

        asyncio.run(scenario())

    def test_same_scheme_type_change_applies_immediately(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        reference = _write_note(vault / "reference" / "Call.md", _typed_note("reference", "# Call\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(reference)
            assert await state.dialogs.set_page_type(NoteType.NOTE) is True
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.note_type is NoteType.NOTE
            assert state.dialogs.pending_labels is None

        asyncio.run(scenario())

    def test_new_draft_scheme_change_applies_without_a_scan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:New person")
            assert await state.dialogs.set_page_category(CategoryLabel("person")) is True
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.scheme is ReferenceScheme.NOTE
            assert state.dialogs.pending_labels is None

        asyncio.run(scenario())

    def test_invalid_status_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            await state.dialogs.set_page_status(Status.ACTIVE)
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.status is None
            assert state.status.message is not None

        asyncio.run(scenario())

    def test_due_date_updates_the_labels(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        project = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(project)
            await state.dialogs.set_page_due_date("January")
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.due_date_error is not None
            await state.dialogs.set_page_due_date("2027-01-02")
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.due_date == datetime.date(2027, 1, 2)

        asyncio.run(scenario())

    def test_requester_updates_the_labels(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        project = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(project)
            await state.dialogs.set_page_asked_by("Priya Nair")
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.asked_by_text == "Priya Nair"
            assert page.is_dirty
            await state.dialogs.set_page_asked_by("")
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.asked_by_text == ""
            assert not page.is_dirty

        asyncio.run(scenario())

    def test_owner_updates_the_labels(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        project = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(project)
            await state.pages.set_page_owner("Sam Rivera")
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.owner_text == "Sam Rivera"
            assert page.is_dirty
            await state.pages.set_page_owner("")
            page = state.pages.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.owner_text == ""
            assert not page.is_dirty

        asyncio.run(scenario())

    def test_assignment_suggestions_come_from_the_scan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        person = _write_note(
            vault / "projects" / "Ada.md",
            _typed_note("project", "# Ada, Countess of Lovelace\n"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            candidates = state.session.assignment_candidates(ReferenceScheme.PROJECT, "countess")
            assert [candidate.path for candidate in candidates] == [person.resolve()]

        asyncio.run(scenario())


class TestPageSaving:
    def test_autosave_writes_a_dirty_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            assert state.pages.edit_page() is True
            await state.pages.set_page_body("# Ada\n\nNew body.\n")
            return await state.pages.autosave()

        saved = asyncio.run(scenario())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert saved is True
        assert document.body == "# Ada\n\nNew body.\n"
        assert state.pages.page is not None
        assert state.pages.page.is_dirty is False

    def test_autosave_skips_a_clean_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            state.pages.edit_page()
            return await state.pages.autosave()

        assert asyncio.run(scenario()) is False

    def test_untouched_new_draft_is_not_written(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Quarterly budget")
            return await state.pages.autosave()

        saved = asyncio.run(scenario())

        assert saved is False
        assert not (vault / "reference" / "Quarterly budget.md").exists()

    def test_new_draft_is_created_on_first_autosave(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Quarterly budget")
            await state.pages.set_page_body("# Quarterly budget\n\nDraft the numbers.\n")
            return await state.pages.autosave()

        saved = asyncio.run(scenario())

        path = vault / "reference" / "Quarterly budget.md"
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert saved is True
        assert path.exists()
        assert document.body == "# Quarterly budget\n\nDraft the numbers.\n"
        assert state.pages.page is not None
        assert state.pages.page.path == path.resolve()
        assert state.pages.page.is_dirty is False

    def test_external_change_stops_autosave(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        external = _note_text("# Ada\n\nExternal edit.\n")

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            state.pages.edit_page()
            await state.pages.set_page_body("# Ada\n\nMy edit.\n")
            path.write_text(external, encoding="utf-8", newline="\n")
            return await state.pages.autosave()

        saved = asyncio.run(scenario())

        assert saved is False
        assert state.pages.conflict == "changed"
        assert path.read_text(encoding="utf-8") == external
        assert state.pages.page is not None
        assert state.pages.page.is_dirty is True

    def test_reload_replaces_the_conflicted_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        external = _note_text("# Ada\n\nExternal edit.\n")

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            state.pages.edit_page()
            await state.pages.set_page_body("# Ada\n\nMy edit.\n")
            path.write_text(external, encoding="utf-8", newline="\n")
            await state.pages.autosave()
            return await state.dialogs.reload_page()

        reloaded = asyncio.run(scenario())

        assert reloaded is True
        assert state.pages.conflict is None
        assert state.pages.editing is False
        assert state.pages.page is not None
        assert state.pages.page.body == "# Ada\n\nExternal edit.\n"

    def test_overwrite_keeps_the_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            state.pages.edit_page()
            await state.pages.set_page_body("# Ada\n\nMy edit.\n")
            path.write_text(_note_text("# Ada\n\nExternal edit.\n"), encoding="utf-8", newline="\n")
            await state.pages.autosave()
            return await state.dialogs.overwrite_page()

        overwritten = asyncio.run(scenario())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert overwritten is True
        assert document.body == "# Ada\n\nMy edit.\n"
        assert state.pages.conflict is None
        assert state.pages.page is not None
        assert state.pages.page.is_dirty is False

    def test_recreate_after_the_file_disappears(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            state.pages.edit_page()
            await state.pages.set_page_body("# Ada\n\nMy edit.\n")
            path.unlink()
            await state.pages.autosave()
            assert state.pages.conflict == "missing"
            return await state.dialogs.recreate_page()

        recreated = asyncio.run(scenario())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert recreated is True
        assert document.body == "# Ada\n\nMy edit.\n"
        assert state.pages.conflict is None

    def test_discard_drops_the_draft_without_writing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        before = path.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            state.pages.edit_page()
            await state.pages.set_page_body("# Ada\n\nMy edit.\n")
            state.pages.clear()

        asyncio.run(scenario())

        assert state.pages.page is None
        assert path.read_bytes() == before

    def test_back_on_a_dirty_draft_commits_first(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(first)
            await state.navigation.open_page(second)
            state.pages.edit_page()
            await state.pages.set_page_body("# Second\n\nChanged.\n")
            await state.navigation.back()

        asyncio.run(scenario())

        document = NoteDocument.from_text(second.read_text(encoding="utf-8"))
        assert document.body == "# Second\n\nChanged.\n"
        assert state.pages.page is not None
        assert state.pages.page.path == first.resolve()

    def test_navigation_commits_a_dirty_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(first)
            state.pages.edit_page()
            await state.pages.set_page_body("# First\n\nChanged.\n")
            await state.navigation.open_page(second)

        asyncio.run(scenario())

        document = NoteDocument.from_text(first.read_text(encoding="utf-8"))
        assert document.body == "# First\n\nChanged.\n"
        assert state.pages.page is not None
        assert state.pages.page.path == second.resolve()
        assert state.navigation.history == (first.resolve(),)

    def test_conflict_blocks_back_until_discarded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(first)
            await state.navigation.open_page(second)
            state.pages.edit_page()
            await state.pages.set_page_body("# Second\n\nMy edit.\n")
            second.write_text(_note_text("# Second\n\nExternal.\n"), encoding="utf-8", newline="\n")
            await state.pages.autosave()
            assert await state.navigation.back() is False
            assert state.pages.page is not None
            assert state.pages.page.path == second.resolve()
            assert state.pages.conflict == "changed"
            state.pages.clear()
            assert await state.navigation.back() is True
            assert state.pages.page is not None
            assert state.pages.page.path == first.resolve()

        asyncio.run(scenario())

    def test_write_error_keeps_the_draft(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def failing_write(
            _self: afanes.core.vault.pages.VaultPages,
            _note_path: Path,
            _text: str,
            _expected_hash: str,
        ) -> str:
            message = "disk full"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.pages.VaultPages, "write_page", failing_write)

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            state.pages.edit_page()
            await state.pages.set_page_body("# Ada\n\nMy edit.\n")
            return await state.pages.autosave()

        saved = asyncio.run(scenario())

        assert saved is False
        assert state.pages.page is not None
        assert state.pages.page.is_dirty is True
        assert state.status.message is not None


class TestPageLinks:
    def test_resolved_link_opens_its_target(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Ada")

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.path == person.resolve()
        assert state.navigation.ambiguous == ()

    def test_ambiguous_link_exposes_the_candidates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        second = _write_note(vault / "notes" / "Ada.md", _typed_note("reference", "# Ada\n", category="person"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Ada")

        asyncio.run(scenario())

        assert state.pages.page is None
        assert set(state.navigation.ambiguous) == {first.resolve(), second.resolve()}

    def test_choosing_a_candidate_opens_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Ada.md", _typed_note("reference", "# Ada\n", category="person"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Ada")
            await state.navigation.choose_candidate(first)

        asyncio.run(scenario())

        assert state.navigation.ambiguous == ()
        assert state.pages.page is not None
        assert state.pages.page.path == first.resolve()

    def test_resolved_role_name_opens_its_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        person = _write_note(
            vault / "reference" / "people" / "Sam Rivera.md",
            _typed_note("reference", "# Sam Rivera\n", category="person"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> afanes.ui.state.navigation.RoleFollowOutcome:
            await state.workspace.choose_vault(vault)
            return await state.navigation.follow_role("Sam Rivera")

        outcome = asyncio.run(scenario())

        assert outcome is afanes.ui.state.navigation.RoleFollowOutcome.OPENED
        assert state.pages.page is not None
        assert state.pages.page.path == person.resolve()

    def test_ambiguous_role_name_exposes_the_candidates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(
            vault / "reference" / "people" / "Sam Rivera.md",
            _typed_note("reference", "# Sam Rivera\n", category="person"),
        )
        second = _write_note(vault / "notes" / "Sam Rivera.md", _typed_note("reference", "# Sam Rivera\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> afanes.ui.state.navigation.RoleFollowOutcome:
            await state.workspace.choose_vault(vault)
            return await state.navigation.follow_role("Sam Rivera")

        outcome = asyncio.run(scenario())

        assert outcome is afanes.ui.state.navigation.RoleFollowOutcome.AMBIGUOUS
        assert set(state.navigation.ambiguous) == {first.resolve(), second.resolve()}
        assert state.pages.page is None

    def test_role_navigation_writes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(
            vault / "reference" / "people" / "Sam Rivera.md",
            _typed_note("reference", "# Sam Rivera\n", category="person"),
        )
        _write_note(vault / "notes" / "Sam Rivera.md", _typed_note("reference", "# Sam Rivera\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        before = _tree_state(vault)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            ambiguous = await state.navigation.follow_role("Sam Rivera")
            assert ambiguous is afanes.ui.state.navigation.RoleFollowOutcome.AMBIGUOUS
            await state.navigation.choose_candidate(first)
            missing = await state.navigation.follow_role("Nobody")
            assert missing is afanes.ui.state.navigation.RoleFollowOutcome.MISSING

        asyncio.run(scenario())

        assert _tree_state(vault) == before
        assert state.pages.page is not None
        assert state.pages.page.path == first.resolve()

    def test_missing_role_name_reports_missing_without_writing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> afanes.ui.state.navigation.RoleFollowOutcome:
            await state.workspace.choose_vault(vault)
            return await state.navigation.follow_role("Sam Rivera")

        outcome = asyncio.run(scenario())

        assert outcome is afanes.ui.state.navigation.RoleFollowOutcome.MISSING
        assert state.pages.page is None
        assert not (vault / "reference" / "Sam Rivera.md").exists()

    def test_missing_references_create_the_right_drafts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Quarterly budget")
            note_page = state.pages.page
            assert note_page is not None
            assert note_page.labels is not None
            assert note_page.labels.note_type is NoteType.REFERENCE
            assert note_page.labels.category is None
            assert note_page.identity == "Quarterly budget"
            await state.navigation.follow_link("project:Release 1.0")
            assert state.pages.page is not None
            assert state.pages.page.labels is not None
            assert state.pages.page.labels.note_type is NoteType.PROJECT

        asyncio.run(scenario())

        assert not (vault / "reference" / "Quarterly budget.md").exists()

        assert not (vault / "projects" / "Release 1.0.md").exists()

    def test_broken_link_opens_raw_rescue(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Broken")

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.mode is afanes.core.editing.DraftMode.RAW
        assert state.pages.page.path == broken.resolve()
        assert state.pages.editing is True

    def test_multiple_broken_files_ask_for_a_candidate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        second = _write_note(vault / "notes" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Broken")

        asyncio.run(scenario())

        assert state.pages.page is None
        assert set(state.navigation.ambiguous) == {first.resolve(), second.resolve()}

    def test_non_internal_destinations_are_inert(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            for destination in (
                "https://example.com",
                "mailto:ada@example.com",
                "attachments/diagram.png",
                "javascript:alert(1)",
                "#section",
            ):
                await state.navigation.follow_link(destination)

        asyncio.run(scenario())

        assert state.pages.page is None
        assert state.status.message is None
        assert state.navigation.ambiguous == ()

    def test_unsafe_name_is_created_and_repaired(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Q1: Planning?")
            await state.pages.set_page_body("# Q1: Planning?\n\nDraft.\n")
            assert await state.pages.autosave() is True
            assert state.pages.repair_preview is not None
            assert [site.path for site in state.pages.repair_preview.sites] == [source.resolve()]
            assert await state.dialogs.apply_repair() is True

        asyncio.run(scenario())

        created = vault / "reference" / "Q1 Planning.md"
        assert created.exists()
        assert "note:Q1 Planning" in source.read_text(encoding="utf-8")
        assert "note:Q1: Planning?" not in source.read_text(encoding="utf-8")
        assert state.pages.repair_preview is None

    def test_keep_leaves_the_unsafe_reference_alone(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        before = source.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> dict[str, bytes]:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Q1: Planning?")
            await state.pages.set_page_body("# Q1: Planning?\n\nDraft.\n")
            await state.pages.autosave()
            before_tree = _tree_state(vault)
            await state.dialogs.keep_repair()
            return before_tree

        before_tree = asyncio.run(scenario())

        assert (vault / "reference" / "Q1 Planning.md").exists()
        assert source.read_bytes() == before
        assert state.pages.repair_preview is None
        assert _tree_state(vault) == before_tree

    def test_cancelling_the_repair_restores_the_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Q1: Planning?")
            await state.pages.set_page_body("# Q1: Planning?\n\nDraft.\n")
            await state.pages.autosave()
            assert await state.dialogs.cancel_repair() is True

        asyncio.run(scenario())

        assert not (vault / "reference" / "Q1 Planning.md").exists()
        assert (vault / "trash" / "Q1 Planning.md").exists()
        assert state.pages.page is not None
        assert state.pages.page.is_new
        assert state.pages.page.is_dirty
        assert state.pages.editing is True
        assert state.pages.repair_preview is None
        assert source.read_bytes() != b""

    def test_existing_safe_page_is_reused(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        existing = _write_note(vault / "reference" / "Q1 Planning.md", _note_text("# Q1 Planning\n"))
        _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Q1: Planning?")

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.path == existing.resolve()
        assert state.pages.repair_preview is not None


class TestRoleCategories:
    def test_offers_person_existing_and_template_categories(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _write_note(
            vault / "reference" / "process" / "Release.md",
            _typed_note("reference", "# Release\n", category="process"),
        )
        _write_note(
            vault / "reference" / "team" / "Platform.md",
            _typed_note("reference", "# Platform\n", category="team"),
        )
        card = vault / "templates" / "place.md"
        card.parent.mkdir(parents=True)
        card.write_text(
            "---\ntype: reference\ncategory: place\ntitle: Place\n---\n\n## Notes\n",
            encoding="utf-8",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> tuple[CategoryLabel, ...]:
            await state.workspace.choose_vault(vault)
            state.browser.query = "release"
            return await state.browser.role_categories()

        categories = asyncio.run(scenario())

        assert [category.value for category in categories] == ["person", "place", "process", "team"]

    def test_offers_person_without_templates_or_references(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> tuple[CategoryLabel, ...]:
            await state.workspace.choose_vault(vault)
            return await state.browser.role_categories()

        categories = asyncio.run(scenario())

        assert [category.value for category in categories] == ["person"]


class TestCreateRoleReference:
    def test_creates_a_categorized_reference_and_opens_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_role_reference("Sam Rivera", CategoryLabel("person"))

        created = asyncio.run(scenario())

        path = vault / "reference" / "person" / "Sam Rivera.md"
        assert created is True
        assert path.is_file()
        assert "# Sam Rivera" in path.read_text(encoding="utf-8")
        assert state.pages.editing is True
        assert state.pages.page is not None
        assert state.pages.page.path == path.resolve()
        assert state.pages.page.labels is not None
        assert state.pages.page.labels.category == CategoryLabel("person")

    def test_creates_an_uncategorized_reference(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_role_reference("Sam Rivera", None)

        created = asyncio.run(scenario())

        path = vault / "reference" / "Sam Rivera.md"
        assert created is True
        assert path.is_file()
        assert state.pages.page is not None
        assert state.pages.page.path == path.resolve()

    def test_uses_the_matching_template_card(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        card = vault / "templates" / "person.md"
        card.parent.mkdir(parents=True)
        card.write_text(
            "---\ntype: reference\ncategory: person\ntitle: Person\n---\n\n## Contact\n\n- Email:\n",
            encoding="utf-8",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_role_reference("Sam Rivera", CategoryLabel("person"))

        created = asyncio.run(scenario())

        path = vault / "reference" / "person" / "Sam Rivera.md"
        assert created is True
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.body.startswith("# Sam Rivera\n")
        assert "## Contact" in document.body
        assert "- Email:" in document.body

    def test_a_collision_writes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        existing = _write_note(vault / "reference" / "Sam Rivera.md", _note_text("# Existing\n"))
        before = existing.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_role_reference("Sam Rivera", None)

        created = asyncio.run(scenario())

        assert created is False
        assert existing.read_bytes() == before
        assert state.status.message is not None

    def test_a_blank_name_writes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.navigation.create_role_reference("   ", None)

        created = asyncio.run(scenario())

        assert created is False
        assert state.status.message == afanes.ui.strings.BROWSER_NAME_REQUIRED


class TestPageRenameTrash:
    def test_rename_is_previewed_and_applied(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        referrer = _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)
            await state.navigation.open_page(first)
            await state.navigation.open_page(person)
            preview = await state.dialogs.begin_rename("Ada King")
            assert preview is not None
            assert preview.heading_update is True
            assert state.dialogs.rename_preview is not None
            assert person.exists()
            assert await state.dialogs.apply_rename() is True

        asyncio.run(scenario())

        target = (vault / "reference" / "people" / "Ada King.md").resolve()
        assert not person.exists()
        assert target.exists()
        assert state.pages.page is not None
        assert state.pages.page.path == target
        assert state.pages.page_title == "Ada King"
        assert state.navigation.history == (target, first.resolve())
        assert "note:Ada King" in referrer.read_text(encoding="utf-8")

    def test_cancelling_a_rename_changes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        referrer = _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        before = _tree_state(vault)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)
            await state.dialogs.begin_rename("Ada King")
            await state.dialogs.cancel_rename()

        asyncio.run(scenario())

        assert person.exists()
        assert not (vault / "reference" / "people" / "Ada King.md").exists()
        assert state.dialogs.rename_preview is None
        assert _tree_state(vault) == before
        assert "note:Ada" in referrer.read_text(encoding="utf-8")

    def test_trash_is_previewed_and_returns_through_history(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _write_note(vault / "notes" / "Ref.md", _note_text("[Second](<note:Second>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(second)
            await state.navigation.open_page(first)
            await state.navigation.open_page(second)
            preview = await state.dialogs.begin_trash()
            assert preview is not None
            assert preview.reference_count == 1
            assert state.dialogs.trash_preview is not None
            assert await state.dialogs.apply_trash() is True

        asyncio.run(scenario())

        assert not second.exists()
        assert (vault / "trash" / "Second.md").exists()
        assert state.pages.page is not None
        assert state.pages.page.path == first.resolve()
        assert state.navigation.history == ()
        assert state.dialogs.trash_preview is None

    def test_cancelling_trash_changes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(second)
            await state.dialogs.begin_trash()
            await state.dialogs.cancel_trash()

        asyncio.run(scenario())

        assert second.exists()
        assert not (vault / "trash").exists()
        assert state.dialogs.trash_preview is None


class TestPageRescue:
    def test_open_failure_opens_raw_rescue(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            failure = state.session.failures[0]
            await state.navigation.open_failure(failure.path)

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.mode is afanes.core.editing.DraftMode.RAW
        assert state.pages.page.path == broken.resolve()
        assert state.pages.page.raw_text == "---\ntype: refrence\n---\nBody\n"
        assert state.pages.editing is True

    def test_raw_save_that_still_fails_stays_raw(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_failure(Path("reference/Broken.md"))
            await state.pages.set_page_raw_text("still broken")
            return await state.pages.autosave()

        saved = asyncio.run(scenario())

        assert saved is True
        assert broken.read_text(encoding="utf-8") == "still broken"
        assert state.pages.page is not None
        assert state.pages.page.mode is afanes.core.editing.DraftMode.RAW
        assert state.pages.page.is_dirty is False

    def test_raw_save_that_parses_upgrades_to_normal(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        fixed = "---\ntype: note\n---\n\n# Fixed\nBody.\n"

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_failure(Path("reference/Broken.md"))
            await state.pages.set_page_raw_text(fixed)
            return await state.pages.autosave()

        saved = asyncio.run(scenario())

        assert saved is True
        assert broken.read_text(encoding="utf-8") == fixed
        assert state.pages.page is not None
        assert state.pages.page.mode is afanes.core.editing.DraftMode.NORMAL
        assert state.pages.page.labels is not None
        assert state.pages.page.labels.note_type is NoteType.NOTE
        assert state.pages.page.is_dirty is False
        assert state.status.message == afanes.ui.strings.PAGE_RAW_UPGRADED
        assert state.pages.editing is True

        async def finish() -> None:
            await state.pages.done_editing()

        asyncio.run(finish())

        assert state.pages.editing is False
        assert state.pages.page is not None
        assert state.pages.page.mode is afanes.core.editing.DraftMode.NORMAL

    def test_raw_save_stops_on_an_external_change(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_failure(Path("reference/Broken.md"))
            await state.pages.set_page_raw_text("my rescue text")
            broken.write_text("external text", encoding="utf-8", newline="\n")
            return await state.pages.autosave()

        saved = asyncio.run(scenario())

        assert saved is False
        assert state.pages.conflict == "changed"
        assert broken.read_text(encoding="utf-8") == "external text"


class TestPageRecoveryLifecycle:
    def test_conflict_rescue_rename_and_trash(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        note = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        fixed = "---\ntype: note\n---\n\n# Recovered\nBody.\n"

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)
            state.pages.edit_page()
            await state.pages.set_page_body("# Ada\n\nMy edit.\n")
            note.write_text(_note_text("# Ada\n\nExternal.\n"), encoding="utf-8", newline="\n")
            assert await state.pages.autosave() is False
            assert state.pages.conflict == "changed"
            assert await state.dialogs.reload_page() is True
            page = state.pages.page
            assert page is not None
            assert page.body == "# Ada\n\nExternal.\n"

            await state.navigation.open_failure(Path("reference/Broken.md"))
            await state.pages.set_page_raw_text(fixed)
            assert await state.pages.autosave() is True
            page = state.pages.page
            assert page is not None
            assert page.mode is afanes.core.editing.DraftMode.NORMAL
            assert await state.pages.done_editing() is True

            assert await state.dialogs.begin_rename("Recovered page") is not None
            assert await state.dialogs.apply_rename() is True
            renamed = vault / "reference" / "Recovered page.md"
            assert renamed.exists()

            assert await state.dialogs.begin_trash() is not None
            assert await state.dialogs.apply_trash() is True

        asyncio.run(scenario())

        assert not broken.exists()
        assert (vault / "trash" / "Recovered page.md").exists()
        assert state.pages.page is not None
        assert state.pages.page.path == note.resolve()


class TestReviewState:
    def test_start_review_orders_inbox_then_stalled_then_healthy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        capture = _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        _write_typed_note(
            vault / "projects" / "Healthy.md",
            "project",
            status="active",
            body="# Healthy\n\n- [ ] Build\n",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.review.start()

        started = asyncio.run(scenario())

        assert started is True
        assert state.review.review_session is not None
        assert [item.kind for item in state.review.review_session.items] == [
            afanes.core.search.ReviewItemKind.INBOX,
            afanes.core.search.ReviewItemKind.PROJECT,
            afanes.core.search.ReviewItemKind.PROJECT,
        ]
        assert [item.path.stem for item in state.review.review_session.items] == ["Buy milk", "Stalled", "Healthy"]
        assert state.processing.note == capture
        assert state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.REVIEW

    def test_review_start_loads_template_cards(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        card = vault / "templates" / "person.md"
        card.parent.mkdir(parents=True)
        card.write_text(
            "---\ntype: reference\ncategory: person\ntitle: Person\n---\n\n## Contact\n",
            encoding="utf-8",
        )
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.review.start()

        started = asyncio.run(scenario())

        assert started is True
        assert [item.title for item in state.processing.cards] == ["Person"]
        assert state.processing.card_issues == ()

    def test_review_advance_loads_template_cards(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        card = vault / "templates" / "person.md"
        card.parent.mkdir(parents=True)
        card.write_text(
            "---\ntype: reference\ncategory: person\ntitle: Person\n---\n\n## Contact\n",
            encoding="utf-8",
        )
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _write_note(vault / "inbox" / "Call Ada.md", _note_text("# Call Ada"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> tuple[bool, Path | None, Path | None]:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            first = state.processing.note
            skipped = await state.review.skip()
            return skipped, first, state.processing.note

        skipped, first, second = asyncio.run(scenario())

        assert skipped is True
        assert first is not None
        assert second is not None
        assert second != first
        assert [item.title for item in state.processing.cards] == ["Person"]
        assert state.processing.card_issues == ()

    def test_zero_pending_starts_no_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.review.start()

        started = asyncio.run(scenario())

        assert started is False
        assert state.review.review_session is None
        assert state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.REVIEW
        assert state.processing.note is None

    def test_start_review_does_not_infer_an_outcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        capture = _write_note(vault / "inbox" / "Call Ada tomorrow.md", _note_text("# Call Ada tomorrow"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.review.start()

        asyncio.run(scenario())

        assert capture.is_file()
        assert not (vault / "projects" / "Call Ada tomorrow.md").exists()
        assert state.processing.plan is None
        assert state.review.review_session is not None
        assert state.review.review_session.current is not None

    def test_processing_apply_advances_the_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            plan = await state.processing.build_plan(ProcessingOutcome.PROJECT)
            assert plan is not None
            target = await state.processing.apply()
            await state.review.record_processed()
            return target

        target = asyncio.run(scenario())

        assert target == vault / "projects" / "Buy milk.md"
        assert state.review.review_session is not None
        assert state.review.review_session.reviewed_count == 1
        assert state.review.review_session.current is not None
        assert state.review.review_session.current.kind is afanes.core.search.ReviewItemKind.PROJECT
        assert state.processing.note is None
        assert state.browser.pending_count() == TWO_PENDING

    def test_skip_leaves_the_capture_and_advances(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        capture = _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            return await state.review.skip()

        skipped = asyncio.run(scenario())

        assert skipped is True
        assert capture.is_file()
        assert state.review.review_session is not None
        assert state.review.review_session.skipped_count == 1
        assert state.review.review_session.complete is True

    def test_review_next_advances_a_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        before = project.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            return await state.review.next()

        advanced = asyncio.run(scenario())

        assert advanced is True
        assert project.read_bytes() == before
        assert state.review.review_session is not None
        assert state.review.review_session.complete is True
        assert state.review.review_session.reviewed_count == 1

    def test_review_next_does_not_skip_an_inbox_item(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            return await state.review.next()

        advanced = asyncio.run(scenario())

        assert advanced is False
        assert state.review.review_session is not None
        assert state.review.review_session.current is not None
        assert state.review.review_session.current.kind is afanes.core.search.ReviewItemKind.INBOX

    def test_mark_project_done_writes_the_status_and_advances(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            return await state.review.mark_project_done()

        changed = asyncio.run(scenario())

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert changed is True
        assert document.status is Status.DONE
        assert state.review.review_session is not None
        assert state.review.review_session.complete is True
        assert state.browser.pending_count() == 0

    def test_defer_project_sets_later_and_remains_pending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            return await state.review.defer_project()

        changed = asyncio.run(scenario())

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert changed is True
        assert document.status is Status.LATER
        assert state.browser.pending_count() == 1

    def test_add_review_step_refreshes_the_project_card(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            return await state.review.add_step("Build the prototype")

        path = asyncio.run(scenario())

        assert path == project
        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert "- [ ] Build the prototype" in document.body
        assert state.review.review_session is not None
        current = state.review.review_session.current
        assert current is not None
        assert current.project is not None
        assert current.project.next_step is not None
        assert current.project.next_step.text == "Build the prototype"
        assert state.review.review_session.reviewed_count == 0

    def test_add_review_step_rejects_blank_text(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        before = project.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            return await state.review.add_step("   ")

        path = asyncio.run(scenario())

        assert path is None
        assert project.read_bytes() == before
        assert state.review.review_session is not None
        current = state.review.review_session.current
        assert current is not None
        assert current.project is not None
        assert current.project.next_step is None

    def test_finish_review_returns_to_the_browser(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            await state.review.finish()

        asyncio.run(scenario())

        assert state.review.review_session is None
        assert state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.INBOX
        assert state.processing.note is None

    def test_new_work_is_not_appended_to_the_current_queue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.review.start()
            await state.session.capture("Second thought")

        asyncio.run(scenario())

        assert state.review.review_session is not None
        assert len(state.review.review_session.items) == 1
        assert state.browser.pending_count() == TWO_PENDING

    def test_reset_does_not_restore_a_review_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.review.start()

        asyncio.run(scenario())
        state.reset()
        asyncio.run(state.workspace.choose_vault(vault))

        assert state.review.review_session is None
        assert state.browser.pending_count() == 1


class TestReset:
    def test_reset_clears_the_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")
            await state.session.select_note(state.session.notes[0].path)

        asyncio.run(scenario())
        state.reset()

        assert state.session.vault_root is None
        assert state.session.notes == ()
        assert state.session.failures == ()
        assert state.session.selected is None
        assert state.session.preview_body is None
        assert state.status.busy is False
        assert state.status.message is None

    def test_reset_allows_a_second_event_loop(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.start())
        state.reset()
        asyncio.run(state.workspace.choose_vault(vault))

        assert state.session.vault_root == vault.resolve()


class TestOpenVaultPath:
    def test_typed_path_opens_and_saves_settings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("Buy milk")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.open_vault_path(f"  {vault}  "))

        assert state.session.vault_root == vault.resolve()
        assert [note.name for note in state.session.notes] == ["Buy milk"]
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(vault.resolve())

    def test_blank_path_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.open_vault_path("   "))

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_PATH_REQUIRED
        assert not settings.exists()

    def test_missing_path_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.open_vault_path(str(tmp_path / "missing")))

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_MISSING

    def test_file_path_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        target = tmp_path / "note.md"
        target.write_text("not a directory", encoding="utf-8")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.open_vault_path(str(target)))

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_NOT_DIRECTORY

    def test_unreadable_path_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")

        def deny_access(*_args: object, **_kwargs: object) -> bool:
            return False

        monkeypatch.setattr(afanes.core.vault.service.os, "access", deny_access)
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.open_vault_path(str(vault)))

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_UNREADABLE


class TestCreateVault:
    def test_creates_seeds_and_remembers_a_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "notes" / "vault"
        state = afanes.ui.state.app_state

        opened = asyncio.run(state.workspace.create_vault(target))

        assert opened is True
        assert state.session.vault_root == target.resolve()
        assert (target / "inbox").is_dir()
        assert (target / "trash").is_dir()
        assert (target / "reference").is_dir()
        assert (target / "projects").is_dir()
        assert not (target / "reference" / "people").exists()
        assert (target / "reference" / "Getting started.md").is_file()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(target.resolve())

    def test_creates_a_vault_from_a_template(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "vault"
        state = afanes.ui.state.app_state

        opened = asyncio.run(state.workspace.create_vault(target, template="work"))

        assert opened is True
        assert state.session.vault_root == target.resolve()
        assert (target / "reference" / "Getting started.md").is_file()
        assert (target / "projects" / "Quarterly planning.md").is_file()

    def test_reports_a_template_failure_through_the_controller(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        target = tmp_path / "vault"

        def refuse(_cls: object) -> None:
            message = "bundled content is broken"
            raise TemplateContentError(message)

        monkeypatch.setattr(afanes.core.templates.TemplateCatalog, "bundled", classmethod(refuse))

        opened = asyncio.run(state.workspace.create_vault(target, template="personal"))

        assert opened is False
        assert state.session.vault_root is None
        assert state.status.message is not None
        assert "bundled content is broken" in state.status.message
        assert not target.exists()

    def test_template_summaries_report_the_catalog(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        summaries = asyncio.run(state.session.template_summaries())

        assert summaries is not None
        assert [summary.identifier for summary in summaries] == ["personal", "work", "study"]

    def test_template_summaries_degrade_when_the_bundle_is_unreadable(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def refuse(_cls: object) -> None:
            message = "bundled content is broken"
            raise TemplateContentError(message)

        monkeypatch.setattr(afanes.core.templates.TemplateCatalog, "summaries", refuse)

        assert asyncio.run(state.session.template_summaries()) is None

    def test_refuses_a_non_empty_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "vault"
        target.mkdir()
        (target / "photo.jpg").write_text("data", encoding="utf-8")
        state = afanes.ui.state.app_state

        opened = asyncio.run(state.workspace.create_vault(target))

        assert opened is False
        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_NOT_EMPTY
        assert sorted(path.name for path in target.iterdir()) == ["photo.jpg"]

    def test_refuses_a_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "note.md"
        target.write_text("body", encoding="utf-8")
        state = afanes.ui.state.app_state

        opened = asyncio.run(state.workspace.create_vault(target))

        assert opened is False
        assert state.status.message == afanes.ui.strings.VAULT_NOT_DIRECTORY

    def test_opens_when_preferences_cannot_be_saved(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")

        def fail_save(_self: SettingsStore, _settings: Settings) -> None:
            message = "read only"
            raise ConfigurationError(message)

        monkeypatch.setattr(afanes.core.settings.SettingsStore, "save", fail_save)
        target = tmp_path / "vault"
        state = afanes.ui.state.app_state

        opened = asyncio.run(state.workspace.create_vault(target))

        assert opened is True
        assert state.session.vault_root == target.resolve()
        assert state.status.message == afanes.ui.strings.VAULT_CREATED_NOT_REMEMBERED.format(detail="read only")


class TestCloseVault:
    def test_close_returns_to_welcome_and_forgets_the_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        vault = tmp_path / "vault"
        _versioned(vault)
        state = afanes.ui.state.app_state
        assert state.status.begin_session() is True

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.workspace.close_vault()

        closed = asyncio.run(scenario())

        assert closed is True
        assert state.session.vault_root is None
        assert state.status.session_active is True
        assert state.status.message is None
        assert not settings.exists()

    def test_close_saves_a_dirty_page(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Note.md", _typed_note("reference", "# Note\n\nOld.\n"))
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            assert state.pages.edit_page() is True
            await state.pages.set_page_body("# Note\n\nNew.\n")
            return await state.workspace.close_vault()

        closed = asyncio.run(scenario())

        assert closed is True
        assert state.session.vault_root is None
        assert NoteDocument.from_text(path.read_text(encoding="utf-8")).body == "# Note\n\nNew.\n"

    def test_close_is_blocked_by_a_disk_conflict(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Note.md", _typed_note("reference", "# Note\n\nOld.\n"))
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            assert state.pages.edit_page() is True
            await state.pages.set_page_body("# Note\n\nMine.\n")
            path.write_text(_typed_note("reference", "# Note\n\nTheirs.\n"), encoding="utf-8")
            return await state.workspace.close_vault()

        closed = asyncio.run(scenario())

        assert closed is False
        assert state.session.vault_root == vault.resolve()
        assert state.pages.conflict is not None
        assert settings.exists()

    def test_close_reports_when_preferences_cannot_be_removed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        vault = tmp_path / "vault"
        _versioned(vault)
        state = afanes.ui.state.app_state

        def fail_clear(_self: SettingsStore) -> None:
            message = "read only"
            raise ConfigurationError(message)

        monkeypatch.setattr(afanes.core.settings.SettingsStore, "clear", fail_clear)

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            return await state.workspace.close_vault()

        closed = asyncio.run(scenario())

        assert closed is True
        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_CLOSE_NOT_FORGOTTEN.format(detail="read only")
        assert settings.exists()

    @pytest.mark.parametrize(
        ("attribute", "message"),
        [
            ("repair_preview", afanes.ui.strings.PAGE_REPAIR_PENDING),
            ("pending_labels", afanes.ui.strings.PAGE_TYPE_CHANGE_LEAVE),
            ("rename_preview", afanes.ui.strings.PAGE_PENDING_DIALOG),
            ("trash_preview", afanes.ui.strings.PAGE_PENDING_DIALOG),
        ],
    )
    def test_pending_page_action_blocks_the_close(
        self,
        attribute: str,
        message: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Note.md", _typed_note("reference", "# Note\n"))
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            target = {
                "repair_preview": state.pages,
                "pending_labels": state.dialogs,
                "rename_preview": state.dialogs,
                "trash_preview": state.dialogs,
            }[attribute]
            monkeypatch.setattr(target, attribute, object())
            if attribute != "repair_preview":
                state.pages.blocking_message = message
            return await state.workspace.close_vault()

        closed = asyncio.run(scenario())

        assert closed is False
        assert state.session.vault_root == vault.resolve()
        assert state.status.message == message
        assert settings.exists()

    def test_close_succeeds_when_the_settings_file_is_already_gone(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        vault = tmp_path / "vault"
        _versioned(vault)
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            settings.unlink()
            return await state.workspace.close_vault()

        closed = asyncio.run(scenario())

        assert closed is True
        assert state.session.vault_root is None

    def test_close_succeeds_when_the_vault_directory_is_gone(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        vault = tmp_path / "vault"
        _versioned(vault)
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            (vault / afanes.core.vault.schema.SCHEMA_FILENAME).unlink()
            vault.rmdir()
            return await state.workspace.close_vault()

        closed = asyncio.run(scenario())

        assert closed is True
        assert state.session.vault_root is None

    def test_close_without_a_vault_does_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        assert asyncio.run(state.workspace.close_vault()) is False
        assert state.session.vault_root is None


class TestOpenVaultForRun:
    def test_supplied_vault_leaves_settings_unchanged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        remembered = tmp_path / "remembered"
        remembered.mkdir()
        supplied = tmp_path / "supplied"
        _versioned(supplied)
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(supplied)).capture("Buy milk")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=remembered))
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.open_vault_for_run(supplied))

        assert state.session.vault_root == supplied.resolve()
        assert [note.name for note in state.session.notes] == ["Buy milk"]
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(remembered.resolve())

    def test_supplied_vault_failure_reports_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.open_vault_for_run(tmp_path / "missing"))

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_MISSING


class TestSessionGuard:
    def test_second_begin_is_refused(self) -> None:
        state = afanes.ui.state.app_state

        assert state.status.begin_session() is True
        assert state.status.begin_session() is False

    def test_release_allows_a_later_session(self) -> None:
        state = afanes.ui.state.app_state

        state.status.begin_session()
        state.status.release_session()

        assert state.status.begin_session() is True

    def test_reset_clears_the_session(self) -> None:
        state = afanes.ui.state.app_state
        state.status.begin_session()

        state.reset()

        assert state.status.session_active is False


class TestReviewStepCommands:
    def _due_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> tuple[Path, afanes.ui.state.controller.AppState]:
        today = datetime.datetime.now(tz=datetime.UTC).astimezone().date()
        vault = tmp_path / "vault"
        project = _write_typed_note(
            vault / "projects" / "Home.md",
            "project",
            status="active",
            body=f"# Home\n\n- [ ] Call <!-- {{plan: {today.isoformat()}}} -->\n",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.review.start()

        asyncio.run(scenario())
        return project, state

    def test_do_it_now_checks_the_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project, state = self._due_project(tmp_path, monkeypatch)

        assert asyncio.run(state.review.do_now()) is True

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        step = StepDocument(document.body).steps[0]
        assert step.checked is True
        assert step.actual == datetime.datetime.now(tz=datetime.UTC).astimezone().date()

    def test_postpone_replaces_the_plan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project, state = self._due_project(tmp_path, monkeypatch)
        new_plan = datetime.date(2026, 12, 1)

        assert asyncio.run(state.review.postpone(new_plan)) is True

        step = StepDocument(NoteDocument.from_text(project.read_text(encoding="utf-8")).body).steps[0]
        assert step.plan == new_plan
        assert step.actual is None

    def test_delegate_adds_an_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project, state = self._due_project(tmp_path, monkeypatch)

        assert asyncio.run(state.review.delegate("Ada")) is True

        step = StepDocument(NoteDocument.from_text(project.read_text(encoding="utf-8")).body).steps[0]
        assert step.owners == ("Ada",)

    def test_reassign_replaces_the_owners(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(
            vault / "projects" / "Home.md",
            "project",
            status="active",
            body="# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.review.start()

        asyncio.run(scenario())

        assert asyncio.run(state.review.reassign("Grace")) is True

        step = StepDocument(NoteDocument.from_text(project.read_text(encoding="utf-8")).body).steps[0]
        assert step.owners == ("Grace",)


class TestStepAwareProjectPage:
    def _project(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        body: str = "# Home\n\nIntro.\n\n- [ ] Call <!-- {owners: [Ada], plan: 2026-11-20, actual: 2026-11-14, tags: [phone], priority: high} -->\n\nDone.\n",
        status: str | None = "active",
        due_date: str | None = None,
    ) -> tuple[Path, afanes.ui.state.controller.AppState]:
        vault = tmp_path / "vault"
        path = _write_typed_note(
            vault / "projects" / "Home.md",
            "project",
            status=status,
            due_date=due_date,
            body=body,
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        return path, state

    def _step(self, path: Path) -> ProjectStep:
        return StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]

    def _index(self, path: Path) -> int:
        return self._step(path).line_index

    def test_project_page_exposes_prose_and_step_blocks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _path, state = self._project(tmp_path, monkeypatch)

        blocks = state.pages.page_body_blocks

        assert any(isinstance(block, StepListBlock) for block in blocks)
        first = blocks[0]
        assert isinstance(first, ProseBlock)
        assert first.source.startswith("# Home")

    def test_non_project_page_has_no_body_blocks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())

        assert state.pages.page_body_blocks == ()

    def test_plan_is_set_and_cleared(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        plan = datetime.date(2026, 12, 1)
        index = self._index(path)

        assert (
            asyncio.run(
                state.pages.edit_page_step_metadata(StepEdit(line_index=index, kind=StepEditKind.PLAN, plan=plan))
            )
            is True
        )
        assert self._step(path).plan == plan

        assert (
            asyncio.run(
                state.pages.edit_page_step_metadata(StepEdit(line_index=index, kind=StepEditKind.PLAN, plan=None))
            )
            is True
        )
        assert self._step(path).plan is None

    def test_owner_list_is_replaced_and_cleared(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        index = self._index(path)

        assert (
            asyncio.run(
                state.pages.edit_page_step_metadata(
                    StepEdit(line_index=index, kind=StepEditKind.OWNERS, owners=("Grace", "Alan"))
                )
            )
            is True
        )
        assert self._step(path).owners == ("Grace", "Alan")

        assert (
            asyncio.run(
                state.pages.edit_page_step_metadata(StepEdit(line_index=index, kind=StepEditKind.OWNERS, owners=()))
            )
            is True
        )
        assert self._step(path).owners == ()

    def test_unknown_metadata_and_completion_survive_an_edit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        index = self._index(path)

        assert (
            asyncio.run(
                state.pages.edit_page_step_metadata(
                    StepEdit(line_index=index, kind=StepEditKind.OWNERS, owners=("Grace",))
                )
            )
            is True
        )

        step = self._step(path)
        assert step.metadata.raw["priority"] == "high"
        assert step.actual == datetime.date(2026, 11, 14)
        assert step.tags == ("phone",)

    def test_other_step_lines_are_byte_identical(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\n- [ ] One\n- [ ] Two <!-- {plan: 2026-11-20} -->\n"
        path, state = self._project(tmp_path, monkeypatch, body=body)
        before_document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        before = before_document.body.splitlines()
        index = StepDocument(before_document.body).steps[1].line_index

        assert (
            asyncio.run(
                state.pages.edit_page_step_metadata(
                    StepEdit(line_index=index, kind=StepEditKind.OWNERS, owners=("Ada",))
                )
            )
            is True
        )

        after = NoteDocument.from_text(path.read_text(encoding="utf-8")).body.splitlines()
        assert after[:index] == before[:index]
        assert after[index + 1 :] == before[index + 1 :]
        assert "owners: [Ada]" in after[index]

    def test_force_autosave_writes_a_read_mode_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        page = state.pages.page
        assert isinstance(page, NormalDraft)
        state.pages.page = page.with_body("# Home\n\nChanged.\n")

        assert asyncio.run(state.pages.autosave(force=True)) is True

        assert "Changed." in path.read_text(encoding="utf-8")

    def test_force_autosave_skips_a_clean_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _path, state = self._project(tmp_path, monkeypatch)

        assert asyncio.run(state.pages.autosave(force=True)) is False

    def test_due_date_is_set_and_cleared_from_read_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        body_before = NoteDocument.from_text(path.read_text(encoding="utf-8")).body

        assert asyncio.run(state.dialogs.save_page_due_date("2026-12-01")) is True
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.due_date == datetime.date(2026, 12, 1)
        assert document.body == body_before

        assert asyncio.run(state.dialogs.save_page_due_date("")) is True
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.due_date is None
        assert document.body == body_before

    def test_invalid_due_date_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        before = path.read_bytes()

        assert asyncio.run(state.dialogs.save_page_due_date("January")) is False

        assert path.read_bytes() == before
        assert state.status.message is not None

    def test_due_date_conflict_keeps_the_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        state.pages.conflict = "changed"
        before = path.read_bytes()

        assert asyncio.run(state.dialogs.save_page_due_date("2026-12-01")) is False

        assert path.read_bytes() == before
        state.pages.conflict = None


class TestLogTypeChange:
    def test_reference_becomes_a_log_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "reference" / "A quiet Tuesday.md",
            "---\ntype: reference\ndate: 2025-10-12\n---\n\n# A quiet Tuesday\n",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            return await state.dialogs.set_page_type(NoteType.LOG)

        assert asyncio.run(scenario()) is True
        target = vault / "log" / "2025" / "10" / "2025-10-12.md"
        assert target.is_file()
        assert not path.exists()
        assert state.pages.page is not None
        assert state.pages.page.path == target

    def test_log_becomes_a_reference(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "log" / "2025" / "10" / "2025-10-12.md",
            "---\ntype: log\ndate: 2025-10-12\n---\n\n# A quiet Tuesday\n",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            return await state.dialogs.set_page_type(NoteType.REFERENCE)

        assert asyncio.run(scenario()) is True
        target = vault / "reference" / "A quiet Tuesday.md"
        assert target.is_file()
        assert not path.exists()
        assert state.pages.page is not None
        assert state.pages.page.path == target

    def test_an_undated_note_is_refused(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "reference" / "Ada.md", _typed_note("reference", "# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            return await state.dialogs.set_page_type(NoteType.LOG)

        assert asyncio.run(scenario()) is False
        assert state.status.message is not None
        assert path.is_file()


class TestRewriteReports:
    def test_rename_reports_updated_and_skipped_notes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        skipped = _write_note(vault / "notes" / "Skipped.md", _note_text("# Skipped\n"))
        failed = _write_note(vault / "notes" / "Failed.md", _note_text("# Failed\n"))
        original = afanes.core.vault.naming.VaultNaming.apply_rename

        def apply_with_partial(
            vault_naming: afanes.core.vault.naming.VaultNaming,
            preview: afanes.core.vault.naming_reports.RenamePreview,
            *,
            confirm: bool = False,
        ) -> afanes.core.vault.naming_reports.RenameReport:
            report = original(vault_naming, preview, confirm=confirm)
            return dataclasses.replace(
                report,
                skipped=(skipped.resolve(),),
                failed=(
                    afanes.core.vault.naming_reports.RewriteFailure(
                        path=failed.resolve(),
                        message="permission denied",
                    ),
                ),
            )

        monkeypatch.setattr(
            afanes.core.vault.naming.VaultNaming,
            "apply_rename",
            apply_with_partial,
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)
            assert await state.dialogs.begin_rename("Ada King") is not None
            return await state.dialogs.apply_rename()

        assert asyncio.run(scenario()) is True
        message = state.status.message
        assert message is not None
        assert "Updated: " in message
        assert "reference/people/Ada King.md" in message
        assert "notes/Ref.md" in message
        assert "notes/Skipped.md (changed on disk after planning)" in message
        assert "notes/Failed.md (permission denied)" in message

    def test_type_change_reports_updated_and_failed_notes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "reference" / "A quiet Tuesday.md",
            "---\ntype: reference\ndate: 2025-10-12\n---\n\n# A quiet Tuesday\n",
        )
        referrer = _write_note(
            vault / "notes" / "Ref.md",
            _note_text("[Tuesday](<note:A quiet Tuesday>)\n"),
        )
        skipped = _write_note(vault / "notes" / "Skipped.md", _note_text("# Skipped\n"))
        failed = _write_note(vault / "notes" / "Failed.md", _note_text("# Failed\n"))
        original = afanes.core.vault.naming.VaultNaming.apply_rename

        def apply_with_partial(
            vault_naming: afanes.core.vault.naming.VaultNaming,
            preview: afanes.core.vault.naming_reports.RenamePreview,
            *,
            confirm: bool = False,
        ) -> afanes.core.vault.naming_reports.RenameReport:
            report = original(vault_naming, preview, confirm=confirm)
            return dataclasses.replace(
                report,
                skipped=(skipped.resolve(),),
                failed=(
                    afanes.core.vault.naming_reports.RewriteFailure(
                        path=failed.resolve(),
                        message="permission denied",
                    ),
                ),
            )

        monkeypatch.setattr(
            afanes.core.vault.naming.VaultNaming,
            "apply_rename",
            apply_with_partial,
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            return await state.dialogs.set_page_type(NoteType.LOG)

        assert asyncio.run(scenario()) is True
        message = state.status.message
        assert message is not None
        assert "Updated: " in message
        assert "notes/Ref.md" in message
        assert "notes/Skipped.md (changed on disk after planning)" in message
        assert "notes/Failed.md (permission denied)" in message
        assert (vault / "log" / "2025" / "10" / "2025-10-12.md").is_file()
        assert "log:2025-10-12" in referrer.read_text(encoding="utf-8")

    def test_date_change_reports_updated_and_skipped_notes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        path = _write_note(
            vault / "log" / "2025" / "10" / "2025-10-12.md",
            "---\ntype: log\ndate: 2025-10-12\n---\n\n# A quiet Tuesday\n",
        )
        referrer = _write_note(
            vault / "notes" / "Ref.md",
            _note_text("[Tuesday](<log:2025-10-12>)\n"),
        )
        skipped = _write_note(vault / "notes" / "Skipped.md", _note_text("# Skipped\n"))
        failed = _write_note(vault / "notes" / "Failed.md", _note_text("# Failed\n"))
        original = afanes.core.vault.naming.VaultNaming.apply_rename

        def apply_with_partial(
            vault_naming: afanes.core.vault.naming.VaultNaming,
            preview: afanes.core.vault.naming_reports.RenamePreview,
            *,
            confirm: bool = False,
        ) -> afanes.core.vault.naming_reports.RenameReport:
            report = original(vault_naming, preview, confirm=confirm)
            return dataclasses.replace(
                report,
                skipped=(skipped.resolve(),),
                failed=(
                    afanes.core.vault.naming_reports.RewriteFailure(
                        path=failed.resolve(),
                        message="permission denied",
                    ),
                ),
            )

        monkeypatch.setattr(
            afanes.core.vault.naming.VaultNaming,
            "apply_rename",
            apply_with_partial,
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            return await state.dialogs.save_page_date("2025-10-13")

        assert asyncio.run(scenario()) is True
        message = state.status.message
        assert message is not None
        assert "Updated: " in message
        assert "notes/Ref.md" in message
        assert "notes/Skipped.md (changed on disk after planning)" in message
        assert "notes/Failed.md (permission denied)" in message
        assert (vault / "log" / "2025" / "10" / "2025-10-13.md").is_file()
        assert "log:2025-10-13" in referrer.read_text(encoding="utf-8")

    def test_repair_reports_updated_and_failed_notes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _versioned(vault)
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        skipped = _write_note(vault / "notes" / "Skipped.md", _note_text("# Skipped\n"))
        failed = _write_note(vault / "notes" / "Failed.md", _note_text("# Failed\n"))
        original = afanes.core.vault.naming.VaultNaming.apply_reference_repair

        def apply_with_partial(
            vault_naming: afanes.core.vault.naming.VaultNaming,
            preview: afanes.core.vault.naming_reports.ReferenceRepairPreview,
            *,
            confirm: bool = False,
        ) -> afanes.core.vault.naming_reports.RewriteReport:
            report = original(vault_naming, preview, confirm=confirm)
            return dataclasses.replace(
                report,
                skipped=(skipped.resolve(),),
                failed=(
                    afanes.core.vault.naming_reports.RewriteFailure(
                        path=failed.resolve(),
                        message="permission denied",
                    ),
                ),
            )

        monkeypatch.setattr(
            afanes.core.vault.naming.VaultNaming,
            "apply_reference_repair",
            apply_with_partial,
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Q1: Planning?")
            await state.pages.set_page_body("# Q1: Planning?\n\nDraft.\n")
            await state.pages.autosave()
            return await state.dialogs.apply_repair()

        assert asyncio.run(scenario()) is True
        message = state.status.message
        assert message is not None
        assert "Updated: " in message
        assert "notes/Source.md" in message
        assert "notes/Skipped.md (changed on disk after planning)" in message
        assert "notes/Failed.md (permission denied)" in message
        assert source.is_file()
