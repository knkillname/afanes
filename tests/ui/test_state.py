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

OLD_NS = 1_700_000_000_000_000_000
NEW_NS = 1_700_000_001_000_000_000


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings, "settings_path", lambda: path)


def _write_settings(path: Path, vault: Path) -> None:
    payload = {"version": afanes.core.settings.SETTINGS_VERSION, "vault": str(vault)}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_note(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _note_text(body: str) -> str:
    return f"---\ntype: note\n---\n{body}"


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
        assert state.processing_body == "Buy milk"
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
            plan = await state.plan_processing(ProcessingOutcome.ACTION)
            assert plan is not None
            assert state.processing_plan is plan

        asyncio.run(scenario())

        assert not (vault / "actions" / "Buy milk.md").exists()

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
            await state.plan_processing(ProcessingOutcome.ACTION)
            target = await state.apply_processing()
            assert target is not None
            return target

        target = asyncio.run(scenario())

        assert target == vault / "actions" / "Buy milk.md"
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
            await state.plan_processing(ProcessingOutcome.ACTION)

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
            await state.plan_processing(ProcessingOutcome.ACTION)
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
            await state.plan_processing(ProcessingOutcome.ACTION)
            await state.apply_processing()
            state.finish_processing()

        asyncio.run(scenario())

        assert state.processing_result is None
        assert state.processing_note is None


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
        assert document.references == ()

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
        assert state.preview_body == "First line\nsecond line"
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
