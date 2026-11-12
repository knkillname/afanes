"""Vault lifecycle, scanning, selection, and refresh state."""

import asyncio
import dataclasses
import logging
from pathlib import Path

import afanes.core.connections
import afanes.core.editing
import afanes.core.links
import afanes.core.names
import afanes.core.search
import afanes.core.steps
import afanes.core.templates
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.steps
import afanes.ui.strings
from afanes.core.errors import (
    AfanesError,
    EmptyCaptureError,
    TemplateError,
    VaultError,
    VaultMissingError,
    VaultNotDirectoryError,
    VaultNotEmptyError,
    VaultUnreadableError,
)
from afanes.core.template_cards import TemplateCardCatalog, TemplateCardListing
from afanes.core.templates import TemplateSummary
from afanes.core.vault.service import Vault, VaultCreation
from afanes.core.vault.snapshot import (
    VaultFailure,
    VaultNote,
    VaultSnapshot,
)
from afanes.models.link import ReferenceScheme
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)

# Workspace refresh interval. A stat walk is cheap enough that a short poll
# converges before a side-by-side edit is acted on, and a rescan happens only
# when the fingerprint moved, so the cost stays bounded.
REFRESH_SECONDS = 5


class VaultOpener:
    """Translate vault path failures into interface messages.

    Notes
    -----
    This is the interface's translation point for the folder picker, the typed
    path field, the creation action, and the command-line vault option. All
    filesystem validation lives in :class:`afanes.core.vault.service.Vault`; this class
    only maps domain errors to user-facing copy.
    """

    @staticmethod
    def open(path: Path) -> Vault:
        """Open and validate a vault directory.

        Parameters
        ----------
        path : pathlib.Path
            Candidate vault directory. A relative path is resolved by
            :class:`afanes.core.vault.service.Vault`.

        Returns
        -------
        Vault
            Validated vault service for the directory.

        Raises
        ------
        VaultError
            If the path is missing, is not a directory, cannot be read, or
            cannot be resolved.
        VaultSchemaMissingError
            If the directory has no settings file.
        VaultSchemaInvalidError
            If its settings file does not match the current shape.
        VaultSchemaUnsupportedError
            If its settings file declares another schema version.

        Notes
        -----
        Path failures become interface messages here. Schema failures keep
        their domain type so the caller can distinguish a missing file that can
        be adopted from a file that must be repaired by hand.
        """
        try:
            return Vault.open(path)
        except VaultMissingError as exc:
            raise VaultError(afanes.ui.strings.VAULT_MISSING) from exc
        except VaultNotDirectoryError as exc:
            raise VaultError(afanes.ui.strings.VAULT_NOT_DIRECTORY) from exc
        except VaultUnreadableError as exc:
            raise VaultError(afanes.ui.strings.VAULT_UNREADABLE) from exc

    @staticmethod
    def create(path: Path, *, template: str | None = None) -> VaultCreation:
        """Create a new vault and translate refusals into interface messages.

        Parameters
        ----------
        path : pathlib.Path
            Directory to create or seed. It must be missing or empty.
        template : str | None
            Bundled template identifier, or ``None`` to write only the guide
            note.

        Returns
        -------
        VaultCreation
            Created vault, the intermediate directories made for it, the
            default folders created inside it, and the notes written into it.

        Raises
        ------
        VaultError
            If the path is not a directory, is not empty, cannot be created, or
            the bundled starter content cannot be written.
        VaultSchemaWriteError
            If the settings file cannot be written. No default folder or
            starter content is written in that case.
        """
        try:
            return Vault.create_directory(path, template=template)
        except TemplateError as exc:
            raise VaultError(afanes.ui.strings.NEW_VAULT_TEMPLATE_FAILED.format(detail=exc)) from exc
        except VaultNotEmptyError as exc:
            raise VaultError(afanes.ui.strings.VAULT_NOT_EMPTY) from exc
        except VaultNotDirectoryError as exc:
            raise VaultError(afanes.ui.strings.VAULT_NOT_DIRECTORY) from exc
        except VaultMissingError as exc:
            raise VaultError(afanes.ui.strings.VAULT_MISSING) from exc
        except VaultUnreadableError as exc:
            raise VaultError(afanes.ui.strings.VAULT_UNREADABLE) from exc


