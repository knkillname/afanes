"""Tests for the Processing Wizard without a rendered window."""

import asyncio
import datetime
import typing
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.core.vault
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.processing
from afanes.core.processing import ProcessingOutcome
from afanes.models.note import NoteType, ReferenceCategory, Status

TWO_WARNINGS = 2


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _noop() -> None:
    return None


async def _noop_async() -> None:
    return None


def _select_outcome(view: afanes.ui.views.processing.ProcessingView) -> None:
    handler = view.outcome.on_select
    assert handler is not None
    typing.cast("typing.Any", handler)()


async def _click(handler: object) -> None:
    await typing.cast("typing.Any", handler)()


def _trigger(handler: object) -> None:
    typing.cast("typing.Any", handler)()


def _open_capture(body: str = "Buy milk") -> afanes.ui.state.AppState:
    state = afanes.ui.state.app_state
    state.processing_note = Path("/vault/inbox/Buy milk.md")
    state.processing_body = body
    return state


def _open_vault_capture(root: Path, capture: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: root.parent / "settings.json")
    )
    state = afanes.ui.state.app_state

    async def scenario() -> None:
        await state.choose_vault(root)
        await state.begin_processing(capture)

    asyncio.run(scenario())


class TestProcessingView:
    def test_shows_the_capture_and_all_outcomes(self) -> None:
        _open_capture()

        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.capture_title.value == "Buy milk"
        assert view.capture_body.value == "Buy milk"
        assert [option.key for option in view.outcome.options] == ["action", "project", "reference", "later", "trash"]
        assert view.plan_panel.visible is False
        assert view.success_panel.visible is False

    def test_capture_panel_shows_the_heading_title(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = afanes.core.vault.Vault(root).capture("Q1: Planning?")
        monkeypatch.setattr(
            afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: tmp_path / "settings.json")
        )
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await state.choose_vault(root)
            await state.begin_processing(capture)

        asyncio.run(scenario())
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.capture_title.value == "Q1: Planning?"
        assert view.capture_body.value == "# Q1: Planning?"

    def test_action_outcome_reveals_metadata(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.ACTION.value

        _select_outcome(view)

        assert view.status.visible is True
        assert view.due_date.visible is True
        assert view.project.visible is True
        assert view.people.visible is True

    def test_reference_outcome_hides_status_and_project(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.REFERENCE.value

        _select_outcome(view)

        assert view.status.visible is False
        assert view.due_date.visible is False
        assert view.project.visible is False
        assert view.people.visible is True

    def test_trash_outcome_hides_all_metadata(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.TRASH.value

        _select_outcome(view)

        assert view.status.visible is False
        assert view.due_date.visible is False
        assert view.project.visible is False
        assert view.people.visible is False

    def test_plan_preview_shows_the_destination(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Buy milk")
        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)
        state = _open_capture()

        state.processing_plan = plan
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.plan_panel.visible is True
        assert str(plan.target_path) in view.plan_destination.value
        assert "Action" in view.plan_details.value

    def test_plan_preview_shows_scheme_and_unresolved_warnings(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create("Note", NoteType.NOTE, body="[Launch](<note:Launch>)\n")
        capture = vault.capture("Launch")
        plan = vault.plan_processing(capture, ProcessingOutcome.PROJECT, people=("Grace",))
        state = _open_capture("Launch")

        state.processing_plan = plan
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.plan_warnings.visible is True
        assert len(view.plan_warnings.controls) == TWO_WARNINGS
        texts = [control.value for control in view.plan_warnings.controls if isinstance(control, ft.Text)]
        assert any("changes scheme" in text for text in texts)
        assert any("Grace" in text for text in texts)

    def test_success_panel_replaces_the_form(self, tmp_path: Path) -> None:
        state = _open_capture()
        target = tmp_path / "actions" / "Buy milk.md"
        state.processing_result = target

        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.success_panel.visible is True
        assert view.form.visible is False
        assert view.cancel_button.visible is False
        assert view.done_button.visible is True
        assert str(target) in view.success_text.value

    def test_message_is_shown_in_a_banner(self) -> None:
        state = _open_capture()
        state.message = "boom"

        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.banners.visible is True
        assert len(view.banners.controls) == 1

    def test_invalid_due_date_is_reported_without_planning(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.ACTION.value
        _select_outcome(view)
        view.due_date.value = "not-a-date"

        assert view.preview_button.on_click is not None
        asyncio.run(_click(view.preview_button.on_click))

        assert view.form_error.visible is True
        assert view.form_error.value == afanes.ui.strings.PROCESSING_INVALID_DATE
        assert afanes.ui.state.app_state.processing_plan is None

    def test_preview_passes_parsed_values_to_the_controller(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _open_capture()
        calls: list[tuple[ProcessingOutcome, dict[str, object]]] = []

        async def fake_plan(
            _self: afanes.ui.state.AppState,
            outcome: ProcessingOutcome,
            **kwargs: object,
        ) -> None:
            calls.append((outcome, kwargs))

        monkeypatch.setattr(afanes.ui.state.AppState, "plan_processing", fake_plan)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.ACTION.value
        _select_outcome(view)
        view.status.value = "waiting"
        view.due_date.value = "2026-11-20"
        view.people.value = "Ada, Grace"
        view.project.value = "Launch"

        assert view.preview_button.on_click is not None
        asyncio.run(_click(view.preview_button.on_click))

        assert len(calls) == 1
        outcome, kwargs = calls[0]
        status = kwargs["status"]
        assert isinstance(status, Status)
        assert outcome is ProcessingOutcome.ACTION
        assert status is Status.WAITING
        assert kwargs["due_date"] == datetime.date(2026, 11, 20)
        assert kwargs["people"] == ("Ada", "Grace")
        assert kwargs["project"] == "Launch"

    def test_people_suggestions_show_the_title_and_store_the_identity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create(
            "Ada",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
            body="# Ada, Countess of Lovelace\n",
        )
        capture = vault.capture("Plan")
        _open_vault_capture(root, capture, monkeypatch)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.ACTION.value
        _select_outcome(view)
        view.people.value = "Countess"

        _trigger(view.people.on_change)

        assert view.people_suggestions.visible is True
        tile = view.people_suggestions.controls[0]
        assert isinstance(tile, ft.ListTile)
        assert tile.title == "Ada, Countess of Lovelace"
        assert tile.subtitle == "Ada"

        asyncio.run(_click(tile.on_click))

        assert view.people.value == "Ada"
        assert view.people_suggestions.visible is False

    def test_selecting_a_people_suggestion_replaces_only_the_active_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create(
            "Ada",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
            body="# Ada, Countess of Lovelace\n",
        )
        capture = vault.capture("Plan")
        _open_vault_capture(root, capture, monkeypatch)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.ACTION.value
        _select_outcome(view)
        view.people.value = "Grace, Countess"

        _trigger(view.people.on_change)
        tile = view.people_suggestions.controls[0]
        assert isinstance(tile, ft.ListTile)
        asyncio.run(_click(tile.on_click))

        assert view.people.value == "Grace, Ada"

    def test_project_suggestions_store_the_identity(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create(
            "Launch",
            NoteType.PROJECT,
            status=Status.ACTIVE,
            body="# Launch the product\n",
        )
        capture = vault.capture("Plan")
        _open_vault_capture(root, capture, monkeypatch)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.ACTION.value
        _select_outcome(view)
        view.project.value = "product"

        _trigger(view.project.on_change)

        tile = view.project_suggestions.controls[0]
        assert isinstance(tile, ft.ListTile)
        assert tile.title == "Launch the product"
        assert tile.subtitle == "Launch"

        asyncio.run(_click(tile.on_click))

        assert view.project.value == "Launch"

    def test_duplicate_titles_remain_distinct_suggestions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create(
            "Ada",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
            body="# Ada, Countess of Lovelace\n",
        )
        vault.create(
            "Ada King",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
            body="# Ada, Countess of Lovelace\n",
        )
        capture = vault.capture("Plan")
        _open_vault_capture(root, capture, monkeypatch)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.ACTION.value
        _select_outcome(view)
        view.people.value = "Countess"

        _trigger(view.people.on_change)

        tiles = [control for control in view.people_suggestions.controls if isinstance(control, ft.ListTile)]
        assert [tile.title for tile in tiles] == ["Ada, Countess of Lovelace", "Ada, Countess of Lovelace"]
        assert {tile.subtitle for tile in tiles} == {"Ada", "Ada King"}

    def test_unmatched_people_text_stays_free_text(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = afanes.core.vault.Vault(root).capture("Plan")
        _open_vault_capture(root, capture, monkeypatch)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.ACTION.value
        _select_outcome(view)
        view.people.value = "Unknown person"

        _trigger(view.people.on_change)

        assert view.people.value == "Unknown person"
        assert view.people_suggestions.visible is False

    def test_cancel_invokes_the_callback(self) -> None:
        _open_capture()
        called = False

        async def cancel() -> None:
            nonlocal called
            called = True

        view = afanes.ui.views.processing.ProcessingView(_noop, cancel, _noop_async)

        assert view.cancel_button.on_click is not None
        asyncio.run(_click(view.cancel_button.on_click))

        assert called is True
