"""Guided review queue session state."""

import asyncio
import dataclasses
import datetime
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Self

import afanes.core.search
import afanes.core.vault.pages
import afanes.core.vault.steps
import afanes.ui.strings
from afanes.core.errors import AfanesError
from afanes.core.search import (
    ProjectSummary,
    ReviewItem,
    ReviewItemKind,
)
from afanes.core.vault.service import Vault
from afanes.models.note import Status
from afanes.ui.state.browser import BrowserState, WorkspaceSection
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.navigation import PageNavigator
from afanes.ui.state.processing import ProcessingState
from afanes.ui.state.session import VaultSession
from afanes.ui.state.status import UiStatus

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewSession:
    """Snapshot queue and progress for one guided review.

    Attributes
    ----------
    items : tuple[ReviewItem, ...]
        Queue captured when the session started.
    index : int
        Position of the current item in :attr:`items`.
    reviewed : tuple[Path, ...]
        Paths the user reviewed, in order.
    skipped : tuple[Path, ...]
        Paths the user skipped, in order.
    """

    items: tuple[ReviewItem, ...]
    index: int = 0
    reviewed: tuple[Path, ...] = ()
    skipped: tuple[Path, ...] = ()

    @property
    def current(self) -> ReviewItem | None:
        """Return the current item, or ``None`` when the queue is complete.

        Returns
        -------
        ReviewItem | None
            Item at :attr:`index`, or ``None`` past the end of the queue.
        """
        if 0 <= self.index < len(self.items):
            return self.items[self.index]
        return None

    @property
    def complete(self) -> bool:
        """Return whether every queued item has been passed.

        Returns
        -------
        bool
            ``True`` when :attr:`index` is at or past the end of the queue.
        """
        return self.index >= len(self.items)

    @property
    def reviewed_count(self) -> int:
        """Return the number of reviewed items.

        Returns
        -------
        int
            Length of :attr:`reviewed`.
        """
        return len(self.reviewed)

    @property
    def skipped_count(self) -> int:
        """Return the number of skipped items.

        Returns
        -------
        int
            Length of :attr:`skipped`.
        """
        return len(self.skipped)

    def record_reviewed(self) -> Self:
        """Mark the current item reviewed and advance.

        Returns
        -------
        ReviewSession
            New session with the current path recorded and the index advanced.
            The original is unchanged. A complete session is returned as is.
        """
        item = self.current
        if item is None:
            return self
        return dataclasses.replace(
            self,
            index=self.index + 1,
            reviewed=(*self.reviewed, item.path),
        )

    def record_skipped(self) -> Self:
        """Mark the current item skipped and advance.

        Returns
        -------
        ReviewSession
            New session with the current path recorded as skipped and the
            index advanced. The original is unchanged.
        """
        item = self.current
        if item is None:
            return self
        return dataclasses.replace(
            self,
            index=self.index + 1,
            skipped=(*self.skipped, item.path),
        )

    def replace_current_project(self, summary: ProjectSummary) -> Self:
        """Replace the current project item with a refreshed summary.

        Parameters
        ----------
        summary : ProjectSummary
            Refreshed summary for the project at the current position.

        Returns
        -------
        ReviewSession
            New session whose current item carries ``summary``. The original is
            unchanged. A non-project or complete session is returned as is.
        """
        item = self.current
        if item is None or item.kind is not ReviewItemKind.PROJECT:
            return self
        replacement = ReviewItem(kind=item.kind, path=item.path, project=summary)
        items = list(self.items)
        items[self.index] = replacement
        return dataclasses.replace(self, items=tuple(items))


