# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Platform-aware application settings stored outside the vault.

The settings file remembers one vault path between launches. It is app-owned
and contains no note content, so the Markdown vault remains portable on its
own. All paths are resolved with :mod:`pathlib` and the file is written through
the same atomic writer used for vault files.
"""

import dataclasses
import json
import os
import sys
from pathlib import Path
from typing import Self

import afanes.core.atomic
from afanes.core.errors import ConfigurationError, VaultError

# Public settings policy. Callers and tests share these values.
APP_DIRECTORY_NAME = "afanes"
SETTINGS_FILENAME = "settings.json"
SETTINGS_VERSION = 1


@dataclasses.dataclass(frozen=True, slots=True)
class Settings:
    """Application preferences remembered between launches.

    Attributes
    ----------
    vault : Path
        Absolute path to the selected vault directory.
    log_modes : dict[str, str]
        Log workspace mode per resolved vault path. A missing or unknown value
        means ``entries``.
    """

    vault: Path
    log_modes: dict[str, str] = dataclasses.field(default_factory=dict)

    def log_mode_for(self, vault: Path) -> str:
        """Return the remembered Log mode for one vault.

        Parameters
        ----------
        vault : Path
            Vault root to look up.

        Returns
        -------
        str
            ``everything`` when remembered, otherwise ``entries``.
        """
        value = self.log_modes.get(str(vault.expanduser().resolve()), "")
        return "everything" if value == "everything" else "entries"

    def with_log_mode(self, vault: Path, mode: str) -> Self:
        """Return settings with one vault's Log mode replaced.

        Parameters
        ----------
        vault : Path
            Vault root to update.
        mode : str
            Requested mode. Any value other than ``everything`` is stored as
            ``entries``.

        Returns
        -------
        Settings
            New settings; the original mapping is unchanged.
        """
        modes = dict(self.log_modes)
        modes[str(vault.expanduser().resolve())] = "everything" if mode == "everything" else "entries"
        return dataclasses.replace(self, log_modes=modes)

    @classmethod
    def from_payload(cls, payload: object, source: Path) -> Self:
        """Build settings from a decoded JSON payload.

        Parameters
        ----------
        payload : object
            Decoded JSON value. It must be an object with a supported version
            and an absolute vault path.
        source : Path
            Settings file the payload came from, used in error messages.

        Returns
        -------
        Settings
            Settings carrying the payload's vault path and Log modes.

        Raises
        ------
        ConfigurationError
            If the payload is not an object, uses an unsupported version, does
            not contain an absolute vault path, or carries malformed Log modes.
        """
        if not isinstance(payload, dict):
            message = f"Settings must be a JSON object: {source}"
            raise ConfigurationError(message)
        version = payload.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version != SETTINGS_VERSION:
            message = f"Unsupported settings version in {source}"
            raise ConfigurationError(message)
        vault = payload.get("vault")
        if not isinstance(vault, str) or not vault:
            message = f"Settings do not contain a vault path: {source}"
            raise ConfigurationError(message)
        vault_path = Path(vault)
        if not vault_path.is_absolute():
            message = f"Settings vault path must be absolute: {source}"
            raise ConfigurationError(message)
        raw_modes = payload.get("log_modes", {})
        if not isinstance(raw_modes, dict):
            message = f"Settings Log modes must be a JSON object: {source}"
            raise ConfigurationError(message)
        log_modes: dict[str, str] = {}
        for key, value in raw_modes.items():
            if not isinstance(key, str) or not isinstance(value, str):
                message = f"Settings Log modes must map paths to strings: {source}"
                raise ConfigurationError(message)
            log_modes[key] = value
        return cls(vault=vault_path, log_modes=log_modes)

    def to_payload(self) -> dict[str, object]:
        """Return the versioned JSON mapping for these settings.

        Returns
        -------
        dict[str, object]
            Mapping containing the settings version, the vault path as a
            string, and the per-vault Log modes.
        """
        return {
            "version": SETTINGS_VERSION,
            "vault": str(self.vault),
            "log_modes": dict(self.log_modes),
        }


@dataclasses.dataclass(frozen=True, slots=True)
class SettingsStore:
    """Application settings file owned by one store instance.

    Attributes
    ----------
    path : Path
        Settings file this store reads and writes.
    """

    path: Path

    @classmethod
    def config_directory(cls) -> Path:
        r"""Return the platform-specific Afanes configuration directory.

        Returns
        -------
        Path
            Linux uses ``$XDG_CONFIG_HOME/afanes`` or ``~/.config/afanes``;
            macOS uses ``~/Library/Application Support/afanes``; Windows uses
            ``%APPDATA%\afanes`` or ``~/AppData/Roaming/afanes``.

        Notes
        -----
        The directory is resolved without creating it. This method reads the
        environment and performs no filesystem write.
        """
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
            return base / APP_DIRECTORY_NAME
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / APP_DIRECTORY_NAME
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config and Path(xdg_config).is_absolute():
            return Path(xdg_config) / APP_DIRECTORY_NAME
        return Path.home() / ".config" / APP_DIRECTORY_NAME

    @classmethod
    def settings_path(cls) -> Path:
        """Return the absolute path of the settings file.

        Returns
        -------
        Path
            ``settings.json`` inside :meth:`config_directory`.
        """
        return cls.config_directory() / SETTINGS_FILENAME

    @classmethod
    def default(cls) -> Self:
        """Return a store for the platform's default settings file.

        Returns
        -------
        SettingsStore
            Store pointing at :meth:`settings_path`.
        """
        return cls(path=cls.settings_path())

    def load(self) -> Settings | None:
        """Load settings from this store's file.

        Returns
        -------
        Settings | None
            Parsed settings, or ``None`` when the file does not exist.

        Raises
        ------
        ConfigurationError
            If the file cannot be read, is not valid JSON, is not a JSON
            object, uses an unsupported version, or does not contain an
            absolute vault path.

        Notes
        -----
        This method performs blocking file I/O and never writes. A malformed
        file is reported without being modified, so the caller can offer a
        recovery path before replacing it.
        """
        if not self.path.exists():
            return None
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            message = f"Could not read settings: {self.path}"
            raise ConfigurationError(message) from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            message = f"Settings are not valid JSON: {self.path}"
            raise ConfigurationError(message) from exc
        return Settings.from_payload(payload, self.path)

    def save(self, settings: Settings) -> None:
        """Write settings atomically to this store's file.

        Parameters
        ----------
        settings : Settings
            Preferences to persist. The vault path is resolved to an absolute
            path before writing.

        Raises
        ------
        ConfigurationError
            If the vault is not an existing directory, the configuration
            directory cannot be created, or the atomic write fails.

        Notes
        -----
        This method creates the configuration directory when missing and
        performs blocking file I/O. A failed write leaves the previous
        settings file intact.
        """
        vault = settings.vault.expanduser().resolve()
        if not vault.is_dir():
            message = f"Vault is not a directory: {vault}"
            raise ConfigurationError(message)
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as exc:
            message = f"Could not create the settings directory: {self.path.parent}"
            raise ConfigurationError(message) from exc
        resolved = dataclasses.replace(settings, vault=vault)
        payload = json.dumps(resolved.to_payload(), ensure_ascii=False, indent=2)
        try:
            afanes.core.atomic.AtomicWriter.write_text_atomic(self.path, f"{payload}\n")
        except (OSError, VaultError) as exc:
            message = f"Could not write settings: {self.path}"
            raise ConfigurationError(message) from exc

    def clear(self) -> None:
        """Forget the remembered vault by removing the settings file.

        Raises
        ------
        ConfigurationError
            If the settings file exists and cannot be removed.

        Notes
        -----
        A missing file is a success, so clearing an already forgotten vault is
        idempotent. This method never reads or writes a vault; it removes only
        the application-owned preferences file and performs blocking file I/O.
        """
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            message = f"Could not remove settings: {self.path}"
            raise ConfigurationError(message) from exc
