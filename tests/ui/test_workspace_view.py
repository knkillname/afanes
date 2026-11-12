"""Tests for the workspace shell and type-grouped browser."""

import asyncio
import datetime
import typing
from collections.abc import Callable, Coroutine
from pathlib import Path

import flet as ft
import pytest

import afanes.core.atomic
import afanes.core.search
import afanes.core.settings
import afanes.core.vault.service
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.workspace
from afanes.core.editing import DraftMode

Handler = Callable[[], Coroutine[typing.Any, typing.Any, None]]
FOUR_SECTIONS = 4


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


async def _change_vault() -> None:
    return None


async def _create_vault() -> None:
    return None


async def _close_vault() -> None:
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
    asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(tmp_path / "vault"))
    return afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, _close_vault)


def _handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_click"))


def _change_handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_change"))


class TestWorkspaceShell:
    def test_builds_capture_bar_and_browser(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(vault))
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, _close_vault)

        assert view.root.key == "workspace-view"
        assert isinstance(view.root, ft.Column)
        assert view.capture_field.label == afanes.ui.strings.COMPOSER_LABEL
        assert len(view.section_tiles) == FOUR_SECTIONS
        assert view.review_tile.title == afanes.ui.strings.REVIEW_TITLE
        assert view.page_view.empty_text.visible is True

    def test_change_menu_offers_open_create_and_close(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(vault))
        calls: list[str] = []

        async def close() -> None:
            calls.append("close")

        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, close)

        assert [item.key for item in view.change_button.items] == [
            "workspace-change-open",
            "workspace-change-create",
            "workspace-close-vault",
        ]
        assert view.change_button.items[0].content == afanes.ui.strings.CHANGE_VAULT_OPEN
        assert view.change_button.items[1].content == afanes.ui.strings.CHANGE_VAULT_CREATE
        assert view.change_button.items[2].content == afanes.ui.strings.CLOSE_VAULT_ACTION

        asyncio.run(_handler(view.change_button.items[2])())

        assert calls == ["close"]

    def test_browser_and_page_are_visible_together(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "inbox" / "Buy milk.md", body="# Buy milk")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)

        asyncio.run(scenario())
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, _close_vault)

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
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)

        asyncio.run(scenario())
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, _close_vault)
        handler = _handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.PROJECTS])

        asyncio.run(handler())

        assert state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.PROJECTS
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

        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.INBOX].value == "2"
        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.PROJECTS].value == "1"
        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.REFERENCES].value == "1"
        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.NEEDS_ATTENTION].value == "0"
        assert "3 pending" in view.review_count.value

    def test_capture_appears_only_under_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "inbox" / "Capture.md", body="# Capture")
        view = _open_workspace(tmp_path, monkeypatch)
        state = afanes.ui.state.app_state

        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.INBOX].value == "1"
        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.NEEDS_ATTENTION].value == "0"

        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.NEEDS_ATTENTION])())

        empty = view.browser_list.controls[0]
        assert isinstance(empty, ft.Container)
        content = empty.content
        assert isinstance(content, ft.Text)
        assert content.value == afanes.ui.strings.BROWSER_EMPTY
        assert state.browser.listing() is not None
        listing = state.browser.listing()
        assert listing is not None
        assert listing.group(afanes.core.search.BrowserSection.NEEDS_ATTENTION).notes == ()
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

        assert afanes.ui.state.app_state.pages.page is not None
        assert afanes.ui.state.app_state.pages.page.mode is DraftMode.RAW
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
        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.INBOX].value == "1"

    def test_empty_capture_keeps_the_field_and_reports(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        view = _open_workspace(tmp_path, monkeypatch)
        view.capture_field.value = "   "

        asyncio.run(_handler(view.capture_button)())

        assert view.capture_field.value == "   "
        assert afanes.ui.state.app_state.status.message == afanes.ui.strings.CAPTURE_EMPTY
        assert list((vault / "inbox").glob("*.md")) == []


class TestBrowserSearch:
    def test_filters_by_title(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Ada.md", note_type="reference", body="# Ada, Countess of Lovelace")
        _write_note(vault / "reference" / "Grace.md", note_type="reference", body="# Grace Hopper")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.REFERENCES])())

        view.search_field.value = "countess"
        asyncio.run(_change_handler(view.search_field)())

        titles = [control.title for control in view.browser_list.controls if isinstance(control, ft.ListTile)]
        assert titles == ["Ada, Countess of Lovelace"]

    def test_filters_by_identity_and_ignores_whitespace(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Ada, Lovelace.md", note_type="reference", body="# A person")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.REFERENCES])())

        view.search_field.value = "Ada,   Lovelace"
        asyncio.run(_change_handler(view.search_field)())

        assert afanes.ui.state.app_state.browser.query == "Ada,   Lovelace"
        titles = [control.title for control in view.browser_list.controls if isinstance(control, ft.ListTile)]
        assert titles == ["A person"]

    def test_body_only_term_lists_the_note(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Ada.md", note_type="reference", body="# Ada\n\nAnalytical engine")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.REFERENCES])())

        view.search_field.value = "analytical"
        asyncio.run(_change_handler(view.search_field)())

        assert _row_for(view.browser_list, "Ada") is not None


class TestBrowserHistory:
    def test_back_returns_to_the_previous_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        first = _write_note(vault / "reference" / "Ada.md", note_type="reference", body="# Ada")
        _write_note(vault / "reference" / "Grace.md", note_type="reference", body="# Grace")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.REFERENCES])())

        asyncio.run(_handler(_row_for(view.browser_list, "Ada"))())
        asyncio.run(_handler(_row_for(view.browser_list, "Grace"))())
        asyncio.run(view.page_view.go_back())

        assert afanes.ui.state.app_state.pages.page is not None
        assert afanes.ui.state.app_state.pages.page.path == first
        assert view.page_view.title.value == "Ada"


