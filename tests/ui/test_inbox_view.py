"""Tests for the welcome view without a rendered window."""

import flet as ft
import pytest

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.inbox


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


async def _change_vault() -> None:
    return None


async def _open_path(_text: str) -> None:
    return None


class TestWelcomeView:
    def test_welcome_has_a_folder_action(self) -> None:
        control = afanes.ui.views.inbox.WelcomeView(_change_vault).build()
        assert isinstance(control, ft.Container)
        content = control.content

        assert isinstance(content, ft.Column)
        buttons = [item for item in content.controls if isinstance(item, ft.FilledButton)]
        assert len(buttons) == 1
        assert buttons[0].content == afanes.ui.strings.WELCOME_CHOOSE

    def test_welcome_shows_the_startup_message(self) -> None:
        afanes.ui.state.app_state.status.message = afanes.ui.strings.SETTINGS_UNREADABLE

        control = afanes.ui.views.inbox.WelcomeView(_change_vault).build()
        assert isinstance(control, ft.Container)
        content = control.content

        assert isinstance(content, ft.Column)
        assert any(isinstance(item, ft.Container) for item in content.controls)


class TestBrowserWelcomeView:
    def test_browser_welcome_has_a_path_field(self) -> None:
        control = afanes.ui.views.inbox.WelcomeView(on_open_path=_open_path).build()
        assert isinstance(control, ft.Container)
        content = control.content
        assert isinstance(content, ft.Column)

        fields = [item for item in content.controls if isinstance(item, ft.TextField)]
        buttons = [item for item in content.controls if isinstance(item, ft.FilledButton)]
        assert len(fields) == 1
        assert len(buttons) == 1
        assert buttons[0].content == afanes.ui.strings.WELCOME_OPEN

    def test_welcome_requires_a_selection_command(self) -> None:
        with pytest.raises(ValueError, match="selection command"):
            afanes.ui.views.inbox.WelcomeView()
