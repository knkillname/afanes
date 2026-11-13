"""Tests for the workspace shell and type-grouped browser."""

import asyncio
import datetime
import typing
from collections.abc import Callable, Coroutine
from pathlib import Path

import flet as ft
import pytest

import afanes.core.atomic
import afanes.core.log
import afanes.core.search
import afanes.core.settings
import afanes.core.vault.service
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
import afanes.ui.views.workspace
from afanes.core.editing import DraftMode
from afanes.core.log import LogMode
from afanes.models.note import NoteDate
from tests.support import ensure_vault, versioned

Handler = Callable[[], Coroutine[typing.Any, typing.Any, None]]
SECTION_COUNT = 5
TWO_ENTRIES = 2
FIRST_DAY = 1
SECOND_DAY = 2
THIRD_DAY = 3


def _today() -> datetime.date:
    return datetime.datetime.now(tz=datetime.UTC).astimezone().date()


def _other_day(today: datetime.date) -> datetime.date:
    return today.replace(day=SECOND_DAY) if today.day != SECOND_DAY else today.replace(day=THIRD_DAY)


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
    date: str | None = None,
) -> Path:
    ensure_vault(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    if status is not None:
        lines.append(f"status: {status}")
    if date is not None:
        lines.append(f"date: {date}")
    lines.extend(["---", body])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _open_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> afanes.ui.views.workspace.WorkspaceView:
    _use_settings_file(monkeypatch, tmp_path / "settings.json")
    asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(versioned(tmp_path / "vault")))
    return afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, _close_vault)


def _handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_click"))


def _freeze(control: ft.Control) -> None:
    object.__setattr__(control, "_frozen", True)


def _record_page_scroll(view: afanes.ui.views.workspace.WorkspaceView) -> list[float | None]:
    positions: list[float | None] = []

    async def recorder(*, offset: float | None = None, **_kwargs: object) -> None:
        positions.append(offset)

    object.__setattr__(view.page_view.content, "scroll_to", recorder)
    return positions


def _change_handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_change"))


def _find_control(control: ft.Control, key: str) -> ft.Control | None:
    if getattr(control, "key", None) == key:
        return control
    for child in getattr(control, "controls", []) or []:
        found = _find_control(child, key)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_control(content, key)
    return None


