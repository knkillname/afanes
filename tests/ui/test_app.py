"""Tests for the application shell routing without a rendered window."""

import asyncio
import json
import typing
from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft
import pytest

import afanes.__about__
import afanes.core.settings
import afanes.core.templates
import afanes.core.vault.pages
import afanes.core.vault.schema
import afanes.core.vault.service
import afanes.core.vault.snapshot
import afanes.ui.app
import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
import afanes.ui.views.page
import afanes.ui.views.workspace
from afanes.core.errors import TemplateContentError
from afanes.core.frontmatter import NoteDocument
from afanes.core.settings import Settings
from afanes.models.note import CategoryLabel
from tests.support import versioned

Handler = Callable[[], Awaitable[None]]
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 760
WIDE_REGION_COUNT = 3
MEDIUM_REGION_COUNT = 2


class FakeWindow:
    width = 0
    height = 0
    min_width = 0
    min_height = 0


class FakePage:
    def __init__(self, *, web: bool = False) -> None:
        self.title = ""
        self.theme_mode = ft.ThemeMode.SYSTEM
        self.theme: ft.Theme | None = None
        self.dark_theme: ft.Theme | None = None
        self.bgcolor: str | None = None
        self.padding = 0
        self.window = FakeWindow()
        self.services: list[object] = []
        self.controls: list[ft.Control] = []
        self.updates = 0
        self.web = web
        self.width = WINDOW_WIDTH
        self.height = WINDOW_HEIGHT
        self.on_resize: Callable[..., None] | None = None
        self.on_keyboard_event: Callable[..., Awaitable[None]] | None = None
        self.on_disconnect: Callable[[], None] | None = None
        self.dialogs: list[ft.AlertDialog] = []

    def add(self, control: ft.Control) -> None:
        self.controls.append(control)

    def update(self) -> None:
        self.updates += 1

    def show_dialog(self, dialog: ft.AlertDialog) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self) -> ft.AlertDialog | None:
        return self.dialogs.pop() if self.dialogs else None


class FakePicker:
    def __init__(self, selected: str | None) -> None:
        self.selected = selected
        self.calls = 0

    async def get_directory_path(self, **_: object) -> str | None:
        self.calls += 1
        return self.selected


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


def _welcome_button(control: ft.Control, key: str = "welcome-choose") -> ft.FilledButton:
    assert isinstance(control, ft.Container)
    return _typed(_find_by_key(control, key), ft.FilledButton)


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: path))


