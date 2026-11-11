"""Tests for the application shell routing without a rendered window."""

import asyncio
import typing
from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.ui.app
import afanes.ui.state
from afanes.core.settings import Settings

Handler = Callable[[], Awaitable[None]]


class FakeWindow:
    width = 0
    height = 0
    min_width = 0
    min_height = 0


class FakePage:
    def __init__(self) -> None:
        self.title = ""
        self.theme_mode = ft.ThemeMode.SYSTEM
        self.padding = 0
        self.window = FakeWindow()
        self.services: list[object] = []
        self.controls: list[ft.Control] = []
        self.updates = 0

    def add(self, control: ft.Control) -> None:
        self.controls.append(control)

    def update(self) -> None:
        self.updates += 1


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
    monkeypatch.setattr(afanes.core.settings, "settings_path", lambda: path)


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
        afanes.core.settings.save_settings(Settings(vault=vault), settings)
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert afanes.ui.state.app_state.vault_root == vault.resolve()
        assert isinstance(page.controls[0], ft.Column)
