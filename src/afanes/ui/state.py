# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Single application state controller for the Flet interface.

Views forward user intent here and render the fields this controller exposes.
All blocking settings, scan, capture, and preview work runs in worker threads
so the Flet event loop stays responsive. One lock serializes commands, which
keeps a capture from overlapping a scan or a vault change.
"""

import asyncio
import dataclasses
import logging
import os
from pathlib import Path

import afanes.ui.strings
from afanes.core.errors import AfanesError, ConfigurationError, EmptyCaptureError, VaultError
from afanes.core.settings import Settings, SettingsStore
from afanes.core.vault import Vault, VaultFailure, VaultNote, VaultSnapshot

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True, eq=False)
class AppState:
    """Mutable state shared by the welcome and Inbox views.

    Attributes
    ----------
    vault : Vault | None
        Active vault service, or ``None`` while the welcome state is shown.
    notes : tuple[VaultNote, ...]
        Inbox notes, newest first.
    failures : tuple[VaultFailure, ...]
        Notes the last scan could not parse.
    selected : Path | None
        Absolute path of the note shown in the preview.
    preview_body : str | None
        Markdown body of the previewed note, without frontmatter.
    busy : bool
        Whether a blocking command is in progress.
    message : str | None
        Banner text for the current error or warning.

    Notes
    -----
    This is the only permitted mutable module-level state in the application.
    Tests call :meth:`reset` between cases. Views must not mutate these fields
    directly; they call the command methods.
    """

    vault: Vault | None = None
    notes: tuple[VaultNote, ...] = ()
    failures: tuple[VaultFailure, ...] = ()
    selected: Path | None = None
    preview_body: str | None = None
    busy: bool = False
    message: str | None = None
    _lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock, repr=False)

    @property
    def vault_root(self) -> Path | None:
        """Return the active vault root, or ``None`` in the welcome state.

        Returns
        -------
        Path | None
            Resolved root of :attr:`vault`, or ``None`` when no vault is open.
        """
        return None if self.vault is None else self.vault.root

    async def start(self) -> None:
        """Load saved settings and open the remembered vault.

        Notes
        -----
        A missing settings file, malformed settings, or an unavailable vault
        leaves the controller in the welcome state with a message. Blocking
        file I/O runs in a worker thread.
        """
        async with self._lock:
            self.busy = True
            try:
                try:
                    settings = await asyncio.to_thread(SettingsStore.default().load)
                except ConfigurationError:
                    logger.debug("Settings could not be read", exc_info=True)
                    self._show_welcome(afanes.ui.strings.SETTINGS_UNREADABLE)
                    return
                if settings is None:
                    self._show_welcome(None)
                    return
                try:
                    vault = await asyncio.to_thread(self._open_vault, settings.vault)
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Saved vault could not be opened", exc_info=True)
                    self._show_welcome(str(exc))
                    return
                self.vault = vault
                self.selected = None
                self.preview_body = None
                self._apply_snapshot(snapshot)
            finally:
                self.busy = False

    async def choose_vault(self, path: Path) -> None:
        """Open a vault and remember it for later launches.

        Parameters
        ----------
        path : Path
            Directory chosen by the user.

        Notes
        -----
        The vault is scanned before its path is saved. A failed scan or save
        leaves the current state unchanged and reports a message. Blocking
        file I/O runs in a worker thread.
        """
        async with self._lock:
            self.busy = True
            self.message = None
            try:
                try:
                    vault = await asyncio.to_thread(self._open_vault, path)
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Selected vault could not be opened", exc_info=True)
                    self.message = str(exc)
                    return
                try:
                    await asyncio.to_thread(
                        SettingsStore.default().save,
                        Settings(vault=vault.root),
                    )
                except ConfigurationError as exc:
                    logger.debug("Vault selection could not be saved", exc_info=True)
                    self.message = afanes.ui.strings.VAULT_SELECTION_FAILED.format(detail=str(exc))
                    return
                self.vault = vault
                self.selected = None
                self.preview_body = None
                self._apply_snapshot(snapshot)
            finally:
                self.busy = False

    async def change_vault(self, path: Path) -> None:
        """Switch to a different vault without restarting the application.

        Parameters
        ----------
        path : Path
            Directory chosen by the user.

        Notes
        -----
        This delegates to :meth:`choose_vault`; the previous vault is never
        modified.
        """
        await self.choose_vault(path)

    async def refresh(self) -> None:
        """Re-read the vault and update the Inbox.

        Notes
        -----
        A selected note is re-read so an external edit appears in the preview.
        If the note disappeared, the preview is cleared. Blocking file I/O
        runs in a worker thread.
        """
        async with self._lock:
            vault = self.vault
            if vault is None:
                return
            self.busy = True
            try:
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Vault scan failed", exc_info=True)
                    self.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
                    return
                self._apply_snapshot(snapshot)
                selected = self.selected
                if selected is None:
                    return
                try:
                    self.preview_body = await asyncio.to_thread(vault.read_body, selected)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Preview could not be refreshed", exc_info=True)
                    self.selected = None
                    self.preview_body = None
                    self.message = afanes.ui.strings.PREVIEW_FAILED.format(detail=str(exc))
            finally:
                self.busy = False

    async def capture(self, text: str) -> Path | None:
        """Capture raw text into the vault's inbox.

        Parameters
        ----------
        text : str
            Thought typed into the composer.

        Returns
        -------
        Path | None
            Absolute path of the created note, or ``None`` when nothing was
            written. The caller keeps the composer text when this is ``None``.

        Notes
        -----
        The first non-blank line becomes the filename and the complete text
        becomes the body. The new note is promoted to the top of the list so
        it is visible even when filesystem timestamps tie. Blocking file I/O
        runs in a worker thread.
        """
        async with self._lock:
            if not text.strip():
                self.message = afanes.ui.strings.CAPTURE_EMPTY
                return None
            vault = self.vault
            if vault is None:
                return None
            self.busy = True
            self.message = None
            try:
                try:
                    path = await asyncio.to_thread(vault.capture, text)
                except EmptyCaptureError:
                    self.message = afanes.ui.strings.CAPTURE_EMPTY
                    return None
                except (AfanesError, OSError) as exc:
                    logger.debug("Capture failed", exc_info=True)
                    self.message = afanes.ui.strings.CAPTURE_FAILED.format(detail=str(exc))
                    return None
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Inbox refresh after capture failed", exc_info=True)
                    self.message = afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc))
                    return path
                self._apply_snapshot(snapshot, focus=path)
                return path
            finally:
                self.busy = False

    async def select_note(self, path: Path) -> None:
        """Load a note body into the read-only preview.

        Parameters
        ----------
        path : Path
            Absolute path of a note shown in the Inbox.

        Notes
        -----
        The body is read from disk on demand and never written back. A parse
        or read failure clears the preview and reports a message. Blocking
        file I/O runs in a worker thread.
        """
        async with self._lock:
            vault = self.vault
            if vault is None:
                return
            self.busy = True
            try:
                try:
                    body = await asyncio.to_thread(vault.read_body, path)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Note preview failed", exc_info=True)
                    self.selected = None
                    self.preview_body = None
                    self.message = afanes.ui.strings.PREVIEW_FAILED.format(detail=str(exc))
                    return
                self.selected = path
                self.preview_body = body
                self.message = None
            finally:
                self.busy = False

    def reset(self) -> None:
        """Return the controller to its initial state.

        Notes
        -----
        Tests call this between cases and the application calls it on
        shutdown. A fresh command lock is created for the next event loop.
        """
        self.vault = None
        self.notes = ()
        self.failures = ()
        self.selected = None
        self.preview_body = None
        self.busy = False
        self.message = None
        self._lock = asyncio.Lock()

    def _open_vault(self, path: Path) -> Vault:
        """Open a vault and map filesystem failures to user-facing errors.

        Parameters
        ----------
        path : Path
            Directory chosen by the user.

        Returns
        -------
        Vault
            Validated vault service for the directory.

        Raises
        ------
        VaultError
            If the path is missing, is not a directory, cannot be read, or
            cannot be resolved.
        """
        if not path.exists():
            raise VaultError(afanes.ui.strings.VAULT_MISSING)
        if not path.is_dir():
            raise VaultError(afanes.ui.strings.VAULT_NOT_DIRECTORY)
        if not os.access(path, os.R_OK):
            raise VaultError(afanes.ui.strings.VAULT_UNREADABLE)
        try:
            return Vault(path)
        except OSError as exc:
            raise VaultError(afanes.ui.strings.VAULT_UNREADABLE) from exc

    def _show_welcome(self, message: str | None) -> None:
        """Clear the vault state and show the welcome screen."""
        self.vault = None
        self.notes = ()
        self.failures = ()
        self.selected = None
        self.preview_body = None
        self.message = message

    def _apply_snapshot(self, snapshot: VaultSnapshot, focus: Path | None = None) -> None:
        """Replace the inbox list from a scan result."""
        notes = list(snapshot.inbox_notes())
        if focus is not None:
            for index, note in enumerate(notes):
                if note.path == focus:
                    notes.insert(0, notes.pop(index))
                    break
        self.notes = tuple(notes)
        self.failures = snapshot.failures
        if self.selected is not None and all(note.path != self.selected for note in self.notes):
            self.selected = None
            self.preview_body = None
        self.message = None


app_state = AppState()
