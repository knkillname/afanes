"""End-to-end locale flow across preferences, the interface, and the command line."""

import asyncio
import typing
from pathlib import Path

import pytest

import afanes.cli.main
import afanes.core.localization
import afanes.core.preferences
import afanes.core.settings
import afanes.i18n.ui
import afanes.ui.app
import afanes.ui.state
from afanes.core.preferences import Preferences, PreferencesStore
from tests.support import constant
from tests.ui.test_app import FakePage


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    afanes.ui.state.app_state.reset()


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(constant(path)))


def _start_ui(page: FakePage) -> None:
    asyncio.run(afanes.ui.app.AppShell.main(typing.cast("typing.Any", page)))


class TestLocaleFlow:
    def test_a_saved_spanish_preference_reaches_the_interface_and_command_line(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        PreferencesStore(tmp_path / "preferences.json").save(Preferences(language="es"))
        page = FakePage(web=True)

        _start_ui(page)

        assert afanes.ui.state.app_state.status.copy.locale.language == "es"
        capsys.readouterr()

        status = afanes.cli.main.CommandLine.main(*["vault", "templates"])

        output = capsys.readouterr().out
        assert status == 0
        assert "Trabajo - Resultados compartidos" in output
        assert "Work - Shared outcomes" not in output

    def test_the_system_spanish_locale_drives_both_surfaces(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        monkeypatch.setenv("LANG", "es_MX.UTF-8")
        page = FakePage(web=True)

        _start_ui(page)

        assert afanes.ui.state.app_state.status.copy.locale.language == "es"
        capsys.readouterr()

        status = afanes.cli.main.CommandLine.main(*["vault", "templates"])

        output = capsys.readouterr().out
        assert status == 0
        assert "Estudio - Trabajo de cursos" in output

    def test_corrupt_preferences_fall_back_consistently_and_stay_untouched(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        path = tmp_path / "preferences.json"
        path.write_text("{not json", encoding="utf-8")
        page = FakePage(web=True)

        _start_ui(page)

        state = afanes.ui.state.app_state
        assert state.status.copy.locale.language == "en"
        assert state.workspace.banner == afanes.i18n.ui.UiCopy.english().PREFERENCES_CORRUPT
        assert path.read_text(encoding="utf-8") == "{not json"
        capsys.readouterr()

        status = afanes.cli.main.CommandLine.main(*["vault", "templates"])

        captured = capsys.readouterr()
        assert status == 0
        assert "not valid JSON" in captured.err
        assert path.read_text(encoding="utf-8") == "{not json"

    def test_a_language_choice_applies_on_the_next_start(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        first_page = FakePage(web=True)

        _start_ui(first_page)

        shell = afanes.ui.app.AppShell(typing.cast("typing.Any", first_page), None)
        asyncio.run(shell.set_language("es"))

        assert PreferencesStore(tmp_path / "preferences.json").load().preferences == Preferences(language="es")
        assert afanes.ui.state.app_state.status.copy.locale.language == "en"

        second_page = FakePage(web=True)
        _start_ui(second_page)

        assert afanes.ui.state.app_state.status.copy.locale.language == "es"
