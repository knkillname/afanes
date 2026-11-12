"""Tests for the step-aware project body view."""

import asyncio
import datetime
import inspect
import typing
from collections.abc import Iterator
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
from afanes.core.frontmatter import NoteDocument
from afanes.core.steps import StepDocument
from afanes.ui.views.project_body import ProjectBodyView

PLAN = datetime.date(2026, 12, 1)


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: path))


def _write_note(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _typed_note(note_type: str, body: str, *, status: str | None = None, due_date: str | None = None) -> str:
    lines = ["---", f"type: {note_type}"]
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    lines.extend(["---", body])
    return "\n".join(lines)


def _open_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    *,
    due_date: str | None = None,
    chosen: datetime.date | None = None,
) -> tuple[Path, ProjectBodyView, list[str]]:
    vault = tmp_path / "vault"
    path = _write_note(vault / "projects" / "Home.md", _typed_note("project", body, status="active", due_date=due_date))
    _use_settings_file(monkeypatch, tmp_path / "settings.json")
    state = afanes.ui.state.app_state
    followed: list[str] = []

    async def follow(destination: str) -> None:
        followed.append(destination)
        await state.navigation.follow_link(destination)

    async def pick_date(_current: datetime.date | None) -> datetime.date | None:
        return chosen

    async def scenario() -> None:
        await state.workspace.choose_vault(vault)
        await state.navigation.open_page(path)

    asyncio.run(scenario())
    view = ProjectBodyView(lambda: None, follow, pick_date)
    return path, view, followed


def _walk(control: ft.Control) -> Iterator[ft.Control]:
    yield control
    for child in getattr(control, "controls", []) or []:
        yield from _walk(child)
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)


def _markdown(control: ft.Control) -> list[ft.Markdown]:
    return [item for item in _walk(control) if isinstance(item, ft.Markdown)]


def _buttons(control: ft.Control) -> list[ft.IconButton]:
    return [item for item in _walk(control) if isinstance(item, ft.IconButton)]


def _button(control: ft.Control, tooltip: str) -> ft.IconButton:
    return next(item for item in _buttons(control) if item.tooltip == tooltip)


def _field(control: ft.Control) -> ft.TextField:
    return next(item for item in _walk(control) if isinstance(item, ft.TextField) and item.key == "step-owner-field")


def _run(handler: object, *args: object) -> object:
    result = typing.cast("typing.Any", handler)(*args)
    if inspect.isawaitable(result):
        return asyncio.run(typing.cast("typing.Coroutine[typing.Any, typing.Any, typing.Any]", result))
    return result


