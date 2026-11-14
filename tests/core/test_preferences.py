"""Tests for the application preferences file."""

import json
from pathlib import Path
from typing import NoReturn

import pytest

import afanes.core.atomic
import afanes.core.preferences
import afanes.core.settings
from afanes.core.errors import ConfigurationError, MessageCode, VaultError
from afanes.core.preferences import Preferences, PreferencesStore
from afanes.core.settings import Settings, SettingsStore
from tests.support import constant, simulated_message


class TestPreferencesPayload:
    def test_default_preferences_use_the_system_locale(self) -> None:
        assert Preferences().language is None

    def test_a_supported_language_round_trips(self) -> None:
        preferences = Preferences(language="es")

        payload = preferences.to_payload()
        loaded = Preferences.from_payload(payload, Path("preferences.json"))

        assert loaded == preferences

    def test_an_unset_language_round_trips(self) -> None:
        preferences = Preferences()

        payload = preferences.to_payload()
        loaded = Preferences.from_payload(payload, Path("preferences.json"))

        assert loaded == preferences

    def test_an_unsupported_language_cannot_be_constructed(self) -> None:
        with pytest.raises(ValueError, match="Unsupported language preference"):
            Preferences(language="fr")

    def test_a_non_object_payload_is_reported(self) -> None:
        path = Path("preferences.json")

        with pytest.raises(ConfigurationError) as info:
            Preferences.from_payload([], path)

        assert info.value.domain_message is not None
        assert info.value.domain_message.code is MessageCode.PREFERENCES_NOT_OBJECT

    def test_an_unsupported_version_is_reported(self) -> None:
        path = Path("preferences.json")

        with pytest.raises(ConfigurationError) as info:
            Preferences.from_payload({"version": 2}, path)

        assert info.value.domain_message is not None
        assert info.value.domain_message.code is MessageCode.PREFERENCES_VERSION_UNSUPPORTED

    def test_a_boolean_version_is_reported(self) -> None:
        path = Path("preferences.json")

        with pytest.raises(ConfigurationError) as info:
            Preferences.from_payload({"version": True}, path)

        assert info.value.domain_message is not None
        assert info.value.domain_message.code is MessageCode.PREFERENCES_VERSION_UNSUPPORTED

    def test_an_unsupported_payload_language_is_reported(self) -> None:
        path = Path("preferences.json")

        with pytest.raises(ConfigurationError) as info:
            Preferences.from_payload({"version": 1, "language": "fr"}, path)

        assert info.value.domain_message is not None
        assert info.value.domain_message.code is MessageCode.PREFERENCES_LANGUAGE_INVALID

    def test_a_non_text_payload_language_is_reported(self) -> None:
        path = Path("preferences.json")

        with pytest.raises(ConfigurationError) as info:
            Preferences.from_payload({"version": 1, "language": 3}, path)

        assert info.value.domain_message is not None
        assert info.value.domain_message.code is MessageCode.PREFERENCES_LANGUAGE_INVALID


class TestPreferencesStorePaths:
    def test_default_uses_the_platform_preferences_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            PreferencesStore,
            "preferences_path",
            classmethod(constant(tmp_path / "preferences.json")),
        )

        assert PreferencesStore.default() == PreferencesStore(tmp_path / "preferences.json")

    def test_the_preferences_path_uses_the_configuration_directory(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            PreferencesStore,
            "config_directory",
            classmethod(constant(Path("config") / "afanes")),
        )

        assert PreferencesStore.preferences_path() == Path("config/afanes/preferences.json")

    def test_the_configuration_directory_matches_settings(self) -> None:
        assert PreferencesStore.config_directory() == SettingsStore.config_directory()


