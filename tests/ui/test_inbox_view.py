"""Tests for the welcome and Inbox views without a rendered window."""

import asyncio
import typing
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.inbox
from afanes.core.editing import DraftMode
from afanes.core.vault.snapshot import VaultFailure
from tests.support import ensure_vault, versioned

TWO_BANNERS = 2


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


async def _change_vault() -> None:
    return None


async def _process(_path: Path) -> None:
    return None


async def _open_path(_text: str) -> None:
    return None


def _write_note(path: Path, body: str) -> Path:
    ensure_vault(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntype: note\n---\n{body}", encoding="utf-8")
    return path


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


class TestInboxView:
    def test_shows_the_composer_and_empty_state(self) -> None:
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)

        assert view.composer.label == afanes.ui.strings.COMPOSER_LABEL
        assert view.capture_button.content == afanes.ui.strings.CAPTURE_ACTION
        assert len(view.list_view.controls) == 1
        assert isinstance(view.list_view.controls[0], ft.Container)
        assert view.page_view.empty_text.visible is True
        assert view.page_view.read_body.visible is False
        assert view.banners.visible is False
        assert view.page_view.process_button.visible is False

    def test_build_returns_the_root_control(self) -> None:
        control = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process).build()

        assert isinstance(control, ft.Column)

    def test_shows_a_captured_note_and_preview(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")
            await state.navigation.open_page(state.session.notes[0].path)

        asyncio.run(scenario())
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)

        row = view.list_view.controls[0]
        assert isinstance(row, ft.ListTile)
        assert row.title == "Buy milk"
        assert view.page_view.title.value == "Buy milk"
        assert view.page_view.read_body.value == "# Buy milk"
        assert view.page_view.read_body.visible is True
        assert view.page_view.read_body.on_tap_link is not None
        assert view.page_view.process_button.visible is True

    def test_list_shows_the_heading_title_and_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Ada.md", "# Ada, Countess of Lovelace\n")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.choose_vault(vault))
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)

        row = view.list_view.controls[0]
        assert isinstance(row, ft.ListTile)
        assert row.title == "Ada, Countess of Lovelace"
        assert row.subtitle == "inbox/Ada.md"

    def test_list_falls_back_to_the_identity(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Plain note.md", "No heading\n")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.choose_vault(vault))
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)

        row = view.list_view.controls[0]
        assert isinstance(row, ft.ListTile)
        assert row.title == "Plain note"

    def test_list_distinguishes_duplicate_titles_by_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "First.md", "# Buy milk\n")
        _write_note(vault / "inbox" / "Second.md", "# Buy milk\n")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state

        asyncio.run(state.workspace.choose_vault(vault))
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)

        rows = [control for control in view.list_view.controls if isinstance(control, ft.ListTile)]
        assert [row.title for row in rows] == ["Buy milk", "Buy milk"]
        assert {row.subtitle for row in rows} == {"inbox/First.md", "inbox/Second.md"}

    def test_preview_header_uses_the_heading_title(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "inbox" / "Ada.md", "# Ada, Countess of Lovelace\n")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)

        asyncio.run(scenario())
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)

        assert view.page_view.title.value == "Ada, Countess of Lovelace"
        assert view.page_view.read_body.value == "# Ada, Countess of Lovelace\n"

    def test_preview_header_falls_back_to_the_identity(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "inbox" / "Plain note.md", "No heading\n")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)

        asyncio.run(scenario())
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)

        assert view.page_view.title.value == "Plain note"

    def test_process_button_calls_the_callback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state
        calls: list[Path] = []

        async def process(path: Path) -> None:
            calls.append(path)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.session.capture("Buy milk")
            await state.navigation.open_page(state.session.notes[0].path)

        asyncio.run(scenario())
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, process)

        assert view.page_view.process_button.on_click is not None
        handler = typing.cast("typing.Any", view.page_view.process_button.on_click)
        asyncio.run(handler())

        assert state.pages.page is not None
        assert calls == [state.pages.page.path]

    def test_shows_message_and_scan_banners(self) -> None:
        state = afanes.ui.state.app_state
        state.status.message = "boom"
        state.session.failures = (VaultFailure(path=Path("inbox/Bad.md"), message="bad"),)

        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)

        assert view.banners.visible is True
        assert len(view.banners.controls) == TWO_BANNERS

    def test_failure_path_opens_raw_rescue(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        broken = vault / "reference" / "Broken.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore,
            "settings_path",
            classmethod(lambda _cls: tmp_path / "settings.json"),
        )
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)

        asyncio.run(scenario())
        view = afanes.ui.views.inbox.InboxView(_noop, _change_vault, _process)
        failure_banner = view.banners.controls[0]
        assert isinstance(failure_banner, ft.Container)
        content = failure_banner.content
        assert isinstance(content, ft.Column)
        button = content.controls[1]
        assert isinstance(button, ft.TextButton)
        handler = typing.cast("typing.Any", button.on_click)
        asyncio.run(handler())

        assert state.pages.page is not None
        assert state.pages.page.mode is DraftMode.RAW
        assert view.page_view.raw_panel.visible is True
