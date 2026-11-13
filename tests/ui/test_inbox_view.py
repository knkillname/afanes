"""Tests for the welcome view without a rendered window."""

import flet as ft
import pytest

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.inbox
from tests.ui.control_tree import emphasis_controls


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


async def _change_vault() -> None:
    return None


async def _create_vault() -> None:
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

    def test_desktop_welcome_shows_one_suggested_action(self) -> None:
        control = afanes.ui.views.inbox.WelcomeView(
            on_choose=_change_vault,
            on_create=_create_vault,
        ).build()

        highlighted = emphasis_controls(control)

        assert len(highlighted) == 1
        assert isinstance(highlighted[0], ft.FilledButton)
        assert highlighted[0].content == afanes.ui.strings.WELCOME_CHOOSE

    def test_new_vault_is_a_regular_action(self) -> None:
        control = afanes.ui.views.inbox.WelcomeView(
            on_choose=_change_vault,
            on_create=_create_vault,
        ).build()
        assert isinstance(control, ft.Container)
        content = control.content
        assert isinstance(content, ft.Column)
        regular = [item for item in content.controls if isinstance(item, ft.OutlinedButton)]

        assert [item.content for item in regular] == [afanes.ui.strings.NEW_VAULT_ACTION]


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

    def test_browser_welcome_shows_one_suggested_action(self) -> None:
        control = afanes.ui.views.inbox.WelcomeView(
            on_open_path=_open_path,
            on_create=_create_vault,
        ).build()

        highlighted = emphasis_controls(control)

        assert len(highlighted) == 1
        button = highlighted[0]
        assert isinstance(button, ft.FilledButton)
        assert button.content == afanes.ui.strings.WELCOME_OPEN
