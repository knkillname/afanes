"""Tests for the welcome and Inbox views without a rendered window."""

import asyncio
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.inbox
from afanes.core.vault import VaultFailure

TWO_BANNERS = 2


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


async def _change_vault() -> None:
    return None


class TestWelcomeView:
    def test_welcome_has_a_folder_action(self) -> None:
        control = afanes.ui.views.inbox.build_welcome(_change_vault)
        assert isinstance(control, ft.Container)
        content = control.content

        assert isinstance(content, ft.Column)
        buttons = [item for item in content.controls if isinstance(item, ft.FilledButton)]
        assert len(buttons) == 1
        assert buttons[0].content == afanes.ui.strings.WELCOME_CHOOSE

    def test_welcome_shows_the_startup_message(self) -> None:
        afanes.ui.state.app_state.message = afanes.ui.strings.SETTINGS_UNREADABLE

        control = afanes.ui.views.inbox.build_welcome(_change_vault)
        assert isinstance(control, ft.Container)
        content = control.content

        assert isinstance(content, ft.Column)
        assert any(isinstance(item, ft.Container) for item in content.controls)


class TestInboxView:
    def test_shows_the_composer_and_empty_state(self) -> None:
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault)

        assert view.composer.label == afanes.ui.strings.COMPOSER_LABEL
        assert view.capture_button.content == afanes.ui.strings.CAPTURE_ACTION
        assert len(view.list_view.controls) == 1
        assert isinstance(view.list_view.controls[0], ft.Container)
        assert view.preview_empty.visible is True
        assert view.preview_body.visible is False
        assert view.banners.visible is False

    def test_build_returns_the_root_control(self) -> None:
        control = afanes.ui.views.inbox.build_inbox(_noop, _change_vault)

        assert isinstance(control, ft.Column)

    def test_shows_a_captured_note_and_preview(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setattr(
            afanes.core.settings,
            "settings_path",
            lambda: tmp_path / "settings.json",
        )
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.capture("Buy milk")
            await state.select_note(state.notes[0].path)

        asyncio.run(scenario())
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault)

        row = view.list_view.controls[0]
        assert isinstance(row, ft.ListTile)
        assert row.title == "Buy milk"
        assert view.preview_title.value == "Buy milk"
        assert view.preview_body.value == "Buy milk"
        assert view.preview_body.visible is True
        assert view.preview_body.on_tap_link is not None

        selected = state.selected
        view.handle_link()
        assert state.selected == selected

    def test_shows_message_and_scan_banners(self) -> None:
        state = afanes.ui.state.app_state
        state.message = "boom"
        state.failures = (VaultFailure(path=Path("inbox/Bad.md"), message="bad"),)

        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault)

        assert view.banners.visible is True
        assert len(view.banners.controls) == TWO_BANNERS