class TestWorkspaceRefresh:
    def test_refresh_repaints_once_and_rebuilds_the_rows(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        asyncio.run(state.workspace.choose_vault(vault))
        repaints: list[int] = []
        view = afanes.ui.views.workspace.WorkspaceView(
            lambda: repaints.append(1),
            _change_vault,
            _create_vault,
            _close_vault,
        )
        _write_note(vault / "inbox" / "External.md", body="# External")
        asyncio.run(state.workspace.refresh())
        repaints.clear()

        view.refresh()

        assert repaints == [1]
        assert _row_for(view.browser_list, "External") is not None

    def test_refresh_performs_no_file_io(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(vault))
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, _close_vault)

        def fail(*_args: object, **_kwargs: object) -> None:
            message = "the workspace refresh must not touch the filesystem"
            raise AssertionError(message)

        monkeypatch.setattr(afanes.core.vault.service.Vault, "scan", fail)
        monkeypatch.setattr(afanes.core.vault.service.Vault, "read_body", fail)
        monkeypatch.setattr(afanes.core.vault.service.Vault, "read_page", fail)
        monkeypatch.setattr(afanes.core.atomic, "write_text_atomic", fail)

        view.refresh()

        assert view.root.key == "workspace-view"


class TestDatePickerWiring:
    def test_picker_callback_reaches_the_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_note(
            vault / "projects" / "Home.md",
            note_type="project",
            status="active",
            body="# Home\n\n- [ ] Call\n",
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        chosen = datetime.date(2026, 12, 1)
        calls: list[datetime.date | None] = []

        async def pick_date(current: datetime.date | None) -> datetime.date | None:
            calls.append(current)
            return chosen

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(project)

        asyncio.run(scenario())
        view = afanes.ui.views.workspace.WorkspaceView(
            _noop,
            _change_vault,
            _create_vault,
            _close_vault,
            pick_date,
        )

        asyncio.run(view.page_view.choose_due_date())

        assert calls == [None]
        document = afanes.core.frontmatter.NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert document.due_date == chosen


def _row_for(browser: ft.ListView, title: str) -> ft.ListTile:
    return next(control for control in browser.controls if isinstance(control, ft.ListTile) and control.title == title)
