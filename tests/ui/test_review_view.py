"""Tests for the guided review cards without a rendered window."""

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
import afanes.ui.views.review
import afanes.ui.views.workspace
from afanes.core.frontmatter import NoteDocument
from afanes.models.note import Status

Handler = Callable[[], Coroutine[typing.Any, typing.Any, None]]


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


async def _change_vault() -> None:
    return None


def _write_typed_note(
    path: Path,
    note_type: str,
    *,
    status: str | None = None,
    project: str | None = None,
    due_date: str | None = None,
    body: str = "",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    if project is not None:
        lines.append(f'project: "{project}"')
    lines.extend(["---", body])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: path))


def _choose_vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> afanes.ui.state.AppState:
    _use_settings_file(monkeypatch, tmp_path / "settings.json")
    state = afanes.ui.state.app_state
    asyncio.run(state.choose_vault(tmp_path / "vault"))
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
    if isinstance(control, ft.Text) and isinstance(control.value, str):
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


def _handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_click"))


def _change_handler(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_change"))


class TestReviewEntry:
    def test_zero_pending_shows_the_zero_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())

        view = afanes.ui.views.review.ReviewView(_noop)

        assert state.review_session is None
        assert afanes.ui.strings.REVIEW_ZERO_TITLE in _texts(view.root)

    def test_start_card_starts_a_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        view = afanes.ui.views.review.ReviewView(_noop)

        start = _find_by_key(view.root, "review-start")
        assert isinstance(start, ft.FilledButton)
        asyncio.run(_handler(start)())

        assert state.review_session is not None
        assert state.review_session.current is not None
        assert state.review_session.current.kind is afanes.core.search.ReviewItemKind.PROJECT