class TestPreferencesStoreLoad:
    def test_a_missing_file_means_the_system_locale(self, tmp_path: Path) -> None:
        result = PreferencesStore(tmp_path / "preferences.json").load()

        assert result.preferences == Preferences()
        assert result.problem is None

    def test_a_saved_language_is_loaded(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        store = PreferencesStore(path)
        store.save(Preferences(language="es"))

        result = store.load()

        assert result.preferences == Preferences(language="es")
        assert result.problem is None

    def test_an_english_preference_round_trips(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        store = PreferencesStore(path)
        store.save(Preferences(language="en"))

        assert store.load().preferences == Preferences(language="en")

    def test_a_system_choice_round_trips(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        store = PreferencesStore(path)
        store.save(Preferences())

        assert store.load().preferences == Preferences()

    def test_malformed_json_is_reported_and_preserved(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        path.write_text("{not json", encoding="utf-8")

        result = PreferencesStore(path).load()

        assert result.preferences == Preferences()
        assert result.problem is not None
        assert result.problem.code is MessageCode.PREFERENCES_JSON_INVALID
        assert path.read_text(encoding="utf-8") == "{not json"

    def test_an_unsupported_version_is_reported_and_preserved(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        original = json.dumps({"version": 9, "language": "es"})
        path.write_text(original, encoding="utf-8")

        result = PreferencesStore(path).load()

        assert result.problem is not None
        assert result.problem.code is MessageCode.PREFERENCES_VERSION_UNSUPPORTED
        assert path.read_text(encoding="utf-8") == original

    def test_an_unsupported_language_is_reported_and_preserved(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        original = json.dumps({"version": 1, "language": "fr"})
        path.write_text(original, encoding="utf-8")

        result = PreferencesStore(path).load()

        assert result.problem is not None
        assert result.problem.code is MessageCode.PREFERENCES_LANGUAGE_INVALID
        assert path.read_text(encoding="utf-8") == original

    def test_a_non_object_payload_is_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        path.write_text("[]", encoding="utf-8")

        result = PreferencesStore(path).load()

        assert result.problem is not None
        assert result.problem.code is MessageCode.PREFERENCES_NOT_OBJECT

    def test_an_unreadable_path_is_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        path.mkdir()

        result = PreferencesStore(path).load()

        assert result.problem is not None
        assert result.problem.code is MessageCode.PREFERENCES_READ_FAILED
        assert path.is_dir()

    def test_the_problem_names_the_file(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"
        path.write_text("{not json", encoding="utf-8")

        result = PreferencesStore(path).load()

        assert result.problem is not None
        assert str(path) in dict(result.problem.values)["source"]


class TestPreferencesStoreSave:
    def test_save_creates_missing_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "config" / "preferences.json"

        PreferencesStore(path).save(Preferences(language="es"))

        assert path.is_file()

    def test_save_needs_no_vault(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"

        PreferencesStore(path).save(Preferences(language="es"))

        assert not any(entry.name == "afanes.yaml" for entry in tmp_path.iterdir())
        assert PreferencesStore(path).load().preferences == Preferences(language="es")

    def test_the_saved_payload_contains_only_version_and_language(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"

        PreferencesStore(path).save(Preferences(language="es"))

        assert json.loads(path.read_text(encoding="utf-8")) == {
            "version": afanes.core.preferences.PREFERENCES_VERSION,
            "language": "es",
        }

    def test_a_failed_write_preserves_the_previous_preferences(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        path = tmp_path / "preferences.json"
        store = PreferencesStore(path)
        store.save(Preferences(language="es"))
        before = path.read_text(encoding="utf-8")

        def fail_write(_destination: Path, _text: str) -> NoReturn:
            raise VaultError(simulated_message())

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", fail_write)

        with pytest.raises(ConfigurationError) as info:
            store.save(Preferences(language="en"))

        assert path.read_text(encoding="utf-8") == before
        assert info.value.domain_message is not None
        assert info.value.domain_message.code is MessageCode.PREFERENCES_WRITE_FAILED

    def test_a_blocked_configuration_directory_is_reported(self, tmp_path: Path) -> None:
        blocker = tmp_path / "blocked"
        blocker.write_text("not a directory", encoding="utf-8")
        path = blocker / "preferences.json"

        with pytest.raises(ConfigurationError) as info:
            PreferencesStore(path).save(Preferences(language="es"))

        assert info.value.domain_message is not None
        assert info.value.domain_message.code is MessageCode.PREFERENCES_DIRECTORY_FAILED

    def test_clearing_settings_does_not_remove_the_preference(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        settings_path = tmp_path / "settings.json"
        preferences_path = tmp_path / "preferences.json"
        SettingsStore(settings_path).save(Settings(vault=vault))
        PreferencesStore(preferences_path).save(Preferences(language="es"))

        SettingsStore(settings_path).clear()

        assert not settings_path.exists()
        assert PreferencesStore(preferences_path).load().preferences == Preferences(language="es")

    def test_a_successful_write_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        path = tmp_path / "preferences.json"

        PreferencesStore(path).save(Preferences(language="es"))

        assert sorted(entry.name for entry in tmp_path.iterdir()) == ["preferences.json"]