@dataclasses.dataclass(slots=True)
class VaultSession:
    """Vault lifecycle, scan snapshot, and selection state.

    Attributes
    ----------
    status : UiStatus
        Shared banner and busy flags.
    command_lock : CommandLock
        Shared command lock.
    vault : Vault | None
        Active vault service, or ``None`` while the welcome state is shown.
    snapshot : VaultSnapshot | None
        Latest scan result.
    notes : tuple[VaultNote, ...]
        Inbox notes, newest first.
    failures : tuple[VaultFailure, ...]
        Notes the last scan could not parse.
    selected : Path | None
        Absolute path of the note shown in the preview.
    preview_body : str | None
        Markdown body of the previewed note, without frontmatter.
    fingerprint : tuple[tuple[str, int, int], ...] | None
        Fingerprint taken with the last applied scan, or ``None`` when no scan
        has been applied. It is compared by the background refresh to decide
        whether a rescan is needed.
    adoption_target : Path | None
        Resolved unversioned folder awaiting an explicit adoption decision, or
        ``None`` when no adoption offer is pending.
    """

    status: UiStatus
    command_lock: CommandLock
    vault: Vault | None = None
    snapshot: VaultSnapshot | None = None
    notes: tuple[VaultNote, ...] = ()
    failures: tuple[VaultFailure, ...] = ()
    selected: Path | None = None
    preview_body: str | None = None
    fingerprint: tuple[tuple[str, int, int], ...] | None = None
    adoption_target: Path | None = None
    _connections: afanes.core.connections.Connections | None = dataclasses.field(default=None, repr=False)
    _connections_snapshot: VaultSnapshot | None = dataclasses.field(default=None, repr=False)

    @property
    def vault_root(self) -> Path | None:
        """Return the active vault root, or ``None`` in the welcome state.

        Returns
        -------
        Path | None
            Resolved root of :attr:`vault`, or ``None`` when no vault is open.
        """
        return None if self.vault is None else self.vault.root

    @property
    def connections(self) -> afanes.core.connections.Connections | None:
        """Return the connection index for the current snapshot.

        Returns
        -------
        afanes.core.connections.Connections | None
            Read-only index for :attr:`snapshot`, or ``None`` when no vault is
            open.

        Notes
        -----
        The index is built lazily the first time a page needs it and reused
        while the snapshot object stays the same. A background refresh that
        applies a new snapshot invalidates the cache by identity, so the next
        reader rebuilds it without an explicit invalidation step.
        """
        snapshot = self.snapshot
        if snapshot is None:
            return None
        if self._connections is None or self._connections_snapshot is not snapshot:
            self._connections = afanes.core.connections.Connections(snapshot)
            self._connections_snapshot = snapshot
        return self._connections

    def reset(self) -> None:
        """Return the session to the welcome state."""
        self.vault = None
        self.snapshot = None
        self.notes = ()
        self.failures = ()
        self.selected = None
        self.preview_body = None
        self.fingerprint = None
        self.adoption_target = None
        self._connections = None
        self._connections_snapshot = None

    def note_title(self, path: Path) -> str:
        """Return the display title for a note in the latest scan.

        Parameters
        ----------
        path : Path
            Absolute path of a note in the vault.

        Returns
        -------
        str
            Display title, or the filename stem when the note is not in the
            latest scan.
        """
        if self.snapshot is not None:
            note = next((note for note in self.snapshot.notes if note.path == path), None)
            if note is not None:
                return note.title
        note = next((note for note in self.notes if note.path == path), None)
        return path.stem if note is None else note.title

    def assignment_candidates(self, scheme: ReferenceScheme, query: str) -> tuple[VaultNote, ...]:
        """Return assignment suggestions from the last vault scan.

        Parameters
        ----------
        scheme : ReferenceScheme
            Namespace to search, normally ``person`` or ``project``.
        query : str
            Free text typed by the user.

        Returns
        -------
        tuple[VaultNote, ...]
            Matching notes ordered by display title, then identity, or an
            empty tuple when no vault is open.
        """
        if self.snapshot is None:
            return ()
        return self.snapshot.assignment_candidates(scheme, query)

    async def refresh_snapshot(self) -> None:
        """Rescan the vault and update the inbox lists."""
        vault = self.vault
        if vault is None:
            return
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError) as exc:
            logger.debug("Snapshot refresh failed", exc_info=True)
            self.status.show_message(afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc)))
            return
        self.apply_snapshot(snapshot)

    async def refresh_if_changed(self, *, preserve_message: bool = False) -> VaultSnapshot | None:
        """Rescan the vault only when its change fingerprint moved.

        Parameters
        ----------
        preserve_message : bool
            Whether to keep the current banner message when the new snapshot is
            applied. Background refresh sets this so feedback from a user
            command survives an unrequested scan.

        Returns
        -------
        VaultSnapshot | None
            The applied scan when the vault changed, or ``None`` when the
            fingerprint matches the last applied scan or no vault is open.

        Notes
        -----
        The fingerprint is read in a worker thread before any scan, so an
        unchanged vault costs one stat walk and no parsing. A fingerprint that
        changed is treated as a request to rescan; the scan result becomes the
        new snapshot and its own fingerprint is stored. A failed fingerprint
        walk or scan leaves the previous snapshot and reports nothing, because
        a background refresh must not interrupt the user. This method performs
        blocking reads only and never writes.
        """
        vault = self.vault
        if vault is None:
            return None
        try:
            fingerprint = await asyncio.to_thread(vault.scan_fingerprint)
        except (VaultError, OSError):
            logger.debug("Vault fingerprint could not be read", exc_info=True)
            return None
        if fingerprint == self.fingerprint:
            return None
        try:
            snapshot = await asyncio.to_thread(vault.scan)
        except (VaultError, OSError):
            logger.debug("Background rescan failed", exc_info=True)
            return None
        self.apply_snapshot(snapshot, preserve_message=preserve_message)
        return snapshot

    def apply_snapshot(
        self,
        snapshot: VaultSnapshot,
        focus: Path | None = None,
        *,
        preserve_message: bool = False,
    ) -> None:
        """Replace the inbox list from a scan result.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Scan result to retain.
        focus : Path | None
            Note to promote to the top of the inbox list.
        preserve_message : bool
            Whether to keep the current banner message instead of clearing it.
        """
        self.snapshot = snapshot
        self.fingerprint = snapshot.fingerprint
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
        if not preserve_message:
            self.status.clear_message()

    async def template_summaries(self) -> tuple[TemplateSummary, ...] | None:
        """Read the bundled template catalog without blocking the interface.

        Returns
        -------
        tuple[TemplateSummary, ...] | None
            Every catalog entry with the number of notes it writes, or ``None``
            when the bundled content cannot be read.

        Notes
        -----
        A read failure is an expected degradation: the creation action still
        offers a vault without starter content. The read performs blocking
        package I/O in a worker thread and never writes.
        """
        try:
            return await asyncio.to_thread(afanes.core.templates.TemplateCatalog.bundled().summaries)
        except (VaultError, OSError):
            logger.debug("Bundled starter content could not be read", exc_info=True)
            return None

    async def template_cards(self) -> TemplateCardListing | None:
        """Read the vault reference template cards without blocking the interface.

        Returns
        -------
        TemplateCardListing | None
            Valid cards plus an issue for each refused file, or ``None`` when no
            vault is open or the folder cannot be read.

        Notes
        -----
        A missing ``templates/`` folder is an empty listing, not an error. The
        read performs blocking file I/O in a worker thread and never writes.
        """
        vault = self.vault
        if vault is None:
            return None
        try:
            return await asyncio.to_thread(self._read_template_cards, vault)
        except (VaultError, OSError) as exc:
            logger.debug("Reference template cards could not be read", exc_info=True)
            self.status.show_message(afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc)))
            return None

    @staticmethod
    def _read_template_cards(vault: Vault) -> TemplateCardListing:
        """Read one vault's template card listing without blocking the UI.

        Parameters
        ----------
        vault : Vault
            Active vault whose ``templates/`` folder should be read.

        Returns
        -------
        TemplateCardListing
            Valid cards plus an issue for each refused file.
        """
        catalog = TemplateCardCatalog.from_root(vault.templates_directory())
        return catalog.load()

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
        async with self.command_lock:
            if not text.strip():
                self.status.show_message(afanes.ui.strings.CAPTURE_EMPTY)
                return None
            vault = self.vault
            if vault is None:
                return None
            self.status.set_busy(busy=True)
            self.status.clear_message()
            try:
                try:
                    path = await asyncio.to_thread(afanes.core.vault.pages.VaultPages(vault).capture, text)
                except EmptyCaptureError:
                    self.status.show_message(afanes.ui.strings.CAPTURE_EMPTY)
                    return None
                except (AfanesError, OSError) as exc:
                    logger.debug("Capture failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.CAPTURE_FAILED.format(detail=str(exc)))
                    return None
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Inbox refresh after capture failed", exc_info=True)
                    self.status.show_message(afanes.ui.strings.REFRESH_FAILED.format(detail=str(exc)))
                    return path
                self.apply_snapshot(snapshot, focus=path)
                return path
            finally:
                self.status.set_busy(busy=False)

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
        async with self.command_lock:
            vault = self.vault
            if vault is None:
                return
            self.status.set_busy(busy=True)
            try:
                try:
                    body = await asyncio.to_thread(vault.read_body, path)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Note preview failed", exc_info=True)
                    self.selected = None
                    self.preview_body = None
                    self.status.show_message(afanes.ui.strings.PREVIEW_FAILED.format(detail=str(exc)))
                    return
                self.selected = path
                self.preview_body = body
                self.status.clear_message()
            finally:
                self.status.set_busy(busy=False)