@dataclasses.dataclass(slots=True)
class ReviewState:
    """Guided review session and queue navigation.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the active vault and snapshot.
    browser : BrowserState
        Sidebar destination state.
    processing : ProcessingState
        Processing state used to load the current capture.
    navigation : PageNavigator
        Navigation state used when a review opens a note.
    status : UiStatus
        Shared banner and busy flags.
    command_lock : CommandLock
        Shared command lock.
    review_session : ReviewSession | None
        Guided review session in progress, or ``None``.
    """

    session: VaultSession
    browser: BrowserState
    processing: ProcessingState
    navigation: PageNavigator
    status: UiStatus
    command_lock: CommandLock
    review_session: ReviewSession | None = None

    def reset(self) -> None:
        """Close the review session."""
        self.review_session = None

    async def start(self) -> bool:
        """Start a guided review from the latest vault scan.

        Returns
        -------
        bool
            ``True`` when a session with at least one item started.

        Notes
        -----
        The queue is a snapshot: pending inbox captures first, then open
        projects without a next action, then healthy open projects. Work
        created during the session waits for the next session. A zero queue
        opens the Review destination without creating a session. Blocking
        reads run in a worker thread.
        """
        async with self.command_lock:
            snapshot = self.session.snapshot
            if snapshot is None:
                return False
            queue = afanes.core.search.ReviewPlanner(snapshot).queue()
            self.review_session = ReviewSession(items=queue) if queue else None
            self.browser.active_section = WorkspaceSection.REVIEW
            self.processing.clear()
            if not queue:
                return False
            await self._enter_current_review_item()
            return True

    async def next(self) -> bool:
        """Mark the current project reviewed and show the next item.

        Returns
        -------
        bool
            ``True`` when the session advanced. Inbox items cannot be advanced
            with this command; they require a processing outcome or Skip.
        """
        async with self.command_lock:
            session = self.review_session
            if session is None or session.current is None or session.current.kind is not ReviewItemKind.PROJECT:
                return False
            self.review_session = session.record_reviewed()
            await self._enter_current_review_item()
            return True

    async def skip(self) -> bool:
        """Skip the current item without changing it.

        Returns
        -------
        bool
            ``True`` when an item was skipped and the session advanced.
        """
        async with self.command_lock:
            session = self.review_session
            if session is None or session.current is None:
                return False
            self.review_session = session.record_skipped()
            await self._enter_current_review_item()
            return True

    async def select(self, index: int) -> bool:
        """Make one queue item current without reviewing or skipping it.

        Parameters
        ----------
        index : int
            Position in the snapshot queue.

        Returns
        -------
        bool
            ``True`` when the session moved to that item.

        Notes
        -----
        Only the current position changes. The reviewed and skipped records and
        the queue order stay untouched.
        """
        async with self.command_lock:
            session = self.review_session
            if session is None or not 0 <= index < len(session.items):
                return False
            if index == session.index:
                return True
            self.review_session = dataclasses.replace(session, index=index)
            await self._enter_current_review_item()
            return True

    async def add_step(self, text: str) -> Path | None:
        """Append the next step to the current stalled project.

        Parameters
        ----------
        text : str
            Step text typed into the review card. Whitespace-only input is
            rejected without writing.

        Returns
        -------
        Path | None
            Absolute path of the project that gained the step, or ``None``
            when nothing was written.

        Notes
        -----
        Only the project body changes. The refreshed summary is applied to the
        current item so the card shows the new next step. Blocking writes and
        scans run in a worker thread.
        """
        async with self.command_lock:
            item = self._current_review_project()
            vault = self.session.vault
            if item is None or vault is None or not text.strip():
                return None
            self.status.set_busy(busy=True)
            try:
                try:
                    await asyncio.to_thread(
                        afanes.core.vault.steps.VaultSteps(vault).append_step, item.path, text, confirm=True
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Review step creation failed", exc_info=True)
                    self.status.show_notice(afanes.ui.strings.REVIEW_STEP_FAILED.format(detail=str(exc)))
                    return None
                await self.session.refresh_snapshot()
                self._replace_review_project(item.path)
                return item.path
            finally:
                self.status.set_busy(busy=False)

    async def do_now(self) -> bool:
        """Complete the current due step and record today as its actual date.

        Returns
        -------
        bool
            ``True`` when the step was written and the session advanced.
        """
        item = self._current_review_step()
        if item is None or item.step is None:
            return False
        return await self._update_review_step(
            lambda vault: afanes.core.vault.steps.VaultSteps(vault).tick_step(
                item.path,
                item.step.line_index,
                datetime.datetime.now(tz=datetime.UTC).astimezone().date(),
                confirm=True,
            ),
        )

    async def postpone(self, plan: datetime.date) -> bool:
        """Postpone the current due step to a later plan date.

        Parameters
        ----------
        plan : datetime.date
            New calendar plan date.

        Returns
        -------
        bool
            ``True`` when the step was written and the session advanced.
        """
        item = self._current_review_step()
        if item is None or item.step is None:
            return False
        return await self._update_review_step(
            lambda vault: afanes.core.vault.steps.VaultSteps(vault).plan_step(
                item.path, item.step.line_index, plan, confirm=True
            ),
        )

    async def delegate(self, owner: str) -> bool:
        """Add an owner to the current due step, moving it to waiting.

        Parameters
        ----------
        owner : str
            Owner name. Whitespace-only input is rejected without writing.

        Returns
        -------
        bool
            ``True`` when the step was written and the session advanced.
        """
        item = self._current_review_step()
        if item is None or item.step is None or not owner.strip():
            return False
        owners = (*item.step.owners, owner.strip())
        return await self._update_review_step(
            lambda vault: afanes.core.vault.steps.VaultSteps(vault).set_step_owners(
                item.path, item.step.line_index, owners, confirm=True
            ),
        )

    async def reassign(self, owner: str) -> bool:
        """Replace the owners of the current waiting step.

        Parameters
        ----------
        owner : str
            New owner name. Whitespace-only input is rejected without writing.

        Returns
        -------
        bool
            ``True`` when the step was written and the session advanced.
        """
        item = self._current_review_step()
        if item is None or item.step is None or not owner.strip():
            return False
        return await self._update_review_step(
            lambda vault: afanes.core.vault.steps.VaultSteps(vault).set_step_owners(
                item.path,
                item.step.line_index,
                (owner.strip(),),
                confirm=True,
            ),
        )

    async def open_project(self) -> bool:
        """Open the project page for the current review item.

        Returns
        -------
        bool
            ``True`` when the project page was loaded.
        """
        item = self._current_review_step() or self._current_review_project()
        if item is None:
            return False
        if not await self.navigation.open_page(item.path):
            return False
        await self.browser.set_section(WorkspaceSection.PROJECTS)
        return True

    async def mark_project_done(self) -> bool:
        """Mark the current review project ``done`` after confirmation.

        Returns
        -------
        bool
            ``True`` when the status changed and the session advanced.
        """
        return await self._set_review_project_status(Status.DONE)

    async def defer_project(self) -> bool:
        """Defer the current review project to ``later`` after confirmation.

        Returns
        -------
        bool
            ``True`` when the status changed and the session advanced.
        """
        return await self._set_review_project_status(Status.LATER)

    async def finish(self) -> None:
        """Close the review session and return to the browser."""
        async with self.command_lock:
            self.review_session = None
            self.browser.active_section = WorkspaceSection.INBOX
            self.processing.clear()

    def _current_review_project(self) -> ReviewItem | None:
        """Return the current project review item, or ``None``."""
        session = self.review_session
        if session is None:
            return None
        item = session.current
        if item is None or item.kind is not ReviewItemKind.PROJECT or item.project is None:
            return None
        return item

    def _current_review_step(self) -> ReviewItem | None:
        """Return the current step review item, or ``None``."""
        session = self.review_session
        if session is None:
            return None
        item = session.current
        if item is None or item.kind not in (ReviewItemKind.DUE_STEP, ReviewItemKind.WAITING_STEP):
            return None
        if item.step is None or item.project is None:
            return None
        return item

    async def _update_review_step(
        self,
        action: Callable[[Vault], object],
    ) -> bool:
        """Apply one confirmed write to the current review step."""
        async with self.command_lock:
            vault = self.session.vault
            if vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    await asyncio.to_thread(action, vault)
                except (AfanesError, OSError) as exc:
                    logger.debug("Review step write failed", exc_info=True)
                    self.status.show_notice(afanes.ui.strings.REVIEW_STEP_FAILED.format(detail=str(exc)))
                    return False
                await self.session.refresh_snapshot()
                session = self.review_session
                if session is not None:
                    self.review_session = session.record_reviewed()
                await self._enter_current_review_item()
                return True
            finally:
                self.status.set_busy(busy=False)

    async def _enter_current_review_item(self) -> None:
        """Load the current review item, skipping captures that disappeared."""
        while True:
            session = self.review_session
            if session is None:
                return
            item = session.current
            self.processing.clear()
            if item is None:
                self.session.selected = None
                self.session.preview_body = None
                return
            if item.kind is not ReviewItemKind.INBOX:
                self.session.selected = None
                self.session.preview_body = None
                return
            if self.session.vault is None:
                return
            try:
                await self.processing.load(item.path)
            except (AfanesError, OSError, UnicodeError) as exc:
                logger.debug("Review capture could not be read", exc_info=True)
                self.status.show_notice(afanes.ui.strings.REVIEW_CAPTURE_READ_FAILED.format(detail=str(exc)))
                self.review_session = session.record_skipped()
                continue
            return

    async def _set_review_project_status(self, status: Status) -> bool:
        """Apply one confirmed status change to the current review project."""
        async with self.command_lock:
            item = self._current_review_project()
            vault = self.session.vault
            if item is None or vault is None:
                return False
            self.status.set_busy(busy=True)
            try:
                try:
                    await asyncio.to_thread(
                        afanes.core.vault.pages.VaultPages(vault).set_status,
                        item.path,
                        status,
                        snapshot=self.session.snapshot,
                        confirm=True,
                    )
                except (AfanesError, OSError) as exc:
                    logger.debug("Review project status change failed", exc_info=True)
                    self.status.show_notice(afanes.ui.strings.REVIEW_PROJECT_FAILED.format(detail=str(exc)))
                    return False
                await self.session.refresh_snapshot()
                session = self.review_session
                if session is not None:
                    self.review_session = session.record_reviewed()
                await self._enter_current_review_item()
                return True
            finally:
                self.status.set_busy(busy=False)

    def _replace_review_project(self, path: Path) -> None:
        """Replace the current review project with its refreshed summary."""
        snapshot = self.session.snapshot
        session = self.review_session
        if snapshot is None or session is None:
            return
        summary = next(
            (value for value in afanes.core.search.ProjectBoard(snapshot).summaries() if value.note.path == path),
            None,
        )
        if summary is not None:
            self.review_session = session.replace_current_project(summary)

    async def record_processed(self) -> bool:
        """Record the current capture as processed and show the next item.

        Returns
        -------
        bool
            ``True`` when an item was recorded and the queue advanced.
        """
        async with self.command_lock:
            session = self.review_session
            if session is None:
                return False
            self.review_session = session.record_reviewed()
            await self._enter_current_review_item()
            return True
