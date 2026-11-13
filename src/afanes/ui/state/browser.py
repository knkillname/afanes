"""Browser section, query, and derived listings."""

import dataclasses
import logging
from enum import StrEnum
from pathlib import Path

import afanes.core.editing
import afanes.core.links
import afanes.core.log
import afanes.core.names
import afanes.core.search
import afanes.core.steps
import afanes.core.templates
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.steps
import afanes.ui.strings
from afanes.core.log import LogMode, LogTimeline
from afanes.core.search import (
    BrowserListing,
    BrowserSection,
    ProjectGroup,
)
from afanes.models.note import CategoryLabel, NoteType
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
    LOG : str
        Dated log entries and the Everything date lens.
    NEEDS_ATTENTION : str
        Unclarified notes found outside the inbox.
    """

    REVIEW = "review"
    INBOX = "inbox"
    PROJECTS = "projects"
    REFERENCES = "references"
    LOG = "log"
    NEEDS_ATTENTION = "needs_attention"

    @property
    def browser_section(self) -> BrowserSection | None:
        """Return the matching browser section, or ``None`` for custom areas.

        Returns
        -------
        BrowserSection | None
            Section used to select browser entries. Review and Log have no flat
            browser section because they change the lower sidebar area.
        """
        if self in (WorkspaceSection.REVIEW, WorkspaceSection.LOG):
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
    log_mode : LogMode
        Entries or Everything for the Log section.
    log_year : int | None
        Calendar year shown by the Log calendar, or ``None`` for the current
        month.
    log_month : int | None
        Calendar month shown by the Log calendar, or ``None`` for the current
        month.
    log_day : int | None
        Selected calendar day in the shown month, or ``None`` when no day is
        selected.
    log_selected : Path | None
        Log entry currently selected in the tree, when one is selected.
    """

    session: VaultSession
    command_lock: CommandLock
    active_section: WorkspaceSection = WorkspaceSection.INBOX
    query: str = ""
    log_mode: LogMode = LogMode.ENTRIES
    log_year: int | None = None
    log_month: int | None = None
    log_day: int | None = None
    log_selected: Path | None = None

    async def set_section(self, section: WorkspaceSection) -> None:
        """Select one workspace sidebar destination.

        Parameters
        ----------
        section : WorkspaceSection
            Destination to show.
        """
        async with self.command_lock:
            self.active_section = section
            self.query = ""

    async def set_query(self, query: str) -> None:
        """Filter browser entries by display title or identity.

        Parameters
        ----------
        query : str
            Text typed into the search field.
        """
        async with self.command_lock:
            self.query = query

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

    def counts(self) -> dict[WorkspaceSection, int]:
        """Return unfiltered totals for every destination.

        Returns
        -------
        dict[WorkspaceSection, int]
            Number of notes behind each destination. Review is omitted; Log
            counts every entry in the active Log lens. An empty mapping is
            returned when no vault is open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return {}
        listing = afanes.core.search.Browser(snapshot).groups()
        counts: dict[WorkspaceSection, int] = {}
        for section in WorkspaceSection:
            if section is WorkspaceSection.REVIEW:
                continue
            if section is WorkspaceSection.LOG:
                counts[section] = len(LogTimeline(snapshot, self.log_mode, "").entries())
                continue
            browser_section = section.browser_section
            if browser_section is None:
                counts[section] = 0
            else:
                counts[section] = sum(len(group.notes) for group in listing.groups_for(browser_section))
        return counts

    def reference_categories(self) -> tuple[CategoryLabel, ...]:
        """Return every category label used by a reference note.

        Returns
        -------
        tuple[CategoryLabel, ...]
            Distinct labels sorted case-insensitively, or an empty tuple when
            no vault is open.

        Notes
        -----
        The result ignores the browser query and the active section, so a
        category is still known when a search filters its notes out of the
        sidebar.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return ()
        listing = afanes.core.search.Browser(snapshot).groups()
        labels = {group.label for group in listing.groups_for(BrowserSection.REFERENCES) if group.label is not None}
        return tuple(sorted(labels, key=lambda label: label.value.casefold()))

    async def role_categories(self) -> tuple[CategoryLabel, ...]:
        """Return category suggestions for a missing role name.

        Returns
        -------
        tuple[CategoryLabel, ...]
            `person`, every category used by a reference note, and every
            category declared by a valid reference template card, sorted
            case-insensitively.

        Notes
        -----
        The suggestions ignore the browser query and the active section. A
        missing ``templates/`` folder still yields `person` and the categories
        already in use. Reading the cards runs blocking I/O in a worker thread
        and never writes.
        """
        categories = {CategoryLabel("person"), *self.reference_categories()}
        listing = await self.session.template_cards()
        if listing is not None:
            categories.update(
                card.category for card in listing.for_type(NoteType.REFERENCE) if card.category is not None
            )
        return tuple(sorted(categories, key=lambda label: label.value.casefold()))

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

    def timeline(self) -> LogTimeline | None:
        """Return the Log timeline for the current snapshot and query.

        Returns
        -------
        LogTimeline | None
            Year, month, day, and calendar query, or ``None`` when no vault is
            open.
        """
        snapshot = self.session.snapshot
        if snapshot is None:
            return None
        return afanes.core.log.LogTimeline(snapshot, self.log_mode, self.query)

    def set_log_mode(self, mode: LogMode) -> None:
        """Select the Log mode.

        Parameters
        ----------
        mode : LogMode
            Entries or Everything.
        """
        self.log_mode = mode

    def show_log_month(self, year: int, month: int) -> None:
        """Select the month shown by the Log calendar.

        Parameters
        ----------
        year : int
            Calendar year.
        month : int
            Calendar month, 1-12.
        """
        self.log_year = year
        self.log_month = month
        self.log_day = None

    def select_log_day(self, day: int | None) -> None:
        """Select the calendar day whose rows should expand.

        Parameters
        ----------
        day : int | None
            Calendar day, or ``None`` to collapse the selected day.
        """
        self.log_day = day

    def select_log_entry(self, path: Path | None) -> None:
        """Remember which log entry is selected in the tree.

        Parameters
        ----------
        path : Path | None
            Selected entry path, or ``None`` to clear the selection.
        """
        self.log_selected = path

    def reset(self) -> None:
        """Return the browser to the Inbox with no query or Log selection."""
        self.active_section = WorkspaceSection.INBOX
        self.query = ""
        self.log_mode = LogMode.ENTRIES
        self.log_year = None
        self.log_month = None
        self.log_day = None
        self.log_selected = None
