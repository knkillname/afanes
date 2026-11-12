"""Tests for the guided review cards without a rendered window."""

import asyncio
import datetime
import typing
from collections.abc import Callable, Coroutine
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.review
from afanes.core.frontmatter import NoteDocument
from afanes.core.steps import StepDocument
from afanes.models.note import Status

TODAY = datetime.datetime.now(tz=datetime.UTC).astimezone().date()
Handler = Callable[[], Coroutine[typing.Any, typing.Any, None]]


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


def _write_note(
    path: Path,
    note_type: str,
    *,
    status: str | None = None,
    due_date: str | None = None,
    body: str = "",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    lines.extend(["---", body])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _choose_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> afanes.ui.state.controller.AppState:
    monkeypatch.setattr(
        afanes.core.settings.SettingsStore,
        "settings_path",
        classmethod(lambda _cls: tmp_path / "settings.json"),
    )
    state = afanes.ui.state.app_state
    asyncio.run(state.workspace.choose_vault(tmp_path / "vault"))
    return state


def _find_by_key(control: ft.Control, key: str) -> ft.Control | None:
    if getattr(control, "key", None) == key:
        return control
    for child in getattr(control, "controls", []) or []:
        found = _find_by_key(child, key)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_by_key(content, key)
    return None


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    if isinstance(control, (ft.Text, ft.Markdown)) and isinstance(control.value, str):
        values.append(control.value)
    content_value = getattr(control, "content", None)
    if isinstance(content_value, str):
        values.append(content_value)
    for child in getattr(control, "controls", []) or []:
        values.extend(_texts(child))
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        values.extend(_texts(content))
    return values


def _plain_texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    if isinstance(control, ft.Text) and isinstance(control.value, str):
        values.append(control.value)
    for child in getattr(control, "controls", []) or []:
        values.extend(_plain_texts(child))
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        values.extend(_plain_texts(content))
    return values


def _markdown(control: ft.Control) -> list[ft.Markdown]:
    found: list[ft.Markdown] = []
    if isinstance(control, ft.Markdown):
        found.append(control)
    for child in getattr(control, "controls", []) or []:
        found.extend(_markdown(child))
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        found.extend(_markdown(content))
    return found


def _handler(control: ft.Control | None) -> Handler:
    assert control is not None
    return typing.cast("Handler", control.__getattribute__("on_click"))


def _change_handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_change"))


def _start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> afanes.ui.state.controller.AppState:
    state = _choose_vault(tmp_path, monkeypatch)
    asyncio.run(state.review.start())
    return state


class TestReviewEntry:
    def test_zero_pending_shows_the_zero_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.review.start())

        view = afanes.ui.views.review.ReviewView(_noop)

        assert state.review.review_session is None
        assert afanes.ui.strings.REVIEW_ZERO_TITLE in _texts(view.root)

    def test_start_card_shows_the_pending_count(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Call.md", "note", body="# Call\n")
        _choose_vault(tmp_path, monkeypatch)

        view = afanes.ui.views.review.ReviewView(_noop)

        assert afanes.ui.strings.review_pending(1) in _texts(view.root)
        assert _find_by_key(view.root, "review-start") is not None

    def test_capture_card_processes_and_skips(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "inbox" / "Call.md", "note", body="# Call\n")
        state = _start(tmp_path, monkeypatch)

        view = afanes.ui.views.review.ReviewView(_noop)

        assert afanes.ui.strings.REVIEW_CAPTURE_TITLE in _texts(view.root)
        skip = _find_by_key(view.root, "review-skip")
        assert skip is not None
        asyncio.run(_handler(skip)())
        assert state.review.review_session is not None
        assert state.review.review_session.skipped_count == 1


class TestDueStepCard:
    def _due_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> afanes.ui.state.controller.AppState:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Home.md",
            "project",
            status="active",
            body=f"# Home\n\n- [ ] Call the plumber <!-- {{plan: {TODAY.isoformat()}}} -->\n",
        )
        return _start(tmp_path, monkeypatch)

    def test_card_shows_the_step_and_its_metadata(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._due_step(tmp_path, monkeypatch)

        view = afanes.ui.views.review.ReviewView(_noop)
        texts = _texts(view.root)

        assert afanes.ui.strings.REVIEW_DUE_STEP_TITLE in texts
        assert "Call the plumber" in texts
        assert afanes.ui.strings.PAGE_STEP_PLAN.format(date=TODAY.isoformat()) in texts

    def test_card_renders_step_markdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        path = _write_note(
            vault / "projects" / "Home.md",
            "project",
            status="active",
            body=(
                "# Home\n\n"
                f"- [ ] **Bold** [Incident notes](<note:Incident notes>) <!-- {{plan: {TODAY.isoformat()}}} -->\n"
            ),
        )
        _start(tmp_path, monkeypatch)
        before = path.read_bytes()
        view = afanes.ui.views.review.ReviewView(_noop)

        rendered = [control for control in _markdown(view.root) if "Bold" in control.value]

        assert len(rendered) == 1
        assert rendered[0].value == "**Bold** [Incident notes](<note:Incident notes>)"
        assert rendered[0].on_tap_link is None
        assert all("](" not in text and "**" not in text for text in _plain_texts(view.root))
        assert path.read_bytes() == before

    def test_do_it_now_checks_the_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._due_step(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        button = _find_by_key(view.root, "review-do-now")
        assert button is not None

        asyncio.run(_handler(button)())

        document = NoteDocument.from_text((tmp_path / "vault" / "projects" / "Home.md").read_text(encoding="utf-8"))
        step = StepDocument(document.body).steps[0]
        assert step.checked is True
        assert step.actual == TODAY

    def test_postpone_sets_the_plan_date(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._due_step(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        postpone = _find_by_key(view.root, "review-postpone")
        assert postpone is not None
        asyncio.run(_handler(postpone)())

        field = _find_by_key(view.root, "review-form-field")
        assert isinstance(field, ft.TextField)
        field.value = "2026-12-01"
        asyncio.run(_change_handler(field)())
        submit = _find_by_key(view.root, "review-form-submit")
        assert submit is not None
        asyncio.run(_handler(submit)())

        document = NoteDocument.from_text((tmp_path / "vault" / "projects" / "Home.md").read_text(encoding="utf-8"))
        assert StepDocument(document.body).steps[0].plan == datetime.date(2026, 12, 1)

    def test_invalid_postpone_date_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._due_step(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-postpone"))())
        field = _find_by_key(view.root, "review-form-field")
        assert isinstance(field, ft.TextField)
        field.value = "soon"
        asyncio.run(_change_handler(field)())
        asyncio.run(_handler(_find_by_key(view.root, "review-form-submit"))())

        assert afanes.ui.strings.REVIEW_INVALID_DATE in _texts(view.root)

    def test_delegate_adds_an_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._due_step(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-delegate"))())
        field = _find_by_key(view.root, "review-form-field")
        assert isinstance(field, ft.TextField)
        field.value = "Ada"
        asyncio.run(_change_handler(field)())
        asyncio.run(_handler(_find_by_key(view.root, "review-form-submit"))())

        document = NoteDocument.from_text((tmp_path / "vault" / "projects" / "Home.md").read_text(encoding="utf-8"))
        assert StepDocument(document.body).steps[0].owners == ("Ada",)

    def test_blank_owner_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._due_step(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-delegate"))())
        asyncio.run(_handler(_find_by_key(view.root, "review-form-submit"))())

        assert afanes.ui.strings.REVIEW_TITLE_REQUIRED in _texts(view.root)

    def test_skip_changes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._due_step(tmp_path, monkeypatch)
        before = (tmp_path / "vault" / "projects" / "Home.md").read_bytes()
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-skip"))())

        assert (tmp_path / "vault" / "projects" / "Home.md").read_bytes() == before


class TestWaitingStepCard:
    def _waiting_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> afanes.ui.state.controller.AppState:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Home.md",
            "project",
            status="active",
            body="# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n",
        )
        return _start(tmp_path, monkeypatch)

    def test_card_names_the_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._waiting_step(tmp_path, monkeypatch)

        view = afanes.ui.views.review.ReviewView(_noop)

        assert afanes.ui.strings.REVIEW_WAITING_STEP_TITLE in _texts(view.root)
        assert afanes.ui.strings.REVIEW_STEP_OWNERS.format(owners="Ada") in _texts(view.root)

    def test_card_renders_step_markdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Home.md",
            "project",
            status="active",
            body="# Home\n\n- [ ] **Waiting** [Incident notes](<note:Incident notes>) <!-- {owners: [Ada]} -->\n",
        )
        _start(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)

        rendered = [control for control in _markdown(view.root) if "Waiting" in control.value]

        assert len(rendered) == 1
        assert rendered[0].value == "**Waiting** [Incident notes](<note:Incident notes>)"
        assert all("](" not in text and "**" not in text for text in _plain_texts(view.root))

    def test_reassign_replaces_the_owner(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._waiting_step(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-reassign"))())
        field = _find_by_key(view.root, "review-form-field")
        assert isinstance(field, ft.TextField)
        field.value = "Grace"
        asyncio.run(_change_handler(field)())
        asyncio.run(_handler(_find_by_key(view.root, "review-form-submit"))())

        document = NoteDocument.from_text((tmp_path / "vault" / "projects" / "Home.md").read_text(encoding="utf-8"))
        assert StepDocument(document.body).steps[0].owners == ("Grace",)

    def test_skip_leaves_the_wait_unchanged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._waiting_step(tmp_path, monkeypatch)
        before = (tmp_path / "vault" / "projects" / "Home.md").read_bytes()
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-skip"))())

        assert (tmp_path / "vault" / "projects" / "Home.md").read_bytes() == before


class TestProjectReviewCard:
    def test_card_shows_status_due_next_and_other_steps(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            "project",
            status="active",
            due_date="2026-11-20",
            body="# Launch\n\n- [ ] Write copy\n- [ ] Update site\n",
        )
        _start(tmp_path, monkeypatch)

        view = afanes.ui.views.review.ReviewView(_noop)
        texts = _texts(view.root)

        assert "Launch" in texts
        assert "Status: Active" in texts
        assert "Due 2026-11-20" in texts
        assert afanes.ui.strings.REVIEW_NEXT_STEP in texts
        assert "Write copy" in texts
        assert afanes.ui.strings.REVIEW_OTHER_STEPS in texts
        assert "Update site" in texts

    def test_next_and_other_steps_render_markdown(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(
            vault / "projects" / "Launch.md",
            "project",
            status="active",
            body=("# Launch\n\n- [ ] **Write** [copy](<note:Copy>)\n- [ ] **Update** [site](<note:Site>)\n"),
        )
        _start(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)

        values = [control.value for control in _markdown(view.root)]

        assert "**Write** [copy](<note:Copy>)" in values
        assert "**Update** [site](<note:Site>)" in values
        assert all("](" not in text and "**" not in text for text in _plain_texts(view.root))

    def test_open_project_opens_the_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_note(
            vault / "projects" / "Launch.md",
            "project",
            status="active",
            body="# Launch\n\n- [ ] Write copy\n",
        )
        state = _start(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)

        asyncio.run(_handler(_find_by_key(view.root, "review-open-project"))())

        assert state.pages.page is not None
        assert state.pages.page.path == project

    def test_next_advances_the_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", "project", status="active", body="# Launch\n\n- [ ] One\n")
        state = _start(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)

        asyncio.run(_handler(_find_by_key(view.root, "review-next"))())

        assert state.review.review_session is not None
        assert state.review.review_session.reviewed_count == 1


class TestStalledProject:
    def _stalled(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> afanes.ui.state.controller.AppState:
        vault = tmp_path / "vault"
        _write_note(vault / "projects" / "Launch.md", "project", status="active", body="# Launch\n")
        return _start(tmp_path, monkeypatch)

    def test_add_step_writes_a_task_item(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._stalled(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-create"))())
        field = _find_by_key(view.root, "review-form-field")
        assert isinstance(field, ft.TextField)
        field.value = "Call the plumber"
        asyncio.run(_change_handler(field)())
        asyncio.run(_handler(_find_by_key(view.root, "review-form-submit"))())

        document = NoteDocument.from_text((tmp_path / "vault" / "projects" / "Launch.md").read_text(encoding="utf-8"))
        assert [step.text for step in StepDocument(document.body).steps] == ["Call the plumber"]
        assert afanes.ui.strings.REVIEW_NEXT_STEP in _texts(view.root)

    def test_blank_step_is_rejected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._stalled(tmp_path, monkeypatch)
        before = (tmp_path / "vault" / "projects" / "Launch.md").read_bytes()
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-create"))())
        asyncio.run(_handler(_find_by_key(view.root, "review-form-submit"))())

        assert afanes.ui.strings.REVIEW_TITLE_REQUIRED in _texts(view.root)
        assert (tmp_path / "vault" / "projects" / "Launch.md").read_bytes() == before

    def test_cancel_add_changes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._stalled(tmp_path, monkeypatch)
        before = (tmp_path / "vault" / "projects" / "Launch.md").read_bytes()
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-create"))())
        asyncio.run(_handler(_find_by_key(view.root, "review-form-cancel"))())

        assert (tmp_path / "vault" / "projects" / "Launch.md").read_bytes() == before

    def test_mark_done_closes_the_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._stalled(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-mark-done"))())
        asyncio.run(_handler(_find_by_key(view.root, "review-confirm"))())

        document = NoteDocument.from_text((tmp_path / "vault" / "projects" / "Launch.md").read_text(encoding="utf-8"))
        assert document.status is Status.DONE

    def test_defer_leaves_the_project_open(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._stalled(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)
        asyncio.run(_handler(_find_by_key(view.root, "review-defer"))())
        asyncio.run(_handler(_find_by_key(view.root, "review-confirm"))())

        document = NoteDocument.from_text((tmp_path / "vault" / "projects" / "Launch.md").read_text(encoding="utf-8"))
        assert document.status is Status.LATER