class TestRendering:
    def test_prose_and_steps_render_in_source_order(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\nIntro.\n\n- [ ] Call\n\nDone.\n"
        _path, view, _followed = _open_project(tmp_path, monkeypatch, body)

        values = [control.value for control in _markdown(view.root)]
        cards = [item for item in _walk(view.root) if isinstance(item, ft.Container) and item.key]

        assert values[0].startswith("# Home")
        assert "Intro." in values[1]
        assert "Call" in values[2]
        assert "Done." in values[3]
        assert cards
        assert cards[0].bgcolor == afanes.ui.theme.STEP_SURFACE_COLOR

    def test_no_separate_steps_panel_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\n- [ ] Call\n"
        _path, view, _followed = _open_project(tmp_path, monkeypatch, body)

        assert not hasattr(view, "steps_panel")
        assert not hasattr(view, "steps_column")

    def test_fallback_block_renders_as_markdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\n- [ ] Task\n- Not a task\n"
        _path, view, _followed = _open_project(tmp_path, monkeypatch, body)

        assert any("- Not a task" in control.value for control in _markdown(view.root))

    def test_step_text_does_not_show_raw_metadata(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\n- [ ] Call <!-- {owners: [Ada], plan: 2026-11-20} -->\n"
        _path, view, _followed = _open_project(tmp_path, monkeypatch, body)

        rendered = " ".join(control.value for control in _markdown(view.root))
        assert "<!--" not in rendered
        assert "Call" in rendered

    def test_step_link_is_forwarded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        ada = _write_note(
            vault / "reference" / "people" / "Ada.md",
            _typed_note("reference", "# Ada\n", status=None),
        )
        body = "# Home\n\n- [ ] Call [Ada](<note:Ada>)\n"
        path = _write_note(vault / "projects" / "Home.md", _typed_note("project", body, status="active"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state
        followed: list[str] = []

        async def follow(destination: str) -> None:
            followed.append(destination)
            await state.navigation.follow_link(destination)

        async def pick_date(_current: datetime.date | None) -> datetime.date | None:
            return None

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = ProjectBodyView(lambda: None, follow, pick_date)
        linked = next(control for control in _markdown(view.root) if "Ada" in control.value)

        _run(linked.on_tap_link, ft.Event(name="tap", control=linked, data="note:Ada"))

        assert followed == ["note:Ada"]
        assert state.pages.page is not None
        assert state.pages.page.path == ada.resolve()


class TestActions:
    def test_every_step_has_visible_muted_actions(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\n- [ ] Call\n"
        _path, view, _followed = _open_project(tmp_path, monkeypatch, body)

        calendar = _button(view.root, afanes.ui.strings.PAGE_STEP_PLAN_ACTION)
        person = _button(view.root, afanes.ui.strings.PAGE_STEP_OWNER_ACTION)

        assert calendar.visible is True
        assert person.visible is True
        assert calendar.icon_color == afanes.ui.theme.STEP_MUTED_ACTION_COLOR
        assert person.icon_color == afanes.ui.theme.STEP_MUTED_ACTION_COLOR
        assert calendar.style is not None
        assert person.style is not None

    def test_calendar_action_sets_the_plan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path, view, _followed = _open_project(tmp_path, monkeypatch, "# Home\n\n- [ ] Call\n", chosen=PLAN)

        _run(_button(view.root, afanes.ui.strings.PAGE_STEP_PLAN_ACTION).on_click)

        step = StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]
        assert step.plan == PLAN

    def test_clear_action_removes_the_plan(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\n- [ ] Call <!-- {plan: 2026-11-20} -->\n"
        path, view, _followed = _open_project(tmp_path, monkeypatch, body)

        _run(_button(view.root, afanes.ui.strings.PAGE_STEP_CLEAR_PLAN).on_click)

        step = StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]
        assert step.plan is None

    def test_owner_panel_adds_and_removes_owners(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n"
        path, view, _followed = _open_project(tmp_path, monkeypatch, body)

        _run(_button(view.root, afanes.ui.strings.PAGE_STEP_OWNER_ACTION).on_click)
        field = _field(view.root)
        field.value = "Grace"
        _run(field.on_submit)

        step = StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]
        assert step.owners == ("Ada", "Grace")

        chip = next(item for item in _walk(view.root) if isinstance(item, ft.Chip) and item.label == "Ada")
        _run(chip.on_delete)

        step = StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]
        assert step.owners == ("Grace",)

    def test_removing_the_last_owner_clears_the_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n"
        path, view, _followed = _open_project(tmp_path, monkeypatch, body)

        _run(_button(view.root, afanes.ui.strings.PAGE_STEP_OWNER_ACTION).on_click)
        chip = next(item for item in _walk(view.root) if isinstance(item, ft.Chip))
        _run(chip.on_delete)

        step = StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]
        assert step.owners == ()
        assert "owners" not in step.metadata.raw

    def test_owner_suggestions_come_from_note_names(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "reference" / "Ada Lovelace.md", _typed_note("reference", "# Ada Lovelace\n"))
        body = "# Home\n\n- [ ] Call\n"
        path = _write_note(vault / "projects" / "Home.md", _typed_note("project", body, status="active"))
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        state = afanes.ui.state.app_state

        async def follow(_destination: str) -> None:
            return None

        async def pick_date(_current: datetime.date | None) -> datetime.date | None:
            return None

        async def scenario() -> None:
            await state.workspace.choose_vault(vault)
            await state.navigation.open_page(path)

        asyncio.run(scenario())
        view = ProjectBodyView(lambda: None, follow, pick_date)
        _run(_button(view.root, afanes.ui.strings.PAGE_STEP_OWNER_ACTION).on_click)
        field = _field(view.root)
        field.value = "Ada"
        _run(field.on_change)

        tile = next(item for item in _walk(view.root) if isinstance(item, ft.ListTile))
        assert tile.title == "Ada Lovelace"
        _run(tile.on_click)

        step = StepDocument(NoteDocument.from_text(path.read_text(encoding="utf-8")).body).steps[0]
        assert step.owners == ("Ada Lovelace",)
