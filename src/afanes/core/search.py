# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only browsing, project, and review queries over a vault snapshot.

The services in this module never read or write files. They derive browser
groups, project summaries, and review queues from an already scanned
:class:`afanes.core.vault.VaultSnapshot`, keeping classification rules out of
the interface layer.
"""

import dataclasses
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Self

import afanes.core.links
import afanes.core.names
from afanes.core.links import ResolutionOutcome
from afanes.core.vault import NoteOrder, VaultFailure, VaultNote, VaultSnapshot
from afanes.models.link import ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status


class BrowserSection(StrEnum):
    """Fixed sections of the vault browser.

    Attributes
    ----------
    INBOX : str
        Captures stored under the vault's inbox directory.
    PROJECTS : str
        Notes of type ``project``.
    ACTIONS : str
        Notes of type ``action``.
    PEOPLE : str
        Reference notes with ``category: person``.
    REFERENCES : str
        Uncategorized reference notes.
    NOTES : str
        Free-form notes outside the inbox.
    """

    INBOX = "inbox"
    PROJECTS = "projects"
    ACTIONS = "actions"
    PEOPLE = "people"
    REFERENCES = "references"
    NOTES = "notes"


class ProjectStage(StrEnum):
    """Presentation groups for project statuses.

    Attributes
    ----------
    ACTIVE : str
        Projects that are active or have no status.
    WAITING : str
        Projects explicitly waiting on something.
    LATER : str
        Projects deferred for later attention.
    CLOSED : str
        Completed, cancelled, or archived projects.
    """

    ACTIVE = "active"
    WAITING = "waiting"
    LATER = "later"
    CLOSED = "closed"


class ReviewItemKind(StrEnum):
    """Kind of work queued for a review session.

    Attributes
    ----------
    INBOX : str
        A capture that still needs an explicit processing outcome.
    PROJECT : str
        An open project whose next step should be confirmed or created.
    """

    INBOX = "inbox"
    PROJECT = "project"


@dataclasses.dataclass(frozen=True, slots=True)
class BrowserGroup:
    """One section of the browser and its notes.

    Attributes
    ----------
    section : BrowserSection
        Section that owns the notes.
    notes : tuple[VaultNote, ...]
        Notes in presentation order. The inbox is newest first; other
        sections are ordered by display title, identity, and path.
    """

    section: BrowserSection
    notes: tuple[VaultNote, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class BrowserListing:
    """Every parsed note grouped for the browser, plus scan failures.

    Attributes
    ----------
    groups : tuple[BrowserGroup, ...]
        One group per browser section, always in section order.
    failures : tuple[VaultFailure, ...]
        Notes the scan could not parse, in scan order.
    """

    groups: tuple[BrowserGroup, ...]
    failures: tuple[VaultFailure, ...]

    def group(self, section: BrowserSection) -> BrowserGroup:
        """Return one browser group.

        Parameters
        ----------
        section : BrowserSection
            Section to return. Every section is always present.

        Returns
        -------
        BrowserGroup
            Group for the requested section.
        """
        return next(group for group in self.groups if group.section is section)

    def filtered(self, query: str) -> Self:
        """Return a listing whose groups match a title or identity query.

        Parameters
        ----------
        query : str
            Free text typed into the browser search field. Matching ignores
            case, Unicode form, and repeated whitespace. An empty query keeps
            every note.

        Returns
        -------
        BrowserListing
            Listing with the same sections and failures. Search never reads a
            note body, so body-only terms match nothing.
        """
        return BrowserListing(
            groups=tuple(
                BrowserGroup(section=group.section, notes=Browser.filter_notes(group.notes, query))
                for group in self.groups
            ),
            failures=self.failures,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ProjectSummary:
    """One project and the actions attributed to it.

    Attributes
    ----------
    note : VaultNote
        Parsed project note.
    open_actions : tuple[VaultNote, ...]
        Actions attributed to the project that are open, ordered by the next
        action policy.
    next_action : VaultNote | None
        First open action, or ``None`` when the project has no open action.
    """

    note: VaultNote
    open_actions: tuple[VaultNote, ...]
    next_action: VaultNote | None

    @property
    def open_count(self) -> int:
        """Return the number of open actions.

        Returns
        -------
        int
            Length of :attr:`open_actions`.
        """
        return len(self.open_actions)


@dataclasses.dataclass(frozen=True, slots=True)
class ProjectGroup:
    """Projects sharing one presentation stage.

    Attributes
    ----------
    stage : ProjectStage
        Stage represented by this group.
    projects : tuple[ProjectSummary, ...]
        Projects in the stage, ordered by due date and title.
    """

    stage: ProjectStage
    projects: tuple[ProjectSummary, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewItem:
    """One snapshot entry in a guided review session.

    Attributes
    ----------
    kind : ReviewItemKind
        Whether the item is an inbox capture or a project.
    path : Path
        Absolute path of the capture or project note.
    project : ProjectSummary | None
        Project data for a project item; ``None`` for an inbox item.
    """

    kind: ReviewItemKind
    path: Path
    project: ProjectSummary | None = None


class Browser:
    """Browser groups and title filtering over one snapshot.

    Parameters
    ----------
    snapshot : VaultSnapshot
        Read-only scan result captured when the browser is shown.
    """

    def __init__(self, snapshot: VaultSnapshot) -> None:
        """Store the snapshot this browser queries.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Read-only scan result.
        """
        self._snapshot = snapshot

    def groups(self) -> BrowserListing:
        """Group every parsed note for the browser.

        Returns
        -------
        BrowserListing
            Six section groups in fixed order plus parse failures. A note
            appears in exactly one group; captures under the inbox appear only
            under ``Inbox``. Notes under ``trash/`` are already excluded by the
            scan.

        Notes
        -----
        This method performs no file I/O and never changes a note.
        """
        groups: dict[BrowserSection, list[VaultNote]] = {section: [] for section in BrowserSection}
        for note in self._snapshot.inbox_notes():
            groups[BrowserSection.INBOX].append(note)
        for note in self._snapshot.notes:
            if note.is_inbox:
                continue
            groups[self._section_for(note)].append(note)
        return BrowserListing(
            groups=tuple(
                BrowserGroup(
                    section=section,
                    notes=tuple(groups[section]) if section is BrowserSection.INBOX else self._sorted(groups[section]),
                )
                for section in BrowserSection
            ),
            failures=self._snapshot.failures,
        )

    def filter(self, query: str) -> BrowserListing:
        """Return browser groups filtered by a title or identity query.

        Parameters
        ----------
        query : str
            Text typed into the browser search field.

        Returns
        -------
        BrowserListing
            Grouped notes that match the query.
        """
        return self.groups().filtered(query)

    @classmethod
    def filter_notes(cls, notes: Iterable[VaultNote], query: str) -> tuple[VaultNote, ...]:
        """Filter notes by display title or identity.

        Parameters
        ----------
        notes : Iterable[VaultNote]
            Notes to filter, in presentation order.
        query : str
            Free text typed by the user. Matching uses
            :func:`afanes.core.names.normalize_name`, so case, Unicode form,
            and repeated whitespace are ignored. An empty query keeps every
            note.

        Returns
        -------
        tuple[VaultNote, ...]
            Matching notes in the input order. The body is never inspected.
        """
        return tuple(note for note in notes if cls.matches(note, query))

    @staticmethod
    def matches(note: VaultNote, query: str) -> bool:
        """Return whether a note matches a title or identity query.

        Parameters
        ----------
        note : VaultNote
            Note to test.
        query : str
            Free text query. An empty query matches every note.

        Returns
        -------
        bool
            ``True`` when the normalized query is contained in the normalized
            display title or identity.
        """
        normalized_query = afanes.core.names.normalize_name(query)
        if not normalized_query:
            return True
        return normalized_query in afanes.core.names.normalize_name(
            note.title
        ) or normalized_query in afanes.core.names.normalize_name(note.name)

    @staticmethod
    def _section_for(note: VaultNote) -> BrowserSection:
        """Return the browser section for a non-inbox note."""
        if note.note_type is NoteType.PROJECT:
            return BrowserSection.PROJECTS
        if note.note_type is NoteType.ACTION:
            return BrowserSection.ACTIONS
        if note.note_type is NoteType.REFERENCE:
            return BrowserSection.PEOPLE if note.category is ReferenceCategory.PERSON else BrowserSection.REFERENCES
        return BrowserSection.NOTES

    @staticmethod
    def _sorted(notes: Iterable[VaultNote]) -> tuple[VaultNote, ...]:
        """Sort notes by display title, identity, and path."""
        return tuple(sorted(notes, key=lambda note: note.alphabetical_order))


class ProjectBoard:
    """Project summaries and stage groups over one snapshot.

    Parameters
    ----------
    snapshot : VaultSnapshot
        Read-only scan result captured when the board is shown.
    """

    def __init__(self, snapshot: VaultSnapshot) -> None:
        """Store the snapshot this board queries.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Read-only scan result.
        """
        self._snapshot = snapshot

    def summaries(self) -> tuple[ProjectSummary, ...]:
        """Build one summary for every parsed project.

        Returns
        -------
        tuple[ProjectSummary, ...]
            Summaries ordered by due date, then display title, identity, and
            path.

        Notes
        -----
        An action belongs to a project only when its ``project`` frontmatter
        reference resolves uniquely to that project. Body links, unresolved
        references, and ambiguous references are ignored. Only actions that
        are open contribute to :attr:`ProjectSummary.open_actions`.
        """
        projects = [note for note in self._snapshot.notes if note.note_type is NoteType.PROJECT]
        actions_by_project: dict[Path, list[VaultNote]] = {project.path: [] for project in projects}
        for note in self._snapshot.notes:
            if note.note_type is not NoteType.ACTION or not note.is_open_action:
                continue
            for path in self._attributed(note):
                actions_by_project[path].append(note)

        summaries = [self._summary(project, tuple(actions_by_project[project.path])) for project in projects]
        return tuple(sorted(summaries, key=ProjectBoard._project_order))

    def groups(self) -> tuple[ProjectGroup, ...]:
        """Group project summaries by presentation stage.

        Returns
        -------
        tuple[ProjectGroup, ...]
            Active, Waiting, Later, and Closed groups in that order. Every
            group is present even when empty. A project with no status is
            active.
        """
        summaries = self.summaries()
        return tuple(
            ProjectGroup(
                stage=stage,
                projects=tuple(summary for summary in summaries if self._stage(summary.note) is stage),
            )
            for stage in ProjectStage
        )

    def _attributed(self, action: VaultNote) -> tuple[Path, ...]:
        """Return project paths that uniquely resolve from one action's reference."""
        paths: list[Path] = []
        for reference in action.frontmatter_references:
            if reference.scheme is not ReferenceScheme.PROJECT:
                continue
            resolution = self._snapshot.catalog.resolve(reference)
            if resolution.outcome is ResolutionOutcome.RESOLVED:
                paths.append(resolution.targets[0])
        return tuple(paths)

    @staticmethod
    def _summary(project: VaultNote, actions: tuple[VaultNote, ...]) -> ProjectSummary:
        """Build one project summary and compute its next action."""
        ordered = tuple(sorted(actions, key=lambda note: note.action_order))
        return ProjectSummary(
            note=project,
            open_actions=ordered,
            next_action=ordered[0] if ordered else None,
        )

    @staticmethod
    def _project_order(summary: ProjectSummary) -> NoteOrder:
        """Order projects by due date, then display title, identity, and path."""
        return summary.note.order

    @staticmethod
    def _stage(note: VaultNote) -> ProjectStage:
        """Map a project status to its presentation stage."""
        if note.status in (Status.DONE, Status.CANCELLED, Status.ARCHIVED):
            return ProjectStage.CLOSED
        if note.status is Status.WAITING:
            return ProjectStage.WAITING
        if note.status is Status.LATER:
            return ProjectStage.LATER
        return ProjectStage.ACTIVE


