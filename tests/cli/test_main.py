"""Tests for the headless command surface and its exit codes."""

import ast
import json
from pathlib import Path

import pytest

import afanes.cli
import afanes.cli.main
import afanes.core.atomic
import afanes.core.settings
import afanes.core.vault.schema
import afanes.core.vault.service
from afanes.core.errors import ConfigurationError
from afanes.core.settings import Settings
from tests.support import constant

CLI_ROOT = Path(afanes.cli.__file__).parent
FAILING_WRITE_CALL = 2


def _use_settings_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(afanes.core.settings.SettingsStore, "settings_path", classmethod(constant(path)))


def _adoptable(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for folder in afanes.core.vault.schema.DEFAULT_FOLDERS:
        (root / folder).mkdir()
    return root


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


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
        status = afanes.cli.main.CommandLine.main(*[])

        assert status == afanes.cli.main.USAGE_EXIT_CODE
        assert "usage" in capsys.readouterr().err.lower()

    def test_missing_action_is_a_usage_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.CommandLine.main(*["vault"])

        assert status == afanes.cli.main.USAGE_EXIT_CODE
        assert "usage" in capsys.readouterr().err.lower()

    def test_unknown_action_is_a_usage_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.CommandLine.main(*["vault", "unknown"])

        assert status == afanes.cli.main.USAGE_EXIT_CODE
        assert "usage" in capsys.readouterr().err.lower()

    def test_missing_directory_is_a_usage_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.CommandLine.main(*["vault", "create"])

        assert status == afanes.cli.main.USAGE_EXIT_CODE
        assert "usage" in capsys.readouterr().err.lower()

    def test_help_exits_successfully(self, capsys: pytest.CaptureFixture[str]) -> None:
        status = afanes.cli.main.CommandLine.main(*["vault", "create", "--help"])

        assert status == 0
        captured = capsys.readouterr().out
        assert "--no-remember" in captured
        assert "--template" in captured


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

        status = afanes.cli.main.CommandLine.main(*["vault", "create", str(target)])

        captured = capsys.readouterr()
        assert status == 0
        assert captured.err == ""
        assert f"Created vault {target.resolve()}" in captured.out
        assert f"Parent folders created: {tmp_path / 'notes'}" in captured.out
        assert "Seeded: inbox/, trash/, reference/, projects/" in captured.out
        assert "Settings file: afanes.yaml (schema version 1)" in captured.out
        assert "Template: none" in captured.out
        assert "Notes written: reference/Getting started.md" in captured.out
        assert "Remembered" in captured.out
        assert (target / "afanes.yaml").read_text(encoding="utf-8") == "schema_version: 1\n"
        assert (target / "reference").is_dir()
        assert (target / "projects").is_dir()
        assert not (target / "reference" / "people").exists()
        assert (target / "reference" / "Getting started.md").is_file()
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

        status = afanes.cli.main.CommandLine.main(*["vault", "create", str(tmp_path / "new"), "--no-remember"])

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

        status = afanes.cli.main.CommandLine.main(*["vault", "create", str(target)])

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

        status = afanes.cli.main.CommandLine.main(*["vault", "create", str(target)])

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

        status = afanes.cli.main.CommandLine.main(*["vault", "create", str(target)])

        captured = capsys.readouterr()
        assert status == 1
        assert f"Created vault {target.resolve()}" in captured.out
        assert "could not be remembered" in captured.err
        assert (target / "inbox").is_dir()

    def test_applies_a_template_and_reports_it(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "vault"

        status = afanes.cli.main.CommandLine.main(*["vault", "create", str(target), "--template", "personal"])

        captured = capsys.readouterr()
        assert status == 0
        assert captured.err == ""
        assert "Template: personal" in captured.out
        assert "reference/Getting started.md" in captured.out
        assert "projects/Home insurance.md" in captured.out
        assert (target / "reference" / "person" / "Sam Rivera.md").is_file()
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(target.resolve())

    def test_refuses_an_unknown_template(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = tmp_path / "vault"

        status = afanes.cli.main.CommandLine.main(*["vault", "create", str(target), "--template", "mystery"])

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert "mystery" in captured.err
        assert "personal" in captured.err
        assert "work" in captured.err
        assert "study" in captured.err
        assert not target.exists()
        assert not settings.exists()

    def test_reports_a_mid_write_failure_and_leaves_written_notes(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        original = afanes.core.atomic.AtomicWriter.write_text_atomic
        calls: list[Path] = []

        def fail_after_the_guide(path: Path, text: str) -> None:
            calls.append(path)
            if len(calls) == FAILING_WRITE_CALL:
                message = "disk full"
                raise OSError(message)
            original(path, text)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", fail_after_the_guide)
        target = tmp_path / "vault"

        status = afanes.cli.main.CommandLine.main(*["vault", "create", str(target), "--template", "personal"])

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert "Could not write bundled note" in captured.err
        assert "reference/Getting started.md" in captured.err
        assert (target / "reference" / "Getting started.md").is_file()
        assert not settings.exists()


class TestAdoptCommand:
    def test_adopts_remembers_and_reports_the_settings_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = _adoptable(tmp_path / "vault")

        status = afanes.cli.main.CommandLine.main(*["vault", "adopt", str(target)])

        captured = capsys.readouterr()
        assert status == 0
        assert captured.err == ""
        assert f"Adopted vault {target.resolve()}" in captured.out
        assert "Settings file: afanes.yaml (schema version 1)" in captured.out
        assert "Remembered" in captured.out
        assert (target / "afanes.yaml").read_text(encoding="utf-8") == "schema_version: 1\n"
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(target.resolve())

    def test_no_remember_leaves_preferences_untouched(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        remembered = _adoptable(tmp_path / "remembered")
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        afanes.core.settings.SettingsStore(settings).save(Settings(vault=remembered))
        target = _adoptable(tmp_path / "vault")

        status = afanes.cli.main.CommandLine.main(*["vault", "adopt", str(target), "--no-remember"])

        captured = capsys.readouterr()
        assert status == 0
        assert "Not remembered" in captured.out
        assert json.loads(settings.read_text(encoding="utf-8"))["vault"] == str(remembered.resolve())

    def test_missing_default_folder_is_refused(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = _adoptable(tmp_path / "vault")
        (target / "log").rmdir()

        status = afanes.cli.main.CommandLine.main(*["vault", "adopt", str(target)])

        captured = capsys.readouterr()
        assert status == 1
        assert captured.out == ""
        assert "log/" in captured.err
        assert not (target / "afanes.yaml").exists()
        assert not settings.exists()

    def test_read_only_folder_is_refused(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = _adoptable(tmp_path / "vault")
        monkeypatch.setattr(
            afanes.core.vault.schema.os,
            "access",
            constant(False),
        )

        status = afanes.cli.main.CommandLine.main(*["vault", "adopt", str(target)])

        captured = capsys.readouterr()
        assert status == 1
        assert "not writable" in captured.err
        assert not (target / "afanes.yaml").exists()
        assert not settings.exists()

    def test_invalid_settings_file_is_refused_and_preserved(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = _adoptable(tmp_path / "vault")
        path = target / "afanes.yaml"
        path.write_text("schema_version: 2\n", encoding="utf-8")
        before = path.read_bytes()

        status = afanes.cli.main.CommandLine.main(*["vault", "adopt", str(target)])

        captured = capsys.readouterr()
        assert status == 1
        assert "schema version 2" in captured.err
        assert path.read_bytes() == before
        assert not settings.exists()

    def test_already_versioned_folder_is_reported_unchanged(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        settings = tmp_path / "settings.json"
        _use_settings_file(monkeypatch, settings)
        target = _adoptable(tmp_path / "vault")
        path = target / "afanes.yaml"
        path.write_text("schema_version: 1\n", encoding="utf-8")
        before = path.read_bytes()

        status = afanes.cli.main.CommandLine.main(*["vault", "adopt", str(target)])

        captured = capsys.readouterr()
        assert status == 0
        assert "already a vault" in captured.out
        assert path.read_bytes() == before
        assert not settings.exists()

    def test_adoption_writes_only_the_settings_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = _adoptable(tmp_path / "vault")
        note = target / "inbox" / "Buy milk.md"
        note.write_text("---\ntype: note\n---\n# Buy milk\n", encoding="utf-8")
        before = _tree_state(target)

        status = afanes.cli.main.CommandLine.main(*["vault", "adopt", str(target), "--no-remember"])

        assert status == 0
        after = _tree_state(target)
        assert set(after) - set(before) == {"afanes.yaml"}
        assert all(after[path] == content for path, content in before.items())

    def test_a_preferences_failure_reports_the_adopted_vault(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        target = _adoptable(tmp_path / "vault")

        def fail_save(_self: afanes.core.settings.SettingsStore, _settings: Settings) -> None:
            message = "settings are read-only"
            raise ConfigurationError(message)

        monkeypatch.setattr(afanes.core.settings.SettingsStore, "save", fail_save)

        status = afanes.cli.main.CommandLine.main(*["vault", "adopt", str(target)])

        captured = capsys.readouterr()
        assert status == 1
        assert f"Adopted vault {target.resolve()}" in captured.out
        assert "could not be remembered" in captured.err
        assert (target / "afanes.yaml").is_file()


class TestTemplatesCommand:
    def test_lists_the_catalog_without_a_vault_or_a_write(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _use_settings_file(monkeypatch, tmp_path / "settings.json")
        monkeypatch.chdir(tmp_path)

        status = afanes.cli.main.CommandLine.main(*["vault", "templates"])

        captured = capsys.readouterr()
        assert status == 0
        assert captured.err == ""
        assert "personal: Personal" in captured.out
        assert "work: Work" in captured.out
        assert "study: Study" in captured.out
        assert "Life administration" in captured.out
        assert list(tmp_path.iterdir()) == []