class TestWorkspaceShell:
    def test_builds_capture_bar_and_browser(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(vault))
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, _close_vault)

        assert view.root.key == "workspace-view"
        assert isinstance(view.root, ft.Stack)
        assert view.capture_field.hint_text == afanes.ui.strings.COMPOSER_HINT
        assert len(view.section_tiles) == SECTION_COUNT
        assert view.review_tile.title == afanes.ui.strings.REVIEW_TITLE
        assert view.page_view.empty_text.visible is True
        assert view.navigation.key == "workspace-navigation"
        assert view.browser_region.key == "workspace-browser"
        assert view.detail_region.key == "workspace-detail"

    def test_navigation_lists_destinations_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)

        assert _find_control(view.navigation, "browser-list") is None
        assert _find_control(view.navigation, "browser-search") is None
        assert _find_control(view.navigation, "review-entry") is not None
        assert _find_control(view.browser_region, "browser-list") is not None
        assert _find_control(view.browser_region, "browser-search") is not None

    def test_change_menu_offers_open_create_and_close(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
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
            "workspace-about",
        ]
        assert view.change_button.items[0].content == afanes.ui.strings.CHANGE_VAULT_OPEN
        assert view.change_button.items[1].content == afanes.ui.strings.CHANGE_VAULT_CREATE
        assert view.change_button.items[2].content == afanes.ui.strings.CLOSE_VAULT_ACTION
        assert view.change_button.items[3].content == afanes.ui.strings.ABOUT_ACTION

        asyncio.run(_handler(view.change_button.items[2])())

        assert calls == ["close"]

    def test_about_menu_item_reaches_the_host(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[str] = []

        async def about() -> None:
            calls.append("about")

        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(versioned(tmp_path / "vault")))
        view = afanes.ui.views.workspace.WorkspaceView(
            _noop,
            _change_vault,
            _create_vault,
            _close_vault,
            on_about=about,
        )

        asyncio.run(_handler(view.change_button.items[3])())

        assert calls == ["about"]

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

        assert view.navigation.visible is True
        assert view.page_view.title.value == "Buy milk"
        assert view.page_view.read_body.visible is True

    def test_surfaces_use_the_theme_stack(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        border = ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR)

        assert view.navigation.bgcolor == afanes.ui.theme.REGION_SURFACE_COLOR
        assert view.navigation.border is None
        assert view.navigation.border_radius is None
        assert view.browser_region.bgcolor == afanes.ui.theme.PAGE_SURFACE_COLOR
        assert view.browser_region.border is None
        assert isinstance(view.page_view.root, ft.Container)
        assert view.page_view.root.bgcolor == afanes.ui.theme.CARD_SURFACE_COLOR
        assert view.page_view.root.border == border

    def test_navigation_holds_the_vault_identity_and_actions(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        navigation_header = typing.cast("ft.Row", view.navigation_header.content)
        browser_header = typing.cast("ft.Row", view.browser_header.content)
        assert view.vault_text in navigation_header.controls
        assert view.change_button in navigation_header.controls
        assert view.refresh_button in browser_header.controls
        assert not hasattr(view, "status_bar")
        assert afanes.ui.strings.APP_TITLE not in _texts(view.root)

    def test_vault_identity_names_the_vault_and_keeps_the_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        root = afanes.ui.state.app_state.session.vault_root

        assert root is not None
        assert view.vault_text.value == root.name
        assert view.vault_text.tooltip == str(root)

    def test_sections_share_one_icon_tint(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        review_icon = typing.cast("ft.Icon", view.review_tile.leading)

        assert all(icon.color == afanes.ui.theme.SECTION_ICON_COLOR for icon in view.section_icons.values())
        assert review_icon.color == afanes.ui.theme.SECTION_ICON_COLOR

    def test_selection_uses_a_neutral_row_without_an_accent_edge(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        inbox = afanes.ui.state.browser.WorkspaceSection.INBOX

        assert view.section_tiles[inbox].selected is True
        assert view.section_edges[inbox].border is None
        assert view.review_edge.border is None
        assert all(edge.border is None for edge in view.section_edges.values())

        asyncio.run(_handler(view.review_tile)())

        assert view.review_tile.selected is True
        assert view.section_tiles[inbox].selected is False
        assert view.review_edge.border is None
        assert view.section_edges[inbox].border is None

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


class TestFrozenControlRecovery:
    def test_section_switch_recovers_a_frozen_entry(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        projects = afanes.ui.state.browser.WorkspaceSection.PROJECTS
        tile = view.section_tiles[projects]
        tile.selected = True
        _freeze(tile)

        asyncio.run(_handler(tile)())

        assert not hasattr(tile, "_frozen")
        assert tile.selected is True
        assert afanes.ui.state.app_state.browser.active_section is projects

    def test_refresh_recovers_a_frozen_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        projects = afanes.ui.state.browser.WorkspaceSection.PROJECTS
        tile = view.section_tiles[projects]
        tile.selected = True
        _freeze(tile)

        view.refresh()

        assert not hasattr(tile, "_frozen")
        assert tile.selected is False

    def test_refresh_recovers_a_frozen_count(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "One.md")
        view = _open_workspace(tmp_path, monkeypatch)
        count = view.section_counts[afanes.ui.state.browser.WorkspaceSection.INBOX]
        count.value = "stale"
        _freeze(count)

        view.refresh()

        assert not hasattr(count, "_frozen")
        assert count.value == "1"

    def test_refresh_leaves_outside_controls_frozen(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        outside = ft.ListTile(title="Outside")
        _freeze(outside)

        view.refresh()

        assert hasattr(outside, "_frozen")


class TestCaptureBar:
    def test_capture_creates_a_note_and_clears_the_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        view = _open_workspace(tmp_path, monkeypatch)
        view.capture_field.value = "Buy milk"

        asyncio.run(_handler(view.capture_button)())

        assert (vault / "inbox" / "Buy milk.md").is_file()
        assert view.capture_field.value == ""
        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.INBOX].value == "1"

    def test_empty_capture_keeps_the_field_and_reports(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
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
        scrolls = _record_page_scroll(view)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.REFERENCES])())

        asyncio.run(_handler(_row_for(view.browser_list, "Ada"))())
        asyncio.run(_handler(_row_for(view.browser_list, "Grace"))())
        asyncio.run(view.page_view.go_back())

        assert scrolls == [0, 0, 0]
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
        versioned(vault)
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
        versioned(vault)
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
            pick_date=pick_date,
        )

        asyncio.run(view.page_view.choose_due_date())

        assert calls == [None]
        document = afanes.core.frontmatter.NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert document.due_date == chosen


class TestBrowserCreationAction:
    def test_the_new_reference_action_is_only_in_references(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(vault))
        calls: list[str] = []

        async def new_reference() -> None:
            calls.append("new")

        view = afanes.ui.views.workspace.WorkspaceView(
            _noop,
            _change_vault,
            _create_vault,
            _close_vault,
            on_new_reference=new_reference,
        )

        assert _find_control(view.browser_actions, "browser-new-reference") is None
        section = afanes.ui.state.browser.WorkspaceSection.REFERENCES
        asyncio.run(_handler(view.section_tiles[section])())
        button = typing.cast("ft.IconButton", _find_control(view.browser_actions, "browser-new-reference"))
        assert button.tooltip == afanes.ui.strings.BROWSER_NEW_REFERENCE

        asyncio.run(_handler(button)())

        assert calls == ["new"]

    def test_the_new_reference_action_is_disabled_while_it_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(vault))
        observed: list[bool] = []

        async def new_reference() -> None:
            observed.append(view.new_reference_button.disabled)

        view = afanes.ui.views.workspace.WorkspaceView(
            _noop,
            _change_vault,
            _create_vault,
            _close_vault,
            on_new_reference=new_reference,
        )
        section = afanes.ui.state.browser.WorkspaceSection.REFERENCES
        asyncio.run(_handler(view.section_tiles[section])())

        asyncio.run(_handler(view.new_reference_button)())

        assert observed == [True]
        assert view.new_reference_button.disabled is False


