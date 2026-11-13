"""Tests for the status-grouped Projects view."""

import asyncio
import typing
from collections.abc import Awaitable, Callable, Coroutine
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.projects
from tests.support import ensure_vault, versioned

Handler = Callable[[], Coroutine[typing.Any, typing.Any, None]]
FocusHandler = Callable[[object], Coroutine[typing.Any, typing.Any, None]]
LinkHandler = Callable[[object], Coroutine[typing.Any, typing.Any, None]]


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


def _freeze(control: ft.Control) -> None:
    object.__setattr__(control, "_frozen", True)


def _write_note(
    path: Path,
    *,
    note_type: str = "project",
    status: str | None = None,
    due_date: str | None = None,
    owner: str | None = None,
    body: str = "",
) -> Path:
    ensure_vault(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    if owner is not None:
        lines.append(f"owner: {owner}")
    lines.extend(["---", body])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


async def _select(_path: Path) -> None:
    return None


def _open_view(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    on_select: Callable[[Path], Awaitable[None]] = _select,
) -> afanes.ui.views.projects.ProjectsView:
    monkeypatch.setattr(
        afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: tmp_path / "settings.json")
    )
    asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(versioned(tmp_path / "vault")))
    return afanes.ui.views.projects.ProjectsView(_noop, on_select)


def _group(view: afanes.ui.views.projects.ProjectsView, stage: str) -> ft.ExpansionTile:
    return next(
        control
        for control in view.root.controls
        if isinstance(control, ft.ExpansionTile) and control.key == f"project-group-{stage}"
    )


def _project_buttons(view: afanes.ui.views.projects.ProjectsView, stage: str) -> list[ft.TextButton]:
    controls = _group(view, stage).controls or []
    if not controls:
        return []
    rows = controls[0]
    assert isinstance(rows, ft.Column)
    buttons: list[ft.TextButton] = []
    for row in rows.controls:
        assert isinstance(row, ft.Container)
        content = row.content
        assert isinstance(content, ft.TextButton)
        buttons.append(content)
    return buttons


def _find_by_key(control: ft.Control, key: str) -> ft.Control | None:
    if getattr(control, "key", None) == key:
        return control
    for child in getattr(control, "controls", None) or []:
        found = _find_by_key(child, key)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if content is not None:
        return _find_by_key(content, key)
    return None


def _row(view: afanes.ui.views.projects.ProjectsView, path: str) -> ft.Container:
    row = _find_by_key(view.root, f"project-row-{path}")
    assert isinstance(row, ft.Container)
    return row


def _button(view: afanes.ui.views.projects.ProjectsView, path: str) -> ft.TextButton:
    button = _find_by_key(view.root, f"project-{path}")
    assert isinstance(button, ft.TextButton)
    return button


def _ring(view: afanes.ui.views.projects.ProjectsView, path: str) -> object:
    row = _row(view, path)
    assert row.border is not None
    return row.border.top.color


def _next_step(button: ft.TextButton) -> ft.Control:
    content = button.content
    assert isinstance(content, ft.Column)
    return content.controls[1]


def _titles(view: afanes.ui.views.projects.ProjectsView, stage: str) -> list[str]:
    titles: list[str] = []
    for button in _project_buttons(view, stage):
        content = button.content
        assert isinstance(content, ft.Column)
        title = content.controls[0]
        assert isinstance(title, ft.Text)
        titles.append(title.value)
    return titles


def _details(button: ft.TextButton) -> list[str]:
    content = button.content
    assert isinstance(content, ft.Column)
    return [control.value for control in content.controls[1:] if isinstance(control, (ft.Text, ft.Markdown))]


def _handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_click"))


