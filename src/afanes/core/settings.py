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

import afanes.core.vault
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
    """

    vault: Path


def config_directory() -> Path:
    r"""Return the platform-specific Afanes configuration directory.

    Returns
    -------
    Path
        Linux uses ``$XDG_CONFIG_HOME/afanes`` or ``~/.config/afanes``;
        macOS uses ``~/Library/Application Support/afanes``; Windows uses
        ``%APPDATA%\afanes`` or ``~/AppData/Roaming/afanes``.

    Notes
    -----
    The directory is resolved without creating it. This function reads the
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


def settings_path() -> Path:
    """Return the absolute path of the settings file.

    Returns
    -------
    Path
        ``settings.json`` inside :func:`config_directory`.
    """
    return config_directory() / SETTINGS_FILENAME


def load_settings(path: Path | None = None) -> Settings | None:
    """Load application settings from disk.

    Parameters
    ----------
    path : Path | None
        Settings file to read. Defaults to :func:`settings_path`.

    Returns
    -------
    Settings | None
        Parsed settings, or ``None`` when the file does not exist.

    Raises
    ------
    ConfigurationError
        If the file cannot be read, is not valid JSON, is not a JSON object,
        uses an unsupported version, or does not contain an absolute vault
        path.

    Notes
    -----
    This function performs blocking file I/O and never writes. A malformed
    file is reported without being modified, so the caller can offer a
    recovery path before replacing it.
    """
    source = settings_path() if path is None else path
    if not source.exists():
        return None
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        message = f"Could not read settings: {source}"
        raise ConfigurationError(message) from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        message = f"Settings are not valid JSON: {source}"
        raise ConfigurationError(message) from exc
    return _settings_from_payload(payload, source)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Write application settings atomically.

    Parameters
    ----------
    settings : Settings
        Preferences to persist. The vault path is resolved to an absolute
        path before writing.
    path : Path | None
        Settings file to write. Defaults to :func:`settings_path`.

    Raises
    ------
    ConfigurationError
        If the vault is not an existing directory, the configuration
        directory cannot be created, or the atomic write fails.

    Notes
    -----
    This function creates the configuration directory when missing and
    performs blocking file I/O. A failed write leaves the previous settings
    file intact.
    """
    destination = settings_path() if path is None else path
    vault = settings.vault.expanduser().resolve()
    if not vault.is_dir():
        message = f"Vault is not a directory: {vault}"
        raise ConfigurationError(message)
    try:
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        message = f"Could not create the settings directory: {destination.parent}"
        raise ConfigurationError(message) from exc
    payload = json.dumps(
        {"version": SETTINGS_VERSION, "vault": str(vault)},
        ensure_ascii=False,
        indent=2,
    )
    try:
        afanes.core.vault.write_text_atomic(destination, f"{payload}\n")
    except (OSError, VaultError) as exc:
        message = f"Could not write settings: {destination}"
        raise ConfigurationError(message) from exc


def _settings_from_payload(payload: object, source: Path) -> Settings:
    """Validate a decoded JSON payload and return settings."""
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
    return Settings(vault=vault_path)
