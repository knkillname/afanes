# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Application preferences stored outside the vault.

The preferences file remembers the optional interface language. It contains no
vault path and no note content, so it survives opening another vault or closing
the current one. A corrupt file is reported and preserved, never overwritten
silently.
"""

import dataclasses
import json
from pathlib import Path
from typing import Self

import afanes.core.atomic
import afanes.core.localization
import afanes.core.settings
from afanes.core.errors import ConfigurationError, DomainMessage, MessageCode, VaultError

# Public preferences policy. Callers and tests share these values.
PREFERENCES_FILENAME = "preferences.json"
PREFERENCES_VERSION = 1


@dataclasses.dataclass(frozen=True, slots=True)
class Preferences:
    """App-owned preferences remembered between launches.

    Attributes
    ----------
    language : str | None
        Saved language code, or ``None`` to resolve the system locale.
    """

    language: str | None = None

    def __post_init__(self) -> None:
        """Validate the optional language.

        Raises
        ------
        ValueError
            If the language is neither ``None`` nor a supported language.
        """
        if self.language is not None and self.language not in afanes.core.localization.SUPPORTED_LANGUAGES:
            message = f"Unsupported language preference: {self.language!r}"
            raise ValueError(message)

    @classmethod
    def from_payload(cls, payload: object, source: Path) -> Self:
        """Build preferences from a decoded JSON payload.

        Parameters
        ----------
        payload : object
            Decoded JSON value. It must be an object with a supported version
            and an optional supported language.
        source : Path
            Preferences file the payload came from, used in error messages.

        Returns
        -------
        Preferences
            Preferences carrying the optional language.

        Raises
        ------
        ConfigurationError
            If the payload is not an object, uses an unsupported version, or
            names an unsupported language. The error carries a structured
            domain message.
        """
        if not isinstance(payload, dict):
            message = DomainMessage.of(MessageCode.PREFERENCES_NOT_OBJECT, source=str(source))
            raise ConfigurationError(message)
        version = payload.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version != PREFERENCES_VERSION:
            message = DomainMessage.of(MessageCode.PREFERENCES_VERSION_UNSUPPORTED, source=str(source))
            raise ConfigurationError(message)
        language = payload.get("language")
        if language is None:
            return cls()
        if not isinstance(language, str) or language not in afanes.core.localization.SUPPORTED_LANGUAGES:
            message = DomainMessage.of(MessageCode.PREFERENCES_LANGUAGE_INVALID, source=str(source))
            raise ConfigurationError(message)
        return cls(language=language)

    def to_payload(self) -> dict[str, object]:
        """Return the versioned JSON mapping for these preferences.

        Returns
        -------
        dict[str, object]
            Mapping containing the preferences version and the optional
            language.
        """
        return {
            "version": PREFERENCES_VERSION,
            "language": self.language,
        }


@dataclasses.dataclass(frozen=True, slots=True)
class PreferencesLoad:
    """Result of loading the preferences file.

    Attributes
    ----------
    preferences : Preferences
        Preferences to use. A corrupt file yields the default preferences.
    problem : DomainMessage | None
        Structured report when the file could not be read or parsed, or
        ``None`` on success.
    """

    preferences: Preferences
    problem: DomainMessage | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class PreferencesStore:
    """Application preferences file owned by one store instance.

    Attributes
    ----------
    path : Path
        Preferences file this store reads and writes.
    """

    path: Path

    @classmethod
    def config_directory(cls) -> Path:
        """Return the directory that owns the application settings file.

        Returns
        -------
        Path
            Parent of the configured ``settings.json`` path, so a custom
            settings location also scopes the preferences file.
        """
        return afanes.core.settings.SettingsStore.settings_path().parent

    @classmethod
    def preferences_path(cls) -> Path:
        """Return the absolute path of the preferences file.

        Returns
        -------
        Path
            ``preferences.json`` inside :meth:`config_directory`.
        """
        return cls.config_directory() / PREFERENCES_FILENAME

    @classmethod
    def default(cls) -> Self:
        """Return a store for the platform's default preferences file.

        Returns
        -------
        PreferencesStore
            Store pointing at :meth:`preferences_path`.
        """
        return cls(path=cls.preferences_path())

    def load(self) -> PreferencesLoad:
        """Load preferences from this store's file.

        Returns
        -------
        PreferencesLoad
            Loaded preferences and a structured problem when the file could not
            be read or parsed.

        Notes
        -----
        This method performs blocking file I/O and never writes. A corrupt file
        is reported without being modified, so the caller can inform the user
        and resolve the system locale instead.
        """
        if not self.path.exists():
            return PreferencesLoad(preferences=Preferences())
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError:
            problem = DomainMessage.of(MessageCode.PREFERENCES_READ_FAILED, source=str(self.path))
            return PreferencesLoad(preferences=Preferences(), problem=problem)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            problem = DomainMessage.of(MessageCode.PREFERENCES_JSON_INVALID, source=str(self.path))
            return PreferencesLoad(preferences=Preferences(), problem=problem)
        try:
            preferences = Preferences.from_payload(payload, self.path)
        except ConfigurationError as exc:
            problem = exc.domain_message
            if problem is None:
                problem = DomainMessage.of(MessageCode.PREFERENCES_NOT_OBJECT, source=str(self.path))
            return PreferencesLoad(preferences=Preferences(), problem=problem)
        return PreferencesLoad(preferences=preferences)

    def save(self, preferences: Preferences) -> None:
        """Write preferences atomically to this store's file.

        Parameters
        ----------
        preferences : Preferences
            Preferences to persist.

        Raises
        ------
        ConfigurationError
            If the configuration directory cannot be created or the atomic
            write fails. The error carries a structured domain message.

        Notes
        -----
        This method creates the configuration directory when missing and
        performs blocking file I/O. It never requires or touches a vault. A
        failed write leaves the previous preferences file intact.
        """
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as exc:
            message = DomainMessage.of(MessageCode.PREFERENCES_DIRECTORY_FAILED, source=str(self.path.parent))
            raise ConfigurationError(message) from exc
        payload = json.dumps(preferences.to_payload(), ensure_ascii=False, indent=2)
        try:
            afanes.core.atomic.AtomicWriter.write_text_atomic(self.path, f"{payload}\n")
        except (OSError, VaultError) as exc:
            message = DomainMessage.of(MessageCode.PREFERENCES_WRITE_FAILED, source=str(self.path))
            raise ConfigurationError(message) from exc