def _adoptable(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for folder in afanes.core.vault.schema.DEFAULT_FOLDERS:
        (root / folder).mkdir()
    return root


def _find_by_key(control: ft.Control, key: str) -> ft.Control | None:
    if getattr(control, "key", None) == key:
        return control
    for child in getattr(control, "controls", []) or []:
        found = _find_by_key(child, key)
        if found is not None:
            return found
    for child in getattr(control, "actions", []) or []:
        found = _find_by_key(child, key)
        if found is not None:
            return found
    for child in getattr(control, "items", []) or []:
        found = _find_by_key(child, key)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_by_key(content, key)
    return None


def _typed[T: ft.Control](control: ft.Control | None, expected: type[T]) -> T:
    assert isinstance(control, expected)
    return control


def _find_span(control: ft.Control, text: str) -> ft.TextSpan | None:
    if isinstance(control, ft.Text):
        for span in control.spans or []:
            found = _find_span_in(span, text)
            if found is not None:
                return found
    for child in getattr(control, "controls", []) or []:
        found = _find_span(child, text)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_span(content, text)
    return None


def _find_span_in(span: object, text: str) -> ft.TextSpan | None:
    if not isinstance(span, ft.TextSpan):
        return None
    if span.text == text:
        return span
    for child in span.spans or []:
        found = _find_span_in(child, text)
        if found is not None:
            return found
    return None


def _find_button_by_label(control: ft.Control, label: str) -> ft.FilledButton | None:
    if isinstance(control, ft.FilledButton) and control.content == label:
        return control
    for child in getattr(control, "controls", []) or []:
        found = _find_button_by_label(child, label)
        if found is not None:
            return found
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        return _find_button_by_label(content, label)
    return None


class TestAppShell:
    def test_without_settings_shows_the_welcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert isinstance(page.controls[0], ft.Container)
        assert afanes.ui.state.app_state.session.vault_root is None

    def test_choosing_a_vault_opens_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        picker = FakePicker(str(vault))
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            button = _welcome_button(page.controls[0])
            handler = typing.cast("Handler", button.on_click)
            await handler()

        asyncio.run(scenario())

        assert afanes.ui.state.app_state.session.vault_root == vault.resolve()
        assert isinstance(page.controls[0], ft.Stack)
        assert settings.is_file()

    def test_cancelling_the_picker_keeps_the_welcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        picker = FakePicker(None)
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            button = _welcome_button(page.controls[0])
            handler = typing.cast("Handler", button.on_click)
            await handler()

        asyncio.run(scenario())

        assert afanes.ui.state.app_state.session.vault_root is None
        assert isinstance(page.controls[0], ft.Container)
        assert not settings.exists()

    def test_saved_settings_reopen_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert afanes.ui.state.app_state.session.vault_root == vault.resolve()
        assert isinstance(page.controls[0], ft.Stack)

    def test_process_action_opens_the_wizard_and_cancel_returns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("Buy milk")
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            await state.navigation.open_page(state.session.notes[0].path)
            process_button = _find_by_key(page.controls[0], "process-note")
            assert isinstance(process_button, ft.TextButton)
            process_handler = typing.cast("Handler", process_button.on_click)
            await process_handler()

            assert state.processing.note is not None
            assert _find_by_key(page.controls[0], "processing-view") is not None

            cancel_button = _find_by_key(page.controls[0], "processing-cancel")
            assert isinstance(cancel_button, ft.TextButton)
            cancel_handler = typing.cast("Handler", cancel_button.on_click)
            await cancel_handler()

        asyncio.run(scenario())

        assert state.processing.note is None
        assert _find_by_key(page.controls[0], "processing-view") is None
        assert _find_by_key(page.controls[0], "process-note") is not None


class TestLogEntryDialog:
    def test_empty_option_describes_a_log_entry_without_a_reference_category(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        page = FakePage()

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            section = _typed(_find_by_key(page.controls[0], "section-log"), ft.ListTile)
            await typing.cast("Handler", section.on_click)()
            today = _typed(_find_by_key(page.controls[0], "log-today-entry"), ft.TextButton)
            await typing.cast("Handler", today.on_click)()

        asyncio.run(scenario())

        selector = _typed(_find_by_key(page.dialogs[-1], "new-log-template"), ft.Dropdown)
        empty = selector.options[-1]
        assert empty.text == afanes.ui.strings.LOG_CARD_EMPTY
        assert "starter body" in (empty.text or "")
        assert "category" not in (empty.text or "").casefold()
        description = _typed(_find_by_key(page.dialogs[-1], "new-log-template-description"), ft.Text)
        assert description.value == afanes.ui.strings.LOG_CARD_DESCRIPTION_EMPTY
        assert "category" not in (description.value or "").casefold()


class TestAdoptionPanel:
    def test_adoptable_remembered_folder_shows_the_panel(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = _adoptable(tmp_path / "vault")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        afanes.core.settings.SettingsStore(tmp_path / "settings.json").save(Settings(vault=vault))
        page = FakePage()
        state = afanes.ui.state.app_state

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        panel = _find_by_key(page.controls[0], "adoption-panel")
        assert isinstance(panel, ft.Container)
        assert afanes.ui.strings.VAULT_SCHEMA_ADOPT_TITLE in _all_texts(panel)
        confirm = _typed(_find_by_key(panel, "adoption-confirm"), ft.FilledButton)
        cancel = _typed(_find_by_key(panel, "adoption-cancel"), ft.TextButton)
        assert confirm.content == afanes.ui.strings.VAULT_SCHEMA_ADOPT_ACTION
        assert cancel.content == afanes.ui.strings.CANCEL_ACTION
        assert state.session.vault_root is None
        assert state.session.adoption_target == vault.resolve()
        assert not (vault / "afanes.yaml").exists()

    def test_confirming_adoption_writes_the_file_and_opens_the_vault(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = _adoptable(tmp_path / "vault")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            panel = _typed(_find_by_key(page.controls[0], "adoption-panel"), ft.Container)
            confirm = _typed(_find_by_key(panel, "adoption-confirm"), ft.FilledButton)
            await typing.cast("Handler", confirm.on_click)()

        asyncio.run(scenario())

        assert (vault / "afanes.yaml").read_text(encoding="utf-8") == "schema_version: 1\n"
        assert state.session.vault_root == vault.resolve()
        assert state.session.adoption_target is None
        assert _find_by_key(page.controls[0], "adoption-panel") is None
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(vault.resolve())

    def test_cancelling_adoption_leaves_the_folder_unmodified(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = _adoptable(tmp_path / "vault")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        afanes.core.settings.SettingsStore(tmp_path / "settings.json").save(Settings(vault=vault))
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            panel = _typed(_find_by_key(page.controls[0], "adoption-panel"), ft.Container)
            cancel = _typed(_find_by_key(panel, "adoption-cancel"), ft.TextButton)
            await typing.cast("Handler", cancel.on_click)()

        asyncio.run(scenario())

        assert state.session.adoption_target is None
        assert state.session.vault_root is None
        assert _find_by_key(page.controls[0], "adoption-panel") is None
        assert isinstance(page.controls[0], ft.Container)
        assert not (vault / "afanes.yaml").exists()


class TestDesktopPresentation:
    def test_desktop_session_configures_the_window(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert page.window.width == WINDOW_WIDTH
        assert page.window.height == WINDOW_HEIGHT
        assert len(page.services) == 1
        assert page.theme_mode is ft.ThemeMode.SYSTEM
        assert page.theme is afanes.ui.theme.LIGHT_THEME
        assert page.dark_theme is afanes.ui.theme.DARK_THEME
        assert page.theme is not page.dark_theme
        assert page.bgcolor == afanes.ui.theme.PAGE_SURFACE_COLOR

    def test_desktop_welcome_has_no_path_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert _find_by_key(page.controls[0], "welcome-path") is None
        assert _welcome_button(page.controls[0]).content == afanes.ui.strings.WELCOME_CHOOSE
        create = _welcome_button(page.controls[0], "welcome-create")
        assert create.content == afanes.ui.strings.NEW_VAULT_ACTION


class TestWebPresentation:
    def test_web_session_skips_window_configuration(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage(web=True)

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert page.window.width == 0
        assert page.window.height == 0
        assert page.services == []

    def test_web_welcome_offers_a_path_field(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage(web=True)

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        field = _typed(_find_by_key(page.controls[0], "welcome-path"), ft.TextField)
        assert field.label == afanes.ui.strings.WELCOME_PATH_LABEL
        assert _welcome_button(page.controls[0], "welcome-open").content == afanes.ui.strings.WELCOME_OPEN
        assert _welcome_button(page.controls[0], "welcome-create").content == afanes.ui.strings.NEW_VAULT_ACTION

    def test_entering_a_path_opens_the_inbox(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("Buy milk")
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            field = _typed(_find_by_key(page.controls[0], "welcome-path"), ft.TextField)
            field.value = str(vault)
            button = _typed(_find_by_key(page.controls[0], "welcome-open"), ft.FilledButton)
            handler = typing.cast("Handler", button.on_click)
            await handler()

        asyncio.run(scenario())

        assert state.session.vault_root == vault.resolve()
        assert [note.name for note in state.session.notes] == ["Buy milk"]
        assert isinstance(page.controls[0], ft.Stack)
        assert settings.is_file()

    def test_invalid_path_keeps_the_welcome(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            field = _typed(_find_by_key(page.controls[0], "welcome-path"), ft.TextField)
            field.value = str(tmp_path / "missing")
            button = _typed(_find_by_key(page.controls[0], "welcome-open"), ft.FilledButton)
            handler = typing.cast("Handler", button.on_click)
            await handler()

        asyncio.run(scenario())

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_MISSING
        assert isinstance(page.controls[0], ft.Container)
        assert not settings.exists()

    def test_change_vault_dialog_switches_the_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        first = tmp_path / "first"
        versioned(first)
        second = tmp_path / "second"
        versioned(second)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=first))
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            change = _typed(_find_by_key(page.controls[0], "workspace-change-open"), ft.PopupMenuItem)
            change_handler = typing.cast("Handler", change.on_click)
            await change_handler()

            assert len(page.dialogs) == 1
            field = _typed(_find_by_key(page.dialogs[0], "change-vault-path"), ft.TextField)
            field.value = str(second)
            open_button = _typed(_find_by_key(page.dialogs[0], "change-vault-open"), ft.FilledButton)
            open_handler = typing.cast("Handler", open_button.on_click)
            await open_handler()

        asyncio.run(scenario())

        assert state.session.vault_root == second.resolve()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(second.resolve())

    def test_change_vault_dialog_cancel_keeps_the_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        first = tmp_path / "first"
        versioned(first)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=first))
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            change = _typed(_find_by_key(page.controls[0], "workspace-change-open"), ft.PopupMenuItem)
            change_handler = typing.cast("Handler", change.on_click)
            await change_handler()
            cancel = _typed(_find_by_key(page.dialogs[0], "change-vault-cancel"), ft.TextButton)
            cancel_handler = typing.cast("Handler", cancel.on_click)
            await cancel_handler()

        asyncio.run(scenario())

        assert page.dialogs == []
        assert state.session.vault_root == first.resolve()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(first.resolve())


class TestLaunchVault:
    def test_supplied_vault_overrides_the_remembered_one(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        remembered = tmp_path / "remembered"
        remembered.mkdir()
        supplied = versioned(tmp_path / "supplied")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=remembered))
        page = FakePage()
        state = afanes.ui.state.app_state

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page), launch_vault=supplied))

        assert state.session.vault_root == supplied.resolve()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(remembered.resolve())


class TestSessionGuard:
    def test_second_session_gets_a_notice(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(vault)).capture("Buy milk")
        first = FakePage()
        second = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", first))
            await afanes.ui.app.main(typing.cast("ft.Page", second))

        asyncio.run(scenario())

        assert state.status.session_active is True
        assert [note.name for note in state.session.notes] == ["Buy milk"]
        assert _find_by_key(second.controls[0], "session-retry") is not None
        assert _find_by_key(second.controls[0], "welcome-path") is None

    def test_a_second_session_does_not_adopt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = _adoptable(tmp_path / "vault")
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        afanes.core.settings.SettingsStore(tmp_path / "settings.json").save(Settings(vault=vault))
        first = FakePage()
        second = FakePage(web=True)

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", first))
            await afanes.ui.app.main(typing.cast("ft.Page", second))

        asyncio.run(scenario())

        assert _find_by_key(first.controls[0], "adoption-panel") is not None
        assert _find_by_key(second.controls[0], "session-retry") is not None
        assert not (vault / "afanes.yaml").exists()

    def test_disconnect_releases_the_session(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        first = FakePage()
        second = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", first))
            await afanes.ui.app.main(typing.cast("ft.Page", second))
            assert first.on_disconnect is not None
            first.on_disconnect()

            retry = _typed(_find_by_key(second.controls[0], "session-retry"), ft.FilledButton)
            handler = typing.cast("Handler", retry.on_click)
            await handler()

        asyncio.run(scenario())

        assert state.status.session_active is True
        assert _find_by_key(second.controls[0], "session-retry") is None
        assert isinstance(second.controls[0], ft.Container)


def _refresh_tasks() -> list[asyncio.Task[object]]:
    current = asyncio.current_task()
    return [
        task
        for task in asyncio.all_tasks()
        if task is not current and task.get_name() == afanes.ui.app.REFRESH_TASK_NAME
    ]


class TestRefreshLoop:
    def test_a_claimed_session_starts_one_refresh_task(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        page = FakePage()

        async def scenario() -> int:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            return len(_refresh_tasks())

        assert asyncio.run(scenario()) == 1

    def test_a_second_session_creates_no_refresh_task(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        first = FakePage()
        second = FakePage(web=True)

        async def scenario() -> int:
            await afanes.ui.app.main(typing.cast("ft.Page", first))
            await afanes.ui.app.main(typing.cast("ft.Page", second))
            return len(_refresh_tasks())

        assert asyncio.run(scenario()) == 1

    def test_a_rejected_session_scans_nothing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        first = FakePage()
        second = FakePage(web=True)
        scans = 0
        original = afanes.core.vault.service.Vault.scan

        async def scenario() -> None:
            nonlocal scans
            await afanes.ui.app.main(typing.cast("ft.Page", first))

            def counting_scan(current: afanes.core.vault.service.Vault) -> afanes.core.vault.snapshot.VaultSnapshot:
                nonlocal scans
                scans += 1
                return original(current)

            monkeypatch.setattr(afanes.core.vault.service.Vault, "scan", counting_scan)
            await afanes.ui.app.main(typing.cast("ft.Page", second))

        asyncio.run(scenario())

        assert scans == 0
        assert _find_by_key(second.controls[0], "session-retry") is not None

    def test_closing_the_vault_leaves_no_running_task(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> int:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            close = _typed(_find_by_key(page.controls[0], "workspace-close-vault"), ft.PopupMenuItem)
            handler = typing.cast("Handler", close.on_click)
            await handler()
            return len(_refresh_tasks())

        assert asyncio.run(scenario()) == 0
        assert state.session.vault_root is None


async def _submit_creation(page: FakePage, path_text: Path | None = None) -> None:
    dialog = page.dialogs[-1]
    if path_text is not None:
        field = _typed(_find_by_key(dialog, "create-vault-path"), ft.TextField)
        field.value = str(path_text)
    submit = _typed(_find_by_key(dialog, "create-vault-submit"), ft.FilledButton)
    await typing.cast("Handler", submit.on_click)()


async def _browse_creation(page: FakePage) -> None:
    browse = _typed(_find_by_key(page.dialogs[-1], "create-vault-browse"), ft.TextButton)
    await typing.cast("Handler", browse.on_click)()


def _select_template(page: FakePage, identifier: str) -> None:
    selector = _typed(_find_by_key(page.dialogs[-1], "create-vault-template"), ft.Dropdown)
    selector.value = identifier
    handler = selector.on_select
    assert handler is not None
    typing.cast("typing.Any", handler)()


async def _open_reference_dialog(page: FakePage) -> None:
    tile = _typed(_find_by_key(page.controls[0], "section-references"), ft.ListTile)
    await typing.cast("Handler", tile.on_click)()
    button = _typed(_find_by_key(page.controls[0], "browser-new-reference"), ft.IconButton)
    await typing.cast("Handler", button.on_click)()


async def _submit_reference(page: FakePage, name: str, template: str = "empty") -> None:
    dialog = page.dialogs[-1]
    name_field = _typed(_find_by_key(dialog, "new-reference-name"), ft.TextField)
    name_field.value = name
    selector = _typed(_find_by_key(dialog, "new-reference-template"), ft.Dropdown)
    selector.value = template
    submit = _typed(_find_by_key(dialog, "new-reference-submit"), ft.FilledButton)
    await typing.cast("Handler", submit.on_click)()


class TestCreation:
    def test_desktop_welcome_offers_creation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert _welcome_button(page.controls[0], "welcome-create").content == afanes.ui.strings.NEW_VAULT_ACTION

    def test_web_welcome_offers_creation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage(web=True)

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page)))

        assert _welcome_button(page.controls[0], "welcome-create").content == afanes.ui.strings.NEW_VAULT_ACTION

    def test_desktop_creation_shows_the_template_choice_first(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "vault"
        target.mkdir()
        picker = FakePicker(str(target))
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()

        asyncio.run(scenario())

        assert len(page.dialogs) == 1
        assert picker.calls == 0
        selector = _typed(_find_by_key(page.dialogs[0], "create-vault-template"), ft.Dropdown)
        assert [option.key for option in selector.options] == ["", "personal", "work", "study"]
        field = _typed(_find_by_key(page.dialogs[0], "create-vault-path"), ft.TextField)
        assert field.value == ""

    def test_desktop_creation_browse_fills_the_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "vault"
        target.mkdir()
        picker = FakePicker(str(target))
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()
            await _browse_creation(page)
            field = _typed(_find_by_key(page.dialogs[-1], "create-vault-path"), ft.TextField)
            assert field.value == str(target)
            await _submit_creation(page)

        asyncio.run(scenario())

        assert picker.calls == 1
        assert state.session.vault_root == target.resolve()
        assert (target / "inbox").is_dir()
        assert (target / "reference").is_dir()
        assert (target / "projects").is_dir()
        assert (target / "reference" / "Getting started.md").is_file()
        assert page.dialogs == []
        assert isinstance(page.controls[0], ft.Stack)
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(target.resolve())

    def test_cancelling_the_browse_keeps_the_form_and_writes_nothing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        picker = FakePicker(None)
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()
            await _browse_creation(page)
            field = _typed(_find_by_key(page.dialogs[-1], "create-vault-path"), ft.TextField)
            assert field.value == ""
            cancel = _typed(_find_by_key(page.dialogs[-1], "create-vault-cancel"), ft.TextButton)
            await typing.cast("Handler", cancel.on_click)()

        asyncio.run(scenario())

        assert picker.calls == 1
        assert state.session.vault_root is None
        assert not settings.exists()
        assert page.dialogs == []
        assert isinstance(page.controls[0], ft.Container)

    def test_desktop_creation_error_stays_in_the_dialog(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        occupied = tmp_path / "occupied"
        occupied.mkdir()
        (occupied / "photo.jpg").write_text("data", encoding="utf-8")
        picker = FakePicker(str(occupied))
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()
            await _browse_creation(page)
            await _submit_creation(page)

        asyncio.run(scenario())

        assert state.session.vault_root is None
        assert state.status.message == afanes.ui.strings.VAULT_NOT_EMPTY
        assert not settings.exists()
        assert len(page.dialogs) == 1
        error = _typed(_find_by_key(page.dialogs[0], "create-vault-error"), ft.Text)
        assert error.visible is True
        assert error.value == afanes.ui.strings.VAULT_NOT_EMPTY

    def test_web_creation_dialog_previews_and_creates_the_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "notes" / "vault"
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()
            preview = _typed(_find_by_key(page.dialogs[0], "create-vault-preview"), ft.Text)
            assert "inbox/" in (preview.value or "")
            assert "projects/" in (preview.value or "")
            assert "afanes.yaml" in (preview.value or "")
            assert "actions/" not in (preview.value or "")
            assert (
                afanes.ui.strings.NEW_VAULT_PREVIEW_GUIDE.format(
                    folders="inbox/, trash/, reference/, projects/, log/",
                )
                == preview.value
            )
            await _submit_creation(page, target)

        asyncio.run(scenario())

        assert state.session.vault_root == target.resolve()
        assert (target / "inbox").is_dir()
        assert page.dialogs == []
        assert isinstance(page.controls[0], ft.Stack)
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(target.resolve())

    def test_web_creation_error_stays_in_the_dialog(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        occupied = tmp_path / "occupied"
        occupied.mkdir()
        (occupied / "photo.jpg").write_text("data", encoding="utf-8")
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()
            await _submit_creation(page, occupied)

        asyncio.run(scenario())

        assert state.session.vault_root is None
        assert len(page.dialogs) == 1
        error = _typed(_find_by_key(page.dialogs[0], "create-vault-error"), ft.Text)
        assert error.visible is True
        assert error.value == afanes.ui.strings.VAULT_NOT_EMPTY
        assert not settings.exists()

    def test_web_cancelling_creation_writes_nothing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()
            cancel = _typed(_find_by_key(page.dialogs[0], "create-vault-cancel"), ft.TextButton)
            await typing.cast("Handler", cancel.on_click)()

        asyncio.run(scenario())

        assert page.dialogs == []
        assert state.session.vault_root is None
        assert not settings.exists()

    def test_creation_preselects_no_starter_content(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        page = FakePage(web=True)

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()

        asyncio.run(scenario())
        selector = _typed(_find_by_key(page.dialogs[0], "create-vault-template"), ft.Dropdown)

        assert selector.value == ""
        assert [option.key for option in selector.options] == ["", "personal", "work", "study"]
        assert all(option.text for option in selector.options)
        preview = _typed(_find_by_key(page.dialogs[0], "create-vault-preview"), ft.Text)
        assert "guide note" in (preview.value or "")

    def test_selecting_a_template_updates_the_preview_and_is_created(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "vault"
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()
            preview = _typed(_find_by_key(page.dialogs[0], "create-vault-preview"), ft.Text)
            assert "guide note" in (preview.value or "")
            _select_template(page, "personal")
            summary = next(
                summary
                for summary in afanes.core.templates.TemplateCatalog.bundled().summaries()
                if summary.identifier == "personal"
            )
            assert f"{summary.note_count} notes" in (preview.value or "")
            assert "guide note" in (preview.value or "")
            await _submit_creation(page, target)

        asyncio.run(scenario())

        assert state.session.vault_root == target.resolve()
        assert (target / "reference" / "Getting started.md").is_file()
        assert (target / "projects" / "Home insurance.md").is_file()
        assert (target / "reference" / "person" / "Sam Rivera.md").is_file()

    def test_unreadable_catalog_degrades_to_a_blank_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "vault"
        page = FakePage(web=True)
        state = afanes.ui.state.app_state

        def refuse(_cls: object) -> None:
            message = "bundled content is broken"
            raise TemplateContentError(message)

        monkeypatch.setattr(afanes.core.templates.TemplateCatalog, "summaries", refuse)

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _welcome_button(page.controls[0], "welcome-create")
            await typing.cast("Handler", create.on_click)()
            warning = _typed(_find_by_key(page.dialogs[0], "create-vault-templates-error"), ft.Text)
            assert warning.visible is True
            selector = _typed(_find_by_key(page.dialogs[0], "create-vault-template"), ft.Dropdown)
            assert [option.key for option in selector.options] == [""]
            await _submit_creation(page, target)

        asyncio.run(scenario())

        assert state.session.vault_root == target.resolve()
        assert (target / "reference" / "Getting started.md").is_file()
        assert [path.name for path in (target / "projects").iterdir()] == []

    def test_creating_a_second_vault_from_the_change_action(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = tmp_path / "first"
        versioned(first)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=first))
        second = tmp_path / "second"
        second.mkdir()
        picker = FakePicker(str(second))
        monkeypatch.setattr(afanes.ui.app.ft, "FilePicker", lambda: picker)
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            create = _typed(_find_by_key(page.controls[0], "workspace-change-create"), ft.PopupMenuItem)
            await typing.cast("Handler", create.on_click)()
            _select_template(page, "study")
            await _browse_creation(page)
            await _submit_creation(page)

        asyncio.run(scenario())

        assert picker.calls == 1
        assert state.session.vault_root == second.resolve()
        assert (second / "inbox").is_dir()
        assert (second / "projects" / "Research essay.md").is_file()
        assert not (first / "inbox").exists()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(second.resolve())

    def test_closing_the_vault_returns_to_the_welcome(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = tmp_path / "first"
        versioned(first)
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=first))
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            close = _typed(_find_by_key(page.controls[0], "workspace-close-vault"), ft.PopupMenuItem)
            await typing.cast("Handler", close.on_click)()

        asyncio.run(scenario())

        assert state.session.vault_root is None
        assert not settings.exists()
        assert isinstance(page.controls[0], ft.Container)
        assert _welcome_button(page.controls[0], "welcome-create") is not None


class TestLaunchDigest:
    def _vault_with_due_step(self, tmp_path: Path) -> Path:
        vault = versioned(tmp_path / "vault")
        path = vault / "projects" / "Home.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "---\ntype: project\nstatus: active\n---\n"
            f"# Home\n\n- [ ] Call <!-- {{plan: {__import__('datetime').date.today().isoformat()}}} -->\n",
            encoding="utf-8",
        )
        return vault

    def test_digest_reports_the_count_and_starts_review(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        vault = self._vault_with_due_step(tmp_path)
        before = {path.relative_to(vault).as_posix(): path.read_bytes() for path in vault.rglob("*") if path.is_file()}
        page = FakePage()
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page), vault)
            digest = _find_by_key(page.controls[0], "launch-digest")
            assert isinstance(digest, ft.Container)
            assert digest.bgcolor == afanes.ui.theme.NOTICE_SURFACE_COLOR
            texts = _all_texts(digest)
            assert any("1 due step" in text for text in texts)
            start = _typed(_find_by_key(digest, "launch-digest-start"), ft.FilledButton)
            await typing.cast("Handler", start.on_click)()

        asyncio.run(scenario())

        after = {path.relative_to(vault).as_posix(): path.read_bytes() for path in vault.rglob("*") if path.is_file()}
        assert after == before
        assert state.review.review_session is not None

    def test_no_digest_without_due_work(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        vault = tmp_path / "vault"
        versioned(vault)
        page = FakePage()

        asyncio.run(afanes.ui.app.main(typing.cast("ft.Page", page), vault))

        assert _find_by_key(page.controls[0], "launch-digest") is None


def _all_texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    if isinstance(control, ft.Text):
        values.append(str(control.value))
    for child in getattr(control, "controls", []) or []:
        values.extend(_all_texts(child))
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        values.extend(_all_texts(content))
    return values


class TestRoleReferenceCreation:
    def test_creating_a_role_reference_refreshes_the_existing_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = versioned(tmp_path / "vault")
        project = vault / "projects" / "Follow.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nstatus: active\nasked_by: Ghost\n---\n# Follow\n",
            encoding="utf-8",
        )
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        page = FakePage()
        state = afanes.ui.state.app_state

        async def ignore_scroll(_view: object) -> None:
            return None

        monkeypatch.setattr(afanes.ui.views.page.PageView, "scroll_to_top", ignore_scroll)

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            workspace = page.controls[0]
            projects = _typed(_find_by_key(workspace, "section-projects"), ft.ListTile)
            await typing.cast("Handler", projects.on_click)()
            follow = _typed(_find_by_key(page.controls[0], "project-projects/Follow.md"), ft.TextButton)
            await typing.cast("Handler", follow.on_click)()
            link = _find_span(page.controls[0], "Ghost")
            assert link is not None
            await typing.cast("Handler", link.on_click)()
            create = _typed(_find_by_key(page.dialogs[-1], "role-reference-create"), ft.FilledButton)

            await typing.cast("Handler", create.on_click)()

            assert page.controls[0] is workspace
            assert page.dialogs == []
            assert state.pages.editing is True
            assert (vault / "reference" / "person" / "Ghost.md").is_file()

            done = _find_button_by_label(page.controls[0], afanes.ui.strings.PAGE_DONE)
            assert done is not None
            await typing.cast("Handler", done.on_click)()

        asyncio.run(scenario())

        assert state.pages.editing is False


class TestBrowserReferenceCreation:
    def _open_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[FakePage, Path]:
        vault = versioned(tmp_path / "vault")
        card = vault / "templates" / "person.md"
        card.parent.mkdir(parents=True)
        card.write_text(
            "---\ntype: reference\ncategory: person\ntitle: Person\n"
            "description: A contact.\n---\n\n## Contact\n\n- Email:\n",
            encoding="utf-8",
        )
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=vault))
        return FakePage(), vault

    def test_creates_a_card_reference_and_opens_edit_mode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        page, vault = self._open_vault(tmp_path, monkeypatch)
        state = afanes.ui.state.app_state

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            state.browser.query = "stale"
            await _open_reference_dialog(page)
            await _submit_reference(page, "Priya Nair", "card:person.md")

        asyncio.run(scenario())

        path = vault / "reference" / "person" / "Priya Nair.md"
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.category == CategoryLabel("person")
        assert document.body == "# Priya Nair\n\n## Contact\n\n- Email:\n"
        assert state.pages.editing is True
        assert state.pages.page is not None
        assert state.pages.page.path == path.resolve()
        assert state.browser.query == ""

    def test_empty_uses_the_general_category(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        page, vault = self._open_vault(tmp_path, monkeypatch)

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            await _open_reference_dialog(page)
            await _submit_reference(page, "Inbox thought", "empty")

        asyncio.run(scenario())

        path = vault / "reference" / "general" / "Inbox thought.md"
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.category == CategoryLabel("general")
        assert document.body == "# Inbox thought\n"

    def test_a_blank_name_keeps_the_dialog_open(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        page, vault = self._open_vault(tmp_path, monkeypatch)

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            await _open_reference_dialog(page)
            await _submit_reference(page, "   ", "empty")

        asyncio.run(scenario())

        assert len(page.dialogs) == 1
        error = _typed(_find_by_key(page.dialogs[-1], "new-reference-error"), ft.Text)
        assert error.visible is True
        assert error.value == afanes.ui.strings.BROWSER_NAME_REQUIRED
        assert not (vault / "reference" / "general").exists()

    def test_a_collision_keeps_the_dialog_open(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        page, vault = self._open_vault(tmp_path, monkeypatch)
        existing = vault / "reference" / "Ada.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("---\ntype: reference\n---\n# Ada\n", encoding="utf-8")

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            await _open_reference_dialog(page)
            await _submit_reference(page, "Ada", "empty")

        asyncio.run(scenario())

        assert len(page.dialogs) == 1
        error = _typed(_find_by_key(page.dialogs[-1], "new-reference-error"), ft.Text)
        assert error.visible is True
        assert not (vault / "reference" / "general" / "Ada.md").exists()
        assert not (vault / "reference" / "general" / "Ada 2.md").exists()

    def test_invalid_cards_are_named_in_the_dialog(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        page, vault = self._open_vault(tmp_path, monkeypatch)
        broken = vault / "templates" / "broken.md"
        broken.write_text("---\ntype: reference\n---\n", encoding="utf-8")

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            await _open_reference_dialog(page)

        asyncio.run(scenario())

        dialog = page.dialogs[-1]
        warning = _typed(_find_by_key(dialog, "new-reference-template-warning"), ft.Text)
        assert warning.visible is True
        assert "broken.md" in warning.value
        selector = _typed(_find_by_key(dialog, "new-reference-template"), ft.Dropdown)
        assert [option.key for option in selector.options] == ["card:person.md", "empty"]


def _shell_row(page: FakePage) -> ft.Row:
    stack = _typed(page.controls[0], ft.Stack)
    column = _typed(stack.controls[0], ft.Column)
    return _typed(column.controls[-1], ft.Row)


def _keyboard(key: str, *, ctrl: bool) -> ft.KeyboardEvent:
    return ft.KeyboardEvent(
        name="key_down",
        control=typing.cast("ft.Page", None),
        key=key,
        shift=False,
        ctrl=ctrl,
        alt=False,
        meta=False,
    )


class TestAdaptiveShell:
    def test_the_initial_width_and_a_resize_arrange_the_shell(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(versioned(tmp_path / "vault")))
        page = FakePage()

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))

        asyncio.run(scenario())

        assert page.on_resize is not None
        assert len(_shell_row(page).controls) == WIDE_REGION_COUNT

        page.width = afanes.ui.theme.SHELL_MEDIUM_MIN
        typing.cast("Callable[[object], None]", page.on_resize)(None)

        assert len(_shell_row(page).controls) == MEDIUM_REGION_COUNT

    def test_the_shortcuts_reach_the_workspace(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(versioned(tmp_path / "vault")))
        page = FakePage()
        calls: list[str] = []

        async def start_capture(_self: afanes.ui.views.workspace.WorkspaceView) -> None:
            calls.append("capture")

        async def focus_search(_self: afanes.ui.views.workspace.WorkspaceView) -> None:
            calls.append("search")

        monkeypatch.setattr(afanes.ui.views.workspace.WorkspaceView, "start_capture", start_capture)
        monkeypatch.setattr(afanes.ui.views.workspace.WorkspaceView, "focus_search", focus_search)

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            assert page.on_keyboard_event is not None
            await page.on_keyboard_event(_keyboard("n", ctrl=True))
            await page.on_keyboard_event(_keyboard("f", ctrl=True))

        asyncio.run(scenario())

        assert calls == ["capture", "search"]

    def test_escape_closes_the_navigation_drawer(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(versioned(tmp_path / "vault")))
        page = FakePage()
        page.width = afanes.ui.theme.SHELL_MEDIUM_MIN

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            toggle = _typed(_find_by_key(page.controls[0], "workspace-navigation-toggle"), ft.IconButton)
            await typing.cast("Handler", toggle.on_click)()
            assert _find_by_key(page.controls[0], "workspace-drawer") is not None
            assert page.on_keyboard_event is not None
            await page.on_keyboard_event(_keyboard("Escape", ctrl=False))

        asyncio.run(scenario())

        assert _find_by_key(page.controls[0], "workspace-drawer") is None


class TestAboutDialog:
    def test_the_primary_menu_names_the_version(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        asyncio.run(afanes.ui.state.app_state.workspace.choose_vault(versioned(tmp_path / "vault")))
        page = FakePage()

        async def scenario() -> None:
            await afanes.ui.app.main(typing.cast("ft.Page", page))
            menu = _typed(_find_by_key(page.controls[0], "workspace-change"), ft.PopupMenuButton)
            item = typing.cast(
                "ft.PopupMenuItem",
                next(
                    entry
                    for entry in menu.items
                    if isinstance(entry, ft.PopupMenuItem) and entry.key == "workspace-about"
                ),
            )
            await typing.cast("Handler", item.on_click)()

        asyncio.run(scenario())

        dialog = page.dialogs[-1]
        title = typing.cast("ft.Text", dialog.title)
        content = _typed(dialog.content, ft.Column)
        version = _typed(content.controls[0], ft.Text)
        license_text = _typed(content.controls[1], ft.Text)
        assert title.value == afanes.ui.strings.ABOUT_TITLE
        assert afanes.__about__.__version__ in (version.value or "")
        assert license_text.value == afanes.ui.strings.ABOUT_LICENSE
