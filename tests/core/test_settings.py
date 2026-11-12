"""Tests for platform-aware application settings."""

import json
import sys
from pathlib import Path
from typing import NoReturn

import pytest

import afanes.core.atomic
import afanes.core.settings
from afanes.core.errors import ConfigurationError, VaultError
from afanes.core.settings import Settings, SettingsStore


class TestConfigDirectory:
    def test_linux_uses_xdg_config_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

        assert SettingsStore.config_directory() == tmp_path / "xdg" / "afanes"

    def test_linux_falls_back_to_home_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        assert SettingsStore.config_directory() == tmp_path / "home" / ".config" / "afanes"

    def test_linux_ignores_a_relative_xdg_config_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.setenv("XDG_CONFIG_HOME", "relative/config")

        assert SettingsStore.config_directory() == tmp_path / "home" / ".config" / "afanes"

    def test_macos_uses_application_support(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

        expected = tmp_path / "home" / "Library" / "Application Support" / "afanes"
        assert SettingsStore.config_directory() == expected

    def test_windows_uses_appdata(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))

        assert SettingsStore.config_directory() == tmp_path / "roaming" / "afanes"

    def test_windows_falls_back_to_roaming_appdata(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("APPDATA", raising=False)

        expected = tmp_path / "home" / "AppData" / "Roaming" / "afanes"
        assert SettingsStore.config_directory() == expected

    def test_settings_path_appends_the_filename(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(SettingsStore, "config_directory", classmethod(lambda _cls: _config_directory()))

        assert SettingsStore.settings_path() == Path("config/afanes/settings.json")


class TestSettingsPayload:
    def test_to_payload_contains_version_and_vault(self, tmp_path: Path) -> None:
        settings = Settings(vault=tmp_path)

        assert settings.to_payload() == {
            "version": afanes.core.settings.SETTINGS_VERSION,
            "vault": str(tmp_path),
            "log_modes": {},
        }

    def test_log_mode_defaults_to_entries(self, tmp_path: Path) -> None:
        settings = Settings(vault=tmp_path)

        assert settings.log_mode_for(tmp_path) == "entries"
        assert settings.log_mode_for(tmp_path / "other") == "entries"

    def test_log_mode_is_stored_per_vault(self, tmp_path: Path) -> None:
        first = tmp_path / "first"
        second = tmp_path / "second"
        first.mkdir()
        second.mkdir()
        settings = Settings(vault=first).with_log_mode(first, "everything")

        assert settings.log_mode_for(first) == "everything"
        assert settings.log_mode_for(second) == "entries"

    def test_unknown_log_mode_is_normalized(self, tmp_path: Path) -> None:
        settings = Settings(vault=tmp_path).with_log_mode(tmp_path, "unknown")

        assert settings.log_mode_for(tmp_path) == "entries"

    def test_payload_round_trips_log_modes(self, tmp_path: Path) -> None:
        settings = Settings(vault=tmp_path).with_log_mode(tmp_path, "everything")
        payload = settings.to_payload()

        loaded = Settings.from_payload(payload, tmp_path / "settings.json")

        assert loaded.log_mode_for(tmp_path) == "everything"

    def test_malformed_log_modes_are_rejected(self, tmp_path: Path) -> None:
        payload: dict[str, object] = {
            "version": afanes.core.settings.SETTINGS_VERSION,
            "vault": str(tmp_path),
            "log_modes": "bad",
        }

        with pytest.raises(ConfigurationError):
            Settings.from_payload(payload, tmp_path / "settings.json")

    def test_from_payload_returns_settings(self, tmp_path: Path) -> None:
        payload = {"version": afanes.core.settings.SETTINGS_VERSION, "vault": str(tmp_path)}

        assert Settings.from_payload(payload, tmp_path / "settings.json") == Settings(vault=tmp_path)

    def test_payload_round_trips(self, tmp_path: Path) -> None:
        settings = Settings(vault=tmp_path)

        assert Settings.from_payload(settings.to_payload(), tmp_path / "settings.json") == settings

    def test_rejects_a_non_object_payload(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError):
            Settings.from_payload([], tmp_path / "settings.json")

    def test_rejects_an_unsupported_version(self, tmp_path: Path) -> None:
        payload = {"version": 2, "vault": str(tmp_path)}

        with pytest.raises(ConfigurationError):
            Settings.from_payload(payload, tmp_path / "settings.json")

    def test_rejects_a_boolean_version(self, tmp_path: Path) -> None:
        payload = {"version": True, "vault": str(tmp_path)}

        with pytest.raises(ConfigurationError):
            Settings.from_payload(payload, tmp_path / "settings.json")

    def test_rejects_a_missing_vault(self, tmp_path: Path) -> None:
        payload = {"version": afanes.core.settings.SETTINGS_VERSION}

        with pytest.raises(ConfigurationError):
            Settings.from_payload(payload, tmp_path / "settings.json")

    def test_rejects_an_empty_vault(self, tmp_path: Path) -> None:
        payload = {"version": afanes.core.settings.SETTINGS_VERSION, "vault": ""}

        with pytest.raises(ConfigurationError):
            Settings.from_payload(payload, tmp_path / "settings.json")

    def test_rejects_a_relative_vault(self, tmp_path: Path) -> None:
        payload = {"version": afanes.core.settings.SETTINGS_VERSION, "vault": "relative"}

        with pytest.raises(ConfigurationError):
            Settings.from_payload(payload, tmp_path / "settings.json")


class TestSettingsStoreLoad:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert SettingsStore(tmp_path / "settings.json").load() is None

    def test_round_trip_returns_the_saved_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "config" / "settings.json"

        SettingsStore(path).save(Settings(vault=vault))

        assert SettingsStore(path).load() == Settings(vault=vault.resolve())

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("{not json", encoding="utf-8")

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

    def test_non_object_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("[]", encoding="utf-8")

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

    def test_unsupported_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"version": 2, "vault": str(tmp_path)}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

    def test_boolean_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"version": True, "vault": str(tmp_path)}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

    def test_missing_version_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"vault": str(tmp_path)}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

    def test_missing_vault_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"version": 1}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

    def test_relative_vault_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"version": 1, "vault": "relative"}), encoding="utf-8")

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

    def test_unreadable_path_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.mkdir()

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

    def test_malformed_file_is_not_rewritten(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("{not json", encoding="utf-8")

        with pytest.raises(ConfigurationError):
            SettingsStore(path).load()

        assert path.read_text(encoding="utf-8") == "{not json"


class TestSettingsStoreSave:
    def test_default_uses_the_platform_settings_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(SettingsStore, "settings_path", classmethod(lambda _cls: tmp_path / "settings.json"))

        assert SettingsStore.default() == SettingsStore(tmp_path / "settings.json")

    def test_save_creates_missing_directories(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "nested" / "config" / "settings.json"

        SettingsStore(path).save(Settings(vault=vault))

        assert path.is_file()

    def test_save_resolves_a_relative_vault(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "settings.json"
        monkeypatch.chdir(tmp_path)

        SettingsStore(path).save(Settings(vault=Path("vault")))
        loaded = SettingsStore(path).load()

        assert loaded is not None
        assert loaded.vault == vault.resolve()

    def test_save_rejects_a_missing_vault(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"

        with pytest.raises(ConfigurationError):
            SettingsStore(path).save(Settings(vault=tmp_path / "missing"))

        assert not path.exists()

    def test_save_rejects_a_file_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.write_text("not a directory", encoding="utf-8")
        path = tmp_path / "settings.json"

        with pytest.raises(ConfigurationError):
            SettingsStore(path).save(Settings(vault=vault))

    def test_save_rejects_a_blocked_config_directory(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        blocker = tmp_path / "blocked"
        blocker.write_text("not a directory", encoding="utf-8")
        path = blocker / "settings.json"

        with pytest.raises(ConfigurationError):
            SettingsStore(path).save(Settings(vault=vault))

    def test_failed_write_preserves_previous_settings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        first_vault = tmp_path / "first"
        second_vault = tmp_path / "second"
        first_vault.mkdir()
        second_vault.mkdir()
        path = tmp_path / "settings.json"
        SettingsStore(path).save(Settings(vault=first_vault))
        before = path.read_text(encoding="utf-8")

        def fail_write(_destination: Path, _text: str) -> NoReturn:
            message = "simulated failure"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.atomic, "write_text_atomic", fail_write)

        with pytest.raises(ConfigurationError):
            SettingsStore(path).save(Settings(vault=second_vault))

        assert path.read_text(encoding="utf-8") == before

    def test_saved_payload_contains_only_version_and_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "settings.json"

        SettingsStore(path).save(Settings(vault=vault))

        assert json.loads(path.read_text(encoding="utf-8")) == {
            "version": afanes.core.settings.SETTINGS_VERSION,
            "vault": str(vault.resolve()),
            "log_modes": {},
        }

    def test_unicode_path_round_trips(self, tmp_path: Path) -> None:
        vault = tmp_path / "Café notes"
        vault.mkdir()
        path = tmp_path / "settings.json"

        SettingsStore(path).save(Settings(vault=vault))

        assert SettingsStore(path).load() == Settings(vault=vault.resolve())

    def test_successful_write_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "settings.json"

        SettingsStore(path).save(Settings(vault=vault))

        assert sorted(entry.name for entry in tmp_path.iterdir()) == ["settings.json", "vault"]


class TestSettingsClear:
    def test_removes_an_existing_settings_file(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        path = tmp_path / "settings.json"
        store = SettingsStore(path)
        store.save(Settings(vault=vault))

        store.clear()

        assert not path.exists()
        assert store.load() is None

    def test_missing_settings_file_is_success(self, tmp_path: Path) -> None:
        SettingsStore(tmp_path / "settings.json").clear()

        assert not (tmp_path / "settings.json").exists()

    def test_unremovable_path_raises_a_configuration_error(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.mkdir()

        with pytest.raises(ConfigurationError) as info:
            SettingsStore(path).clear()

        assert str(path) in str(info.value)

    def test_clearing_leaves_the_vault_untouched(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        note = vault / "note.md"
        note.write_text("---\ntype: reference\n---\n\n# Note\n", encoding="utf-8")
        path = tmp_path / "settings.json"
        store = SettingsStore(path)
        store.save(Settings(vault=vault))
        before = note.read_bytes()

        store.clear()

        assert note.read_bytes() == before


def _config_directory() -> Path:
    return Path("config") / "afanes"
