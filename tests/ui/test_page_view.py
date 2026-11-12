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

TWO_CANDIDATES = 2


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: path))


def _write_note(path: Path, content: str) -> Path:
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
            await state.choose_vault(vault)
            await state.open_page(path)

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

        async def scenario() -> None:
            await state.choose_vault(vault)
            event = ft.Event(name="tap", control=ft.Markdown(), data="note:Ada")
            await view.handle_link(event)

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.path == person.resolve()

    def test_edit_button_switches_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(path)
            view.refresh()
            await view.start_edit()

        asyncio.run(scenario())

        assert state.editing is True
        assert view.edit_form.visible is True
        assert view.read_body.visible is False
        assert view.done_button.visible is True

    def test_back_button_returns_to_the_previous_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        first = _write_note(vault / "notes" / "First.md", _note_text("# First\n"))
        second = _write_note(vault / "notes" / "Second.md", _note_text("# Second\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(first)
            await state.open_page(second)
            view.refresh()
            await view.go_back()

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.path == first.resolve()
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
            await state.choose_vault(vault)
            await state.open_page(path)
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
            await state.choose_vault(vault)
            await state.open_page(path)
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
            await state.choose_vault(vault)
            await state.open_page(path)
            view.refresh()
            await view.start_edit()
            view.body_field.value = "# Ada\n\nChanged.\n"
            await view.change_body()

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.body == "# Ada\n\nChanged.\n"
        assert state.page.is_dirty is True

    def test_invalid_due_date_is_shown_inline(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "projects" / "Call.md", _typed_note("project", "# Call\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(path)
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
            await state.choose_vault(vault)
            await state.open_page(path)
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
        assert state.page is not None
        assert state.page.labels is not None
        assert state.page.labels.category is not None
        assert state.page.labels.category.value == "person"

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
            await state.choose_vault(vault)
            await state.open_page(person)
            view.refresh()
            await view.start_edit()
            view.type_dropdown.value = "project"
            await view.change_type()
            assert view.type_change_panel.visible is True
            assert state.pending_labels is not None
            await view.confirm_type_change()

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.labels is not None
        assert state.page.labels.note_type is NoteType.PROJECT
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
            await state.choose_vault(vault)
            await state.open_page(person)
            view.refresh()
            await view.start_edit()
            view.type_dropdown.value = "project"
            await view.change_type()
            await view.cancel_type_change()

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.labels is not None
        assert state.page.labels.scheme is ReferenceScheme.NOTE
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
            await state.choose_vault(vault)
            await state.open_failure(Path("reference/Broken.md"))
            view.refresh()

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.mode is DraftMode.RAW
        assert view.raw_panel.visible is True
        assert view.raw_field.value == "---\ntype: refrence\n---\nBody\n"
        assert view.raw_warning.value
        assert view.edit_form.visible is False

    def test_raw_save_upgrades_the_view(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        _write_note(vault / "reference" / "Broken.md", "---\ntype: refrence\n---\nBody\n")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)
        fixed = "---\ntype: note\n---\n\n# Fixed\nBody.\n"

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_failure(Path("reference/Broken.md"))
            view.refresh()
            view.raw_field.value = fixed
            await view.save_raw()

        asyncio.run(scenario())

        assert state.page is not None
        assert state.page.mode is DraftMode.NORMAL
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
            await state.choose_vault(vault)
            await state.open_page(path)
            view.refresh()
            await view.start_edit()
            view.body_field.value = "# Ada\n\nMy edit.\n"
            await view.change_body()
            path.write_text(_note_text("# Ada\n\nExternal.\n"), encoding="utf-8", newline="\n")
            await state.autosave()
            view.refresh()
            assert view.conflict_panel.visible is True
            assert view.reload_button.visible is True
            assert view.overwrite_button.visible is True
            assert view.recreate_button.visible is False
            await view.overwrite_page()

        asyncio.run(scenario())

        assert state.conflict is None
        assert view.conflict_panel.visible is False

    def test_missing_conflict_offers_recreate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = _write_note(vault / "notes" / "Ada.md", _note_text("# Ada\n\nBody.\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.open_page(path)
            view.refresh()
            await view.start_edit()
            view.body_field.value = "# Ada\n\nMy edit.\n"
            await view.change_body()
            path.unlink()
            await state.autosave()
            view.refresh()
            assert view.recreate_button.visible is True
            await view.recreate_page()

        asyncio.run(scenario())

        assert path.exists()
        assert state.conflict is None

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

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Ada")
            view.refresh()
            assert view.ambiguous_panel.visible is True
            assert len(view.ambiguous_list.controls) == TWO_CANDIDATES
            tile = view.ambiguous_list.controls[0]
            assert isinstance(tile, ft.ListTile)
            assert tile.on_click is not None
            handler = typing.cast("typing.Any", tile.on_click)
            await handler()

        asyncio.run(scenario())

        assert state.ambiguous == ()
        assert state.page is not None
        assert state.page.path in {first.resolve(), second.resolve()}
        assert view.ambiguous_panel.visible is False

    def test_repair_panel_rewrites_the_links(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        source = _write_note(vault / "notes" / "Source.md", _note_text("[Q1](<note:Q1: Planning?>)\n"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        view = PageView(lambda: None)

        async def scenario() -> None:
            await state.choose_vault(vault)
            await state.follow_link("note:Q1: Planning?")
            view.refresh()
            await state.set_page_body("# Q1: Planning?\n\nDraft.\n")
            await state.autosave()
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
            await state.choose_vault(vault)
            await state.open_page(note)
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
            await state.choose_vault(vault)
            await state.open_page(note)
            view.refresh()
            await view.begin_trash()
            assert view.trash_panel.visible is True
            assert view.trash_text.value
            await view.confirm_trash()

        asyncio.run(scenario())

        assert not note.exists()
        assert (vault / "trash" / "Ada.md").exists()
        assert state.page is None
        assert view.trash_panel.visible is False


class TestSteps:
    def _project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, afanes.ui.state.AppState]:
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
            await state.choose_vault(vault)
            await state.open_page(path)

        asyncio.run(scenario())
        return path, state

    def test_steps_render_as_rows_and_hide_the_comment(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._project(tmp_path, monkeypatch)

        view = PageView(lambda: None)
        texts = _texts(view.steps_column)

        assert view.steps_panel.visible is True
        assert "Call" in texts
        assert afanes.ui.strings.PAGE_STEP_OWNERS.format(owners="Ada") in texts
        assert afanes.ui.strings.PAGE_STEP_PLAN.format(date="2026-11-20") in texts
        assert afanes.ui.strings.PAGE_STEP_ACTUAL.format(date="2026-11-14") in texts
        assert afanes.ui.strings.PAGE_STEP_TAGS.format(tags="phone") in texts
        assert "<!--" not in view.read_body.value

    def test_ticking_a_step_rewrites_only_its_line(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, _state = self._project(tmp_path, monkeypatch)
        view = PageView(lambda: None)
        checkbox = _find_checkbox(view.steps_column)
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
            await state.choose_vault(tmp_path / "vault")
            await state.open_page(path)

        asyncio.run(scenario())
        view = PageView(lambda: None)
        checkbox = _find_checkbox(view.steps_column)
        assert isinstance(checkbox, ft.Checkbox)
        checkbox.value = False

        asyncio.run(typing.cast("typing.Any", checkbox.on_change)(ft.Event(name="change", control=checkbox)))

        step = StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]
        assert step.checked is False
        assert step.actual is None
        assert step.plan == datetime.date(2026, 11, 20)


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    if isinstance(control, ft.Text):
        values.append(str(control.value))
    if isinstance(control, ft.Checkbox):
        values.append(str(control.label))
    for child in getattr(control, "controls", []) or []:
        values.extend(_texts(child))
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
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
