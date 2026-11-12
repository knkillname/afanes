"""Tests for the single application state controller."""

import asyncio
import datetime
import json
import os
import threading
from pathlib import Path

import pytest

import afanes.core.settings
import afanes.core.vault
import afanes.ui.state
import afanes.ui.strings
from afanes.core.errors import ConfigurationError, VaultError
from afanes.core.frontmatter import NoteDocument
from afanes.core.processing import ProcessingOutcome
from afanes.core.settings import Settings, SettingsStore
from afanes.core.steps import StepDocument
from afanes.models.link import ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType, Status

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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


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
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> tuple[bool, Path]:
            await state.choose_vault(vault)
            capture = await state.capture("Buy milk")
            assert capture is not None
            opened = await state.begin_processing(capture)
            return opened, capture

        opened, capture = asyncio.run(scenario())

        assert opened is True
        assert state.processing_note == capture
        assert state.processing_body == "# Buy milk"
        assert state.selected == capture

    def test_begin_processing_rejects_a_missing_capture(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            return await state.begin_processing(vault / "inbox" / "Missing.md")

        opened = asyncio.run(scenario())

        assert opened is False
        assert state.message == afanes.ui.strings.PROCESSING_MISSING

    def test_begin_processing_performs_no_writes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> dict[str, bytes]:
            await state.choose_vault(vault)
            capture = await state.capture("Buy milk")
            assert capture is not None
            before = _tree_state(vault)
            await state.begin_processing(capture)
            return before

        before = asyncio.run(scenario())

        assert _tree_state(vault) == before

    def test_plan_processing_builds_a_plan_without_writing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            capture = await state.capture("Buy milk")
            assert capture is not None
            await state.begin_processing(capture)
            plan = await state.plan_processing(ProcessingOutcome.PROJECT)
            assert plan is not None
            assert state.processing_plan is plan

        asyncio.run(scenario())

        assert not (vault / "projects" / "Buy milk.md").exists()

    def test_plan_processing_failure_sets_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            capture = await state.capture("Buy milk")
            assert capture is not None
            await state.begin_processing(capture)
            plan = await state.plan_processing(
                ProcessingOutcome.REFERENCE,
                due_date=datetime.date(2026, 11, 20),
            )
            assert plan is None

        asyncio.run(scenario())

        assert state.processing_plan is None
        assert state.message is not None
        assert state.message.startswith("Could not prepare")

    def test_apply_processing_moves_the_capture(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path:
            await state.choose_vault(vault)
            capture = await state.capture("Buy milk")
            assert capture is not None
            await state.begin_processing(capture)
            await state.plan_processing(ProcessingOutcome.PROJECT)
            target = await state.apply_processing()
            assert target is not None
            return target

        target = asyncio.run(scenario())

        assert target == vault / "projects" / "Buy milk.md"
        assert target.exists()
        assert state.processing_result == target
        assert state.processing_note is None
        assert state.processing_plan is None
        assert state.notes == ()

    def test_apply_processing_failure_keeps_the_plan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        capture_path: Path | None = None

        async def scenario() -> None:
            nonlocal capture_path
            await state.choose_vault(vault)
            capture_path = await state.capture("Buy milk")
            assert capture_path is not None
            await state.begin_processing(capture_path)
            await state.plan_processing(ProcessingOutcome.PROJECT)

        asyncio.run(scenario())

        def fail_apply(_vault: object, _plan: object, **_kwargs: object) -> Path:
            message = "write failed"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.Vault, "apply_processing", fail_apply)
        result = asyncio.run(state.apply_processing())

        assert result is None
        assert state.processing_plan is not None
        assert state.message is not None
        assert capture_path is not None
        assert capture_path.exists()

    def test_cancel_processing_clears_the_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            capture = await state.capture("Buy milk")
            assert capture is not None
            await state.begin_processing(capture)
            await state.plan_processing(ProcessingOutcome.PROJECT)
            state.cancel_processing()

        asyncio.run(scenario())

        assert state.processing_note is None
        assert state.processing_body is None
        assert state.processing_plan is None
        assert state.processing_result is None
        assert state.message is None

    def test_finish_processing_clears_the_success_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            capture = await state.capture("Buy milk")
            assert capture is not None
            await state.begin_processing(capture)
            await state.plan_processing(ProcessingOutcome.PROJECT)
            await state.apply_processing()
            state.finish_processing()

        asyncio.run(scenario())

        assert state.processing_result is None
        assert state.processing_note is None


class TestAssignmentCandidates:
    def test_returns_candidates_from_the_last_scan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects/Ada.md",
            "---\ntype: project\nstatus: active\n---\n# Ada, Countess of Lovelace\n",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.choose_vault(vault))
        candidates = state.assignment_candidates(ReferenceScheme.PROJECT, "countess")

        assert [note.name for note in candidates] == ["Ada"]
        assert candidates[0].title == "Ada, Countess of Lovelace"

    def test_returns_nothing_without_a_vault(self) -> None:
        state = afanes.ui.state.app_state

        assert state.assignment_candidates(ReferenceScheme.PROJECT, "ada") == ()

    def test_candidates_follow_a_refresh(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> tuple[afanes.core.vault.VaultNote, ...]:
            await state.choose_vault(vault)
            _write_note(
                vault / "projects/Launch.md",
                "---\ntype: project\nstatus: active\n---\n# Launch the product\n",
            )
            await state.refresh()
            return state.assignment_candidates(ReferenceScheme.PROJECT, "product")

        candidates = asyncio.run(scenario())

        assert [note.name for note in candidates] == ["Launch"]


class TestStartup:
    def test_without_settings_shows_welcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.start())

        assert state.vault_root is None
        assert state.notes == ()
        assert state.message is None

    def test_malformed_settings_show_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        settings.write_text("{not json", encoding="utf-8")
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.start())

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.SETTINGS_UNREADABLE
        assert settings.read_text(encoding="utf-8") == "{not json"

    def test_missing_vault_shows_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        missing = tmp_path / "missing"
        settings = tmp_path / "settings.json"
        _write_settings(settings, missing)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.start())

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_MISSING
        assert not missing.exists()

    def test_file_vault_shows_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.write_text("not a directory", encoding="utf-8")
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.start())

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_NOT_DIRECTORY

    def test_valid_settings_opens_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = afanes.core.vault.Vault(vault).capture("First")
        second = afanes.core.vault.Vault(vault).capture("Second")
        os.utime(first, ns=(OLD_NS, OLD_NS))
        os.utime(second, ns=(NEW_NS, NEW_NS))
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.start())

        assert state.vault_root == vault.resolve()
        assert [note.name for note in state.notes] == ["Second", "First"]
        assert state.message is None

    def test_starting_does_not_create_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state
        before = _tree_state(vault)

        asyncio.run(state.start())

        assert not (vault / "inbox").exists()
        assert _tree_state(vault) == before

    def test_unreadable_notes_are_reported(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        afanes.core.vault.Vault(vault).capture("Good")
        bad = _write_note(vault / "inbox" / "Bad.md", "---\ntype: [unclosed\n---\n")
        settings = tmp_path / "settings.json"
        _write_settings(settings, vault)
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.start())

        assert [note.name for note in state.notes] == ["Good"]
        assert [failure.path.as_posix() for failure in state.failures] == ["inbox/Bad.md"]
        assert bad.read_text(encoding="utf-8") == "---\ntype: [unclosed\n---\n"


