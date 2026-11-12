"""Tests for the workspace shell and type-grouped browser."""

import asyncio
import typing
from collections.abc import Callable, Coroutine
from pathlib import Path

import flet as ft
import pytest

import afanes.core.search
import afanes.core.settings
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.workspace
from afanes.core.editing import DraftMode

Handler = Callable[[], Coroutine[typing.Any, typing.Any, None]]
SIX_SECTIONS = 6


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


async def _change_vault() -> None:
    return None


async def _create_vault() -> None:
    return None


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: path))


def _write_note(
    path: Path,
    *,
    note_type: str = "note",
    status: str | None = None,
    category: str | None = None,
    body: str = "",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    if status is not None:
        lines.append(f"status: {status}")
    lines.extend(["---", body])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _open_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> afanes.ui.views.workspace.WorkspaceView:
    _use_settings_file(monkeypatch, tmp_path / "settings.json")
    asyncio.run(afanes.ui.state.app_state.choose_vault(tmp_path / "vault"))
    return afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault)


def _handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_click"))


def _change_handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_change"))


class TestWorkspaceShell:
    def test_builds_capture_bar_and_browser(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.choose_vault(vault))
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault)

        assert view.root.key == "workspace-view"
        assert isinstance(view.root, ft.Column)
        assert view.capture_field.label == afanes.ui.strings.COMPOSER_LABEL
        assert len(view.section_tiles) == SIX_SECTIONS
        assert view.review_tile.title == afanes.ui.strings.REVIEW_TITLE
        assert view.page_view.empty_text.visible is True

    def test_browser_and_page_are_visible_together(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "inbox" / "Buy milk.md", body="# Buy milk")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(note)

        asyncio.run(scenario())
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault)

        assert view.sidebar.visible is True
        assert view.page_view.title.value == "Buy milk"
        assert view.page_view.read_body.visible is True

    def test_switching_sections_keeps_the_open_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "inbox" / "Buy milk.md", body="# Buy milk")
        _write_note(vault / "projects" / "Launch.md", note_type="project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(note)

        asyncio.run(scenario())
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault)
        handler = _handler(view.section_tiles[afanes.ui.state.WorkspaceSection.PROJECTS])

        asyncio.run(handler())

        assert state.active_section is afanes.ui.state.WorkspaceSection.PROJECTS
        assert view.page_view.title.value == "Buy milk"
        projects_root = next(
            control for control in view.browser_list.controls if getattr(control, "key", None) == "projects-view"
        )
        assert isinstance(projects_root, ft.Column)
        active_group = next(
            control
            for control in projects_root.controls
            if isinstance(control, ft.ExpansionTile) and control.key == "project-group-active"
        )
        titles = [control.title for control in active_group.controls or [] if isinstance(control, ft.ListTile)]
        assert titles == ["Launch"]

    def test_section_counts_follow_the_scan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "One.md")
        _write_note(vault / "inbox" / "Two.md")
        _write_note(vault / "projects" / "Launch.md", note_type="project", status="active")
        _write_note(vault / "reference" / "people" / "Ada.md", note_type="reference", category="person")
        view = _open_workspace(tmp_path, monkeypatch)

        assert view.section_counts[afanes.ui.state.WorkspaceSection.INBOX].value == "2"
        assert view.section_counts[afanes.ui.state.WorkspaceSection.PROJECTS].value == "1"
        assert view.section_counts[afanes.ui.state.WorkspaceSection.PEOPLE].value == "1"
        assert view.section_counts[afanes.ui.state.WorkspaceSection.ACTIONS].value == "0"
        assert "3 pending" in view.review_count.value

    def test_capture_appears_only_under_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "inbox" / "Capture.md", body="# Capture")
        view = _open_workspace(tmp_path, monkeypatch)
        state = afanes.ui.state.app_state

        assert view.section_counts[afanes.ui.state.WorkspaceSection.INBOX].value == "1"
        assert view.section_counts[afanes.ui.state.WorkspaceSection.NOTES].value == "0"

        asyncio.run(_handler(view.section_tiles[afanes.ui.state.WorkspaceSection.NOTES])())

        empty = view.browser_list.controls[0]
        assert isinstance(empty, ft.Container)
        content = empty.content
        assert isinstance(content, ft.Text)
        assert content.value == afanes.ui.strings.BROWSER_EMPTY
        assert state.browser_listing is not None
        assert state.browser_listing.group(afanes.core.search.BrowserSection.NOTES).notes == ()
        assert note.is_file()

    def test_unreadable_note_is_listed_and_opens_in_rescue_mode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        broken = vault / "reference" / "Broken.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        view = _open_workspace(tmp_path, monkeypatch)

        assert view.failures_column.visible is True
        tile = next(
            control
            for control in view.failures_column.controls
            if isinstance(control, ft.ListTile) and control.title == "reference/Broken.md"
        )
        asyncio.run(_handler(tile)())

        assert afanes.ui.state.app_state.page is not None
        assert afanes.ui.state.app_state.page.mode is DraftMode.RAW
        assert view.page_view.raw_panel.visible is True


