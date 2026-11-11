"""Tests for platform-aware application settings."""

import json
import sys
from pathlib import Path
from typing import NoReturn

import pytest

import afanes.core.settings
import afanes.core.vault
from afanes.core.errors import ConfigurationError, VaultError
from afanes.core.settings import Settings


class TestConfigDirectory:
    def test_linux_uses_xdg_config_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

        assert afanes.core.settings.config_directory() == tmp_path / "xdg" / "afanes"

    def test_linux_falls_back_to_home_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        assert afanes.core.settings.config_directory() == tmp_path / "home" / ".config" / "afanes"

    def test_linux_ignores_a_relative_xdg_config_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_CONFIG_HOME", "relative/config")

        assert afanes.core.settings.config_directory() == tmp_path / "home" / ".config" / "afanes"

    def test_macos_uses_application_support(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        expected = tmp_path / "home" / "Library" / "Application Support" / "afanes"
        assert afanes.core.settings.config_directory() == expected

    def test_windows_uses_appdata(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))

        assert afanes.core.settings.config_directory() == tmp_path / "roaming" / "afanes"

    def test_windows_falls_back_to_roaming_appdata(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("APPDATA", raising=False)

        expected = tmp_path / "home" / "AppData" / "Roaming" / "afanes"
        assert afanes.core.settings.config_directory() == expected

    def test_settings_path_appends_the_filename(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(afanes.core.settings, "config_directory", _config_directory)

        assert afanes.core.settings.settings_path() == Path("config/afanes/settings.json")


class TestLoadSettings:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert afanes.core.settings.load_settings(tmp_path / "settings.json") is None

    def test_round_trip_returns_the_saved_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "config" / "settings.json"

        afanes.core.settings.save_settings(Settings(vault=vault), path)

        assert afanes.core.settings.load_settings(path) == Settings(vault=vault.resolve())

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("{not json", encoding="utf-8")

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

    def test_non_object_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("[]", encoding="utf-8")

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

    def test_unsupported_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"version": 2, "vault": str(tmp_path)}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

    def test_boolean_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"version": True, "vault": str(tmp_path)}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"vault": str(tmp_path)}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

    def test_missing_vault_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"version": 1}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

    def test_relative_vault_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"version": 1, "vault": "relative"}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

    def test_unreadable_path_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.mkdir()

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

    def test_malformed_file_is_not_rewritten(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("{not json", encoding="utf-8")

        with pytest.raises(ConfigurationError):
            afanes.core.settings.load_settings(path)

        assert path.read_text(encoding="utf-8") == "{not json"


class TestSaveSettings:
    def test_save_creates_missing_directories(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "nested" / "config" / "settings.json"

        afanes.core.settings.save_settings(Settings(vault=vault), path)

        assert path.is_file()

    def test_save_resolves_a_relative_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "settings.json"
        monkeypatch.chdir(tmp_path)

        afanes.core.settings.save_settings(Settings(vault=Path("vault")), path)
        loaded = afanes.core.settings.load_settings(path)

        assert loaded is not None
        assert loaded.vault == vault.resolve()

    def test_save_rejects_a_missing_vault(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"

        with pytest.raises(ConfigurationError):
            afanes.core.settings.save_settings(Settings(vault=tmp_path / "missing"), path)

        assert not path.exists()

    def test_save_rejects_a_file_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.write_text("not a directory", encoding="utf-8")
        path = tmp_path / "settings.json"

        with pytest.raises(ConfigurationError):
            afanes.core.settings.save_settings(Settings(vault=vault), path)

    def test_save_rejects_a_blocked_config_directory(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        blocker = tmp_path / "blocked"
        blocker.write_text("not a directory", encoding="utf-8")
        path = blocker / "settings.json"

        with pytest.raises(ConfigurationError):
            afanes.core.settings.save_settings(Settings(vault=vault), path)

    def test_failed_write_preserves_previous_settings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        first_vault = tmp_path / "first"
        second_vault = tmp_path / "second"
        first_vault.mkdir()
        second_vault.mkdir()
        path = tmp_path / "settings.json"
        afanes.core.settings.save_settings(Settings(vault=first_vault), path)
        before = path.read_text(encoding="utf-8")

        def fail_write(_destination: Path, _text: str) -> NoReturn:
            message = "simulated failure"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault, "write_text_atomic", fail_write)

        with pytest.raises(ConfigurationError):
            afanes.core.settings.save_settings(Settings(vault=second_vault), path)

        assert path.read_text(encoding="utf-8") == before

    def test_saved_payload_contains_only_version_and_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "settings.json"

        afanes.core.settings.save_settings(Settings(vault=vault), path)

        assert json.loads(path.read_text(encoding="utf-8")) == {
            "version": afanes.core.settings.SETTINGS_VERSION,
            "vault": str(vault.resolve()),
        }

    def test_unicode_path_round_trips(self, tmp_path: Path) -> None:
        vault = tmp_path / "Café notes"
        vault.mkdir()
        path = tmp_path / "settings.json"

        afanes.core.settings.save_settings(Settings(vault=vault), path)

        assert afanes.core.settings.load_settings(path) == Settings(vault=vault.resolve())

    def test_successful_write_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "settings.json"

        afanes.core.settings.save_settings(Settings(vault=vault), path)

        assert sorted(entry.name for entry in tmp_path.iterdir()) == ["settings.json", "vault"]


def _config_directory() -> Path:
    return Path("config") / "afanes"