class TestGlobalSearch:
    def test_results_span_every_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md", body="# Buy milk\n\nshared term")
        _write_note(
            vault / "projects" / "Launch.md",
            note_type="project",
            status="active",
            body="# Launch\n\nshared term",
        )
        _write_note(vault / "reference" / "Ada.md", note_type="reference", body="# Ada\n\nshared term")
        view = _open_workspace(tmp_path, monkeypatch)

        view.search_field.value = "shared term"
        asyncio.run(_change_handler(view.search_field)())

        titles = [control.title for control in view.browser_list.controls if isinstance(control, ft.ListTile)]
        assert set(titles) == {"Buy milk", "Launch", "Ada"}
        headings = _texts(view.browser_list)
        assert "Inbox (1)" in headings
        assert "Projects (1)" in headings
        assert "References (1)" in headings

    def test_a_match_outside_the_active_section_is_listed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Buy milk.md")
        _write_note(vault / "projects" / "Launch.md", note_type="project", status="active")
        view = _open_workspace(tmp_path, monkeypatch)

        view.search_field.value = "launch"
        asyncio.run(_change_handler(view.search_field)())

        assert afanes.ui.state.app_state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.INBOX
        assert _row_for(view.browser_list, "Launch") is not None

    def test_navigation_counts_remain_unfiltered_totals(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "One.md", body="# One\n\nterm")
        _write_note(vault / "inbox" / "Two.md", body="# Two")
        view = _open_workspace(tmp_path, monkeypatch)

        view.search_field.value = "term"
        asyncio.run(_change_handler(view.search_field)())

        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.INBOX].value == "2"

    def test_clearing_restores_the_active_destination(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "One.md", body="# One\n\nterm")
        _write_note(vault / "inbox" / "Two.md", body="# Two")
        view = _open_workspace(tmp_path, monkeypatch)
        view.search_field.value = "term"
        asyncio.run(_change_handler(view.search_field)())

        view.search_field.value = ""
        asyncio.run(_change_handler(view.search_field)())

        titles = [control.title for control in view.browser_list.controls if isinstance(control, ft.ListTile)]
        assert titles == ["Two", "One"]

    def test_switching_destinations_clears_the_query(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "One.md")
        view = _open_workspace(tmp_path, monkeypatch)
        view.search_field.value = "one"
        asyncio.run(_change_handler(view.search_field)())

        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.PROJECTS])())

        assert afanes.ui.state.app_state.browser.query == ""
        assert view.search_field.value == ""

    def test_a_miss_names_the_query(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_note(tmp_path / "vault" / "inbox" / "One.md")
        view = _open_workspace(tmp_path, monkeypatch)
        view.search_field.value = "absent"
        asyncio.run(_change_handler(view.search_field)())

        assert any("absent" in text for text in _texts(view.browser_list))
        assert afanes.ui.strings.BROWSER_NO_MATCH_QUERY.format(query="absent") in _texts(view.browser_list)


class TestCapturePlacement:
    def test_the_composer_appears_only_in_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_note(tmp_path / "vault" / "inbox" / "One.md")
        view = _open_workspace(tmp_path, monkeypatch)

        assert view.capture_row.visible is True
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.PROJECTS])())

        assert view.capture_row.visible is False

    def test_new_capture_switches_to_inbox_and_focuses(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "One.md")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.PROJECTS])())
        focused: list[str] = []

        async def record(control: ft.TextField) -> None:
            focused.append(str(control.key or ""))

        monkeypatch.setattr(ft.TextField, "focus", record)

        asyncio.run(_handler(view.new_capture_button)())

        assert afanes.ui.state.app_state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.INBOX
        assert view.capture_row.visible is True
        assert focused == ["workspace-capture-field"]

    def test_capture_is_the_only_suggested_action(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_note(tmp_path / "vault" / "inbox" / "One.md")
        view = _open_workspace(tmp_path, monkeypatch)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.REFERENCES])())

        assert isinstance(view.capture_button, ft.FilledButton)
        assert not isinstance(view.new_reference_button, ft.FilledButton)
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.LOG])())
        assert view.log_today_button is not None
        assert not isinstance(view.log_today_button, ft.FilledButton)


