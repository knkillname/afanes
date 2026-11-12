"""Tests for the headless command surface and its exit codes."""

import ast
import json
from pathlib import Path

import pytest

import afanes.cli
import afanes.cli.main
import afanes.core.settings
import afanes.core.vault
from afanes.core.errors import ConfigurationError
from afanes.core.settings import Settings

CLI_ROOT = Path(afanes.cli.__file__).parent


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(lambda _cls: path))


def _first_party_and_third_party_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class TestHeadlessIsolation:
    def test_cli_imports_neither_the_interface_nor_the_toolkit(self) -> None:
        forbidden = [
            f"{path.name}: {module}"
            for path in sorted(CLI_ROOT.glob("*.py"))
            for module in _first_party_and_third_party_imports(path)
            if module == "flet" or module.startswith(("flet.", "afanes.ui"))
        ]

        assert forbidden == []


class TestUsage:
    def test_missing_command_is_a_usage_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.main([])

        assert status == afanes.cli.main.USAGE_EXIT_CODE
        assert "usage" in capsys.readouterr().err.lower()

    def test_missing_action_is_a_usage_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.main(["vault"])

        assert status == afanes.cli.main.USAGE_EXIT_CODE
        assert "usage" in capsys.readouterr().err.lower()

    def test_unknown_action_is_a_usage_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.main(["vault", "unknown"])

        assert status == afanes.cli.main.USAGE_EXIT_CODE
        assert "usage" in capsys.readouterr().err.lower()

    def test_missing_directory_is_a_usage_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.main(["vault", "create"])

        assert status == afanes.cli.main.USAGE_EXIT_CODE
        assert "usage" in capsys.readouterr().err.lower()

    def test_help_exits_successfully(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.main(["vault", "create", "--help"])

        assert status == 0
        assert "--no-remember" in capsys.readouterr().out


class TestCreateCommand:
    def test_creates_seeds_and_remembers_a_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "notes" / "vault"

        status = afanes.cli.main.main(["vault", "create", str(target)])

        captured = capsys.readouterr()
        assert status == 0
        assert captured.err == ""
        assert f"Created vault {target.resolve()}" in captured.out
        assert f"Parent folders created: {tmp_path / 'notes'}" in captured.out
        assert "Seeded: inbox/, trash/, reference/, projects/" in captured.out
        assert "Remembered" in captured.out
        assert (target / "reference").is_dir()
        assert (target / "projects").is_dir()
        assert not (target / "reference" / "people").exists()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(target.resolve())

    def test_no_remember_leaves_preferences_untouched(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        remembered = tmp_path / "remembered"
        remembered.mkdir()
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=remembered))

        status = afanes.cli.main.main(["vault", "create", str(tmp_path / "new"), "--no-remember"])

        captured = capsys.readouterr()
        assert status == 0
        assert "Not remembered" in captured.out
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(remembered.resolve())

    def test_refuses_a_non_empty_directory(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "vault"
        target.mkdir()
        (target / "photo.jpg").write_text("data", encoding="utf-8")

        status = afanes.cli.main.main(["vault", "create", str(target)])

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert "not empty" in captured.err
        assert sorted(path.name for path in target.iterdir()) == ["photo.jpg"]
        assert not settings.exists()

    def test_refuses_a_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "note.md"
        target.write_text("body", encoding="utf-8")

        status = afanes.cli.main.main(["vault", "create", str(target)])

        captured = capsys.readouterr()
        assert status == 1
        assert "not a directory" in captured.err
        assert target.read_text(encoding="utf-8") == "body"

    def test_reports_a_preferences_failure_and_keeps_the_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = tmp_path / "vault"

        def fail_save(_self: afanes.core.settings.SettingsStore, _settings: Settings) -> None:
            message = "settings are read-only"
            raise ConfigurationError(message)

        monkeypatch.setattr(afanes.core.settings.SettingsStore, "save", fail_save)

        status = afanes.cli.main.main(["vault", "create", str(target)])

        captured = capsys.readouterr()
        assert status == 1
        assert f"Created vault {target.resolve()}" in captured.out
        assert "could not be remembered" in captured.err
        assert (target / "inbox").is_dir()