class TestProjectReviewCard:
    def test_card_shows_status_due_next_and_other_actions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(
            vault / "projects" / "Launch.md",
            "project",
            status="active",
            due_date="2026-11-20",
            body="# Launch",
        )
        _write_typed_note(
            vault / "actions" / "Write copy.md",
            "action",
            status="active",
            due_date="2026-11-01",
            project="project:Launch",
            body="# Write copy",
        )
        _write_typed_note(
            vault / "actions" / "Update site.md",
            "action",
            status="waiting",
            project="project:Launch",
            body="# Update site",
        )
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        texts = _texts(view.root)

        assert "Launch" in texts
        assert "Status: Active" in texts
        assert "Due 2026-11-20" in texts
        assert afanes.ui.strings.REVIEW_NEXT_STEP in texts
        assert "Write copy" in texts
        assert afanes.ui.strings.REVIEW_OTHER_ACTIONS in texts
        assert "Update site" in texts

    def test_open_project_switches_sections(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        button = _find_by_key(view.root, "review-open-project")
        assert isinstance(button, ft.TextButton)
        asyncio.run(_handler(button)())

        assert state.page is not None
        assert state.page.path == project
        assert state.active_section is afanes.ui.state.WorkspaceSection.PROJECTS

    def test_open_next_action_switches_sections(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        action = _write_typed_note(
            vault / "actions" / "Write copy.md",
            "action",
            status="active",
            project="project:Launch",
            body="# Write copy",
        )
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        button = _find_by_key(view.root, "review-open-action")
        assert isinstance(button, ft.TextButton)
        asyncio.run(_handler(button)())

        assert state.page is not None
        assert state.page.path == action
        assert state.active_section is afanes.ui.state.WorkspaceSection.ACTIONS

    def test_next_advances_the_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        button = _find_by_key(view.root, "review-next")
        assert isinstance(button, ft.FilledButton)
        asyncio.run(_handler(button)())

        assert state.review_session is not None
        assert state.review_session.complete is True
        assert afanes.ui.strings.REVIEW_COMPLETE_TITLE in _texts(view.root)

    def test_skip_leaves_the_project_unchanged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        before = project.read_bytes()
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        button = _find_by_key(view.root, "review-skip")
        assert isinstance(button, ft.TextButton)
        asyncio.run(_handler(button)())

        assert project.read_bytes() == before
        assert state.review_session is not None
        assert state.review_session.skipped_count == 1


class TestStalledProject:
    def test_stalled_card_offers_the_stalled_choices(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        texts = _texts(view.root)

        assert afanes.ui.strings.REVIEW_NO_NEXT_STEP in texts
        assert _find_by_key(view.root, "review-create") is not None
        assert _find_by_key(view.root, "review-mark-done") is not None
        assert _find_by_key(view.root, "review-defer") is not None

    def test_create_form_writes_a_next_action(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        create = _find_by_key(view.root, "review-create")
        assert isinstance(create, ft.OutlinedButton)
        asyncio.run(_handler(create)())

        field = _find_by_key(view.root, "review-action-title")
        assert isinstance(field, ft.TextField)
        field.value = "Build the prototype"
        asyncio.run(_change_handler(field)())

        submit = _find_by_key(view.root, "review-action-submit")
        assert isinstance(submit, ft.FilledButton)
        asyncio.run(_handler(submit)())

        assert (vault / "actions" / "Build the prototype.md").is_file()
        assert afanes.ui.strings.REVIEW_NEXT_STEP in _texts(view.root)
        assert "Build the prototype" in _texts(view.root)
        assert _find_by_key(view.root, "review-action-title") is None

    def test_blank_title_shows_a_form_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        create = _find_by_key(view.root, "review-create")
        assert isinstance(create, ft.OutlinedButton)
        asyncio.run(_handler(create)())

        submit = _find_by_key(view.root, "review-action-submit")
        assert isinstance(submit, ft.FilledButton)
        asyncio.run(_handler(submit)())

        assert afanes.ui.strings.REVIEW_TITLE_REQUIRED in _texts(view.root)
        assert not (vault / "actions").exists()

    def test_mark_done_requires_confirmation_and_writes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        mark = _find_by_key(view.root, "review-mark-done")
        assert isinstance(mark, ft.OutlinedButton)
        asyncio.run(_handler(mark)())
        assert NoteDocument.from_text(project.read_text(encoding="utf-8")).status is Status.ACTIVE

        confirm = _find_by_key(view.root, "review-confirm")
        assert isinstance(confirm, ft.FilledButton)
        asyncio.run(_handler(confirm)())

        assert NoteDocument.from_text(project.read_text(encoding="utf-8")).status is Status.DONE
        assert state.review_session is not None
        assert state.review_session.complete is True

    def test_defer_requires_confirmation_and_writes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        defer = _find_by_key(view.root, "review-defer")
        assert isinstance(defer, ft.OutlinedButton)
        asyncio.run(_handler(defer)())
        assert NoteDocument.from_text(project.read_text(encoding="utf-8")).status is Status.ACTIVE

        confirm = _find_by_key(view.root, "review-confirm")
        assert isinstance(confirm, ft.FilledButton)
        asyncio.run(_handler(confirm)())

        assert NoteDocument.from_text(project.read_text(encoding="utf-8")).status is Status.LATER

    def test_cancelling_a_confirmation_changes_nothing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        project = _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        before = project.read_bytes()
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)

        mark = _find_by_key(view.root, "review-mark-done")
        assert isinstance(mark, ft.OutlinedButton)
        asyncio.run(_handler(mark)())

        cancel = _find_by_key(view.root, "review-cancel-confirmation")
        assert isinstance(cancel, ft.TextButton)
        asyncio.run(_handler(cancel)())

        assert project.read_bytes() == before
        assert _find_by_key(view.root, "review-confirm") is None


class TestReviewCompletion:
    def test_completion_summary_reports_counts_and_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "projects" / "Launch.md", "project", status="active")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.review.ReviewView(_noop)
        skip = _find_by_key(view.root, "review-skip")
        assert isinstance(skip, ft.TextButton)
        asyncio.run(_handler(skip)())

        assert afanes.ui.strings.REVIEW_COMPLETE_BODY.format(reviewed=0, skipped=1) in _texts(view.root)

        finish = _find_by_key(view.root, "review-finish")
        assert isinstance(finish, ft.FilledButton)
        asyncio.run(_handler(finish)())

        assert state.review_session is None
        assert state.active_section is afanes.ui.state.WorkspaceSection.INBOX


class TestReviewProcessing:
    def test_inbox_review_embeds_the_processing_wizard(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "inbox" / "Buy milk.md", "note", body="# Buy milk")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())

        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault)

        assert state.processing_note is not None
        assert _find_by_key(view.main_host, "processing-view") is not None

    def test_cancelling_processing_keeps_the_capture_and_shows_the_card(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        capture = _write_typed_note(vault / "inbox" / "Buy milk.md", "note", body="# Buy milk")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault)

        cancel = _find_by_key(view.main_host, "processing-cancel")
        assert isinstance(cancel, ft.TextButton)
        asyncio.run(_handler(cancel)())

        assert capture.is_file()
        assert state.processing_note is None
        assert _find_by_key(view.main_host, "review-process-capture") is not None

    def test_processing_cancel_then_reopen_uses_explicit_processing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        _write_typed_note(vault / "inbox" / "Buy milk.md", "note", body="# Buy milk")
        state = _choose_vault(tmp_path, monkeypatch)
        asyncio.run(state.start_review())
        view = afanes.ui.views.workspace.WorkspaceView(_noop, _change_vault)

        cancel = _find_by_key(view.main_host, "processing-cancel")
        assert isinstance(cancel, ft.TextButton)
        asyncio.run(_handler(cancel)())

        process = _find_by_key(view.main_host, "review-process-capture")
        assert isinstance(process, ft.FilledButton)
        asyncio.run(_handler(process)())

        assert state.processing_note is not None
        assert _find_by_key(view.main_host, "processing-view") is not None
