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


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


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


def _project_tiles(view: afanes.ui.views.projects.ProjectsView, stage: str) -> list[ft.ListTile]:
    return [control for control in _group(view, stage).controls or [] if isinstance(control, ft.ListTile)]


def _details(tile: ft.ListTile) -> list[str]:
    subtitle = tile.subtitle
    assert isinstance(subtitle, ft.Column)
    return [control.value for control in subtitle.controls if isinstance(control, (ft.Text, ft.Markdown))]


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

        assert [tile.title for tile in _project_tiles(view, "active")] == ["Now", "Plain"]
        assert [tile.title for tile in _project_tiles(view, "waiting")] == ["Blocked"]
        assert [tile.title for tile in _project_tiles(view, "later")] == ["Someday"]
        assert [tile.title for tile in _project_tiles(view, "closed")] == ["Finished"]

    def test_closed_group_starts_collapsed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Finished.md", status="done")
        view = _open_view(tmp_path, monkeypatch)

        assert _group(view, "active").expanded is True
        assert _group(view, "waiting").expanded is True
        assert _group(view, "later").expanded is True
        assert _group(view, "closed").expanded is False

    def test_status_labels_are_shown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Now.md", status="active")
        _write_note(vault / "projects" / "Plain.md")
        view = _open_view(tmp_path, monkeypatch)

        active_details = _details(_project_tiles(view, "active")[0])
        plain_details = _details(_project_tiles(view, "active")[1])

        assert "Status: Active" in active_details
        assert "Status: Active" in plain_details


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

        details = _details(_project_tiles(view, "active")[0])

        assert "Due 2026-11-20" in details
        assert "1 open step" in details
        assert "Next: Write copy" in details

    def test_row_without_due_date_omits_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        view = _open_view(tmp_path, monkeypatch)

        details = _details(_project_tiles(view, "active")[0])

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

        tiles = _project_tiles(view, "waiting")
        assert [tile.title for tile in tiles] == ["Launch"]
        details = _details(tiles[0])
        assert "Status: Waiting" in details
        assert afanes.ui.strings.PROJECT_DUE.format(date="2026-12-01") in details
        assert "2 open steps" in details
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

        tiles = _project_tiles(view, "waiting")
        assert [tile.title for tile in tiles] == ["Launch"]
        details = _details(tiles[0])
        assert "Status: Waiting" in details
        assert afanes.ui.strings.PROJECT_DUE.format(date="2026-12-01") in details
        assert "2 open steps" in details
        assert any("Write copy" in detail for detail in details)
        assert "Sam Rivera" not in " ".join(details)

    def test_checked_step_is_not_counted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active", body="# Launch\n\n- [x] Someday\n")
        view = _open_view(tmp_path, monkeypatch)

        details = _details(_project_tiles(view, "active")[0])

        assert "0 open steps" in details
        assert "No next step" in details

    def test_next_step_renders_markdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [ ] **Write** [copy](<note:Copy>)\n",
        )
        view = _open_view(tmp_path, monkeypatch)
        tile = _project_tiles(view, "active")[0]
        subtitle = tile.subtitle
        assert isinstance(subtitle, ft.Column)

        rendered = [control for control in subtitle.controls if isinstance(control, ft.Markdown)]
        plain = [control.value for control in subtitle.controls if isinstance(control, ft.Text)]

        assert [control.value for control in rendered] == ["Next: **Write** [copy](<note:Copy>)"]
        assert rendered[0].on_tap_link is None
        assert all("](" not in text and "**" not in text for text in plain)

    def test_remaining_open_steps_are_counted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [ ] One\n- [ ] Two\n",
        )
        view = _open_view(tmp_path, monkeypatch)

        details = _details(_project_tiles(view, "active")[0])

        assert "2 open steps" in details


class TestProjectSelection:
    def test_selecting_a_project_opens_it(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_note(vault / "projects" / "Launch.md", status="active", body="# Launch")
        state = afanes.ui.state.app_state

        async def open_page(path: Path) -> None:
            await state.navigation.open_page(path)

        view = _open_view(tmp_path, monkeypatch, on_select=open_page)

        asyncio.run(_handler(_project_tiles(view, "active")[0])())

        assert state.pages.page is not None
        assert state.pages.page.path == project

    def test_selection_uses_the_supplied_callback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        opened: list[Path] = []

        async def select(path: Path) -> None:
            opened.append(path)

        view = _open_view(tmp_path, monkeypatch, on_select=select)
        asyncio.run(_handler(_project_tiles(view, "active")[0])())

        assert [path.name for path in opened] == ["Launch.md"]


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
        assert "1 open step" in _details(_project_tiles(view, "active")[0])

        _write_note(
            vault / "projects" / "Launch.md",
            status="active",
            body="# Launch\n\n- [x] Write copy\n",
        )
        asyncio.run(afanes.ui.state.app_state.workspace.refresh())
        view.refresh()

        details = _details(_project_tiles(view, "active")[0])
        assert "0 open steps" in details
        assert "No next step" in details

    def test_search_filters_projects(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", status="active")
        _write_note(vault / "projects" / "Archive.md", status="active")
        view = _open_view(tmp_path, monkeypatch)
        asyncio.run(afanes.ui.state.app_state.browser.set_query("launch"))

        view.refresh()

        assert [tile.title for tile in _project_tiles(view, "active")] == ["Launch"]

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

        tiles = _project_tiles(view, "active")
        assert [tile.title for tile in tiles] == ["Launch"]
        details = _details(tiles[0])
        assert any("Write copy" in detail for detail in details)
        assert "printer" not in " ".join(details).lower()