class TestCaptureBar:
    def test_capture_creates_a_note_and_clears_the_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        view = _open_workspace(tmp_path, monkeypatch)
        view.capture_field.value = "Buy milk"

        asyncio.run(_handler(view.capture_button)())

        assert (vault / "inbox" / "Buy milk.md").is_file()
        assert view.capture_field.value == ""
        assert view.section_counts[afanes.ui.state.WorkspaceSection.INBOX].value == "1"

    def test_empty_capture_keeps_the_field_and_reports(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        view = _open_workspace(tmp_path, monkeypatch)
        view.capture_field.value = "   "

        asyncio.run(_handler(view.capture_button)())

        assert view.capture_field.value == "   "
        assert afanes.ui.state.app_state.message == afanes.ui.strings.CAPTURE_EMPTY
        assert list((vault / "inbox").glob("*.md")) == []


class TestBrowserSearch:
    def test_filters_by_title(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Ada.md", note_type="reference", body="# Ada, Countess of Lovelace")
        _write_note(vault / "reference" / "Grace.md", note_type="reference", body="# Grace Hopper")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.WorkspaceSection.REFERENCES])())

        view.search_field.value = "countess"
        asyncio.run(_change_handler(view.search_field)())

        titles = [control.title for control in view.browser_list.controls if isinstance(control, ft.ListTile)]
        assert titles == ["Ada, Countess of Lovelace"]

    def test_filters_by_identity_and_ignores_whitespace(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Ada, Lovelace.md", note_type="reference", body="# A person")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.WorkspaceSection.REFERENCES])())

        view.search_field.value = "Ada,   Lovelace"
        asyncio.run(_change_handler(view.search_field)())

        assert afanes.ui.state.app_state.browser_query == "Ada,   Lovelace"
        titles = [control.title for control in view.browser_list.controls if isinstance(control, ft.ListTile)]
        assert titles == ["A person"]

    def test_body_only_term_lists_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Ada.md", note_type="reference", body="# Ada\n\nAnalytical engine")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.WorkspaceSection.REFERENCES])())

        view.search_field.value = "analytical"
        asyncio.run(_change_handler(view.search_field)())

        empty = view.browser_list.controls[0]
        assert isinstance(empty, ft.Container)
        content = empty.content
        assert isinstance(content, ft.Text)
        assert content.value == afanes.ui.strings.BROWSER_NO_MATCH


class TestBrowserHistory:
    def test_back_returns_to_the_previous_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        first = _write_note(vault / "reference" / "Ada.md", note_type="reference", body="# Ada")
        _write_note(vault / "reference" / "Grace.md", note_type="reference", body="# Grace")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.WorkspaceSection.REFERENCES])())

        asyncio.run(_handler(_row_for(view.browser_list, "Ada"))())
        asyncio.run(_handler(_row_for(view.browser_list, "Grace"))())
        asyncio.run(view.page_view.go_back())

        assert afanes.ui.state.app_state.page is not None
        assert afanes.ui.state.app_state.page.path == first
        assert view.page_view.title.value == "Ada"


def _row_for(browser: ft.ListView, title: str) -> ft.ListTile:
    return next(control for control in browser.controls if isinstance(control, ft.ListTile) and control.title == title)