class TestProjectGrouping:
    def test_groups_projects_by_status(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Plain.md")
        _write_note(vault / "projects" / "Now.md", status="active")
        _write_note(vault / "projects" / "Blocked.md", status="waiting")
        _write_note(vault / "projects" / "Someday.md", status="later")
        _write_note(vault / "projects" / "Finished.md", status="done")
        view = _open_view(tmp_path, monkeypatch)

        assert _titles(view, "active") == ["Now", "Plain"]
        assert _titles(view, "waiting") == ["Blocked"]
        assert _titles(view, "later") == ["Someday"]
        assert _titles(view, "closed") == ["Finished"]

    def test_closed_group_starts_collapsed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Finished.md", status="done")
        view = _open_view(tmp_path, monkeypatch)

        assert _group(view, "active").expanded is True
        assert _group(view, "waiting").expanded is True
        assert _group(view, "later").expanded is True
        assert _group(view, "closed").expanded is False

    def test_status_is_shown_in_the_metadata_line(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Now.md", status="active")
        _write_note(vault / "projects" / "Plain.md")
        view = _open_view(tmp_path, monkeypatch)
        expected = afanes.ui.strings.PROJECT_META_SEPARATOR.join(["Active", afanes.ui.strings.open_step_count(0)])

        active_details = _details(_project_buttons(view, "active")[0])
        plain_details = _details(_project_buttons(view, "active")[1])

        assert active_details[-1] == expected
        assert plain_details[-1] == expected


class TestProjectRows:
    def test_row_shows_due_date_open_count_and_next_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            due_date="2026-11-20",
            body="# Launch\n\n- [ ] Write copy\n- [x] Done\n",
        )
        view = _open_view(tmp_path, monkeypatch)

        details = _details(_project_buttons(view, "active")[0])

        assert "Due 2026-11-20" in details[-1]
        assert "1 open step" in details[-1]
        assert "Next: Write copy" in details

    def test_row_leads_with_the_next_step_and_keeps_metadata_quiet(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            due_date="2026-11-20",
            body="# Launch\n\n- [ ] Write copy\n",
        )
        view = _open_view(tmp_path, monkeypatch)
        button = _project_buttons(view, "active")[0]
        content = button.content
        row = _row(view, "projects/Launch.md")

        assert isinstance(content, ft.Column)
        title, next_step, metadata = content.controls
        assert isinstance(title, ft.Text)
        assert title.value == "Launch"
        assert title.style == afanes.ui.theme.TEXT_ROLES["heading"]
        assert isinstance(next_step, ft.Markdown)
        style_sheet = next_step.md_style_sheet
        assert style_sheet is not None
        assert style_sheet.p_text_style == afanes.ui.theme.TEXT_ROLES["body"]
        assert isinstance(metadata, ft.Text)
        assert metadata.style == afanes.ui.theme.TEXT_ROLES["caption"]
        assert not _group(view, "active").dense
        assert row.bgcolor == afanes.ui.theme.TRANSPARENT_COLOR
        assert row.border is not None
        assert row.border.top.color == afanes.ui.theme.TRANSPARENT_COLOR

        focus = typing.cast("FocusHandler", button.on_focus)
        asyncio.run(focus(None))

        assert row.border.top.color == afanes.ui.theme.FOCUS_RING_COLOR
        assert row.bgcolor == afanes.ui.theme.TRANSPARENT_COLOR

        blur = typing.cast("FocusHandler", button.on_blur)
        asyncio.run(blur(None))

        assert row.border.top.color == afanes.ui.theme.TRANSPARENT_COLOR

    def test_row_without_due_date_omits_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        view = _open_view(tmp_path, monkeypatch)

        details = _details(_project_buttons(view, "active")[0])

        assert all(not detail.startswith("Due ") for detail in details)

    def test_row_keeps_the_owner_out_of_the_summary(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="waiting",
            due_date="2026-12-01",
            owner="Sam Rivera",
            body="# Launch\n\n- [ ] Write copy\n- [ ] Review\n",
        )
        view = _open_view(tmp_path, monkeypatch)

        tiles = _project_buttons(view, "waiting")
        assert _titles(view, "waiting") == ["Launch"]
        details = _details(tiles[0])
        assert "Waiting" in details[-1]
        assert afanes.ui.strings.PROJECT_DUE.format(date="2026-12-01") in details[-1]
        assert "2 open steps" in details[-1]
        assert any("Write copy" in detail for detail in details)
        assert "Sam Rivera" not in " ".join(details)
        assert all("Owner" not in detail for detail in details)

    def test_clearing_the_owner_keeps_the_project_row(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_note(
            vault / "projects" / "Launch.md",
            status="waiting",
            due_date="2026-12-01",
            owner="Sam Rivera",
            body="# Launch\n\n- [ ] Write copy\n- [ ] Review\n",
        )
        view = _open_view(tmp_path, monkeypatch)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.navigation.open_page(project)
            assert await state.pages.set_page_owner("", save=True) is True

        asyncio.run(scenario())
        view.refresh()

        tiles = _project_buttons(view, "waiting")
        assert _titles(view, "waiting") == ["Launch"]
        details = _details(tiles[0])
        assert "Waiting" in details[-1]
        assert afanes.ui.strings.PROJECT_DUE.format(date="2026-12-01") in details[-1]
        assert "2 open steps" in details[-1]
        assert any("Write copy" in detail for detail in details)
        assert "Sam Rivera" not in " ".join(details)

    def test_checked_step_is_not_counted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active", body="# Launch\n\n- [x] Someday\n")
        view = _open_view(tmp_path, monkeypatch)

        details = _details(_project_buttons(view, "active")[0])

        assert "0 open steps" in details[-1]
        assert afanes.ui.strings.PROJECT_NO_NEXT_STEP in details

    def test_next_step_renders_markdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [ ] **Write** [copy](<note:Copy>)\n",
        )
        view = _open_view(tmp_path, monkeypatch)
        button = _project_buttons(view, "active")[0]
        content = button.content
        assert isinstance(content, ft.Column)

        rendered = [control for control in content.controls[1:] if isinstance(control, ft.Markdown)]
        plain = [control.value for control in content.controls[1:] if isinstance(control, ft.Text)]

        assert [control.value for control in rendered] == ["Next: **Write** [copy](<note:Copy>)"]
        assert rendered[0].selectable is False
        assert rendered[0].on_tap_link is not None
        style_sheet = rendered[0].md_style_sheet
        assert style_sheet is not None
        assert style_sheet.a_text_style is not None
        assert style_sheet.a_text_style.decoration != ft.TextDecoration.UNDERLINE
        assert all("](" not in text and "**" not in text for text in plain)

    def test_remaining_open_steps_are_counted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [ ] One\n- [ ] Two\n",
        )
        view = _open_view(tmp_path, monkeypatch)

        details = _details(_project_buttons(view, "active")[0])

        assert "2 open steps" in details[-1]


