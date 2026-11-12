"""Browser section, query, and derived listings."""

import dataclasses
import logging
from enum import StrEnum

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
from afanes.core.search import (
    BrowserListing,
    BrowserSection,
    ProjectGroup,
)
from afanes.ui.state.lock import CommandLock
from afanes.ui.state.session import VaultSession

logger = logging.getLogger(__name__)


class WorkspaceSection(StrEnum):
    """Top-level destinations in the workspace sidebar.

    Attributes
    ----------
    REVIEW : str
        Guided review of pending captures, steps, and projects.
    INBOX : str
        Captures stored under the inbox directory.
    PROJECTS : str
        Project notes grouped by status.
    REFERENCES : str
        Reference notes grouped by category label.
    NEEDS_ATTENTION : str
        Unclarified notes found outside the inbox.
    """

    REVIEW = "review"
    INBOX = "inbox"
    PROJECTS = "projects"
    REFERENCES = "references"
    NEEDS_ATTENTION = "needs_attention"

    @property
    def browser_section(self) -> BrowserSection | None:
        """Return the matching browser section, or ``None`` for Review.

        Returns
        -------
        BrowserSection | None
            Section used to select browser entries. Review has no browser
            section because it changes the main workspace area.
        """
        if self is WorkspaceSection.REVIEW:
            return None
        return BrowserSection(self.value)


@dataclasses.dataclass(slots=True)
class BrowserState:
    """Sidebar destination and browser query.

    Attributes
    ----------
    session : VaultSession
        Vault state that owns the scan snapshot.
    command_lock : CommandLock
        Shared command lock.
    active_section : WorkspaceSection
        Sidebar destination currently shown.
    query : str
        Title and identity filter typed into the browser search field.
    """

    session: VaultSession
    command_lock: CommandLock
    active_section: WorkspaceSection = WorkspaceSection.INBOX
    query: str = ""

    async def set_section(self, section: WorkspaceSection) -> None:
        """Select one workspace sidebar destination.

        Parameters
        ----------
        section : WorkspaceSection
            Destination to show.
        """
        async with self.command_lock:
            self.active_section = section
            self.session.status.clear_message()

    async def set_query(self, query: str) -> None:
        """Filter browser entries by display title or identity.

        Parameters
        ----------
        query : str
            Text typed into the search field.
        """
        async with self.command_lock:
            self.query = query
            self.session.status.clear_message()

    def listing(self) -> BrowserListing | None:
        """Return the current browser groups after applying the query.

        Returns
        -------
        BrowserListing | None
            Grouped notes from the latest scan, or ``None`` when no vault is
            open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return None
        return afanes.core.search.Browser(snapshot).filter(self.query)

    def project_groups(self) -> tuple[ProjectGroup, ...]:
        """Return project summaries grouped by presentation stage.

        Returns
        -------
        tuple[ProjectGroup, ...]
            Active, Waiting, Later, and Closed groups, or an empty tuple when
            no vault is open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return ()
        return afanes.core.search.ProjectBoard(snapshot).groups()

    def pending_count(self) -> int:
        """Return the number of items that need review attention.

        Returns
        -------
        int
            Pending inbox captures plus open projects without an open action.
            Zero when no vault is open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return 0
        return afanes.core.search.ReviewPlanner(snapshot).pending_count()

    def due_count(self) -> int:
        """Return the number of due or overdue own steps.

        Returns
        -------
        int
            Due own steps from the latest scan. Zero when no vault is open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return 0
        return afanes.core.search.ReviewPlanner(snapshot).due_count()

    def reset(self) -> None:
        """Return the browser to the Inbox with no query."""
        self.active_section = WorkspaceSection.INBOX
        self.query = ""