class TestReviewQueue:
    def _open_review(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> afanes.ui.views.workspace.WorkspaceView:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "One.md")
        _write_note(vault / "inbox" / "Two.md")
        _write_note(vault / "projects" / "Launch.md", note_type="project", status="active")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.review.start()

        asyncio.run(scenario())
        return afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault, _create_vault, _close_vault)

    def _queue_titles(self, view: afanes.ui.views.workspace.WorkspaceView) -> list[str]:
        return [str(control.title) for control in view.browser_list.controls if isinstance(control, ft.ListTile)]

    def test_the_queue_follows_the_session_order(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = self._open_review(tmp_path, monkeypatch)
        session = afanes.ui.state.app_state.review.review_session

        assert session is not None
        assert self._queue_titles(view) == [self._review_title(item) for item in session.items]
        assert self._queue_titles(view)[0] == "Two"

    def test_the_current_item_is_marked(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = self._open_review(tmp_path, monkeypatch)
        rows = [control for control in view.browser_list.controls if isinstance(control, ft.ListTile)]

        assert rows[0].selected is True
        assert not any(row.selected for row in rows[1:])

        asyncio.run(afanes.ui.state.app_state.review.skip())
        view.refresh()
        rows = [control for control in view.browser_list.controls if isinstance(control, ft.ListTile)]

        assert rows[0].selected is False
        assert rows[1].selected is True

    def test_new_work_waits_for_the_next_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = self._open_review(tmp_path, monkeypatch)
        before = self._queue_titles(view)
        state = afanes.ui.state.app_state
        _write_note(tmp_path / "vault" / "inbox" / "Later.md")

        async def scenario() -> None:
            await state.workspace.refresh()

        asyncio.run(scenario())
        view.refresh()

        assert self._queue_titles(view) == before

    def test_a_completed_session_marks_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = self._open_review(tmp_path, monkeypatch)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            session = state.review.review_session
            assert session is not None
            for _ in session.items:
                await state.review.skip()

        asyncio.run(scenario())
        view.refresh()
        rows = [control for control in view.browser_list.controls if isinstance(control, ft.ListTile)]

        assert rows
        assert not any(row.selected for row in rows)

    @staticmethod
    def _review_title(item: afanes.core.search.ReviewItem) -> str:
        if item.step is not None:
            return item.step.text
        if item.project is not None:
            return item.project.note.title
        note = next(
            (candidate for candidate in afanes.ui.state.app_state.session.notes if candidate.path == item.path),
            None,
        )
        return note.title if note is not None else item.path.stem


class TestAdaptiveLayout:
    def test_a_wide_window_shows_three_regions(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)

        view.resize(afanes.ui.theme.SHELL_WIDE_MIN)

        assert view.shell_row.controls == [view.navigation, view.browser_region, view.detail_region]
        assert view.nav_toggle.visible is False
        assert view.drawer_close_button.visible is False
        assert view.navigation.border is None
        assert view.navigation.border_radius is None
        assert view.navigation.shadow is None
        assert view.navigation.padding is None
        assert view.navigation.left is None
        assert view.navigation.width == afanes.ui.theme.NAVIGATION_WIDTH

    def test_a_medium_window_keeps_browser_and_detail(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)

        view.resize(afanes.ui.theme.SHELL_MEDIUM_MIN)

        assert view.shell_row.controls == [view.browser_region, view.detail_region]
        assert view.nav_toggle.visible is True
        assert view.drawer_close_button.visible is True
        assert view.navigation.border is not None
        assert view.navigation.border_radius == afanes.ui.theme.SURFACE_RADIUS
        assert view.navigation.shadow == afanes.ui.theme.DRAWER_SHADOW
        assert view.navigation.padding == afanes.ui.theme.ITEM_GAP
        assert view.navigation.left == afanes.ui.theme.PAGE_PADDING
        assert view.navigation.width == afanes.ui.theme.DRAWER_WIDTH

    def test_a_narrow_presentation_starts_with_the_browser(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        view = _open_workspace(tmp_path, monkeypatch)

        view.resize(afanes.ui.theme.SHELL_MEDIUM_MIN - 1)

        assert view.shell_row.controls == [view.browser_region]
        assert view.browser_region.expand is True

    def test_a_narrow_presentation_opens_and_returns_from_the_detail(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "One.md", body="# One")
        view = _open_workspace(tmp_path, monkeypatch)
        view.resize(afanes.ui.theme.SHELL_MEDIUM_MIN - 1)
        _record_page_scroll(view)

        asyncio.run(_handler(_row_for(view.browser_list, "One"))())

        assert view.shell_row.controls == [view.detail_region]
        assert view.page_view.back_button.disabled is False

        asyncio.run(view.page_view.go_back())

        assert view.shell_row.controls == [view.browser_region]

    def test_a_resize_preserves_the_page_destination_and_query(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "inbox" / "One.md")
        view = _open_workspace(tmp_path, monkeypatch)
        _record_page_scroll(view)
        asyncio.run(_handler(_row_for(view.browser_list, "One"))())
        asyncio.run(afanes.ui.state.app_state.browser.set_query("one"))
        view.refresh()

        view.resize(afanes.ui.theme.SHELL_MEDIUM_MIN - 1)
        view.resize(afanes.ui.theme.SHELL_WIDE_MIN)

        state = afanes.ui.state.app_state
        assert state.browser.active_section is afanes.ui.state.browser.WorkspaceSection.INBOX
        assert state.browser.query == "one"
        assert state.pages.page is not None
        assert state.pages.page.path == note

    def test_the_drawer_exposes_the_navigation_and_closes_on_selection(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        view.resize(afanes.ui.theme.SHELL_MEDIUM_MIN)

        asyncio.run(_handler(view.nav_toggle)())

        drawer = next(control for control in view.root.controls if getattr(control, "key", None) == "workspace-drawer")
        assert view.navigation in typing.cast("ft.Stack", drawer).controls

        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.PROJECTS])())

        assert view.root.controls == [view.shell_column]

    def test_escape_closes_the_drawer(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        view.resize(afanes.ui.theme.SHELL_MEDIUM_MIN)
        asyncio.run(_handler(view.nav_toggle)())

        view.close_drawer()

        assert view.root.controls == [view.shell_column]

    def test_the_drawer_close_button_closes_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view = _open_workspace(tmp_path, monkeypatch)
        view.resize(afanes.ui.theme.SHELL_MEDIUM_MIN)
        asyncio.run(_handler(view.nav_toggle)())

        asyncio.run(_handler(view.drawer_close_button)())

        assert view.root.controls == [view.shell_column]


def _row_for(browser: ft.ListView, title: str) -> ft.ListTile:
    return next(control for control in browser.controls if isinstance(control, ft.ListTile) and control.title == title)


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    if isinstance(control, ft.Text):
        values.append(str(control.value))
    for child in getattr(control, "controls", []) or []:
        values.extend(_texts(child))
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        values.extend(_texts(content))
    return values


class TestLogSection:
    def _log_path(self, vault: Path, date: datetime.date, title: str) -> Path:
        return _write_note(
            vault / "log" / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.isoformat()}.md",
            note_type="log",
            body=f"# {title}\n",
            date=date.isoformat(),
        )

    def _open_log(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        on_log_entry: Callable[[NoteDate], Coroutine[typing.Any, typing.Any, None]] | None = None,
    ) -> afanes.ui.views.workspace.WorkspaceView:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(versioned(tmp_path / "vault")))
        view = afanes.ui.views.workspace.WorkspaceView(
            _noop,
            _change_vault,
            _create_vault,
            _close_vault,
            on_log_entry=on_log_entry,
        )
        asyncio.run(_handler(view.section_tiles[afanes.ui.state.browser.WorkspaceSection.LOG])())
        return view

    def test_log_section_builds_calendar_and_tree(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        today = _today()
        self._log_path(vault, today, "Today")
        view = self._open_log(tmp_path, monkeypatch)

        assert view.log_calendar is not None
        assert view.log_tree is not None
        assert view.log_today_button is not None
        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.LOG].value == "1"
        assert view.log_calendar.day_buttons[today.day].data["count"] == 1

    def test_calendar_day_opens_a_single_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        today = _today()
        self._log_path(vault, today, "Today")
        view = self._open_log(tmp_path, monkeypatch)
        _record_page_scroll(view)

        asyncio.run(view.open_log_day(today.day))

        assert afanes.ui.state.app_state.pages.page is not None
        assert (
            afanes.ui.state.app_state.pages.page.path
            == vault / "log" / f"{today.year:04d}" / f"{today.month:02d}" / f"{today.isoformat()}.md"
        )

    def test_empty_calendar_day_requests_creation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        requested: list[NoteDate] = []

        async def on_log_entry(date: NoteDate) -> None:
            requested.append(date)

        view = self._open_log(tmp_path, monkeypatch, on_log_entry=on_log_entry)
        today = _today()

        asyncio.run(view.open_log_day(FIRST_DAY))

        assert requested == [NoteDate.from_text(f"{today.year:04d}-{today.month:02d}-01")]

    def test_today_button_requests_today(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        requested: list[NoteDate] = []

        async def on_log_entry(date: NoteDate) -> None:
            requested.append(date)

        view = self._open_log(tmp_path, monkeypatch, on_log_entry=on_log_entry)

        asyncio.run(view.open_today_log())

        assert requested == [NoteDate.from_date(_today())]

    def test_mode_switch_changes_the_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        view = self._open_log(tmp_path, monkeypatch)

        asyncio.run(view.show_log_mode("everything"))

        assert afanes.ui.state.app_state.browser.log_mode is LogMode.EVERYTHING

    def test_search_filters_the_calendar_and_tree(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        today = _today()
        self._log_path(vault, today, "Dentist")
        other = today.replace(day=1) if today.day != 1 else today.replace(day=2)
        self._log_path(vault, other, "Groceries")
        view = self._open_log(tmp_path, monkeypatch)

        asyncio.run(afanes.ui.state.app_state.browser.set_query("dentist"))
        view.refresh()

        tree = view.log_tree
        calendar = view.log_calendar
        assert tree is not None
        assert calendar is not None
        assert [note.title for note in tree.note_rows.values()] == ["Dentist"]
        assert calendar.day_buttons[today.day].data["count"] == 1
        assert calendar.day_buttons[other.day].data["count"] == 0

    def test_clearing_the_query_restores_the_tree_and_calendar(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        today = _today()
        self._log_path(vault, today, "Dentist")
        other = today.replace(day=1) if today.day != 1 else today.replace(day=2)
        self._log_path(vault, other, "Groceries")
        view = self._open_log(tmp_path, monkeypatch)
        asyncio.run(afanes.ui.state.app_state.browser.set_query("dentist"))
        view.refresh()

        asyncio.run(afanes.ui.state.app_state.browser.set_query(""))
        view.refresh()

        tree = view.log_tree
        calendar = view.log_calendar
        assert tree is not None
        assert calendar is not None
        titles = [note.title for note in tree.note_rows.values()]
        assert len(titles) == TWO_ENTRIES
        assert "Dentist" in titles
        assert "Groceries" in titles
        assert calendar.day_buttons[today.day].data["count"] == 1
        assert calendar.day_buttons[other.day].data["count"] == 1

    def test_month_plus_requests_a_month_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        today = _today()
        self._log_path(vault, today, "Today")
        requested: list[NoteDate] = []

        async def on_log_entry(date: NoteDate) -> None:
            requested.append(date)

        view = self._open_log(tmp_path, monkeypatch, on_log_entry=on_log_entry)

        asyncio.run(view.open_log_month(today.year, today.month))

        assert requested == [NoteDate.from_text(f"{today.year:04d}-{today.month:02d}")]

    def test_tree_refreshes_after_a_new_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        view = self._open_log(tmp_path, monkeypatch)
        today = _today()
        self._log_path(vault, today, "New")

        asyncio.run(afanes.ui.state.app_state.workspace.refresh())
        view.refresh()

        assert view.section_counts[afanes.ui.state.browser.WorkspaceSection.LOG].value == "1"

    def test_back_returns_to_the_previous_log_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        today = _today()
        first = self._log_path(vault, today, "First")
        second = self._log_path(vault, _other_day(today), "Second")
        view = self._open_log(tmp_path, monkeypatch)
        scrolls = _record_page_scroll(view)

        async def scenario() -> None:
            await view.open_note(first)
            await view.open_note(second)
            await afanes.ui.state.app_state.navigation.back()

        asyncio.run(scenario())

        assert scrolls == [0, 0]
        assert afanes.ui.state.app_state.pages.page is not None
        assert afanes.ui.state.app_state.pages.page.path == first