class TestChooseVault:
    def test_choose_vault_saves_settings_and_lists_notes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        afanes.core.vault.Vault(vault).capture("Buy milk")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.choose_vault(vault))

        assert state.vault_root == vault.resolve()
        assert [note.name for note in state.notes] == ["Buy milk"]
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(vault.resolve())

    def test_choose_vault_rejects_a_missing_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        missing = tmp_path / "missing"
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.choose_vault(missing))

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_MISSING
        assert not settings.exists()

    def test_choose_vault_rejects_a_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.write_text("not a directory", encoding="utf-8")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.choose_vault(vault))

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_NOT_DIRECTORY

    def test_choose_vault_reports_a_save_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def fail_save(_store: SettingsStore, _settings: Settings) -> None:
            message = "simulated"
            raise ConfigurationError(message)

        monkeypatch.setattr(afanes.ui.state.SettingsStore, "save", fail_save)

        asyncio.run(state.choose_vault(vault))

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_SELECTION_FAILED.format(detail="simulated")

    def test_choose_vault_does_not_write_to_the_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        before = _tree_state(vault)

        asyncio.run(state.choose_vault(vault))

        assert _tree_state(vault) == before


class TestChangeVault:
    def test_change_vault_switches_and_preserves_the_previous(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = tmp_path / "first"
        second = tmp_path / "second"
        first.mkdir()
        second.mkdir()
        afanes.core.vault.Vault(first).capture("First note")
        afanes.core.vault.Vault(second).capture("Second note")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state
        first_before = _tree_state(first)

        async def scenario() -> None:
            await state.choose_vault(first)
            await state.change_vault(second)

        asyncio.run(scenario())

        assert state.vault_root == second.resolve()
        assert [note.name for note in state.notes] == ["Second note"]
        assert _tree_state(first) == first_before
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(second.resolve())

    def test_change_vault_failure_keeps_the_current_vault(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = tmp_path / "first"
        first.mkdir()
        afanes.core.vault.Vault(first).capture("First note")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(first)
            await state.change_vault(tmp_path / "missing")

        asyncio.run(scenario())

        assert state.vault_root == first.resolve()
        assert state.message == afanes.ui.strings.VAULT_MISSING
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(first.resolve())


class TestCapture:
    def test_capture_writes_and_promotes_the_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.choose_vault(vault)
            return await state.capture("Buy milk")

        path = asyncio.run(scenario())

        assert path is not None
        assert path.name == "Buy milk.md"
        assert state.notes[0].path == path
        assert path.read_text(encoding="utf-8").startswith("---\ntype: note\n---\n")
        assert state.message is None

    def test_empty_capture_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.choose_vault(vault)
            return await state.capture(" \n\t")

        path = asyncio.run(scenario())

        assert path is None
        assert state.message == afanes.ui.strings.CAPTURE_EMPTY
        assert state.notes == ()

    def test_successful_capture_clears_the_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("")
            await state.capture("Buy milk")

        asyncio.run(scenario())

        assert state.message is None
        assert len(state.notes) == 1

    def test_capture_failure_reports_and_keeps_the_list(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def fail_capture(_vault: afanes.core.vault.Vault, _text: str) -> Path:
            message = "disk full"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.Vault, "capture", fail_capture)

        async def scenario() -> Path | None:
            await state.choose_vault(vault)
            return await state.capture("Buy milk")

        path = asyncio.run(scenario())

        assert path is None
        assert state.message == afanes.ui.strings.CAPTURE_FAILED.format(detail="disk full")
        assert state.notes == ()

    def test_repeated_captures_get_distinct_names(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Buy milk")
            await state.capture("Buy milk")

        asyncio.run(scenario())

        assert [note.name for note in state.notes] == ["Buy milk 2", "Buy milk"]

    def test_capture_works_with_an_unreadable_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Bad.md", "---\ntype: [unclosed\n---\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.choose_vault(vault)
            return await state.capture("Buy milk")

        path = asyncio.run(scenario())

        assert path is not None
        assert [note.name for note in state.notes] == ["Buy milk"]
        assert len(state.failures) == 1

    def test_capture_does_not_infer_structure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.choose_vault(vault)
            return await state.capture("Ask Ada about 2026-11-20")

        path = asyncio.run(scenario())

        assert path is not None
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw == {"type": "note"}
        assert document.due_date is None
        assert document.category is None

    def test_capture_does_not_modify_other_notes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        existing = _write_note(vault / "work" / "Existing.md", _note_text("Do not touch"))
        before = existing.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Buy milk")

        asyncio.run(scenario())

        assert existing.read_bytes() == before


class TestPreview:
    def test_select_note_loads_body_without_frontmatter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("First line\nsecond line")
            await state.select_note(state.notes[0].path)

        asyncio.run(scenario())

        assert state.selected == state.notes[0].path
        assert state.preview_body == "# First line\nsecond line"
        assert "type: note" not in (state.preview_body or "")

    def test_preview_performs_no_write(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        before: list[tuple[bytes, int]] = []

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Buy milk")
            path = state.notes[0].path
            before.append((path.read_bytes(), path.stat().st_mtime_ns))
            await state.select_note(path)

        asyncio.run(scenario())

        path = state.notes[0].path
        assert (path.read_bytes(), path.stat().st_mtime_ns) == before[0]

    def test_preview_failure_clears_the_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Buy milk")
            state.notes[0].path.unlink()
            await state.select_note(state.notes[0].path)

        asyncio.run(scenario())

        assert state.selected is None
        assert state.preview_body is None
        assert state.message is not None
        assert state.message.startswith("Could not read this note:")


class TestRefresh:
    def test_refresh_adds_an_external_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            afanes.core.vault.Vault(vault).capture("External note")
            await state.refresh()

        asyncio.run(scenario())

        assert [note.name for note in state.notes] == ["External note"]

    def test_refresh_removes_a_deleted_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Buy milk")
            state.notes[0].path.unlink()
            await state.refresh()

        asyncio.run(scenario())

        assert state.notes == ()

    def test_refresh_updates_the_selected_preview(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Old body")
            path = state.notes[0].path
            await state.select_note(path)
            path.write_text(_note_text("New body\n"), encoding="utf-8")
            await state.refresh()

        asyncio.run(scenario())

        assert state.preview_body == "New body\n"

    def test_refresh_clears_a_disappeared_selection(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Buy milk")
            path = state.notes[0].path
            await state.select_note(path)
            path.unlink()
            await state.refresh()

        asyncio.run(scenario())

        assert state.selected is None
        assert state.preview_body is None

    def test_refresh_without_a_vault_is_a_no_op(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.refresh())

        assert state.notes == ()
        assert state.message is None


class TestConcurrency:
    def test_commands_are_serialized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        entered = threading.Event()
        release = threading.Event()
        original = afanes.core.vault.Vault.capture

        def blocking_capture(vault: afanes.core.vault.Vault, text: str) -> Path:
            entered.set()
            release.wait(timeout=5)
            return original(vault, text)

        monkeypatch.setattr(afanes.core.vault.Vault, "capture", blocking_capture)

        async def scenario() -> None:
            await state.choose_vault(vault)
            first = asyncio.create_task(state.capture("Buy milk"))
            assert await asyncio.to_thread(entered.wait, 2) is True
            assert state.busy is True
            second = asyncio.create_task(state.refresh())
            await asyncio.sleep(0)
            assert second.done() is False
            release.set()
            await asyncio.gather(first, second)
            assert state.busy is False

        asyncio.run(scenario())

        assert [note.name for note in state.notes] == ["Buy milk"]


class TestPageSession:
    def test_open_page_loads_a_read_only_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        before = path.read_bytes()

        async def scenario() -> bool:
            await state.choose_vault(vault)
            return await state.open_page(path)

        opened = asyncio.run(scenario())

        assert opened is True
        assert state.page is not None
        assert state.page.path == path.resolve()
        assert state.editing is False
        assert state.page_title == "Ada"
        assert path.read_bytes() == before

    def test_opening_a_second_page_pushes_history(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(first)
            await state.open_page(second)
            assert state.history == (first.resolve(),)
            assert state.page is not None
            assert state.page.path == second.resolve()
            await state.back()
            assert state.page is not None
            assert state.page.path == first.resolve()
            assert state.history == ()
            await state.back()
            assert state.page is None

        asyncio.run(scenario())

    def test_back_discards_an_untouched_new_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(first)
            await state.follow_link("note:Missing")
            assert state.page is not None
            assert state.page.is_new
            assert state.editing is True
            await state.back()
            assert state.page is not None
            assert state.page.path == first.resolve()
            assert not (vault / "reference" / "Missing.md").exists()

        asyncio.run(scenario())

    def test_history_is_bounded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        paths = [
            _write_note(vault / "notes" / f"Note {index:02d}.md", _note_text(f"# Note {index:02d}\n"))
            for index in range(55)
        ]
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            for path in paths:
                await state.open_page(path)

        asyncio.run(scenario())

        assert len(state.history) == afanes.ui.state.PAGE_HISTORY_LIMIT
        assert state.history[0] == paths[4].resolve()
        assert state.history[-1] == paths[53].resolve()

    def test_back_skips_a_missing_history_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(first)
            await state.open_page(second)
            first.unlink()
            await state.back()

        asyncio.run(scenario())

        assert state.page is None
        assert state.message is not None

    def test_done_editing_commits_the_body(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(path)
            assert state.edit_page() is True
            await state.set_page_body("# Ada\n\nNew body.\n")
            committed = await state.done_editing()
            assert committed is True

        asyncio.run(scenario())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.body == "# Ada\n\nNew body.\n"
        assert state.editing is False
        assert state.page is not None
        assert state.page.is_dirty is False

    def test_reset_clears_the_page_and_history(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(first)

        asyncio.run(scenario())
        state.reset()

        assert state.page is None
        assert state.history == ()
        assert state.editing is False


class TestPageLabels:
    def test_type_change_with_referrers_waits_for_confirmation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        referrer = _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(person)
            applied = await state.set_page_type(NoteType.PROJECT)
            assert applied is False
            page = state.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.scheme is ReferenceScheme.NOTE
            assert state.pending_labels is not None
            assert state.pending_labels.scheme is ReferenceScheme.PROJECT
            assert len(state.type_change_sites) == 1
            assert state.type_change_sites[0].path == referrer.resolve()
            assert await state.apply_type_change() is True
            page = state.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.note_type is NoteType.PROJECT
            assert page.labels.category is None
            assert state.pending_labels is None

        asyncio.run(scenario())

    def test_cancelling_a_type_change_keeps_the_original_labels(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(person)
            await state.set_page_type(NoteType.PROJECT)
            await state.cancel_type_change()
            page = state.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.scheme is ReferenceScheme.NOTE
            assert state.pending_labels is None
            assert state.type_change_sites == ()

        asyncio.run(scenario())

    def test_same_scheme_type_change_applies_immediately(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        reference = _write_note(vault / "reference" / "Call.md", _typed_note("reference", "# Call\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(reference)
            assert await state.set_page_type(NoteType.NOTE) is True
            page = state.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.note_type is NoteType.NOTE
            assert state.pending_labels is None

        asyncio.run(scenario())

    def test_new_draft_scheme_change_applies_without_a_scan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:New person")
            assert await state.set_page_category(CategoryLabel("person")) is True
            page = state.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.scheme is ReferenceScheme.NOTE
            assert state.pending_labels is None

        asyncio.run(scenario())

    def test_invalid_status_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(path)
            await state.set_page_status(Status.ACTIVE)
            page = state.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.status is None
            assert state.message is not None

        asyncio.run(scenario())

    def test_due_date_updates_the_labels(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        project = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(project)
            await state.set_page_due_date("January")
            page = state.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.due_date_error is not None
            await state.set_page_due_date("2027-01-02")
            page = state.page
            assert page is not None
            assert page.labels is not None
            assert page.labels.due_date == datetime.date(2027, 1, 2)

        asyncio.run(scenario())

    def test_assignment_suggestions_come_from_the_scan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "projects" / "Ada.md",
            _typed_note("project", "# Ada, Countess of Lovelace\n"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            candidates = state.assignment_candidates(ReferenceScheme.PROJECT, "countess")
            assert [candidate.path for candidate in candidates] == [person.resolve()]

        asyncio.run(scenario())


class TestPageSaving:
    def test_autosave_writes_a_dirty_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_page(path)
            assert state.edit_page() is True
            await state.set_page_body("# Ada\n\nNew body.\n")
            return await state.autosave()

        saved = asyncio.run(scenario())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert saved is True
        assert document.body == "# Ada\n\nNew body.\n"
        assert state.page is not None
        assert state.page.is_dirty is False

    def test_autosave_skips_a_clean_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_page(path)
            state.edit_page()
            return await state.autosave()

        assert asyncio.run(scenario()) is False

    def test_untouched_new_draft_is_not_written(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.follow_link("note:Quarterly budget")
            return await state.autosave()

        saved = asyncio.run(scenario())

        assert saved is False
        assert not (vault / "reference" / "Quarterly budget.md").exists()

    def test_new_draft_is_created_on_first_autosave(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.follow_link("note:Quarterly budget")
            await state.set_page_body("# Quarterly budget\n\nDraft the numbers.\n")
            return await state.autosave()

        saved = asyncio.run(scenario())

        path = vault / "reference" / "Quarterly budget.md"
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert saved is True
        assert path.exists()
        assert document.body == "# Quarterly budget\n\nDraft the numbers.\n"
        assert state.page is not None
        assert state.page.path == path.resolve()
        assert state.page.is_dirty is False

    def test_external_change_stops_autosave(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        external = _note_text("# Ada\n\nExternal edit.\n")

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_page(path)
            state.edit_page()
            await state.set_page_body("# Ada\n\nMy edit.\n")
            path.write_text(external, encoding="utf-8", newline="\n")
            return await state.autosave()

        saved = asyncio.run(scenario())

        assert saved is False
        assert state.conflict == "changed"
        assert path.read_text(encoding="utf-8") == external
        assert state.page is not None
        assert state.page.is_dirty is True

    def test_reload_replaces_the_conflicted_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        external = _note_text("# Ada\n\nExternal edit.\n")

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_page(path)
            state.edit_page()
            await state.set_page_body("# Ada\n\nMy edit.\n")
            path.write_text(external, encoding="utf-8", newline="\n")
            await state.autosave()
            return await state.reload_page()

        reloaded = asyncio.run(scenario())

        assert reloaded is True
        assert state.conflict is None
        assert state.editing is False
        assert state.page is not None
        assert state.page.body == "# Ada\n\nExternal edit.\n"

    def test_overwrite_keeps_the_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_page(path)
            state.edit_page()
            await state.set_page_body("# Ada\n\nMy edit.\n")
            path.write_text(_note_text("# Ada\n\nExternal edit.\n"), encoding="utf-8", newline="\n")
            await state.autosave()
            return await state.overwrite_page()

        overwritten = asyncio.run(scenario())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert overwritten is True
        assert document.body == "# Ada\n\nMy edit.\n"
        assert state.conflict is None
        assert state.page is not None
        assert state.page.is_dirty is False

    def test_recreate_after_the_file_disappears(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_page(path)
            state.edit_page()
            await state.set_page_body("# Ada\n\nMy edit.\n")
            path.unlink()
            await state.autosave()
            assert state.conflict == "missing"
            return await state.recreate_page()

        recreated = asyncio.run(scenario())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert recreated is True
        assert document.body == "# Ada\n\nMy edit.\n"
        assert state.conflict is None

    def test_discard_drops_the_draft_without_writing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        before = path.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(path)
            state.edit_page()
            await state.set_page_body("# Ada\n\nMy edit.\n")
            await state.discard_draft()

        asyncio.run(scenario())

        assert state.page is None
        assert path.read_bytes() == before

    def test_back_on_a_dirty_draft_commits_first(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(first)
            await state.open_page(second)
            state.edit_page()
            await state.set_page_body("# Second\n\nChanged.\n")
            await state.back()

        asyncio.run(scenario())

        document = NoteDocument.from_text(second.read_text(encoding="utf-8"))
        assert document.body == "# Second\n\nChanged.\n"
        assert state.page is not None
        assert state.page.path == first.resolve()

    def test_navigation_commits_a_dirty_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(first)
            state.edit_page()
            await state.set_page_body("# First\n\nChanged.\n")
            await state.open_page(second)

        asyncio.run(scenario())

        document = NoteDocument.from_text(first.read_text(encoding="utf-8"))
        assert document.body == "# First\n\nChanged.\n"
        assert state.page is not None
        assert state.page.path == second.resolve()
        assert state.history == (first.resolve(),)

    def test_conflict_blocks_back_until_discarded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(first)
            await state.open_page(second)
            state.edit_page()
            await state.set_page_body("# Second\n\nMy edit.\n")
            second.write_text(_note_text("# Second\n\nExternal.\n"), encoding="utf-8", newline="\n")
            await state.autosave()
            assert await state.back() is False
            assert state.page is not None
            assert state.page.path == second.resolve()
            assert state.conflict == "changed"
            await state.discard_draft()
            assert await state.back() is True
            assert state.page is not None
            assert state.page.path == first.resolve()

        asyncio.run(scenario())

    def test_write_error_keeps_the_draft(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        def failing_write(
            _self: afanes.core.vault.Vault,
            _note_path: Path,
            _text: str,
            _expected_hash: str,
        ) -> str:
            message = "disk full"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.Vault, "write_page", failing_write)

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_page(path)
            state.edit_page()
            await state.set_page_body("# Ada\n\nMy edit.\n")
            return await state.autosave()

        saved = asyncio.run(scenario())

        assert saved is False
        assert state.page is not None
        assert state.page.is_dirty is True
        assert state.message is not None


class TestPageLinks:
    def test_resolved_link_opens_its_target(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Ada")

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.path == person.resolve()
        assert state.ambiguous == ()

    def test_ambiguous_link_exposes_the_candidates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        second = _write_note(vault / "notes" / "Ada.md", _typed_note("reference", "# Ada\n", category="person"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Ada")

        asyncio.run(scenario())

        assert state.page is None
        assert set(state.ambiguous) == {first.resolve(), second.resolve()}

    def test_choosing_a_candidate_opens_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Ada.md", _typed_note("reference", "# Ada\n", category="person"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Ada")
            await state.choose_candidate(first)

        asyncio.run(scenario())

        assert state.ambiguous == ()
        assert state.page is not None
        assert state.page.path == first.resolve()

    def test_missing_references_create_the_right_drafts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Quarterly budget")
            note_page = state.page
            assert note_page is not None
            assert note_page.labels is not None
            assert note_page.labels.note_type is NoteType.REFERENCE
            assert note_page.labels.category is None
            assert note_page.identity == "Quarterly budget"
            await state.follow_link("project:Release 1.0")
            assert state.page is not None
            assert state.page.labels is not None
            assert state.page.labels.note_type is NoteType.PROJECT

        asyncio.run(scenario())

        assert not (vault / "reference" / "Quarterly budget.md").exists()

        assert not (vault / "projects" / "Release 1.0.md").exists()

    def test_broken_link_opens_raw_rescue(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Broken")

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.mode is afanes.core.editing.DraftMode.RAW
        assert state.page.path == broken.resolve()
        assert state.editing is True

    def test_multiple_broken_files_ask_for_a_candidate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        second = _write_note(vault / "notes" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Broken")

        asyncio.run(scenario())

        assert state.page is None
        assert set(state.ambiguous) == {first.resolve(), second.resolve()}

    def test_non_internal_destinations_are_inert(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            for destination in (
                "https://example.com",
                "mailto:ada@example.com",
                "attachments/diagram.png",
                "javascript:alert(1)",
                "#section",
            ):
                await state.follow_link(destination)

        asyncio.run(scenario())

        assert state.page is None
        assert state.message is None
        assert state.ambiguous == ()

    def test_unsafe_name_is_created_and_repaired(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Q1: Planning?")
            await state.set_page_body("# Q1: Planning?\n\nDraft.\n")
            assert await state.autosave() is True
            assert state.repair_preview is not None
            assert [site.path for site in state.repair_preview.sites] == [source.resolve()]
            assert await state.apply_repair() is True

        asyncio.run(scenario())

        created = vault / "reference" / "Q1 Planning.md"
        assert created.exists()
        assert "note:Q1 Planning" in source.read_text(encoding="utf-8")
        assert "note:Q1: Planning?" not in source.read_text(encoding="utf-8")
        assert state.repair_preview is None

    def test_keep_leaves_the_unsafe_reference_alone(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        before = source.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Q1: Planning?")
            await state.set_page_body("# Q1: Planning?\n\nDraft.\n")
            await state.autosave()
            await state.keep_repair()

        asyncio.run(scenario())

        assert (vault / "reference" / "Q1 Planning.md").exists()
        assert source.read_bytes() == before
        assert state.repair_preview is None

    def test_cancelling_the_repair_restores_the_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Q1: Planning?")
            await state.set_page_body("# Q1: Planning?\n\nDraft.\n")
            await state.autosave()
            assert await state.cancel_repair() is True

        asyncio.run(scenario())

        assert not (vault / "reference" / "Q1 Planning.md").exists()
        assert (vault / "trash" / "Q1 Planning.md").exists()
        assert state.page is not None
        assert state.page.is_new
        assert state.page.is_dirty
        assert state.editing is True
        assert state.repair_preview is None
        assert source.read_bytes() != b""

    def test_existing_safe_page_is_reused(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        existing = _write_note(vault / "reference" / "Q1 Planning.md", _note_text("# Q1 Planning\n"))
        _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Q1: Planning?")

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.path == existing.resolve()
        assert state.repair_preview is not None


class TestPageRenameTrash:
    def test_rename_is_previewed_and_applied(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        referrer = _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(person)
            await state.open_page(first)
            await state.open_page(person)
            preview = await state.begin_rename("Ada King")
            assert preview is not None
            assert preview.heading_update is True
            assert state.rename_preview is not None
            assert person.exists()
            assert await state.apply_rename() is True

        asyncio.run(scenario())

        target = (vault / "reference" / "people" / "Ada King.md").resolve()
        assert not person.exists()
        assert target.exists()
        assert state.page is not None
        assert state.page.path == target
        assert state.page_title == "Ada King"
        assert state.history == (target, first.resolve())
        assert "note:Ada King" in referrer.read_text(encoding="utf-8")

    def test_cancelling_a_rename_changes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(person)
            await state.begin_rename("Ada King")
            await state.cancel_rename()

        asyncio.run(scenario())

        assert person.exists()
        assert not (vault / "reference" / "people" / "Ada King.md").exists()
        assert state.rename_preview is None

    def test_trash_is_previewed_and_returns_through_history(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _write_note(vault / "notes" / "Ref.md", _note_text("[Second](<note:Second>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(second)
            await state.open_page(first)
            await state.open_page(second)
            preview = await state.begin_trash()
            assert preview is not None
            assert preview.reference_count == 1
            assert state.trash_preview is not None
            assert await state.apply_trash() is True

        asyncio.run(scenario())

        assert not second.exists()
        assert (vault / "trash" / "Second.md").exists()
        assert state.page is not None
        assert state.page.path == first.resolve()
        assert state.history == ()
        assert state.trash_preview is None

    def test_cancelling_trash_changes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(second)
            await state.begin_trash()
            await state.cancel_trash()

        asyncio.run(scenario())

        assert second.exists()
        assert not (vault / "trash").exists()
        assert state.trash_preview is None


class TestPageRescue:
    def test_open_failure_opens_raw_rescue(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            failure = state.failures[0]
            await state.open_failure(failure.path)

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.mode is afanes.core.editing.DraftMode.RAW
        assert state.page.path == broken.resolve()
        assert state.page.raw_text == "---\ntype: refrence\n---\nBody\n"
        assert state.editing is True

    def test_raw_save_that_still_fails_stays_raw(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_failure(Path("reference/Broken.md"))
            await state.set_page_raw_text("still broken")
            return await state.autosave()

        saved = asyncio.run(scenario())

        assert saved is True
        assert broken.read_text(encoding="utf-8") == "still broken"
        assert state.page is not None
        assert state.page.mode is afanes.core.editing.DraftMode.RAW
        assert state.page.is_dirty is False

    def test_raw_save_that_parses_upgrades_to_normal(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        fixed = "---\ntype: note\n---\n\n# Fixed\nBody.\n"

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_failure(Path("reference/Broken.md"))
            await state.set_page_raw_text(fixed)
            return await state.autosave()

        saved = asyncio.run(scenario())

        assert saved is True
        assert broken.read_text(encoding="utf-8") == fixed
        assert state.page is not None
        assert state.page.mode is afanes.core.editing.DraftMode.NORMAL
        assert state.page.labels is not None
        assert state.page.labels.note_type is NoteType.NOTE
        assert state.page.is_dirty is False
        assert state.message == afanes.ui.strings.PAGE_RAW_UPGRADED
        assert state.editing is True

        async def finish() -> None:
            await state.done_editing()

        asyncio.run(finish())

        assert state.editing is False
        assert state.page is not None
        assert state.page.mode is afanes.core.editing.DraftMode.NORMAL

    def test_raw_save_stops_on_an_external_change(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.open_failure(Path("reference/Broken.md"))
            await state.set_page_raw_text("my rescue text")
            broken.write_text("external text", encoding="utf-8", newline="\n")
            return await state.autosave()

        saved = asyncio.run(scenario())

        assert saved is False
        assert state.conflict == "changed"
        assert broken.read_text(encoding="utf-8") == "external text"


class TestPageRecoveryLifecycle:
    def test_conflict_rescue_rename_and_trash(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        note = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        broken = _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        fixed = "---\ntype: note\n---\n\n# Recovered\nBody.\n"

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(note)
            state.edit_page()
            await state.set_page_body("# Ada\n\nMy edit.\n")
            note.write_text(_note_text("# Ada\n\nExternal.\n"), encoding="utf-8", newline="\n")
            assert await state.autosave() is False
            assert state.conflict == "changed"
            assert await state.reload_page() is True
            page = state.page
            assert page is not None
            assert page.body == "# Ada\n\nExternal.\n"

            await state.open_failure(Path("reference/Broken.md"))
            await state.set_page_raw_text(fixed)
            assert await state.autosave() is True
            page = state.page
            assert page is not None
            assert page.mode is afanes.core.editing.DraftMode.NORMAL
            assert await state.done_editing() is True

            assert await state.begin_rename("Recovered page") is not None
            assert await state.apply_rename() is True
            renamed = vault / "reference" / "Recovered page.md"
            assert renamed.exists()

            assert await state.begin_trash() is not None
            assert await state.apply_trash() is True

        asyncio.run(scenario())

        assert not broken.exists()
        assert (vault / "trash" / "Recovered page.md").exists()
        assert state.page is not None
        assert state.page.path == note.resolve()


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
            await state.choose_vault(vault)
            return await state.start_review()

        started = asyncio.run(scenario())

        assert started is True
        assert state.review_session is not None
        assert [item.kind for item in state.review_session.items] == [
            afanes.core.search.ReviewItemKind.INBOX,
            afanes.core.search.ReviewItemKind.PROJECT,
            afanes.core.search.ReviewItemKind.PROJECT,
        ]
        assert [item.path.stem for item in state.review_session.items] == ["Buy milk", "Stalled", "Healthy"]
        assert state.processing_note == capture
        assert state.active_section is afanes.ui.state.WorkspaceSection.REVIEW

    def test_zero_pending_starts_no_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            return await state.start_review()

        started = asyncio.run(scenario())

        assert started is False
        assert state.review_session is None
        assert state.active_section is afanes.ui.state.WorkspaceSection.REVIEW
        assert state.processing_note is None

    def test_start_review_does_not_infer_an_outcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        capture = _write_note(vault / "inbox" / "Call Ada tomorrow.md", _note_text("# Call Ada tomorrow"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.start_review()

        asyncio.run(scenario())

        assert capture.is_file()
        assert not (vault / "projects" / "Call Ada tomorrow.md").exists()
        assert state.processing_plan is None
        assert state.review_session is not None
        assert state.review_session.current is not None

    def test_processing_apply_advances_the_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.choose_vault(vault)
            await state.start_review()
            plan = await state.plan_processing(ProcessingOutcome.PROJECT)
            assert plan is not None
            return await state.apply_processing()

        target = asyncio.run(scenario())

        assert target == vault / "projects" / "Buy milk.md"
        assert state.review_session is not None
        assert state.review_session.reviewed_count == 1
        assert state.review_session.current is not None
        assert state.review_session.current.kind is afanes.core.search.ReviewItemKind.PROJECT
        assert state.processing_note is None
        assert state.review_pending_count == TWO_PENDING

    def test_skip_leaves_the_capture_and_advances(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        capture = _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.start_review()
            return await state.review_skip()

        skipped = asyncio.run(scenario())

        assert skipped is True
        assert capture.is_file()
        assert state.review_session is not None
        assert state.review_session.skipped_count == 1
        assert state.review_session.complete is True

    def test_review_next_advances_a_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        before = project.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.start_review()
            return await state.review_next()

        advanced = asyncio.run(scenario())

        assert advanced is True
        assert project.read_bytes() == before
        assert state.review_session is not None
        assert state.review_session.complete is True
        assert state.review_session.reviewed_count == 1

    def test_review_next_does_not_skip_an_inbox_item(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.start_review()
            return await state.review_next()

        advanced = asyncio.run(scenario())

        assert advanced is False
        assert state.review_session is not None
        assert state.review_session.current is not None
        assert state.review_session.current.kind is afanes.core.search.ReviewItemKind.INBOX

    def test_mark_project_done_writes_the_status_and_advances(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.start_review()
            return await state.mark_review_project_done()

        changed = asyncio.run(scenario())

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert changed is True
        assert document.status is Status.DONE
        assert state.review_session is not None
        assert state.review_session.complete is True
        assert state.review_pending_count == 0

    def test_defer_project_sets_later_and_remains_pending(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Stalled.md", "project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> bool:
            await state.choose_vault(vault)
            await state.start_review()
            return await state.defer_review_project()

        changed = asyncio.run(scenario())

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert changed is True
        assert document.status is Status.LATER
        assert state.review_pending_count == 1

    def test_add_review_step_refreshes_the_project_card(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.choose_vault(vault)
            await state.start_review()
            return await state.add_review_step("Build the prototype")

        path = asyncio.run(scenario())

        assert path == project
        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert "- [ ] Build the prototype" in document.body
        assert state.review_session is not None
        current = state.review_session.current
        assert current is not None
        assert current.project is not None
        assert current.project.next_step is not None
        assert current.project.next_step.text == "Build the prototype"
        assert state.review_session.reviewed_count == 0

    def test_add_review_step_rejects_blank_text(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        before = project.read_bytes()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> Path | None:
            await state.choose_vault(vault)
            await state.start_review()
            return await state.add_review_step("   ")

        path = asyncio.run(scenario())

        assert path is None
        assert project.read_bytes() == before
        assert state.review_session is not None
        current = state.review_session.current
        assert current is not None
        assert current.project is not None
        assert current.project.next_step is None

    def test_finish_review_returns_to_the_browser(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.start_review()
            await state.finish_review()

        asyncio.run(scenario())

        assert state.review_session is None
        assert state.active_section is afanes.ui.state.WorkspaceSection.INBOX
        assert state.processing_note is None

    def test_new_work_is_not_appended_to_the_current_queue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.start_review()
            await state.capture("Second thought")

        asyncio.run(scenario())

        assert state.review_session is not None
        assert len(state.review_session.items) == 1
        assert state.review_pending_count == TWO_PENDING

    def test_reset_does_not_restore_a_review_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", _note_text("# Buy milk"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.start_review()

        asyncio.run(scenario())
        state.reset()
        asyncio.run(state.choose_vault(vault))

        assert state.review_session is None
        assert state.review_pending_count == 1


class TestReset:
    def test_reset_clears_the_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Buy milk")
            await state.select_note(state.notes[0].path)

        asyncio.run(scenario())
        state.reset()

        assert state.vault_root is None
        assert state.notes == ()
        assert state.failures == ()
        assert state.selected is None
        assert state.preview_body is None
        assert state.busy is False
        assert state.message is None

    def test_reset_allows_a_second_event_loop(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.start())
        state.reset()
        asyncio.run(state.choose_vault(vault))

        assert state.vault_root == vault.resolve()


class TestOpenVaultPath:
    def test_typed_path_opens_and_saves_settings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        afanes.core.vault.Vault(vault).capture("Buy milk")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.open_vault_path(f"  {vault}  "))

        assert state.vault_root == vault.resolve()
        assert [note.name for note in state.notes] == ["Buy milk"]
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(vault.resolve())

    def test_blank_path_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        state = afanes.ui.state.app_state

        asyncio.run(state.open_vault_path("   "))

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_PATH_REQUIRED
        assert not settings.exists()

    def test_missing_path_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.open_vault_path(str(tmp_path / "missing")))

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_MISSING

    def test_file_path_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        target = tmp_path / "note.md"
        target.write_text("not a directory", encoding="utf-8")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.open_vault_path(str(target)))

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_NOT_DIRECTORY

    def test_unreadable_path_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")

        def deny_access(*_args: object, **_kwargs: object) -> bool:
            return False

        monkeypatch.setattr(afanes.core.vault.os, "access", deny_access)
        state = afanes.ui.state.app_state

        asyncio.run(state.open_vault_path(str(vault)))

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_UNREADABLE


class TestCreateVault:
    def test_creates_seeds_and_remembers_a_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "notes" / "vault"
        state = afanes.ui.state.app_state

        opened = asyncio.run(state.create_vault(target))

        assert opened is True
        assert state.vault_root == target.resolve()
        assert (target / "inbox").is_dir()
        assert (target / "trash").is_dir()
        assert (target / "reference").is_dir()
        assert (target / "projects").is_dir()
        assert not (target / "reference" / "people").exists()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(target.resolve())

    def test_refuses_a_non_empty_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "vault"
        target.mkdir()
        (target / "photo.jpg").write_text("data", encoding="utf-8")
        state = afanes.ui.state.app_state

        opened = asyncio.run(state.create_vault(target))

        assert opened is False
        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_NOT_EMPTY
        assert sorted(path.name for path in target.iterdir()) == ["photo.jpg"]

    def test_refuses_a_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "note.md"
        target.write_text("body", encoding="utf-8")
        state = afanes.ui.state.app_state

        opened = asyncio.run(state.create_vault(target))

        assert opened is False
        assert state.message == afanes.ui.strings.VAULT_NOT_DIRECTORY

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

        opened = asyncio.run(state.create_vault(target))

        assert opened is True
        assert state.vault_root == target.resolve()
        assert state.message == afanes.ui.strings.VAULT_CREATED_NOT_REMEMBERED.format(detail="read only")


class TestOpenVaultForRun:
    def test_supplied_vault_leaves_settings_unchanged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        remembered = tmp_path / "remembered"
        remembered.mkdir()
        supplied = tmp_path / "supplied"
        supplied.mkdir()
        afanes.core.vault.Vault(supplied).capture("Buy milk")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=remembered))
        state = afanes.ui.state.app_state

        asyncio.run(state.open_vault_for_run(supplied))

        assert state.vault_root == supplied.resolve()
        assert [note.name for note in state.notes] == ["Buy milk"]
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(remembered.resolve())

    def test_supplied_vault_failure_reports_a_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        asyncio.run(state.open_vault_for_run(tmp_path / "missing"))

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_MISSING


class TestSessionGuard:
    def test_second_begin_is_refused(self) -> None:
        state = afanes.ui.state.app_state

        assert state.begin_session() is True
        assert state.begin_session() is False

    def test_release_allows_a_later_session(self) -> None:
        state = afanes.ui.state.app_state

        state.begin_session()
        state.release_session()

        assert state.begin_session() is True

    def test_reset_clears_the_session(self) -> None:
        state = afanes.ui.state.app_state
        state.begin_session()

        state.reset()

        assert state.session_active is False


class TestReviewStepCommands:
    def _due_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, afanes.ui.state.AppState]:
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
            await state.choose_vault(vault)
            await state.start_review()

        asyncio.run(scenario())
        return project, state

    def test_do_it_now_checks_the_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project, state = self._due_project(tmp_path, monkeypatch)

        assert asyncio.run(state.review_do_now()) is True

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        step = StepDocument(document.body).steps[0]
        assert step.checked is True
        assert step.actual == datetime.datetime.now(tz=datetime.UTC).astimezone().date()

    def test_postpone_replaces_the_plan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project, state = self._due_project(tmp_path, monkeypatch)
        new_plan = datetime.date(2026, 12, 1)

        assert asyncio.run(state.review_postpone(new_plan)) is True

        step = StepDocument(NoteDocument.from_text(project.read_text(encoding="utf-8")).body).steps[0]
        assert step.plan == new_plan
        assert step.actual is None

    def test_delegate_adds_an_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project, state = self._due_project(tmp_path, monkeypatch)

        assert asyncio.run(state.review_delegate("Ada")) is True

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
            await state.choose_vault(vault)
            await state.start_review()

        asyncio.run(scenario())

        assert asyncio.run(state.review_reassign("Grace")) is True

        step = StepDocument(NoteDocument.from_text(project.read_text(encoding="utf-8")).body).steps[0]
        assert step.owners == ("Grace",)
