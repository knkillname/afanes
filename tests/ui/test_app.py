"""Tests for the application shell routing without a rendered window."""

import asyncio
import json
import typing
from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.core.vault
import afanes.ui.app
import afanes.ui.state
import afanes.ui.strings
from afanes.core.settings import Settings

Handler = Callable[[], Awaitable[None]]
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 760


class FakeWindow:
    width = 0
    height = 0
    min_width = 0
    min_height = 0


class FakePage:
    def __init__(self, *, web: bool = False) -> None:
        self.title = ""
        self.theme_mode = ft.ThemeMode.SYSTEM
        self.padding = 0
        self.window = FakeWindow()
        self.services: list[object] = []
        self.controls: list[ft.Control] = []
        self.updates = 0
        self.web = web
        self.on_disconnect: Callable[[], None] | None = None
        self.dialogs: list[ft.AlertDialog] = []

    def add(self, control: ft.Control) -> None:
        self.controls.append(control)

    def update(self) -> None:
        self.updates += 1

    def show_dialog(self, dialog: ft.AlertDialog) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self) -> ft.AlertDialog | None:
        return self.dialogs.pop() if self.dialogs else None


class FakePicker:
    def __init__(self, selected: str | None) -> None:
        self.selected = selected

    async def get_directory_path(self, **_: object) -> str | None:
        return self.selected


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _welcome_button(control: ft.Control) -> ft.FilledButton:
    assert isinstance(control, ft.Container)
    content = control.content
    assert isinstance(content, ft.Column)
    buttons = [item for item in content.controls if isinstance(item, ft.FilledButton)]
    assert len(buttons) == 1
    return buttons[0]


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: path))


def _find_by_key(control: ft.Control, key: str) -> ft.Control | None:
    if getattr(control, "key", None) == key:
        return control
    for child in getattr(control, "controls", []) or []:
        found = _find_by_key(child, key)
        if found is not None:
            return found
    for child in getattr(control, "actions", []) or []:
        found = _find_by_key(child, key)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_by_key(content, key)
    return None


def _find_by_content(control: ft.Control, text: str) -> ft.Control | None:
    if getattr(control, "content", None) == text and getattr(control, "on_click", None) is not None:
        return control
    for child in getattr(control, "controls", []) or []:
        found = _find_by_content(child, text)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_by_content(content, text)
    return None


def _typed[T: ft.Control](control: ft.Control | None, expected: type[T]) -> T:
    assert isinstance(control, expected)
    return control


class TestAppShell:
    def test_without_settings_shows_the_welcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert isinstance(page.controls[0], ft.Container)
        assert afanes.ui.state.app_state.vault_root is None

    def test_choosing_a_vault_opens_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        picker = FakePicker(str(vault))
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            button = _welcome_button(page.controls[0])
            handler = typing.cast("Handler", button.on_click)
            await handler()

        asyncio.run(scenario())

        assert afanes.ui.state.app_state.vault_root == vault.resolve()
        assert isinstance(page.controls[0], ft.Column)
        assert settings.is_file()

    def test_cancelling_the_picker_keeps_the_welcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        picker = FakePicker(None)
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            button = _welcome_button(page.controls[0])
            handler = typing.cast("Handler", button.on_click)
            await handler()

        asyncio.run(scenario())

        assert afanes.ui.state.app_state.vault_root is None
        assert isinstance(page.controls[0], ft.Container)
        assert not settings.exists()

    def test_saved_settings_reopen_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert afanes.ui.state.app_state.vault_root == vault.resolve()
        assert isinstance(page.controls[0], ft.Column)

    def test_process_action_opens_the_wizard_and_cancel_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        afanes.core.vault.Vault(vault).capture("Buy milk")
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            await state.open_page(state.notes[0].path)
            process_button = _find_by_key(page.controls[0], "process-note")
            assert isinstance(process_button, ft.TextButton)
            process_handler = typing.cast("Handler", process_button.on_click)
            await process_handler()

            assert state.processing_note is not None
            assert _find_by_key(page.controls[0], "processing-view") is not None

            cancel_button = _find_by_key(page.controls[0], "processing-cancel")
            assert isinstance(cancel_button, ft.TextButton)
            cancel_handler = typing.cast("Handler", cancel_button.on_click)
            await cancel_handler()

        asyncio.run(scenario())

        assert state.processing_note is None
        assert _find_by_key(page.controls[0], "processing-view") is None
        assert _find_by_key(page.controls[0], "process-note") is not None


