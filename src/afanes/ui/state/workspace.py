"""Workspace lifecycle and refresh coordination across the page domains."""

import asyncio
import dataclasses
import logging
from pathlib import Path

from afanes.core.editing import PageDraftFactory
from afanes.core.errors import (
    AfanesError,
    ConfigurationError,
    VaultError,
    VaultSchemaError,
    VaultSchemaMissingError,
    VaultSchemaNotAdoptableError,
)
from afanes.core.log import LogMode
from afanes.core.settings import Settings, SettingsStore
from afanes.core.vault.schema import VaultSchemaStore
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import VaultSnapshot
from afanes.ui.state.browser import BrowserState
from afanes.ui.state.dialogs import PageDialogState
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.navigation import PageNavigator
from afanes.ui.state.pages import PageEditorState
from afanes.ui.state.processing import ProcessingState
from afanes.ui.state.review import ReviewState
from afanes.ui.state.session import VaultOpener, VaultSession
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class WorkspaceController:
    """Coordinate vault lifecycle and refresh across the domain states.

    Attributes
    ----------
    session : VaultSession
        Vault lifecycle, snapshot, and selection state.
    browser : BrowserState
        Sidebar destination and browser query.
    pages : PageEditorState
        Page draft, editing mode, and conflict state.
    navigation : PageNavigator
        Page movement and history.
    dialogs : PageDialogState
        Pending page dialogs.
    processing : ProcessingState
        Processing Wizard session.
    review : ReviewState
        Guided review session.
    status : UiStatus
        Shared banner and busy flags.
    command_lock : CommandLock
        Shared command lock.
    banner : str | None
        Persistent vault or selection condition shown on the welcome surface
        or the workspace shell, or ``None`` when no condition is active.
    """

    session: VaultSession
    browser: BrowserState
    pages: PageEditorState
    navigation: PageNavigator
    dialogs: PageDialogState
    processing: ProcessingState
    review: ReviewState
    status: UiStatus
    command_lock: CommandLock
    banner: str | None = None

    async def start(self) -> None:
        """Load saved settings and open the remembered vault.

        Notes
        -----
        A missing settings file, malformed settings, or an unavailable vault
        leaves the controller in the welcome state with a message. Blocking
        file I/O runs in a worker thread.
        """
        self.pages.start_autosave()
        async with self.command_lock:
            self.status.set_busy(busy=True)
            try:
                try:
                    settings = await asyncio.to_thread(SettingsStore.default().load)
                except ConfigurationError:
                    logger.debug("Settings could not be read", exc_info=True)
                    self._show_welcome(self.status.copy.SETTINGS_UNREADABLE)
                    return
                if settings is None:
                    self._show_welcome(None)
                    return
                try:
                    vault = await asyncio.to_thread(VaultOpener.open, settings.vault)
                    snapshot = await asyncio.to_thread(vault.scan)
                except VaultSchemaMissingError:
                    logger.debug("Remembered vault has no settings file", exc_info=True)
                    await self._offer_adoption(settings.vault, welcome=True)
                    return
                except VaultSchemaError as exc:
                    logger.debug("Remembered vault settings cannot be used", exc_info=True)
                    self._show_welcome(self.status.copy.render_error(exc))
                    return
                except (VaultError, OSError) as exc:
                    logger.debug("Saved vault could not be opened", exc_info=True)
                    self._show_welcome(self.status.copy.render_error(exc))
                    return
                await self._enter_vault(vault, snapshot, settings.log_mode_for(vault.root))
            finally:
                self.status.set_busy(busy=False)

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
        async with self.command_lock:
            await self._open_vault_state(path, remember=True)

    async def open_vault_path(self, text: str) -> None:
        """Open a vault from a path typed by the user.

        Parameters
        ----------
        text : str
            Path typed into the welcome state or the change-vault dialog.
            Leading and trailing whitespace is ignored. Blank input is
            rejected before any filesystem access.

        Notes
        -----
        Delegates to :meth:`choose_vault`, so resolution, validation, and
        settings persistence are shared with the folder picker. A rejected
        path leaves the controller in its previous state and sets
        :attr:`banner`.
        """
        trimmed = text.strip()
        if not trimmed:
            self.banner = self.status.copy.VAULT_PATH_REQUIRED
            return
        await self.choose_vault(Path(trimmed))

    async def open_vault_for_run(self, path: Path) -> None:
        """Open a vault for this run without replacing remembered settings.

        Parameters
        ----------
        path : Path
            Vault directory supplied when the process started.

        Notes
        -----
        The vault is validated, scanned, and shown exactly as
        :meth:`choose_vault` would, but the settings file is not written, so
        the remembered vault survives the run. Blocking file I/O runs in a
        worker thread.
        """
        self.pages.start_autosave()
        async with self.command_lock:
            await self._open_vault_state(path, remember=False)

    async def _offer_adoption(self, path: Path, *, welcome: bool) -> None:
        """Offer adoption for an unversioned folder without writing to it.

        Parameters
        ----------
        path : Path
            Folder the user selected or that the preferences name.
        welcome : bool
            Whether to return to the welcome state. A change-vault offer keeps
            the current vault open.

        Notes
        -----
        The eligibility check is read-only and runs in a worker thread. A
        folder that cannot be adopted is refused with a message and no pending
        target.
        """
        target: Path | None = None
        adoptable = False
        try:
            store = VaultSchemaStore(path)
            adoptable = await asyncio.to_thread(store.is_adoptable)
            target = store.root
        except (VaultError, OSError):
            logger.debug("Adoption eligibility could not be checked", exc_info=True)
        if welcome:
            self._show_welcome(None)
        if adoptable and target is not None:
            self.session.adoption_target = target
            self.banner = self.status.copy.VAULT_SCHEMA_ADOPT_MESSAGE
            return
        self.session.adoption_target = None
        self.banner = self.status.copy.VAULT_SCHEMA_UNAVAILABLE

    async def _open_vault_state(self, path: Path, *, remember: bool) -> None:
        """Open a vault while the command lock is held."""
        if not await self.pages.commit():
            return
        self.status.set_busy(busy=True)
        self.banner = None
        try:
            existing = await self._load_settings()
            try:
                vault = await asyncio.to_thread(VaultOpener.open, path)
                snapshot = await asyncio.to_thread(vault.scan)
            except VaultSchemaMissingError:
                logger.debug("Selected folder has no settings file", exc_info=True)
                if remember:
                    await self._offer_adoption(path, welcome=False)
                else:
                    self.banner = self.status.copy.VAULT_SCHEMA_UNAVAILABLE
                return
            except VaultSchemaError as exc:
                logger.debug("Selected folder settings cannot be used", exc_info=True)
                self.banner = self.status.copy.render_error(exc)
                return
            except (VaultError, OSError) as exc:
                logger.debug("Selected vault could not be opened", exc_info=True)
                self.banner = self.status.copy.render_error(exc)
                return
            if remember:
                try:
                    await asyncio.to_thread(
                        SettingsStore.default().save,
                        self._settings_for(existing, vault.root),
                    )
                except ConfigurationError as exc:
                    logger.debug("Vault selection could not be saved", exc_info=True)
                    self.banner = self.status.copy.VAULT_SELECTION_FAILED.format(
                        detail=self.status.copy.render_error(exc)
                    )
                    return
            await self._enter_vault(
                vault,
                snapshot,
                existing.log_mode_for(vault.root) if existing is not None else "entries",
            )
        finally:
            self.status.set_busy(busy=False)

    async def create_vault(self, path: Path, template: str | None = None) -> bool:
        """Create a new vault, seed it, and open it.

        Parameters
        ----------
        path : pathlib.Path
            Directory to create or seed. Missing intermediate folders are
            created.
        template : str | None
            Bundled template identifier, or ``None`` to write only the guide
            note.

        Returns
        -------
        bool
            ``True`` when the new vault opened, ``False`` when creation was
            refused or the current draft could not be saved.

        Notes
        -----
        The vault is created and scanned before its path is saved. When the
        preferences write fails, the created vault still opens for this session
        and :attr:`message` explains that it will not be remembered. Blocking
        file I/O runs in a worker thread.
        """
        async with self.command_lock:
            return await self._create_vault_state(path, template)

    async def close_vault(self) -> bool:
        """Close the current vault and return to the welcome state.

        Returns
        -------
        bool
            ``True`` when the vault was closed, ``False`` when no vault was
            open or the open page could not be committed.

        Notes
        -----
        Closing saves a dirty draft and forgets the remembered vault by removing
        the preferences file. When the preferences cannot be removed, the
        welcome state is still shown and :attr:`message` explains that the
        vault may reopen next launch. The single-session guard is not released.
        Blocking file I/O runs in a worker thread.
        """
        async with self.command_lock:
            if self.session.vault is None:
                return False
            if not await self.pages.commit():
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    await asyncio.to_thread(SettingsStore.default().clear)
                except ConfigurationError as exc:
                    logger.debug("Remembered vault could not be forgotten", exc_info=True)
                    self._show_welcome(
                        self.status.copy.VAULT_CLOSE_NOT_FORGOTTEN.format(detail=self.status.copy.render_error(exc))
                    )
                    return True
                self._show_welcome(None)
                return True
            finally:
                self.status.set_busy(busy=False)

    async def adopt_vault(self) -> bool:
        """Write the settings file for the pending adoption target and open it.

        Returns
        -------
        bool
            ``True`` when the folder became a vault and opened, ``False``
            when no offer is pending, the draft could not be saved, or the
            write or open failed.

        Notes
        -----
        Only ``afanes.yaml`` is written. The current vault stays open until the
        settings file exists and the adopted folder scans successfully. A write
        failure leaves the pending target in place so the user can retry.
        Blocking file I/O runs in a worker thread.
        """
        target = self.session.adoption_target
        if target is None:
            return False
        async with self.command_lock:
            return await self._adopt_vault_state(target)

    def cancel_adoption(self) -> None:
        """Dismiss the pending adoption offer without writing anything."""
        self.session.adoption_target = None
        self.banner = None

    def take_banner(self, fallback: str) -> str:
        """Return the workspace banner and clear it.

        Parameters
        ----------
        fallback : str
            Text returned when no banner is active.

        Returns
        -------
        str
            The active banner text, or ``fallback`` when none is set.
        """
        message = self.banner if self.banner is not None else fallback
        self.banner = None
        return message

    async def _adopt_vault_state(self, target: Path) -> bool:
        """Adopt and open one folder while the command lock is held."""
        if not await self.pages.commit():
            return False
        self.status.set_busy(busy=True)
        self.banner = None
        try:
            try:
                await asyncio.to_thread(VaultSchemaStore(target).adopt)
                vault = await asyncio.to_thread(VaultOpener.open, target)
                snapshot = await asyncio.to_thread(vault.scan)
            except VaultSchemaNotAdoptableError as exc:
                logger.debug("Adoption target is no longer eligible", exc_info=True)
                self.banner = self.status.copy.VAULT_SCHEMA_NOT_ADOPTABLE.format(
                    detail=self.status.copy.render_error(exc)
                )
                return False
            except (VaultError, OSError) as exc:
                logger.debug("Adoption target could not be opened", exc_info=True)
                self.banner = self.status.copy.render_error(exc)
                return False
            existing = await self._load_settings()
            remember_failure: str | None = None
            try:
                await asyncio.to_thread(
                    SettingsStore.default().save,
                    self._settings_for(existing, vault.root),
                )
            except ConfigurationError as exc:
                logger.debug("Adopted vault could not be remembered", exc_info=True)
                remember_failure = self.status.copy.VAULT_SCHEMA_ADOPTED_NOT_REMEMBERED.format(
                    detail=self.status.copy.render_error(exc)
                )
            await self._enter_vault(
                vault,
                snapshot,
                existing.log_mode_for(vault.root) if existing is not None else "entries",
            )
            if remember_failure is not None:
                self.banner = remember_failure
            return True
        finally:
            self.status.set_busy(busy=False)

    async def _create_vault_state(self, path: Path, template: str | None) -> bool:
        """Create a vault while the command lock is held."""
        if not await self.pages.commit():
            return False
        self.status.set_busy(busy=True)
        self.banner = None
        try:
            existing = await self._load_settings()
            try:
                creation = await asyncio.to_thread(VaultOpener.create, path, self.status.copy, template=template)
                snapshot = await asyncio.to_thread(creation.vault.scan)
            except (VaultError, OSError) as exc:
                logger.debug("New vault could not be created", exc_info=True)
                self.banner = self.status.copy.render_error(exc)
                return False
            remember_failure: str | None = None
            try:
                await asyncio.to_thread(
                    SettingsStore.default().save,
                    self._settings_for(existing, creation.vault.root),
                )
            except ConfigurationError as exc:
                logger.debug("New vault could not be remembered", exc_info=True)
                remember_failure = self.status.copy.VAULT_CREATED_NOT_REMEMBERED.format(
                    detail=self.status.copy.render_error(exc)
                )
            await self._enter_vault(
                creation.vault,
                snapshot,
                existing.log_mode_for(creation.vault.root) if existing is not None else "entries",
            )
            if remember_failure is not None:
                self.banner = remember_failure
            return True
        finally:
            self.status.set_busy(busy=False)

    async def set_log_mode(self, mode: str) -> None:
        """Persist the Log workspace mode for the current vault.

        Parameters
        ----------
        mode : str
            ``entries`` or ``everything``. Any other value is stored as
            ``entries``.

        Notes
        -----
        The mode applies for this session even when the preferences file cannot
        be written. Blocking file I/O runs in a worker thread.
        """
        async with self.command_lock:
            try:
                selected = LogMode(mode)
            except ValueError:
                selected = LogMode.ENTRIES
            self.browser.set_log_mode(selected)
            vault = self.session.vault
            if vault is None:
                return
            existing = await self._load_settings()
            try:
                await asyncio.to_thread(
                    SettingsStore.default().save,
                    self._settings_for(existing, vault.root).with_log_mode(vault.root, selected.value),
                )
            except ConfigurationError as exc:
                logger.debug("Log mode could not be saved", exc_info=True)
                self.status.show_notice(
                    self.status.copy.LOG_MODE_NOT_REMEMBERED.format(detail=self.status.copy.render_error(exc))
                )

    async def _load_settings(self) -> Settings | None:
        """Load settings without failing the active command.

        Returns
        -------
        Settings | None
            Stored settings, or ``None`` when the file is missing or unreadable.
        """
        try:
            return await asyncio.to_thread(SettingsStore.default().load)
        except ConfigurationError:
            logger.debug("Settings could not be read", exc_info=True)
            return None

    @staticmethod
    def _settings_for(existing: Settings | None, vault: Path) -> Settings:
        """Return settings pointing at a vault while preserving preferences.

        Parameters
        ----------
        existing : Settings | None
            Previously loaded settings, or ``None``.
        vault : Path
            Vault root to remember.

        Returns
        -------
        Settings
            Settings with the new vault and the previous Log modes.
        """
        if existing is None:
            return Settings(vault=vault)
        return dataclasses.replace(existing, vault=vault)

    async def _enter_vault(self, vault: Vault, snapshot: VaultSnapshot, log_mode: str = "entries") -> None:
        """Reset per-vault state, apply a snapshot, and run trash retention.

        Parameters
        ----------
        vault : Vault
            Vault that was just opened.
        snapshot : VaultSnapshot
            Scan result for the opened vault.
        log_mode : str
            Remembered Log mode for this vault.

        Notes
        -----
        Retention runs after schema validation and after the active scan, but
        before the workspace is shown. A failure becomes the persistent trash
        banner and never blocks the open.
        """
        self.banner = None
        self.session.reset()
        self.session.vault = vault
        self.processing.clear()
        self.browser.reset()
        try:
            self.browser.set_log_mode(LogMode(log_mode))
        except ValueError:
            self.browser.set_log_mode(LogMode.ENTRIES)
        self.review.reset()
        self.navigation.reset()
        self.dialogs.clear()
        self.pages.clear()
        self.session.apply_snapshot(snapshot)
        await self.session.maintain_trash(vault.today())

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
        async with self.command_lock:
            vault = self.session.vault
            if vault is None:
                return
            self.status.set_busy(busy=True)
            try:
                try:
                    snapshot = await asyncio.to_thread(vault.scan)
                except (VaultError, OSError) as exc:
                    logger.debug("Vault scan failed", exc_info=True)
                    self.session.banner = self.status.copy.REFRESH_FAILED.format(
                        detail=self.status.copy.render_error(exc)
                    )
                    return
                self.session.apply_snapshot(snapshot)
                await self.session.refresh_trash()
                if (
                    self.pages.trash_entry is not None
                    and self.session.trash_snapshot is not None
                    and not await self.pages.follow_trash_change(self.session.trash_snapshot)
                ):
                    self.status.show_notice(self.status.copy.TRASH_PAGE_GONE)
                page = self.pages.page
                if (
                    page is not None
                    and page.path is not None
                    and not self.pages.editing
                    and self.pages.trash_entry is None
                ):
                    try:
                        content = await asyncio.to_thread(vault.read_page, page.path)
                        self.pages.page = PageDraftFactory.from_page(content, page.reference)
                    except (AfanesError, OSError, UnicodeError) as exc:
                        logger.debug("Page could not be refreshed", exc_info=True)
                        self.pages.clear()
                        self.status.show_notice(
                            self.status.copy.PAGE_OPEN_FAILED.format(detail=self.status.copy.render_error(exc))
                        )
                selected = self.session.selected
                if selected is None:
                    return
                try:
                    self.session.preview_body = await asyncio.to_thread(vault.read_body, selected)
                except (AfanesError, OSError, UnicodeError) as exc:
                    logger.debug("Preview could not be refreshed", exc_info=True)
                    self.session.selected = None
                    self.session.preview_body = None
                    self.status.show_notice(
                        self.status.copy.PREVIEW_FAILED.format(detail=self.status.copy.render_error(exc))
                    )
            finally:
                self.status.set_busy(busy=False)

    async def refresh_workspace(self) -> bool:
        """Apply an external vault change without interrupting the user.

        Returns
        -------
        bool
            ``True`` when a changed scan was applied, ``False`` when nothing
            changed, no vault is open, or a command already holds the lock.

        Notes
        -----
        This command is the background counterpart of :meth:`refresh`. It
        skips the tick instead of waiting when another command holds the
        command lock, never sets the busy indicator, and never replaces an
        owned banner or a transient notice. A processing or review flow stays
        on its note. An open page follows the change: a clean draft reloads, a
        dirty draft raises the existing conflict state, and a vanished file is
        reported as missing. Blocking reads run in a worker thread and no note
        file is created, changed, or removed.
        """
        if self.session.vault is None or self.command_lock.locked():
            return False
        async with self.command_lock:
            snapshot = await self.session.refresh_if_changed()
            trash_snapshot = await self.session.refresh_trash_if_changed()
            if snapshot is None and trash_snapshot is None:
                return False
            focused = (
                self.processing.note is None and self.processing.result is None and self.review.review_session is None
            )
            if focused and snapshot is not None:
                await self.pages.follow_external_change(snapshot)
            if focused and self.pages.trash_entry is not None:
                current = self.session.trash_snapshot
                if current is not None and not await self.pages.follow_trash_change(current):
                    self.status.show_notice(self.status.copy.TRASH_PAGE_GONE)
            return True

    def _show_welcome(self, message: str | None) -> None:
        """Clear the vault state and show the welcome screen."""
        self.session.reset()
        self.browser.reset()
        self.review.reset()
        self.navigation.reset()
        self.dialogs.clear()
        self.processing.clear()
        self.pages.clear()
        self.banner = message
