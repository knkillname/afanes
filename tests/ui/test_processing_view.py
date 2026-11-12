"""Tests for the Processing Wizard without a rendered window."""

import asyncio
import datetime
import typing
from pathlib import Path

import flet as ft
import pytest

import afanes.core.settings
import afanes.core.template_cards
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.views.processing
from afanes.core.processing import ProcessingOutcome, ProcessingPlan
from afanes.models.note import CategoryLabel, NoteType, Status


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


def _open_capture(body: str = "Buy milk") -> afanes.ui.state.controller.AppState:
    state = afanes.ui.state.app_state
    state.processing.note = Path("/vault/inbox/Buy milk.md")
    state.processing.body = body
    return state


def _open_vault_capture(root: Path, capture: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: root.parent / "settings.json")
    )
    state = afanes.ui.state.app_state

    async def scenario() -> None:
        await state.workspace.choose_vault(root)
        await state.processing.begin(capture)

    asyncio.run(scenario())


def _card(
    *,
    title: str = "Person",
    category: str = "person",
    path: str = "person.md",
    description: str | None = "A contact.",
    body: str = "## Contact\n",
) -> afanes.core.template_cards.TemplateCard:
    return afanes.core.template_cards.TemplateCard(
        relative_path=Path(path),
        note_type=NoteType.REFERENCE,
        category=CategoryLabel(category),
        title=title,
        description=description,
        body=body,
        text="",
    )