class ReviewPlanner:
    """Guided review queue and pending count over one snapshot.

    Parameters
    ----------
    snapshot : VaultSnapshot
        Read-only scan result captured when the session starts.
    """

    def __init__(self, snapshot: VaultSnapshot) -> None:
        """Store the snapshot this planner queries.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Read-only scan result.
        """
        self._snapshot = snapshot

    def queue(self) -> tuple[ReviewItem, ...]:
        """Build the ordered queue for one review session.

        Returns
        -------
        tuple[ReviewItem, ...]
            Pending inbox captures first, newest first; then open projects
            with no open action; then healthy open projects for confirmation.
            Closed projects are excluded.

        Notes
        -----
        The result is a snapshot. Work created or changed after this call is
        not appended to an existing queue; start a new session to include it.
        """
        return (*self._inbox_items(), *self._project_items())

    def pending_count(self) -> int:
        """Count the work that needs attention before a review.

        Returns
        -------
        int
            Number of pending inbox captures plus open projects with no open
            action. Healthy open projects do not contribute to the count.

        Notes
        -----
        This method performs no file I/O and never changes a note.
        """
        summaries = ProjectBoard(self._snapshot).summaries()
        stalled = sum(1 for summary in summaries if summary.note.is_open_project and summary.next_action is None)
        return len(self._inbox_items()) + stalled

    def _inbox_items(self) -> tuple[ReviewItem, ...]:
        """Return pending inbox captures in newest-first order."""
        return tuple(ReviewItem(kind=ReviewItemKind.INBOX, path=note.path) for note in self._snapshot.inbox_notes())

    def _project_items(self) -> tuple[ReviewItem, ...]:
        """Return stalled and healthy open projects in review order."""
        open_projects = [
            summary
            for group in ProjectBoard(self._snapshot).groups()
            if group.stage is not ProjectStage.CLOSED
            for summary in group.projects
        ]
        stalled = tuple(
            ReviewItem(kind=ReviewItemKind.PROJECT, path=summary.note.path, project=summary)
            for summary in open_projects
            if summary.next_action is None
        )
        healthy = tuple(
            ReviewItem(kind=ReviewItemKind.PROJECT, path=summary.note.path, project=summary)
            for summary in open_projects
            if summary.next_action is not None
        )
        return (*stalled, *healthy)
