"""Tests for the read, edit, raw rescue, and confirmation page controls."""

import asyncio
import datetime
import typing
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.core.template_cards
import afanes.core.vault.service
import afanes.core.vault.trash_catalog
import afanes.ui.state
import afanes.ui.state.browser
import afanes.ui.state.controller
import afanes.ui.state.status
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.editing import DraftMode
from afanes.core.frontmatter import NoteDocument
from afanes.core.steps import StepDocument
from afanes.models.link import ReferenceScheme
from afanes.models.note import NoteDate, NoteType
from afanes.ui.views.page import PageActions, PageView
from tests.support import constant, ensure_vault, versioned
from tests.ui.control_tree import emphasis_controls
from tests.ui.test_conformance import HEADER_ACTION_KEYS

TWO_CANDIDATES = 2
FOUR_SUBSECTIONS = 4
STARTER_OPTION_COUNT = 2
PAGE_MENU_ITEM_COUNT = 4


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(constant(path)))


def _write_note(path: Path, content: str) -> Path:
    ensure_vault(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _note_text(body: str) -> str:
    return f"---\ntype: note\n---\n{body}"


def _typed_note(note_type: str, body: str, *, category: str | None = None, extra: str = "") -> str:
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    if extra:
        lines.append(extra)
    lines.extend(["---", body])
    return "\n".join(lines)


def _action_labels(panel: ft.Container) -> list[str]:
    content = panel.content
    assert isinstance(content, ft.Column)
    row = content.controls[-1]
    assert isinstance(row, ft.Row)
    return [str(getattr(control, "content", "")) for control in row.controls]


class TestReadMode:
    def test_read_mode_shows_title_path_and_body(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))

        assert view.title.value == "Ada"
        assert view.path.value == "notes/Ada.md"
        assert view.read_body.visible is True
        assert view.read_body.value == "# Ada\n\nBody.\n"
        assert view.edit_form.visible is False
        assert view.raw_panel.visible is False
        assert view.edit_button.visible is True
        assert view.done_button.visible is False

    def test_empty_page_shows_the_placeholder(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert view.empty_text.visible is True
        assert view.read_body.visible is False
        assert view.edit_form.visible is False
        assert view.raw_panel.visible is False

    def test_scroll_to_top_tolerates_an_unattached_pane(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        asyncio.run(view.scroll_to_top())

        assert view.content.expand is True

    def test_link_tap_forwards_the_destination(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))
        scrolls = _record_scroll(view)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            event = ft.Event(name="tap", control=ft.Markdown(), data="note:Ada")
            await view.handle_link(event)

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.path == person.resolve()
        assert scrolls == [0]

    def test_edit_mode_preserves_project_task_list_lines(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        body = "# Launch\n\n- [ ] Write copy\n- [x] Done\n"
        path = _write_note(vault / "projects" / "Launch.md", _typed_note("project", body))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert view.body_field.value == body

    def test_edit_button_switches_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert state.pages.editing is True
        assert view.edit_form.visible is True
        assert view.read_body.visible is False
        assert view.done_button.visible is True
        assert view.content.visible is False
        assert view.edit_form.expand is True
        assert view.body_field.expand is True
        assert view.body_field.fit_parent_size is True
        assert view.body_field.min_lines is None
        assert view.body_field.max_lines is None
        assert view.body_field.text_vertical_align == ft.VerticalAlignment.START

    def test_invalid_category_shows_inline_without_a_notice(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "reference" / "Ada.md", _typed_note("reference", "# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.category_field.value = "people/uk"
            await view.change_category()

        asyncio.run(scenario())

        assert view.category_error.visible is True
        assert view.category_error.value == afanes.ui.strings.PAGE_CATEGORY_INVALID
        assert state.status.notice is None

    def test_blank_rename_shows_inline_without_a_notice(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.begin_rename()
            view.rename_field.value = "   "
            await view.preview_rename()

        asyncio.run(scenario())

        assert view.rename_error.visible is True
        assert view.rename_error.value == afanes.ui.strings.PAGE_RENAME_LABEL
        assert state.status.notice is None

    def test_category_combobox_suggests_existing_labels(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(
            vault / "reference" / "places" / "Office.md",
            _typed_note("reference", "# Office\n", category="place"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert isinstance(view.category_field, ft.Dropdown)
        assert view.category_field.editable is True
        assert view.category_field.enable_filter is True
        assert [option.key for option in view.category_field.options] == ["person", "place"]

    def test_category_combobox_has_no_suggestions_without_labeled_references(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "reference" / "Ada.md", _typed_note("reference", "# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert view.category_field.options == []
        assert view.category_field.value == ""

    def test_back_button_returns_to_the_previous_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))
        scrolls = _record_scroll(view)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(first)
            await state.navigation.open_page(second)
            view.refresh()
            await view.go_back()

        asyncio.run(scenario())

        assert scrolls == [0]
        assert state.pages.page is not None
        assert state.pages.page.path == first.resolve()
        assert view.title.value == "First"


class TestEditMode:
    def test_edit_mode_renders_the_body_and_labels(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(
            vault / "projects" / "Call.md",
            _typed_note(
                "project",
                "# Call Ada\nBody.\n",
                extra="status: waiting\ndue_date: 2026-01-02",
            ),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert view.body_field.value == "# Call Ada\nBody.\n"
        assert view.type_dropdown.value == "project"
        assert view.category_field.visible is False
        assert view.status_dropdown.visible is True
        assert view.status_dropdown.value == "waiting"
        assert view.due_field.visible is True
        assert view.due_field.value == "2026-01-02"
        assert "Call" in view.identity_text.value
        assert view.type_dropdown.height == afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT
        assert view.date_field.height == afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT
        assert view.owner_field.height == afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT
        assert view.edit_form.spacing == afanes.ui.theme.SECTION_GAP
        assert view.form_fields.row.columns == afanes.ui.theme.FIELD_FLOW_COLUMNS
        assert view.form_fields.row.controls == [
            view.type_dropdown,
            view.category_field,
            view.status_dropdown,
            view.date_field,
            view.log_starter_picker.dropdown,
            view.due_field,
            view.owner_field,
            view.asked_by_field,
        ]
        assert view.mode_host.fit == ft.StackFit.EXPAND
        assert view.mode_host.controls == [view.content, view.edit_form, view.raw_panel]

    def test_asked_by_field_renders_for_projects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(
            vault / "projects" / "Call.md",
            _typed_note("project", "# Call Ada\nBody.\n", extra="asked_by: Priya Nair"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert view.asked_by_field.visible is True
        assert view.asked_by_field.value == "Priya Nair"

    @pytest.mark.parametrize("note_type", ["reference", "note"])
    def test_asked_by_field_is_hidden_for_non_projects(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        note_type: str,
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _typed_note(note_type, "# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert view.asked_by_field.visible is False

    def test_asked_by_change_forwards_to_the_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.asked_by_field.value = "Priya Nair"
            await view.change_asked_by()

        asyncio.run(scenario())

        page = state.pages.page
        assert page is not None
        assert page.labels is not None
        assert page.labels.asked_by_text == "Priya Nair"

    def test_owner_field_renders_for_projects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(
            vault / "projects" / "Call.md",
            _typed_note("project", "# Call Ada\nBody.\n", extra="owner: Sam Rivera"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert view.owner_field.visible is True
        assert view.owner_field.value == "Sam Rivera"

    @pytest.mark.parametrize("note_type", ["reference", "note"])
    def test_owner_field_is_hidden_for_non_projects(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        note_type: str,
    ) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _typed_note(note_type, "# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert view.owner_field.visible is False

    def test_owner_change_forwards_to_the_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.owner_field.value = "Sam Rivera"
            await view.change_owner()

        asyncio.run(scenario())

        page = state.pages.page
        assert page is not None
        assert page.labels is not None
        assert page.labels.owner_text == "Sam Rivera"

    def test_owner_field_suggests_vault_names(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _write_note(
            vault / "reference" / "person" / "Sam Rivera.md",
            _typed_note("reference", "# Sam Rivera\n", category="person"),
        )
        path = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.owner_field.value = "Sam"
            await view.change_owner()

        asyncio.run(scenario())

        assert view.name_suggestions.visible is True
        tiles = [control for control in view.name_suggestions.controls if isinstance(control, ft.ListTile)]
        assert [tile.title for tile in tiles] == ["Sam Rivera"]

        asyncio.run(typing.cast("typing.Any", tiles[0].on_click)())

        assert view.owner_field.value == "Sam Rivera"
        page = state.pages.page
        assert page is not None
        assert page.labels is not None
        assert page.labels.owner_text == "Sam Rivera"

    def test_asked_by_field_suggests_vault_names(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _write_note(
            vault / "reference" / "person" / "Priya Nair.md",
            _typed_note("reference", "# Priya Nair\n", category="person"),
        )
        path = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.asked_by_field.value = "Pri"
            await view.change_asked_by()

        asyncio.run(scenario())

        assert view.name_suggestions.visible is True
        tiles = [control for control in view.name_suggestions.controls if isinstance(control, ft.ListTile)]
        assert [tile.title for tile in tiles] == ["Priya Nair"]

    def test_owner_field_accepts_free_text(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.owner_field.value = "New Person"
            await view.change_owner()

        asyncio.run(scenario())

        assert view.name_suggestions.visible is False
        page = state.pages.page
        assert page is not None
        assert page.labels is not None
        assert page.labels.owner_text == "New Person"

    def test_status_options_follow_the_type(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        keys = {option.key for option in view.status_dropdown.options}
        assert keys == {"", "later", "archived"}

    def test_body_change_forwards_to_the_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.body_field.value = "# Ada\n\nChanged.\n"
            await view.change_body()

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.body == "# Ada\n\nChanged.\n"
        assert state.pages.page.is_dirty is True

    def test_invalid_due_date_is_shown_inline(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.due_field.value = "January"
            await view.change_due_date()

        asyncio.run(scenario())

        assert view.due_error.visible is True
        assert view.due_error.value

    def test_category_change_previews_and_moves_the_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(
            vault / "reference" / "Ada.md",
            _typed_note("reference", "# Ada\n"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.category_field.value = "person"
            await view.change_category()
            assert view.category_move_panel.visible is True
            assert "reference/person" in view.category_move_text.value
            await view.confirm_category_move()

        asyncio.run(scenario())

        moved = vault / "reference" / "person" / "Ada.md"
        assert moved.is_file()
        assert not path.exists()
        assert state.pages.page is not None
        assert state.pages.page.labels is not None
        assert state.pages.page.labels.category is not None
        assert state.pages.page.labels.category.value == "person"

    def test_type_change_opens_the_confirmation_panel(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)
            view.refresh()
            await view.start_edit()
            view.type_dropdown.value = "project"
            await view.change_type()
            assert view.type_change_panel.visible is True
            assert state.dialogs.pending_labels is not None
            await view.confirm_type_change()

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.labels is not None
        assert state.pages.page.labels.note_type is NoteType.PROJECT
        assert view.type_change_panel.visible is False

    def test_cancelling_a_type_change_keeps_the_original(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Ref.md", _note_text("[Ada](<note:Ada>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)
            view.refresh()
            await view.start_edit()
            view.type_dropdown.value = "project"
            await view.change_type()
            await view.cancel_type_change()

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.labels is not None
        assert state.pages.page.labels.scheme is ReferenceScheme.NOTE
        assert view.type_change_panel.visible is False


class TestRawMode:
    def test_raw_mode_renders_the_warning_and_editor(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_failure(Path("reference/Broken.md"))
            view.refresh()

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.mode is DraftMode.RAW
        assert view.raw_panel.visible is True
        assert view.raw_field.value == "---\ntype: refrence\n---\nBody\n"
        assert view.raw_warning.value
        assert view.edit_form.visible is False
        assert view.content.visible is False
        assert view.raw_panel.expand is True
        assert view.raw_field.expand is True
        assert view.raw_field.fit_parent_size is True
        assert view.raw_field.min_lines is None
        assert view.raw_field.max_lines is None
        assert view.raw_field.text_vertical_align == ft.VerticalAlignment.START

    def test_raw_save_upgrades_the_view(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))
        fixed = "---\ntype: note\n---\n\n# Fixed\nBody.\n"

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_failure(Path("reference/Broken.md"))
            view.refresh()
            view.raw_field.value = fixed
            await view.save_raw()

        asyncio.run(scenario())

        assert state.pages.page is not None
        assert state.pages.page.mode is DraftMode.NORMAL
        assert view.raw_panel.visible is False
        assert view.edit_form.visible is True


class TestPanels:
    def test_the_page_menu_stays_small_and_has_no_close_action(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert len(view.menu_button.items) == PAGE_MENU_ITEM_COUNT
        assert all(item.content not in (afanes.ui.strings.CLOSE_ACTION, "Done") for item in view.menu_button.items)

    def test_inline_confirmation_panels_remain_inline(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert isinstance(view.dialogs, ft.Column)
        assert all(isinstance(panel, ft.Container) for panel in view.dialogs.controls)

    def test_page_banner_renders_the_page_conflict(self) -> None:
        afanes.ui.state.app_state.pages.conflict = "changed"

        view = PageView(PageActions(update=lambda: None))

        assert view.banners.visible is True
        assert len(view.banners.controls) == 1

    def test_panels_use_the_container_surface(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert view.conflict_panel.bgcolor == afanes.ui.theme.SURFACE_CONTAINER_COLOR
        assert view.conflict_panel.border_radius == afanes.ui.theme.SURFACE_RADIUS

    def test_trash_is_available_from_the_page_menu(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert view.trash_item.content == afanes.ui.strings.PAGE_TRASH
        assert view.trash_item.key == "page-trash"
        assert view.menu_button.icon == ft.Icons.MORE_VERT_OUTLINED

    def test_conflict_panel_offers_reload_and_overwrite(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.body_field.value = "# Ada\n\nMy edit.\n"
            await view.change_body()
            path.write_text(_note_text("# Ada\n\nExternal.\n"), encoding="utf-8", newline="\n")
            await state.pages.autosave()
            view.refresh()
            assert view.conflict_panel.visible is True
            assert view.reload_button.visible is True
            assert view.overwrite_button.visible is True
            assert view.recreate_button.visible is False
            await view.overwrite_page()

        asyncio.run(scenario())

        assert state.pages.conflict is None
        assert view.conflict_panel.visible is False

    def test_missing_conflict_offers_recreate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()
            view.body_field.value = "# Ada\n\nMy edit.\n"
            await view.change_body()
            path.unlink()
            await state.pages.autosave()
            view.refresh()
            assert view.recreate_button.visible is True
            await view.recreate_page()

        asyncio.run(scenario())

        assert path.exists()
        assert state.pages.conflict is None

    def test_ambiguity_picker_lists_and_opens_candidates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        second = _write_note(
            vault / "notes" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))
        scrolls = _record_scroll(view)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Ada")
            view.refresh()
            assert view.ambiguous_panel.visible is True
            assert len(view.ambiguous_list.controls) == TWO_CANDIDATES
            tile = view.ambiguous_list.controls[0]
            assert isinstance(tile, ft.ListTile)
            assert tile.on_click is not None
            handler = typing.cast("typing.Any", tile.on_click)
            await handler()

        asyncio.run(scenario())

        assert scrolls == [0]
        assert state.navigation.ambiguous == ()
        assert state.pages.page is not None
        assert state.pages.page.path in {first.resolve(), second.resolve()}
        assert view.ambiguous_panel.visible is False

    def test_repair_panel_rewrites_the_links(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.follow_link("note:Q1: Planning?")
            view.refresh()
            await state.pages.set_page_body("# Q1: Planning?\n\nDraft.\n")
            await state.pages.autosave()
            view.refresh()
            assert view.repair_panel.visible is True
            assert view.repair_text.value
            await view.rewrite_links()

        asyncio.run(scenario())

        assert "note:Q1 Planning" in source.read_text(encoding="utf-8")
        assert view.repair_panel.visible is False

    def test_rename_panel_previews_and_confirms(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        note = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)
            view.refresh()
            await view.begin_rename()
            assert view.rename_panel.visible is True
            view.rename_field.value = "Ada King"
            await view.preview_rename()
            assert view.rename_preview_text.value
            assert view.rename_confirm_button.visible is True
            await view.confirm_rename()

        asyncio.run(scenario())

        assert (vault / "notes" / "Ada King.md").exists()
        assert view.rename_panel.visible is False

    def test_trash_moves_immediately_and_offers_undo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        note = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)
            view.refresh()
            await view.trash_page()

        asyncio.run(scenario())

        assert not note.exists()
        trashed = afanes.core.vault.trash_catalog.TrashCatalog(afanes.core.vault.service.Vault(vault)).load()
        assert trashed.count == 1
        assert trashed.entries[0].birthplace == Path("notes/Ada.md")
        assert state.pages.page is None
        notice = state.status.take_notice()
        assert notice is not None
        assert notice.message == afanes.ui.strings.PAGE_TRASH_MOVED
        assert notice.action is afanes.ui.state.status.NoticeAction.UNDO_TRASH

    def test_log_page_hides_rename_and_keeps_trash(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        note = _write_note(
            vault / "log" / "2025" / "10" / "2025-10-12.md",
            _typed_note("log", "# A quiet Tuesday\n", extra="date: 2025-10-12"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)
            view.refresh()

        asyncio.run(scenario())

        assert view.rename_item.visible is False
        assert view.trash_item.visible is True


class TestSteps:
    def _project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> tuple[Path, afanes.ui.state.controller.AppState]:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "projects" / "Home.md",
            _typed_note(
                "project",
                "# Home\n\n- [ ] Call <!-- {owners: [Ada], plan: 2026-11-20, actual: 2026-11-14, tags: [phone]} -->\n",
            ),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        return path, state

    def test_steps_render_as_rows_and_hide_the_comment(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)

        view = PageView(PageActions(update=lambda: None))
        texts = _texts(view.project_body.root)

        assert view.project_body.root.visible is True
        assert view.read_body.visible is False
        assert "Call" in texts
        assert afanes.ui.strings.PAGE_STEP_OWNERS_LABEL in texts
        assert "Ada" in texts
        assert afanes.ui.strings.PAGE_STEP_PLAN.format(date="2026-11-20") in texts
        assert afanes.ui.strings.PAGE_STEP_ACTUAL.format(date="2026-11-14") in texts
        assert afanes.ui.strings.PAGE_STEP_TAGS.format(tags="phone") in texts
        assert "<!--" not in " ".join(texts)

    def test_ticking_a_step_rewrites_only_its_line(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        checkbox = _find_checkbox(view.project_body.root)
        assert isinstance(checkbox, ft.Checkbox)
        checkbox.value = True

        asyncio.run(typing.cast("typing.Any", checkbox.on_change)(ft.Event(name="change", control=checkbox)))

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        step = StepDocument(document.body).steps[0]
        assert step.checked is True
        assert step.actual == datetime.datetime.now(tz=datetime.UTC).astimezone().date()
        assert step.plan == datetime.date(2026, 11, 20)
        assert step.owners == ("Ada",)

    def test_unticking_removes_the_actual_date(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = _write_note(
            tmp_path / "vault" / "projects" / "Home.md",
            _typed_note("project", "# Home\n\n- [x] Call <!-- {plan: 2026-11-20, actual: 2026-11-14} -->\n"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(versioned(tmp_path / "vault"))
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))
        checkbox = _find_checkbox(view.project_body.root)
        assert isinstance(checkbox, ft.Checkbox)
        checkbox.value = False

        asyncio.run(typing.cast("typing.Any", checkbox.on_change)(ft.Event(name="change", control=checkbox)))

        step = StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]
        assert step.checked is False
        assert step.actual is None
        assert step.plan == datetime.date(2026, 11, 20)


class TestProjectMeta:
    def _project(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        due_date: str | None = "2026-12-01",
        asked_by: str | None = None,
        owner: str | None = None,
    ) -> tuple[Path, afanes.ui.state.controller.AppState]:
        vault = tmp_path / "vault"
        extra = "status: waiting" + (f"\ndue_date: {due_date}" if due_date else "")
        if asked_by is not None:
            extra += f"\nasked_by: {asked_by}"
        if owner is not None:
            extra += f"\nowner: {owner}"
        path = _write_note(
            vault / "projects" / "Home.md",
            _typed_note("project", "# Home\n\n- [ ] Call\n", extra=extra),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        return path, state

    def test_project_meta_row_shows_status_and_due_date(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)

        view = PageView(PageActions(update=lambda: None))

        assert view.meta_row.visible is True
        assert view.meta_status.value == afanes.ui.strings.PROJECT_STATUS.format(status="Waiting")
        assert view.meta_due.value == afanes.ui.strings.PROJECT_DUE.format(date="2026-12-01")
        assert view.meta_due_clear.visible is True
        assert view.edit_form.visible is False

    def test_project_without_due_date_offers_the_action(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch, due_date=None)

        view = PageView(PageActions(update=lambda: None))

        assert view.meta_row.visible is True
        assert view.meta_due.value == afanes.ui.strings.PAGE_PROJECT_NO_DUE
        assert view.meta_due_clear.visible is False

    def test_project_meta_row_shows_the_requester(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch, asked_by="Priya Nair")

        view = PageView(PageActions(update=lambda: None))

        assert view.meta_asked.visible is True
        assert _spans_text(view.meta_asked) == "Asked by Priya Nair"

    def test_project_meta_row_shows_the_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch, owner="Sam Rivera")

        view = PageView(PageActions(update=lambda: None))

        assert view.meta_owner.visible is True
        assert _spans_text(view.meta_owner) == "Owner Sam Rivera"

    def test_owner_is_shown_before_the_requester(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch, owner="Sam Rivera", asked_by="Priya Nair")

        view = PageView(PageActions(update=lambda: None))

        controls = list(view.meta_row.controls)
        assert controls.index(view.meta_owner) < controls.index(view.meta_asked)

    def test_project_without_an_owner_omits_the_label(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)

        view = PageView(PageActions(update=lambda: None))

        assert view.meta_owner.visible is False
        assert view.meta_owner.spans == []

    def test_owner_action_icon_sets_the_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        calls: list[tuple[str, str | None]] = []

        async def pick(role: str, current: str | None) -> str | None:
            calls.append((role, current))
            return "Grace Hopper"

        view = PageView(PageActions(update=lambda: None, pick_role=pick))

        asyncio.run(view.choose_owner())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.owner == "Grace Hopper"
        assert calls == [("owner", None)]
        assert state.pages.editing is False

    def test_owner_action_icon_clears_the_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch, owner="Sam Rivera")

        async def pick(_role: str, _current: str | None) -> str | None:
            return ""

        view = PageView(PageActions(update=lambda: None, pick_role=pick))

        asyncio.run(view.choose_owner())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.owner is None

    def test_asked_by_action_icon_sets_the_requester(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch)
        calls: list[tuple[str, str | None]] = []

        async def pick(role: str, current: str | None) -> str | None:
            calls.append((role, current))
            return "Priya Nair"

        view = PageView(PageActions(update=lambda: None, pick_role=pick))

        asyncio.run(view.choose_asked_by())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.asked_by == "Priya Nair"
        assert calls == [("asked_by", None)]

    def test_role_action_icons_are_visible_only_for_projects(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        note = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        self._project(tmp_path, monkeypatch)
        project_view = PageView(PageActions(update=lambda: None))
        assert project_view.meta_owner_button.visible is True
        assert project_view.meta_asked_button.visible is True

        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.navigation.open_page(note)

        asyncio.run(scenario())
        note_view = PageView(PageActions(update=lambda: None))

        assert note_view.meta_owner_button.visible is False
        assert note_view.meta_asked_button.visible is False

    def test_owner_name_opens_its_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        person = _write_note(
            vault / "reference" / "people" / "Sam Rivera.md",
            _typed_note("reference", "# Sam Rivera\n", category="person"),
        )
        project = _write_note(
            vault / "projects" / "Home.md",
            _typed_note("project", "# Home\n", extra="owner: Sam Rivera"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(project)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))
        scrolls = _record_scroll(view)
        name_span = (view.meta_owner.spans or [])[1]

        asyncio.run(typing.cast("typing.Any", name_span.on_click)())

        assert scrolls == [0]
        assert state.pages.page is not None
        assert state.pages.page.path == person.resolve()

    def test_missing_owner_uses_the_broken_style_and_asks_to_create(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        project = _write_note(
            vault / "projects" / "Home.md",
            _typed_note("project", "# Home\n", extra="owner: Nobody"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        requested: list[str] = []

        async def missing(name: str) -> None:
            requested.append(name)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(project)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None, on_missing_role=missing))
        name_span = (view.meta_owner.spans or [])[1]

        assert name_span.style is afanes.ui.theme.ROLE_BROKEN_TEXT_STYLE
        assert name_span.tooltip == afanes.ui.strings.ROLE_LINK_MISSING

        asyncio.run(typing.cast("typing.Any", name_span.on_click)())

        assert requested == ["Nobody"]
        assert not (vault / "reference" / "Nobody.md").exists()

    def test_project_without_a_requester_omits_the_label(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)

        view = PageView(PageActions(update=lambda: None))

        assert view.meta_asked.visible is False
        assert view.meta_asked.spans == []

    def test_note_page_shows_only_the_date(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))

        assert view.meta_row.visible is True
        assert view.meta_date.value == afanes.ui.strings.PAGE_NO_DATE
        assert view.meta_status.visible is False
        assert view.meta_due.visible is False
        assert view.meta_due_button.visible is False
        assert view.meta_owner.visible is False
        assert view.meta_asked.visible is False

    def test_due_date_is_set_from_read_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch, due_date=None)
        body_before = NoteDocument.from_text(path.read_text(encoding="utf-8")).body

        async def pick_date(_current: datetime.date | None) -> datetime.date | None:
            return datetime.date(2026, 12, 5)

        view = PageView(PageActions(update=lambda: None, pick_date=pick_date))
        asyncio.run(view.choose_due_date())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.due_date == datetime.date(2026, 12, 5)
        assert document.body == body_before

    def test_due_date_is_cleared_from_read_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch)
        body_before = NoteDocument.from_text(path.read_text(encoding="utf-8")).body

        view = PageView(PageActions(update=lambda: None))
        asyncio.run(view.clear_due_date())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.due_date is None
        assert document.body == body_before

    def test_edit_mode_keeps_the_due_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))

        asyncio.run(view.start_edit())

        assert view.meta_row.visible is False
        assert view.due_field.visible is True
        assert view.due_field.value == "2026-12-01"

    def test_read_mode_uses_github_flavored_markdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\n- [ ] Task\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))

        assert view.read_body.extension_set is ft.MarkdownExtensionSet.GITHUB_FLAVORED


def _spans_text(control: ft.Text) -> str:
    return "".join(str(span.text) for span in control.spans or [])


def _freeze(control: ft.Control) -> None:
    object.__setattr__(control, "_frozen", True)


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _record_scroll(view: PageView) -> list[float | None]:
    positions: list[float | None] = []

    async def recorder(*, offset: float | None = None, **_kwargs: object) -> None:
        positions.append(offset)

    object.__setattr__(view.content, "scroll_to", recorder)
    return positions


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    if isinstance(control, ft.Text):
        values.append(control.value)
    if isinstance(control, ft.Checkbox):
        values.append(str(control.label))
    if isinstance(control, ft.Markdown):
        values.append(control.value)
    values.extend(str(span.text) for span in getattr(control, "spans", []) or [] if isinstance(span, ft.TextSpan))
    for child in getattr(control, "controls", []) or []:
        values.extend(_texts(child))
    content = getattr(control, "content", None)
    if isinstance(content, str):
        values.append(content)
    elif isinstance(content, ft.Control):
        values.extend(_texts(content))
    return values


def _find_checkbox(control: ft.Control) -> ft.Control | None:
    if isinstance(control, ft.Checkbox):
        return control
    for child in getattr(control, "controls", []) or []:
        found = _find_checkbox(child)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_checkbox(content)
    return None


def _connection_section(view: PageView, title: str) -> ft.Control:
    for control in view.connections_body.controls:
        if title in _texts(control):
            return control
    message = f"missing connection section {title!r}"
    raise AssertionError(message)


def _panel_actions(panel: ft.Control) -> list[ft.Control]:
    column = getattr(panel, "content", None)
    assert isinstance(column, ft.Column)
    actions = column.controls[-1]
    assert isinstance(actions, ft.Row)
    return list(actions.controls)


def _find_text_button(control: ft.Control, label: str) -> ft.TextButton | None:
    if isinstance(control, ft.TextButton):
        content = control.content
        if content == label:
            return control
        if isinstance(content, ft.Text) and content.value == label:
            return control
    for child in getattr(control, "controls", []) or []:
        found = _find_text_button(child, label)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_text_button(content, label)
    return None


class TestConnections:
    def _open_person(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Call.md", _note_text("# Call\n\n[Ada](<note:Ada>)\n"))
        _write_note(
            vault / "projects" / "Home.md",
            _typed_note(
                "project",
                "# Home\n\n- [ ] Review <!-- {owners: [Ada]} -->\n- [x] Done <!-- {owners: [Ada]} -->\n",
                extra="owner: Ada\nasked_by: Ada",
            ),
        )
        _write_note(
            vault / "projects" / "Finished.md",
            _typed_note("project", "# Finished\n", extra="status: done\nasked_by: Ada"),
        )
        _write_note(
            vault / "projects" / "Old.md",
            _typed_note("project", "# Old\n", extra="status: done\nowner: Ada"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)

        asyncio.run(scenario())

    def test_section_lists_all_four_subsections(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        subsections = view.connections_body.controls

        assert view.connections_panel.visible is True
        assert len(subsections) == FOUR_SUBSECTIONS
        assert afanes.ui.strings.PAGE_CONNECTIONS_LINKED_FROM in _texts(subsections[0])
        assert afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS in _texts(subsections[1])
        assert afanes.ui.strings.PAGE_CONNECTIONS_OWNED_STEPS in _texts(subsections[2])
        assert afanes.ui.strings.PAGE_CONNECTIONS_REQUESTED_PROJECTS in _texts(subsections[3])

    def test_only_sections_with_visible_rows_are_rendered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Call.md", _note_text("# Call\n\n[Ada](<note:Ada>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))
        headings = [
            title
            for title in (
                afanes.ui.strings.PAGE_CONNECTIONS_LINKED_FROM,
                afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS,
                afanes.ui.strings.PAGE_CONNECTIONS_OWNED_STEPS,
                afanes.ui.strings.PAGE_CONNECTIONS_REQUESTED_PROJECTS,
            )
            if any(title in _texts(control) for control in view.connections_body.controls)
        ]

        assert headings == [afanes.ui.strings.PAGE_CONNECTIONS_LINKED_FROM]
        assert view.connections_steps_toggle.visible is False
        assert view.connections_projects_toggle.visible is False

    def test_an_empty_section_does_not_reorder_the_others(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "notes" / "Call.md", _note_text("# Call\n\n[Ada](<note:Ada>)\n"))
        _write_note(vault / "projects" / "Home.md", _typed_note("project", "# Home\n", extra="owner: Ada"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))
        headings = [
            title
            for title in (
                afanes.ui.strings.PAGE_CONNECTIONS_LINKED_FROM,
                afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS,
                afanes.ui.strings.PAGE_CONNECTIONS_OWNED_STEPS,
                afanes.ui.strings.PAGE_CONNECTIONS_REQUESTED_PROJECTS,
            )
            if any(title in _texts(control) for control in view.connections_body.controls)
        ]

        assert headings == [
            afanes.ui.strings.PAGE_CONNECTIONS_LINKED_FROM,
            afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS,
        ]

    def test_owned_project_alone_renders_the_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(vault / "projects" / "Home.md", _typed_note("project", "# Home\n", extra="owner: Ada"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))
        headings = [
            title
            for title in (
                afanes.ui.strings.PAGE_CONNECTIONS_LINKED_FROM,
                afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS,
                afanes.ui.strings.PAGE_CONNECTIONS_OWNED_STEPS,
                afanes.ui.strings.PAGE_CONNECTIONS_REQUESTED_PROJECTS,
            )
            if any(title in _texts(control) for control in view.connections_body.controls)
        ]

        assert headings == [afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS]
        assert "Home" in _texts(_connection_section(view, afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS))

    def test_finished_owned_project_keeps_the_footer_control_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(
            vault / "projects" / "Old.md",
            _typed_note("project", "# Old\n", extra="status: done\nowner: Ada"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))

        assert view.connections_body.controls == []
        assert view.connections_panel.visible is True
        assert view.connections_projects_toggle.visible is True
        assert view.connections_steps_toggle.visible is False
        assert view.connections_projects_toggle in _panel_actions(view.connections_panel)

        view.connections_projects_toggle.value = True
        asyncio.run(view.toggle_finished_projects(ft.Event(name="change", control=view.connections_projects_toggle)))

        assert "Old" in _texts(_connection_section(view, afanes.ui.strings.PAGE_CONNECTIONS_OWNED_PROJECTS))

    def test_completed_owned_step_keeps_the_footer_control_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(
            vault / "projects" / "Home.md",
            _typed_note("project", "# Home\n\n- [x] Done <!-- {owners: [Ada]} -->\n"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))

        assert view.connections_body.controls == []
        assert view.connections_panel.visible is True
        assert view.connections_steps_toggle.visible is True
        assert view.connections_projects_toggle.visible is False
        assert view.connections_steps_toggle in _panel_actions(view.connections_panel)

        view.connections_steps_toggle.value = True
        asyncio.run(view.toggle_completed_steps(ft.Event(name="change", control=view.connections_steps_toggle)))

        assert "Done" in _texts(_connection_section(view, afanes.ui.strings.PAGE_CONNECTIONS_OWNED_STEPS))

    def test_linked_from_rows_use_display_titles(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))

        assert "Call" in _texts(view.connections_body.controls[0])

    def test_owned_projects_list_open_projects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        texts = _texts(view.connections_body.controls[1])

        assert "Home" in texts
        assert "Old" not in texts

    def test_owned_steps_group_under_project_headings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        texts = _texts(view.connections_body.controls[2])

        assert "Home" in texts
        assert "Review" in texts
        assert "Done" not in texts

    def test_requested_projects_list_open_projects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        texts = _texts(view.connections_body.controls[3])

        assert "Home" in texts
        assert "Finished" not in texts
        assert "Old" not in texts

    def test_selecting_a_linked_note_opens_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        scrolls = _record_scroll(view)
        button = _find_text_button(view.connections_body.controls[0], "Call")
        assert button is not None

        asyncio.run(typing.cast("typing.Any", button.on_click)())

        assert scrolls == [0]
        assert view.title.value == "Call"

    def test_selecting_an_owned_step_opens_its_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        scrolls = _record_scroll(view)
        button = _find_text_button(view.connections_body.controls[2], "Review")
        assert button is not None

        asyncio.run(typing.cast("typing.Any", button.on_click)())

        assert view.title.value == "Home"
        assert scrolls == [0]

    def test_selecting_a_project_heading_opens_its_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        scrolls = _record_scroll(view)
        button = _find_text_button(view.connections_body.controls[2], "Home")
        assert button is not None

        asyncio.run(typing.cast("typing.Any", button.on_click)())

        assert view.title.value == "Home"
        assert scrolls == [0]

    def test_selecting_an_owned_project_opens_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        scrolls = _record_scroll(view)
        button = _find_text_button(view.connections_body.controls[1], "Home")
        assert button is not None

        asyncio.run(typing.cast("typing.Any", button.on_click)())

        assert view.title.value == "Home"
        assert scrolls == [0]

    def test_enabling_completed_steps_reveals_them(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        assert view.connections_steps_toggle.visible is True
        assert view.connections_steps_toggle.value is False
        assert "Done" not in _texts(view.connections_body.controls[2])

        view.connections_steps_toggle.value = True
        asyncio.run(view.toggle_completed_steps(ft.Event(name="change", control=view.connections_steps_toggle)))

        assert "Done" in _texts(view.connections_body.controls[2])
        assert view.connections_steps_toggle.value

    def test_enabling_finished_projects_reveals_both_roles(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        assert view.connections_projects_toggle.visible is True
        assert view.connections_projects_toggle.value is False
        assert "Old" not in _texts(view.connections_body.controls[1])
        assert "Finished" not in _texts(view.connections_body.controls[3])

        view.connections_projects_toggle.value = True
        asyncio.run(view.toggle_finished_projects(ft.Event(name="change", control=view.connections_projects_toggle)))

        assert "Old" in _texts(view.connections_body.controls[1])
        assert "Finished" in _texts(view.connections_body.controls[3])
        assert view.connections_projects_toggle.value

    def test_changing_the_page_resets_both_toggles(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        view.connections_steps_toggle.value = True
        asyncio.run(view.toggle_completed_steps(ft.Event(name="change", control=view.connections_steps_toggle)))
        view.connections_projects_toggle.value = True
        asyncio.run(view.toggle_finished_projects(ft.Event(name="change", control=view.connections_projects_toggle)))
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.navigation.open_page(tmp_path / "vault" / "notes" / "Call.md")
            view.refresh()
            await state.navigation.open_page(tmp_path / "vault" / "reference" / "people" / "Ada.md")
            view.refresh()

        asyncio.run(scenario())

        assert not view.connections_steps_toggle.value
        assert not view.connections_projects_toggle.value
        assert "Done" not in _texts(view.connections_body.controls[2])
        assert "Old" not in _texts(view.connections_body.controls[1])
        assert "Finished" not in _texts(view.connections_body.controls[3])

    def test_reading_and_toggling_connections_writes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        vault = tmp_path / "vault"
        before = _tree_state(vault)

        view.connections_steps_toggle.value = True
        asyncio.run(view.toggle_completed_steps(ft.Event(name="change", control=view.connections_steps_toggle)))
        view.connections_projects_toggle.value = True
        asyncio.run(view.toggle_finished_projects(ft.Event(name="change", control=view.connections_projects_toggle)))

        assert _tree_state(vault) == before

    def test_page_without_connections_hides_the_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))

        assert view.connections_panel.visible is False
        assert view.connections_body.controls == []

    def test_edit_mode_hides_the_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))
        assert view.connections_panel.visible is True

        asyncio.run(view.start_edit())

        assert not view.connections_panel.visible

    def test_raw_rescue_hides_the_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_failure(Path("reference/Broken.md"))

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))

        assert view.raw_panel.visible is True
        assert view.connections_panel.visible is False

    def test_owned_steps_render_in_project_and_document_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        person = _write_note(
            vault / "reference" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _write_note(
            vault / "projects" / "Zulu.md",
            _typed_note("project", "# Zulu\n\n- [ ] Third <!-- {owners: [Ada]} -->\n"),
        )
        _write_note(
            vault / "projects" / "Alpha.md",
            _typed_note(
                "project",
                "# Alpha\n\n- [ ] First <!-- {owners: [Ada]} -->\n- [ ] Second <!-- {owners: [Ada]} -->\n",
            ),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(person)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))
        texts = _texts(_connection_section(view, afanes.ui.strings.PAGE_CONNECTIONS_OWNED_STEPS))

        assert (
            texts.index("Alpha")
            < texts.index("First")
            < texts.index("Second")
            < texts.index("Zulu")
            < texts.index("Third")
        )

    def test_completed_steps_toggle_does_not_reveal_finished_projects(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))

        view.connections_steps_toggle.value = True
        asyncio.run(view.toggle_completed_steps(ft.Event(name="change", control=view.connections_steps_toggle)))

        assert "Done" in _texts(view.connections_body.controls[2])
        assert view.connections_projects_toggle.value is False
        assert "Finished" not in _texts(view.connections_body.controls[3])

    def test_finished_projects_toggle_does_not_reveal_completed_steps(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(PageActions(update=lambda: None))

        view.connections_projects_toggle.value = True
        asyncio.run(view.toggle_finished_projects(ft.Event(name="change", control=view.connections_projects_toggle)))

        assert "Finished" in _texts(view.connections_body.controls[3])
        assert view.connections_steps_toggle.value is False
        assert "Done" not in _texts(view.connections_body.controls[2])


class TestFrozenPageRecovery:
    def test_refresh_recovers_a_frozen_content_control(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))
        _freeze(view.content)

        view.refresh()

        assert not hasattr(view.content, "_frozen")


class TestPageDates:
    def _open(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        path: Path,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(versioned(tmp_path / "vault"))
            await state.navigation.open_page(path)

        asyncio.run(scenario())

    def test_note_date_is_shown_in_the_meta_row(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Ada.md", _typed_note("note", "# Ada\n", extra="date: 2025-10"))
        self._open(tmp_path, monkeypatch, path)
        view = PageView(PageActions(update=lambda: None))

        assert view.meta_row.visible is True
        assert view.meta_date.value == afanes.ui.strings.PAGE_DATE.format(date="2025-10")
        assert view.meta_status.visible is False

    def test_project_shows_both_dates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "projects" / "Launch.md",
            _typed_note("project", "# Launch\n", extra="date: 2025-10"),
        )
        self._open(tmp_path, monkeypatch, path)
        view = PageView(PageActions(update=lambda: None))

        assert afanes.ui.strings.PAGE_DATE.format(date="2025-10") == view.meta_date.value
        assert view.meta_due.value == afanes.ui.strings.PAGE_PROJECT_NO_DUE

    def test_log_form_hides_workflow_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "log" / "2025" / "10" / "2025-10-12.md",
            _typed_note("log", "# Tuesday\n", extra="date: 2025-10-12"),
        )
        self._open(tmp_path, monkeypatch, path)
        view = PageView(PageActions(update=lambda: None))

        asyncio.run(view.start_edit())

        assert view.date_field.visible is True
        assert view.category_field.visible is False
        assert view.status_dropdown.visible is False
        assert view.due_field.visible is False
        assert view.asked_by_field.visible is False
        assert view.owner_field.visible is False

    def test_malformed_date_shows_a_warning(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "notes" / "Ada.md",
            _typed_note("note", "# Ada\n", extra="date: last Tuesday"),
        )
        self._open(tmp_path, monkeypatch, path)
        view = PageView(PageActions(update=lambda: None))

        asyncio.run(view.start_edit())

        assert view.date_error.visible is True
        assert view.date_error.value

    def test_log_date_change_renames_and_moves(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "log" / "2025" / "10" / "2025-10-12.md",
            _typed_note("log", "# Tuesday\n", extra="date: 2025-10-12"),
        )
        self._open(tmp_path, monkeypatch, path)
        view = PageView(PageActions(update=lambda: None))
        asyncio.run(view.start_edit())
        view.date_field.value = "2025-10-13"

        asyncio.run(view.commit_date())

        target = vault / "log" / "2025" / "10" / "2025-10-13.md"
        assert target.is_file()
        assert not path.exists()
        assert afanes.ui.state.app_state.pages.page is not None
        assert afanes.ui.state.app_state.pages.page.path == target

    def test_reference_date_change_updates_in_place(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "reference" / "Ada.md",
            _typed_note("reference", "# Ada\n"),
        )
        self._open(tmp_path, monkeypatch, path)
        view = PageView(PageActions(update=lambda: None))
        asyncio.run(view.start_edit())
        view.date_field.value = "2025-10"

        asyncio.run(view.commit_date())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.date is not None
        assert document.date.text == "2025-10"
        assert path.is_file()


class TestLogStarter:
    @staticmethod
    def _card() -> afanes.core.template_cards.TemplateCard:
        return afanes.core.template_cards.TemplateCard(
            relative_path=Path("daily.md"),
            note_type=NoteType.LOG,
            category=None,
            title="Daily entry",
            description=None,
            body="## What happened\n",
            text="",
        )

    def _open(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        issues: tuple[afanes.core.template_cards.TemplateCardIssue, ...] = (),
    ) -> tuple[
        afanes.ui.state.controller.AppState,
        afanes.core.template_cards.TemplateCard,
        PageView,
    ]:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        card = self._card()
        listing = afanes.core.template_cards.TemplateCardListing(cards=(card,), issues=issues)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(versioned(tmp_path / "vault"))
            await state.navigation.start_log_draft(NoteDate.from_text("2025-10-12"), listing)

        asyncio.run(scenario())
        return state, card, PageView(PageActions(update=lambda: None))

    def test_the_starter_is_visible_for_a_new_log_draft(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _state, _card, view = self._open(tmp_path, monkeypatch)

        assert view.log_starter_panel.visible is True
        assert view.log_starter_picker.dropdown.visible is True
        assert view.log_starter_picker.dropdown in view.form_fields.row.controls
        assert view.log_starter_picker.dropdown.value == "empty"
        assert view.log_starter_picker.dropdown.options[-1].text == afanes.ui.strings.LOG_CARD_EMPTY

    def test_the_starter_control_sits_in_the_label_flow(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _state, _card, view = self._open(tmp_path, monkeypatch)

        assert view.log_starter_picker.dropdown in view.form_fields.row.controls
        assert view.log_starter_picker.dropdown not in view.log_starter_panel.controls
        flow_index = view.edit_form.controls.index(view.form_fields.row)
        panel_index = view.edit_form.controls.index(view.log_starter_panel)
        body_index = view.edit_form.controls.index(view.body_field)
        assert flow_index < panel_index < body_index

    def test_a_wide_log_draft_shares_the_label_row(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _state, _card, view = self._open(tmp_path, monkeypatch)

        view.form_fields.layout(1200)

        assert [view.type_dropdown.col, view.date_field.col, view.log_starter_picker.dropdown.col] == [4, 4, 4]

    def test_a_narrow_log_draft_stacks_the_label_row(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _state, _card, view = self._open(tmp_path, monkeypatch)

        view.form_fields.layout(300)

        assert [view.type_dropdown.col, view.date_field.col, view.log_starter_picker.dropdown.col] == [
            12,
            12,
            12,
        ]

    def test_selecting_a_card_fills_the_body(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        state, _card, view = self._open(tmp_path, monkeypatch)
        view.log_starter_picker.dropdown.value = "card:daily.md"

        asyncio.run(view.change_log_starter())

        assert state.pages.page is not None
        assert state.pages.page.body == "# October 12, 2025\n\n## What happened\n"
        assert view.body_field.value == state.pages.page.body
        assert view.log_starter_panel.visible is True

    def test_selecting_empty_restores_the_heading(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        state, _card, view = self._open(tmp_path, monkeypatch)
        view.log_starter_picker.dropdown.value = "card:daily.md"
        asyncio.run(view.change_log_starter())
        view.log_starter_picker.dropdown.value = "empty"

        asyncio.run(view.change_log_starter())

        assert state.pages.page is not None
        assert state.pages.page.body == "# October 12, 2025\n\n"
        assert view.body_field.value == state.pages.page.body

    def test_typing_beyond_the_body_hides_the_starter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _state, _card, view = self._open(tmp_path, monkeypatch)
        view.body_field.value = "# October 12, 2025\n\nExtra\n"

        asyncio.run(view.change_body())

        assert view.log_starter_panel.visible is False
        assert view.log_starter_picker.dropdown.visible is False
        assert view.type_dropdown.col == 6
        assert view.date_field.col == 6

    def test_invalid_cards_are_named_beside_the_starter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        issue = afanes.core.template_cards.TemplateCardIssue(relative_path=Path("broken.md"), message="bad")
        _state, _card, view = self._open(tmp_path, monkeypatch, issues=(issue,))

        assert view.log_starter_picker.warning.visible is True
        assert "broken.md" in (view.log_starter_picker.warning.value or "")
        assert len(view.log_starter_picker.dropdown.options) == STARTER_OPTION_COUNT

    def test_an_existing_entry_has_no_starter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        path = _write_note(
            vault / "log" / "2025" / "10" / "2025-10-12.md",
            _typed_note("log", "# Tuesday\n", extra="date: 2025-10-12"),
        )
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(versioned(vault))
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))
        asyncio.run(view.start_edit())

        assert view.log_starter_panel.visible is False
        assert view.log_starter_picker.dropdown.visible is False
        assert state.pages.log_starter is None


class TestPageWidth:
    def test_the_column_expands_in_read_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = PageView(PageActions(update=lambda: None))

        assert view.page_column.expand is True
        assert view.page_column.width is None
        assert view.edit_form.visible is False

    def test_the_column_expands_in_edit_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert view.page_column.expand is True
        assert view.page_column.width is None
        assert view.edit_form.visible is True
        assert view.body_field.expand is True

    def test_the_page_card_no_longer_tracks_a_reading_width(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert not hasattr(view, "fit_width")
        assert view.root.on_size_change is not None


class TestConflictActions:
    def test_the_conflict_panel_shows_one_suggested_action(self) -> None:
        view = PageView(PageActions(update=lambda: None))
        view.conflict_panel.visible = True
        view.reload_button.visible = True
        view.overwrite_button.visible = True

        highlighted = emphasis_controls(view.conflict_panel)

        assert len(highlighted) == 1
        assert highlighted[0] is view.reload_button
        assert not isinstance(view.overwrite_button, ft.FilledButton)
        assert not isinstance(view.recreate_button, ft.FilledButton)


class TestRenameAndRepairActions:
    def test_the_rename_panel_shows_one_suggested_action(self) -> None:
        view = PageView(PageActions(update=lambda: None))
        view.rename_panel.visible = True
        view.rename_preview_button.visible = False
        view.rename_confirm_button.visible = True

        highlighted = emphasis_controls(view.rename_panel)

        assert len(highlighted) == 1
        assert highlighted[0] is view.rename_confirm_button
        assert not isinstance(view.rename_preview_button, ft.FilledButton)

    def test_the_repair_panel_shows_one_suggested_action(self) -> None:
        view = PageView(PageActions(update=lambda: None))
        view.repair_panel.visible = True

        highlighted = emphasis_controls(view.repair_panel)

        assert len(highlighted) == 1
        assert highlighted[0] is view.repair_rewrite_button


class TestConfirmationOrder:
    def test_type_change_puts_cancel_first(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert _action_labels(view.type_change_panel) == [
            afanes.ui.strings.PAGE_CANCEL,
            afanes.ui.strings.PAGE_TYPE_CHANGE_CONFIRM,
        ]

    def test_category_move_puts_cancel_first(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert _action_labels(view.category_move_panel) == [
            afanes.ui.strings.PAGE_CANCEL,
            afanes.ui.strings.PAGE_CATEGORY_MOVE_CONFIRM,
        ]

    def test_rename_puts_cancel_first(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert _action_labels(view.rename_panel) == [
            afanes.ui.strings.PAGE_CANCEL,
            afanes.ui.strings.PAGE_RENAME_PREVIEW_ACTION,
            afanes.ui.strings.PAGE_RENAME_CONFIRM,
        ]

    def test_repair_puts_cancel_first(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert _action_labels(view.repair_panel) == [
            afanes.ui.strings.PAGE_REPAIR_CANCEL,
            afanes.ui.strings.PAGE_REPAIR_KEEP,
            afanes.ui.strings.PAGE_REPAIR_REWRITE,
        ]


class TestRenameAvailability:
    def test_the_rename_actions_start_insensitive(self) -> None:
        view = PageView(PageActions(update=lambda: None))

        assert view.rename_preview_button.disabled is True
        assert view.rename_confirm_button.disabled is True

    def test_a_non_blank_name_enables_both_actions(self) -> None:
        view = PageView(PageActions(update=lambda: None))
        view.rename_field.value = "New name"

        asyncio.run(view.change_rename_text())

        assert view.rename_preview_button.disabled is False
        assert view.rename_confirm_button.disabled is False

    def test_a_blank_name_disables_both_actions(self) -> None:
        view = PageView(PageActions(update=lambda: None))
        view.rename_field.value = "New name"
        asyncio.run(view.change_rename_text())
        view.rename_field.value = "   "

        asyncio.run(view.change_rename_text())

        assert view.rename_preview_button.disabled is True
        assert view.rename_confirm_button.disabled is True


class TestToolbarActions:
    def test_the_toolbar_actions_match_the_gate_allowlist(self) -> None:
        view = PageView(PageActions(update=lambda: None))
        keys = {control.key for control in view.header.controls if getattr(control, "key", None) in HEADER_ACTION_KEYS}

        assert keys == HEADER_ACTION_KEYS


class TestTrashPage:
    def _open_trashed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> tuple[PageView, afanes.ui.state.app_state.__class__, Path]:
        vault = tmp_path / "vault"
        source = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(source)
            assert await state.dialogs.trash_page() is True
            await state.browser.set_section(afanes.ui.state.browser.WorkspaceSection.TRASH)
            entry = state.browser.trash_entries()[0]
            assert await state.navigation.open_trash(entry) is True

        asyncio.run(scenario())
        view.refresh()
        return view, state, source

    def test_the_trashed_page_shows_origin_and_read_only_actions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        view, state, _source = self._open_trashed(tmp_path, monkeypatch)

        assert state.pages.trash_entry is not None
        assert view.trash_info.visible is True
        assert afanes.ui.strings.TRASH_INFO.format(
            path="notes/Ada.md",
            date=state.pages.trash_entry.trashed_on.isoformat() if state.pages.trash_entry.trashed_on else "",
        ) in (view.trash_info.value or "")
        assert view.restore_button.visible is True
        assert view.edit_button.visible is False
        assert view.done_button.visible is False
        assert view.rename_item.visible is False
        assert view.trash_item.visible is False
        assert view.delete_item.visible is True
        assert view.edit_form.visible is False
        assert view.meta_row.visible is False
        assert view.raw_panel.visible is False

    def test_the_trashed_page_never_shows_its_storage_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        view, state, _source = self._open_trashed(tmp_path, monkeypatch)
        entry = state.pages.trash_entry
        assert entry is not None

        assert entry.entry_id not in (view.path.value or "")
        assert entry.entry_id not in (view.trash_info.value or "")
        assert state.pages.page_path_label == "notes/Ada.md"

    def test_restore_returns_the_note_to_its_active_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        view, state, source = self._open_trashed(tmp_path, monkeypatch)

        asyncio.run(typing.cast("typing.Any", view.restore_button.on_click)())

        assert source.is_file()
        assert state.pages.trash_entry is None
        assert view.restore_button.visible is False
        assert view.edit_button.visible is True

    def test_an_occupied_birthplace_shows_the_overwrite_panel(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        view, state, source = self._open_trashed(tmp_path, monkeypatch)
        source.write_text(_note_text("# Occupant\n"), encoding="utf-8")

        asyncio.run(typing.cast("typing.Any", view.restore_button.on_click)())

        assert view.overwrite_trash_panel.visible is True
        assert view.overwrite_trash.title.value == afanes.ui.strings.TRASH_OVERWRITE_TITLE
        assert "notes/Ada.md" in (view.overwrite_trash.body.value or "")
        asyncio.run(typing.cast("typing.Any", view.overwrite_trash.cancel.on_click)())
        assert not view.overwrite_trash_panel.visible
        assert source.read_text(encoding="utf-8") == _note_text("# Occupant\n")
        assert state.session.trash_count == 1

        asyncio.run(typing.cast("typing.Any", view.restore_button.on_click)())
        asyncio.run(typing.cast("typing.Any", view.overwrite_trash.confirm.on_click)())

        assert source.read_text(encoding="utf-8") == _note_text("# Ada\n\nBody\n")
        assert view.overwrite_trash_panel.visible is False
        assert state.session.trash_count == 0

    def test_permanent_delete_shows_a_confirmation_without_the_uuid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        view, state, _source = self._open_trashed(tmp_path, monkeypatch)
        entry = state.pages.trash_entry
        assert entry is not None

        asyncio.run(view.begin_delete_trash())

        assert view.delete_trash_panel.visible is True
        assert view.delete_trash.title.value == afanes.ui.strings.TRASH_DELETE_TITLE
        assert entry.entry_id not in (view.delete_trash.body.value or "")
        asyncio.run(typing.cast("typing.Any", view.delete_trash.cancel.on_click)())
        assert state.session.trash_count == 1

        asyncio.run(view.begin_delete_trash())
        asyncio.run(typing.cast("typing.Any", view.delete_trash.confirm.on_click)())

        assert state.session.trash_count == 0
        assert state.pages.trash_entry is None


class TestTrashedProjectPage:
    def test_a_trashed_project_renders_markdown_without_step_controls(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        source = _write_note(
            vault / "projects" / "Build shed.md",
            _typed_note("project", "# Build shed\n\n- [ ] Buy timber\n"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(PageActions(update=lambda: None))

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(source)
            assert await state.dialogs.trash_page() is True
            await state.browser.set_section(afanes.ui.state.browser.WorkspaceSection.TRASH)
            entry = state.browser.trash_entries()[0]
            assert await state.navigation.open_trash(entry) is True

        asyncio.run(scenario())
        view.refresh()

        assert view.read_body.visible is True
        assert "Buy timber" in (view.read_body.value or "")
        assert view.project_body.root.visible is False
        assert view.edit_form.visible is False