class TestProcessingView:
    def test_shows_the_capture_and_all_outcomes(self) -> None:
        _open_capture()

        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.capture_title.value == "Buy milk"
        assert view.capture_body.value == "Buy milk"
        assert view.capture_body.extension_set is ft.MarkdownExtensionSet.GITHUB_FLAVORED
        assert [option.key for option in view.outcome.options] == [
            "project",
            "done_now",
            "append_step",
            "reference",
            "later",
            "trash",
        ]
        assert view.plan_panel.visible is False
        assert view.success_panel.visible is False

    def test_capture_panel_shows_the_heading_title(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Q1: Planning?")
        _open_vault_capture(root, capture, monkeypatch)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.capture_title.value == "Q1: Planning?"
        assert view.capture_body.value == "# Q1: Planning?"

    def test_project_outcome_reveals_status_and_due_date(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.PROJECT.value

        _select_outcome(view)

        assert view.status.visible is True
        assert view.due_date.visible is True
        assert view.project.visible is False

    def test_append_outcome_reveals_the_project_field(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.APPEND_STEP.value

        _select_outcome(view)

        assert view.status.visible is False
        assert view.due_date.visible is False
        assert view.project.visible is True

    def test_reference_outcome_hides_metadata(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.REFERENCE.value

        _select_outcome(view)

        assert view.status.visible is False
        assert view.due_date.visible is False
        assert view.project.visible is False
        assert view.template.visible is True
        assert view.template_description.visible is True

    def test_later_outcome_reveals_the_template_picker(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.LATER.value

        _select_outcome(view)

        assert view.template.visible is True
        assert view.template_description.visible is True

    def test_project_outcome_hides_the_template_picker(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.PROJECT.value

        _select_outcome(view)

        assert view.template.visible is False
        assert view.template_description.visible is False

    def test_trash_outcome_hides_all_metadata(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.TRASH.value

        _select_outcome(view)

        assert view.status.visible is False
        assert view.due_date.visible is False
        assert view.project.visible is False
        assert view.template.visible is False

    def test_template_options_list_cards_then_empty(self) -> None:
        state = _open_capture()
        state.processing.cards = (
            _card(),
            _card(title="Place", category="place", path="place.md", description="A location."),
        )

        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert [option.key for option in view.template.options] == [
            "card:person.md",
            "card:place.md",
            "empty",
        ]
        assert view.template.value == "empty"

    def test_template_options_refresh_when_the_catalog_changes(self) -> None:
        state = _open_capture()
        state.processing.cards = (_card(),)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        state.processing.cards = (_card(title="Place", category="place", path="place.md"),)
        view.outcome.value = ProcessingOutcome.REFERENCE.value

        _select_outcome(view)

        assert [option.key for option in view.template.options] == ["card:place.md", "empty"]

    def test_refresh_keeps_a_valid_template_selection(self) -> None:
        state = _open_capture()
        state.processing.cards = (_card(),)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.template.value = "card:person.md"
        state.processing.cards = (_card(), _card(title="Place", category="place", path="place.md"))
        view.outcome.value = ProcessingOutcome.REFERENCE.value

        _select_outcome(view)

        assert view.template.value == "card:person.md"

    def test_refresh_resets_a_removed_template_to_empty(self) -> None:
        state = _open_capture()
        state.processing.cards = (_card(),)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.template.value = "card:person.md"
        state.processing.cards = ()
        view.outcome.value = ProcessingOutcome.REFERENCE.value

        _select_outcome(view)

        assert view.template.value == "empty"
        assert [option.key for option in view.template.options] == ["empty"]

    def test_selecting_a_card_shows_its_description(self) -> None:
        state = _open_capture()
        state.processing.cards = (_card(description="A contact."),)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.REFERENCE.value
        _select_outcome(view)
        view.template.value = "card:person.md"

        _select_outcome(view)

        assert view.template_description.value == "A contact."

    def test_empty_describes_the_general_category(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.REFERENCE.value

        _select_outcome(view)

        assert view.template_description.value == afanes.ui.strings.PROCESSING_TEMPLATE_DESCRIPTION_EMPTY

    def test_a_card_without_a_description_says_so(self) -> None:
        state = _open_capture()
        state.processing.cards = (_card(description=None),)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.REFERENCE.value
        _select_outcome(view)
        view.template.value = "card:person.md"

        _select_outcome(view)

        assert view.template_description.value == afanes.ui.strings.PROCESSING_TEMPLATE_NO_DESCRIPTION

    def test_duplicate_titles_show_the_card_path(self) -> None:
        state = _open_capture()
        state.processing.cards = (
            _card(title="Same", path="alpha.md"),
            _card(title="Same", path="zeta.md"),
        )

        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        texts = [option.text or "" for option in view.template.options]
        assert "alpha.md" in texts[0]
        assert "zeta.md" in texts[1]

    def test_invalid_cards_show_a_warning(self) -> None:
        state = _open_capture()
        state.processing.card_issues = (
            afanes.core.template_cards.TemplateCardIssue(relative_path=Path("broken.md"), message="bad"),
        )
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.REFERENCE.value

        _select_outcome(view)

        assert view.template_warning.visible is True
        assert "broken.md" in view.template_warning.value

    def test_plan_preview_shows_the_destination(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Buy milk")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(capture, ProcessingOutcome.PROJECT)
        assert isinstance(plan, ProcessingPlan)
        state = _open_capture()

        state.processing.plan = plan
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.plan_panel.visible is True
        assert str(plan.target_path) in view.plan_destination.value
        assert "Project" in view.plan_details.value

    def test_plan_preview_names_the_category_and_starter_body(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Approve the invoice")
        card = afanes.core.template_cards.TemplateCard(
            relative_path=Path("process.md"),
            note_type=NoteType.REFERENCE,
            category=CategoryLabel("process"),
            title="Process",
            description="A procedure.",
            body="## Steps\n",
            text="",
        )
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            capture, ProcessingOutcome.REFERENCE, card=card
        )
        assert isinstance(plan, ProcessingPlan)
        state = _open_capture("Approve the invoice")

        state.processing.plan = plan
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert "Category: process" in view.plan_details.value
        assert afanes.ui.strings.PROCESSING_PLAN_SCAFFOLD in view.plan_details.value

    def test_plan_preview_names_general_for_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Approve the invoice")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(capture, ProcessingOutcome.REFERENCE)
        assert isinstance(plan, ProcessingPlan)
        state = _open_capture("Approve the invoice")

        state.processing.plan = plan
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert "Category: general" in view.plan_details.value
        assert afanes.ui.strings.PROCESSING_PLAN_SCAFFOLD not in view.plan_details.value

    def test_plan_preview_shows_the_scheme_warning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        note = vault.create("Note", NoteType.REFERENCE, body="[Launch](<note:Launch>)\n")
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Launch")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(capture, ProcessingOutcome.PROJECT)
        state = _open_capture("Launch")
        assert note.is_file()

        state.processing.plan = plan
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.plan_warnings.visible is True
        texts = [control.value for control in view.plan_warnings.controls if isinstance(control, ft.Text)]
        assert any("changes scheme" in text for text in texts)

    def test_append_preview_shows_the_project_and_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n")
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Call the plumber")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            capture, ProcessingOutcome.APPEND_STEP, project="Home"
        )
        state = _open_capture("Call the plumber")

        state.processing.plan = plan
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert str(project) in view.plan_destination.value
        assert "Call the plumber" in view.plan_details.value

    def test_success_panel_replaces_the_form(self, tmp_path: Path) -> None:
        state = _open_capture()
        target = tmp_path / "projects" / "Buy milk.md"
        state.processing.result = target

        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.success_panel.visible is True
        assert view.form.visible is False
        assert view.cancel_button.visible is False
        assert view.done_button.visible is True
        assert str(target) in view.success_text.value

    def test_message_is_shown_in_a_banner(self) -> None:
        state = _open_capture()
        state.status.message = "boom"

        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)

        assert view.banners.visible is True
        assert len(view.banners.controls) == 1

    def test_invalid_due_date_is_reported_without_planning(self) -> None:
        _open_capture()
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.PROJECT.value
        _select_outcome(view)
        view.due_date.value = "not-a-date"

        assert view.preview_button.on_click is not None
        asyncio.run(_click(view.preview_button.on_click))

        assert view.form_error.visible is True
        assert view.form_error.value == afanes.ui.strings.PROCESSING_INVALID_DATE
        assert afanes.ui.state.app_state.processing.plan is None

    def test_preview_passes_parsed_values_to_the_controller(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _open_capture()
        calls: list[tuple[ProcessingOutcome, dict[str, object]]] = []

        async def fake_plan(
            _self: afanes.ui.state.processing.ProcessingState,
            outcome: ProcessingOutcome,
            **kwargs: object,
        ) -> None:
            calls.append((outcome, kwargs))

        monkeypatch.setattr(afanes.ui.state.processing.ProcessingState, "build_plan", fake_plan)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.PROJECT.value
        _select_outcome(view)
        view.status.value = "waiting"
        view.due_date.value = "2026-11-20"

        assert view.preview_button.on_click is not None
        asyncio.run(_click(view.preview_button.on_click))

        assert len(calls) == 1
        outcome, kwargs = calls[0]
        status = kwargs["status"]
        assert isinstance(status, Status)
        assert outcome is ProcessingOutcome.PROJECT
        assert status is Status.WAITING
        assert kwargs["due_date"] == datetime.date(2026, 11, 20)
        assert kwargs["project"] is None

    def test_append_preview_passes_the_project_identity(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _open_capture()
        calls: list[tuple[ProcessingOutcome, dict[str, object]]] = []

        async def fake_plan(
            _self: afanes.ui.state.processing.ProcessingState,
            outcome: ProcessingOutcome,
            **kwargs: object,
        ) -> None:
            calls.append((outcome, kwargs))

        monkeypatch.setattr(afanes.ui.state.processing.ProcessingState, "build_plan", fake_plan)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.APPEND_STEP.value
        _select_outcome(view)
        view.project.value = "Launch"

        asyncio.run(_click(view.preview_button.on_click))

        assert calls[0][0] is ProcessingOutcome.APPEND_STEP
        assert calls[0][1]["project"] == "Launch"

    def test_reference_preview_passes_the_selected_card(self, monkeypatch: pytest.MonkeyPatch) -> None:
        state = _open_capture()
        card = _card()
        state.processing.cards = (card,)
        calls: list[tuple[ProcessingOutcome, dict[str, object]]] = []

        async def fake_plan(
            _self: afanes.ui.state.processing.ProcessingState,
            outcome: ProcessingOutcome,
            **kwargs: object,
        ) -> None:
            calls.append((outcome, kwargs))

        monkeypatch.setattr(afanes.ui.state.processing.ProcessingState, "build_plan", fake_plan)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.REFERENCE.value
        _select_outcome(view)
        view.template.value = "card:person.md"

        assert view.preview_button.on_click is not None
        asyncio.run(_click(view.preview_button.on_click))

        assert calls[0][0] is ProcessingOutcome.REFERENCE
        assert calls[0][1]["card"] is card

    def test_reference_preview_passes_empty_as_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _open_capture()
        calls: list[tuple[ProcessingOutcome, dict[str, object]]] = []

        async def fake_plan(
            _self: afanes.ui.state.processing.ProcessingState,
            outcome: ProcessingOutcome,
            **kwargs: object,
        ) -> None:
            calls.append((outcome, kwargs))

        monkeypatch.setattr(afanes.ui.state.processing.ProcessingState, "build_plan", fake_plan)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.LATER.value
        _select_outcome(view)

        assert view.preview_button.on_click is not None
        asyncio.run(_click(view.preview_button.on_click))

        assert calls[0][1]["card"] is None

    def test_project_suggestions_store_the_identity(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        vault.create("Launch", NoteType.PROJECT, body="# Launch the product\n")
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Plan")
        _open_vault_capture(root, capture, monkeypatch)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.APPEND_STEP.value
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
        vault = afanes.core.vault.service.Vault(root)
        vault.create("Home", NoteType.PROJECT, body="# Home improvements\n")
        vault.create("Cabin", NoteType.PROJECT, body="# Home improvements\n")
        capture = afanes.core.vault.pages.VaultPages(vault).capture("Plan")
        _open_vault_capture(root, capture, monkeypatch)
        view = afanes.ui.views.processing.ProcessingView(_noop, _noop_async, _noop_async)
        view.outcome.value = ProcessingOutcome.APPEND_STEP.value
        _select_outcome(view)
        view.project.value = "improvements"

        _trigger(view.project.on_change)

        tiles = [control for control in view.project_suggestions.controls if isinstance(control, ft.ListTile)]
        assert [tile.title for tile in tiles] == ["Home improvements", "Home improvements"]
        assert {tile.subtitle for tile in tiles} == {"Cabin", "Home"}

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