class TestProjectSelection:
    def test_selecting_a_project_opens_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_note(vault / "projects" / "Launch.md", status="active", body="# Launch")
        state = afanes.ui.state.app_state

        async def open_page(path: Path) -> None:
            await state.navigation.open_page(path)

        view = _open_view(tmp_path, monkeypatch, on_select=open_page)

        asyncio.run(_handler(_project_buttons(view, "active")[0])())

        assert state.pages.page is not None
        assert state.pages.page.path == project

    def test_selection_uses_the_supplied_callback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        opened: list[Path] = []

        async def select(path: Path) -> None:
            opened.append(path)

        view = _open_view(tmp_path, monkeypatch, on_select=select)
        asyncio.run(_handler(_project_buttons(view, "active")[0])())

        assert [path.name for path in opened] == ["Launch.md"]

    def test_selection_updates_in_place(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active", body="# Launch")
        state = afanes.ui.state.app_state

        async def open_page(path: Path) -> None:
            await state.navigation.open_page(path)

        view = _open_view(tmp_path, monkeypatch, on_select=open_page)
        button = _project_buttons(view, "active")[0]
        row = _row(view, "projects/Launch.md")
        assert row.bgcolor == afanes.ui.theme.TRANSPARENT_COLOR

        asyncio.run(_handler(button)())
        view.refresh()

        assert _project_buttons(view, "active")[0] is button
        assert _row(view, "projects/Launch.md") is row
        assert row.bgcolor == afanes.ui.theme.SELECTED_ROW_COLOR


class TestProjectRowInteraction:
    def test_preview_text_is_not_selectable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active", body="# Launch\n\n- [ ] Write copy\n")
        view = _open_view(tmp_path, monkeypatch)

        next_step = _next_step(_button(view, "projects/Launch.md"))

        assert isinstance(next_step, ft.Markdown)
        assert next_step.selectable is False

    def test_missing_step_preview_is_not_selectable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        view = _open_view(tmp_path, monkeypatch)

        next_step = _next_step(_button(view, "projects/Launch.md"))

        assert isinstance(next_step, ft.Text)
        assert next_step.selectable is not True

    def test_tapping_a_preview_link_opens_the_row(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [ ] Call [the printer](<note:Printer>)\n",
        )
        state = afanes.ui.state.app_state

        async def open_page(path: Path) -> None:
            await state.navigation.open_page(path)

        view = _open_view(tmp_path, monkeypatch, on_select=open_page)
        next_step = _next_step(_button(view, "projects/Launch.md"))
        assert isinstance(next_step, ft.Markdown)
        assert next_step.on_tap_link is not None

        asyncio.run(typing.cast("LinkHandler", next_step.on_tap_link)(None))

        assert state.pages.page is not None
        assert state.pages.page.path == project


class TestProjectFocus:
    def test_clicking_a_second_row_moves_the_ring_and_rejects_a_late_blur(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        _write_note(vault / "projects" / "Ship.md", status="active")
        opened: list[Path] = []

        async def select(path: Path) -> None:
            opened.append(path)

        view = _open_view(tmp_path, monkeypatch, on_select=select)
        first = _button(view, "projects/Launch.md")
        second = _button(view, "projects/Ship.md")

        asyncio.run(typing.cast("FocusHandler", first.on_focus)(None))
        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.FOCUS_RING_COLOR

        asyncio.run(_handler(second)())

        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.TRANSPARENT_COLOR
        assert _ring(view, "projects/Ship.md") == afanes.ui.theme.FOCUS_RING_COLOR

        asyncio.run(typing.cast("FocusHandler", first.on_blur)(None))

        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.TRANSPARENT_COLOR
        assert _ring(view, "projects/Ship.md") == afanes.ui.theme.FOCUS_RING_COLOR
        assert [path.name for path in opened] == ["Ship.md"]

    def test_a_frozen_row_is_recovered_before_the_ring_is_painted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        view = _open_view(tmp_path, monkeypatch)
        first = _button(view, "projects/Launch.md")
        row = _row(view, "projects/Launch.md")
        _freeze(row)

        asyncio.run(typing.cast("FocusHandler", first.on_focus)(None))

        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.FOCUS_RING_COLOR
        assert not hasattr(row, "_frozen")

    def test_keyboard_focus_moves_the_ring_between_rows(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        _write_note(vault / "projects" / "Ship.md", status="active")
        view = _open_view(tmp_path, monkeypatch)
        first = _button(view, "projects/Launch.md")
        second = _button(view, "projects/Ship.md")

        asyncio.run(typing.cast("FocusHandler", first.on_focus)(None))
        asyncio.run(typing.cast("FocusHandler", second.on_focus)(None))
        asyncio.run(typing.cast("FocusHandler", first.on_blur)(None))

        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.TRANSPARENT_COLOR
        assert _ring(view, "projects/Ship.md") == afanes.ui.theme.FOCUS_RING_COLOR

    def test_a_content_rebuild_drops_the_old_ring(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active", body="# Launch\n\n- [ ] Write copy\n")
        view = _open_view(tmp_path, monkeypatch)
        button = _button(view, "projects/Launch.md")
        asyncio.run(typing.cast("FocusHandler", button.on_focus)(None))
        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.FOCUS_RING_COLOR

        _write_note(vault / "projects" / "Launch.md", status="active", body="# Launch\n\n- [x] Write copy\n")
        asyncio.run(afanes.ui.state.app_state.workspace.refresh())
        view.refresh()

        assert _button(view, "projects/Launch.md") is not button
        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.TRANSPARENT_COLOR

    def test_opening_another_page_clears_the_old_ring(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        launch = _write_note(vault / "projects" / "Launch.md", status="active")
        ship = _write_note(vault / "projects" / "Ship.md", status="active")
        state = afanes.ui.state.app_state

        async def open_page(path: Path) -> None:
            await state.navigation.open_page(path)

        view = _open_view(tmp_path, monkeypatch, on_select=open_page)
        asyncio.run(_handler(_button(view, "projects/Launch.md"))())
        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.FOCUS_RING_COLOR
        assert state.pages.page is not None
        assert state.pages.page.path == launch

        asyncio.run(state.navigation.open_page(ship))
        view.refresh()

        assert _ring(view, "projects/Launch.md") == afanes.ui.theme.TRANSPARENT_COLOR
        assert _ring(view, "projects/Ship.md") == afanes.ui.theme.TRANSPARENT_COLOR
        assert _row(view, "projects/Ship.md").bgcolor == afanes.ui.theme.SELECTED_ROW_COLOR


class TestProjectRefresh:
    def test_counts_and_next_step_recompute_after_a_change(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [ ] Write copy\n",
        )
        view = _open_view(tmp_path, monkeypatch)
        assert "1 open step" in _details(_project_buttons(view, "active")[0])[-1]

        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [x] Write copy\n",
        )
        asyncio.run(afanes.ui.state.app_state.workspace.refresh())
        view.refresh()

        details = _details(_project_buttons(view, "active")[0])
        assert "0 open steps" in details[-1]
        assert afanes.ui.strings.PROJECT_NO_NEXT_STEP in details

    def test_search_filters_projects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        _write_note(vault / "projects" / "Archive.md", status="active")
        view = _open_view(tmp_path, monkeypatch)
        asyncio.run(afanes.ui.state.app_state.browser.set_query("launch"))

        view.refresh()

        assert _titles(view, "active") == ["Launch"]

    def test_step_text_search_lists_the_project_without_the_matching_step(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [ ] Write copy\n- [ ] Call the printer\n",
        )
        _write_note(vault / "projects" / "Archive.md", status="active", body="# Archive\n\n- [ ] File it\n")
        view = _open_view(tmp_path, monkeypatch)
        asyncio.run(afanes.ui.state.app_state.browser.set_query("printer"))

        view.refresh()

        tiles = _project_buttons(view, "active")
        assert _titles(view, "active") == ["Launch"]
        details = _details(tiles[0])
        assert any("Write copy" in detail for detail in details)
        assert "printer" not in " ".join(details).lower()