class TestDesktopPresentation:
    def test_desktop_session_configures_the_window(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert page.window.width == WINDOW_WIDTH
        assert page.window.height == WINDOW_HEIGHT
        assert len(page.services) == 1

    def test_desktop_welcome_has_no_path_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert _find_by_key(page.controls[0], "welcome-path") is None
        assert _welcome_button(page.controls[0]).content == afanes.ui.strings.WELCOME_CHOOSE


class TestWebPresentation:
    def test_web_session_skips_window_configuration(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage(web=True)

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert page.window.width == 0
        assert page.window.height == 0
        assert page.services == []

    def test_web_welcome_offers_a_path_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage(web=True)

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        field = _typed(_find_by_key(page.controls[0], "welcome-path"), ft.TextField)
        assert field.label == afanes.ui.strings.WELCOME_PATH_LABEL
        assert _welcome_button(page.controls[0]).content == afanes.ui.strings.WELCOME_OPEN

    def test_entering_a_path_opens_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.vault.Vault(vault).capture("Buy milk")
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            field = _typed(_find_by_key(page.controls[0], "welcome-path"), ft.TextField)
            field.value = str(vault)
            button = _typed(_find_by_key(page.controls[0], "welcome-open"), ft.FilledButton)
            handler = typing.cast("Handler", button.on_click)
            await handler()

        asyncio.run(scenario())

        assert state.vault_root == vault.resolve()
        assert [note.name for note in state.notes] == ["Buy milk"]
        assert isinstance(page.controls[0], ft.Column)
        assert settings.is_file()

    def test_invalid_path_keeps_the_welcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            field = _typed(_find_by_key(page.controls[0], "welcome-path"), ft.TextField)
            field.value = str(tmp_path / "missing")
            button = _typed(_find_by_key(page.controls[0], "welcome-open"), ft.FilledButton)
            handler = typing.cast("Handler", button.on_click)
            await handler()

        asyncio.run(scenario())

        assert state.vault_root is None
        assert state.message == afanes.ui.strings.VAULT_MISSING
        assert isinstance(page.controls[0], ft.Container)
        assert not settings.exists()

    def test_change_vault_dialog_switches_the_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        first = tmp_path / "first"
        first.mkdir()
        second = tmp_path / "second"
        second.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=first))
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            change = _typed(_find_by_content(page.controls[0], afanes.ui.strings.CHANGE_VAULT_ACTION), ft.TextButton)
            change_handler = typing.cast("Handler", change.on_click)
            await change_handler()

            assert len(page.dialogs) == 1
            field = _typed(_find_by_key(page.dialogs[0], "change-vault-path"), ft.TextField)
            field.value = str(second)
            open_button = _typed(_find_by_key(page.dialogs[0], "change-vault-open"), ft.FilledButton)
            open_handler = typing.cast("Handler", open_button.on_click)
            await open_handler()

        asyncio.run(scenario())

        assert state.vault_root == second.resolve()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(second.resolve())

    def test_change_vault_dialog_cancel_keeps_the_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        first = tmp_path / "first"
        first.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=first))
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            change = _typed(_find_by_content(page.controls[0], afanes.ui.strings.CHANGE_VAULT_ACTION), ft.TextButton)
            change_handler = typing.cast("Handler", change.on_click)
            await change_handler()
            cancel = _typed(_find_by_key(page.dialogs[0], "change-vault-cancel"), ft.TextButton)
            cancel_handler = typing.cast("Handler", cancel.on_click)
            await cancel_handler()

        asyncio.run(scenario())

        assert page.dialogs == []
        assert state.vault_root == first.resolve()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(first.resolve())


class TestLaunchVault:
    def test_supplied_vault_overrides_the_remembered_one(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        remembered = tmp_path / "remembered"
        remembered.mkdir()
        supplied = tmp_path / "supplied"
        supplied.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=remembered))
        page = FakePage()
        state = afanes.ui.state.app_state

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page), launch_vault=supplied))

        assert state.vault_root == supplied.resolve()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(remembered.resolve())


class TestSessionGuard:
    def test_second_session_gets_a_notice(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        afanes.core.vault.Vault(vault).capture("Buy milk")
        first = FakePage()
        second = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", first))
            await afanes.ui.app.main(typing.cast("ft.Page", second))

        asyncio.run(scenario())

        assert state.session_active is True
        assert [note.name for note in state.notes] == ["Buy milk"]
        assert _find_by_key(second.controls[0], "session-retry") is not None
        assert _find_by_key(second.controls[0], "welcome-path") is None

    def test_disconnect_releases_the_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        first = FakePage()
        second = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", first))
            await afanes.ui.app.main(typing.cast("ft.Page", second))
            assert first.on_disconnect is not None
            first.on_disconnect()

            retry = _typed(_find_by_key(second.controls[0], "session-retry"), ft.FilledButton)
            handler = typing.cast("Handler", retry.on_click)
            await handler()

        asyncio.run(scenario())

        assert state.session_active is True
        assert _find_by_key(second.controls[0], "session-retry") is None
        assert isinstance(second.controls[0], ft.Container)
