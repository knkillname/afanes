"""Tests for the read, edit, raw rescue, and confirmation page controls."""

import asyncio
import datetime
import typing
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.ui.state
from afanes.core.editing import DraftMode
from afanes.core.frontmatter import NoteDocument
from afanes.core.steps import StepDocument
from afanes.models.link import ReferenceScheme
from afanes.models.note import NoteType
from afanes.ui.views.page import PageView
from tests.support import ensure_vault, versioned

TWO_CANDIDATES = 2
FOUR_SUBSECTIONS = 4


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: path))


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
        view = PageView(lambda: None)

        assert view.title.value == "Ada"
        assert view.path.value == "notes/Ada.md"
        assert view.read_body.visible is True
        assert view.read_body.value == "# Ada\n\nBody.\n"
        assert view.edit_form.visible is False
        assert view.raw_panel.visible is False
        assert view.edit_button.visible is True
        assert view.done_button.visible is False

    def test_empty_page_shows_the_placeholder(self) -> None:
        view = PageView(lambda: None)

        assert view.empty_text.visible is True
        assert view.read_body.visible is False
        assert view.edit_form.visible is False
        assert view.raw_panel.visible is False

    def test_link_tap_forwards_the_destination(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        person = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", category="person"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)

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
        assert view.form_fields.wrap is True
        assert view.form_fields.controls == [
            view.type_dropdown,
            view.category_field,
            view.status_dropdown,
            view.date_field,
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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)
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
    def test_conflict_panel_offers_reload_and_overwrite(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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

    def test_trash_panel_confirms(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        note = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)
            view.refresh()
            await view.begin_trash()
            assert view.trash_panel.visible is True
            assert view.trash_text.value
            await view.confirm_trash()

        asyncio.run(scenario())

        assert not note.exists()
        assert (vault / "trash" / "Ada.md").exists()
        assert state.pages.page is None
        assert view.trash_panel.visible is False

    def test_log_page_hides_rename_and_keeps_trash(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        note = _write_note(
            vault / "log" / "2025" / "10" / "2025-10-12.md",
            _typed_note("log", "# A quiet Tuesday\n", extra="date: 2025-10-12"),
        )
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(note)
            view.refresh()

        asyncio.run(scenario())

        assert view.rename_button.visible is False
        assert view.trash_button.visible is True


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

        view = PageView(lambda: None)
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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)
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

        view = PageView(lambda: None)

        assert view.meta_row.visible is True
        assert view.meta_status.value == afanes.ui.strings.PROJECT_STATUS.format(status="Waiting")
        assert view.meta_due.value == afanes.ui.strings.PROJECT_DUE.format(date="2026-12-01")
        assert view.meta_due_clear.visible is True
        assert view.edit_form.visible is False

    def test_project_without_due_date_offers_the_action(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch, due_date=None)

        view = PageView(lambda: None)

        assert view.meta_row.visible is True
        assert view.meta_due.value == afanes.ui.strings.PAGE_PROJECT_NO_DUE
        assert view.meta_due_clear.visible is False

    def test_project_meta_row_shows_the_requester(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch, asked_by="Priya Nair")

        view = PageView(lambda: None)

        assert view.meta_asked.visible is True
        assert _spans_text(view.meta_asked) == "Asked by Priya Nair"

    def test_project_meta_row_shows_the_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch, owner="Sam Rivera")

        view = PageView(lambda: None)

        assert view.meta_owner.visible is True
        assert _spans_text(view.meta_owner) == "Owner Sam Rivera"

    def test_owner_is_shown_before_the_requester(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch, owner="Sam Rivera", asked_by="Priya Nair")

        view = PageView(lambda: None)

        controls = list(view.meta_row.controls)
        assert controls.index(view.meta_owner) < controls.index(view.meta_asked)

    def test_project_without_an_owner_omits_the_label(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)

        view = PageView(lambda: None)

        assert view.meta_owner.visible is False
        assert view.meta_owner.spans == []

    def test_owner_action_icon_sets_the_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, state = self._project(tmp_path, monkeypatch)
        calls: list[tuple[str, str | None]] = []

        async def pick(role: str, current: str | None) -> str | None:
            calls.append((role, current))
            return "Grace Hopper"

        view = PageView(lambda: None, pick_role=pick)

        asyncio.run(view.choose_owner())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.owner == "Grace Hopper"
        assert calls == [("owner", None)]
        assert state.pages.editing is False

    def test_owner_action_icon_clears_the_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch, owner="Sam Rivera")

        async def pick(_role: str, _current: str | None) -> str | None:
            return ""

        view = PageView(lambda: None, pick_role=pick)

        asyncio.run(view.choose_owner())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.owner is None

    def test_asked_by_action_icon_sets_the_requester(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch)
        calls: list[tuple[str, str | None]] = []

        async def pick(role: str, current: str | None) -> str | None:
            calls.append((role, current))
            return "Priya Nair"

        view = PageView(lambda: None, pick_role=pick)

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
        project_view = PageView(lambda: None)
        assert project_view.meta_owner_button.visible is True
        assert project_view.meta_asked_button.visible is True

        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.navigation.open_page(note)

        asyncio.run(scenario())
        note_view = PageView(lambda: None)

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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None, on_missing_role=missing)
        name_span = (view.meta_owner.spans or [])[1]

        assert name_span.style is afanes.ui.theme.ROLE_BROKEN_TEXT_STYLE
        assert name_span.tooltip == afanes.ui.strings.ROLE_LINK_MISSING

        asyncio.run(typing.cast("typing.Any", name_span.on_click)())

        assert requested == ["Nobody"]
        assert not (vault / "reference" / "Nobody.md").exists()

    def test_project_without_a_requester_omits_the_label(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)

        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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

        view = PageView(lambda: None, pick_date=pick_date)
        asyncio.run(view.choose_due_date())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.due_date == datetime.date(2026, 12, 5)
        assert document.body == body_before

    def test_due_date_is_cleared_from_read_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch)
        body_before = NoteDocument.from_text(path.read_text(encoding="utf-8")).body

        view = PageView(lambda: None)
        asyncio.run(view.clear_due_date())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.due_date is None
        assert document.body == body_before

    def test_edit_mode_keeps_the_due_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        values.append(str(control.value))
    if isinstance(control, ft.Checkbox):
        values.append(str(control.label))
    if isinstance(control, ft.Markdown):
        values.append(str(control.value))
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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

        assert "Call" in _texts(view.connections_body.controls[0])

    def test_owned_projects_list_open_projects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        texts = _texts(view.connections_body.controls[1])

        assert "Home" in texts
        assert "Old" not in texts

    def test_owned_steps_group_under_project_headings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        texts = _texts(view.connections_body.controls[2])

        assert "Home" in texts
        assert "Review" in texts
        assert "Done" not in texts

    def test_requested_projects_list_open_projects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        texts = _texts(view.connections_body.controls[3])

        assert "Home" in texts
        assert "Finished" not in texts
        assert "Old" not in texts

    def test_selecting_a_linked_note_opens_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        scrolls = _record_scroll(view)
        button = _find_text_button(view.connections_body.controls[0], "Call")
        assert button is not None

        asyncio.run(typing.cast("typing.Any", button.on_click)())

        assert scrolls == [0]
        assert view.title.value == "Call"

    def test_selecting_an_owned_step_opens_its_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)
        scrolls = _record_scroll(view)
        button = _find_text_button(view.connections_body.controls[2], "Home")
        assert button is not None

        asyncio.run(typing.cast("typing.Any", button.on_click)())

        assert view.title.value == "Home"
        assert scrolls == [0]

    def test_selecting_an_owned_project_opens_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        scrolls = _record_scroll(view)
        button = _find_text_button(view.connections_body.controls[1], "Home")
        assert button is not None

        asyncio.run(typing.cast("typing.Any", button.on_click)())

        assert view.title.value == "Home"
        assert scrolls == [0]

    def test_enabling_completed_steps_reveals_them(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        assert view.connections_steps_toggle.visible is True
        assert view.connections_steps_toggle.value is False
        assert "Done" not in _texts(view.connections_body.controls[2])

        view.connections_steps_toggle.value = True
        asyncio.run(view.toggle_completed_steps(ft.Event(name="change", control=view.connections_steps_toggle)))

        assert "Done" in _texts(view.connections_body.controls[2])
        assert view.connections_steps_toggle.value is True

    def test_enabling_finished_projects_reveals_both_roles(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        assert view.connections_projects_toggle.visible is True
        assert view.connections_projects_toggle.value is False
        assert "Old" not in _texts(view.connections_body.controls[1])
        assert "Finished" not in _texts(view.connections_body.controls[3])

        view.connections_projects_toggle.value = True
        asyncio.run(view.toggle_finished_projects(ft.Event(name="change", control=view.connections_projects_toggle)))

        assert "Old" in _texts(view.connections_body.controls[1])
        assert "Finished" in _texts(view.connections_body.controls[3])
        assert view.connections_projects_toggle.value is True

    def test_changing_the_page_resets_both_toggles(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
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

        assert view.connections_steps_toggle.value is False
        assert view.connections_projects_toggle.value is False
        assert "Done" not in _texts(view.connections_body.controls[2])
        assert "Old" not in _texts(view.connections_body.controls[1])
        assert "Finished" not in _texts(view.connections_body.controls[3])

    def test_reading_and_toggling_connections_writes_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)

        assert view.connections_panel.visible is False
        assert view.connections_body.controls == []

    def test_edit_mode_hides_the_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        assert view.connections_panel.visible is True

        asyncio.run(view.start_edit())

        assert view.connections_panel.visible is False

    def test_raw_rescue_hides_the_section(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_failure(Path("reference/Broken.md"))

        asyncio.run(scenario())
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)

        view.connections_steps_toggle.value = True
        asyncio.run(view.toggle_completed_steps(ft.Event(name="change", control=view.connections_steps_toggle)))

        assert "Done" in _texts(view.connections_body.controls[2])
        assert view.connections_projects_toggle.value is False
        assert "Finished" not in _texts(view.connections_body.controls[3])

    def test_finished_projects_toggle_does_not_reveal_completed_steps(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._open_person(tmp_path, monkeypatch)
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

        assert afanes.ui.strings.PAGE_DATE.format(date="2025-10") == view.meta_date.value
        assert view.meta_due.value == afanes.ui.strings.PAGE_PROJECT_NO_DUE

    def test_log_form_hides_workflow_fields(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "log" / "2025" / "10" / "2025-10-12.md",
            _typed_note("log", "# Tuesday\n", extra="date: 2025-10-12"),
        )
        self._open(tmp_path, monkeypatch, path)
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)

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
        view = PageView(lambda: None)
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
        view = PageView(lambda: None)
        asyncio.run(view.start_edit())
        view.date_field.value = "2025-10"

        asyncio.run(view.commit_date())

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.date is not None
        assert document.date.text == "2025-10"
        assert path.is_file()
