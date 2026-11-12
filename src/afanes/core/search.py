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
import datetime
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Self

import afanes.core.names
from afanes.core.vault import NoteOrder, VaultFailure, VaultNote, VaultSnapshot
from afanes.models.note import CategoryLabel, NoteType, Status
from afanes.models.step import ProjectStep


class BrowserSection(StrEnum):
    """Fixed sections of the vault browser.

    Attributes
    ----------
    INBOX : str
        Captures stored under the vault's inbox directory.
    PROJECTS : str
        Notes of type ``project``.
    REFERENCES : str
        Reference notes, grouped by their free-form category label.
    NEEDS_ATTENTION : str
        Unclarified notes found outside the inbox.
    """

    INBOX = "inbox"
    PROJECTS = "projects"
    REFERENCES = "references"
    NEEDS_ATTENTION = "needs_attention"


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
    DUE_STEP : str
        An own, unchecked step whose plan date is today or earlier.
    WAITING_STEP : str
        An unchecked step with at least one owner.
    PROJECT : str
        An open project reviewed through its next step or its missing step.
    """

    INBOX = "inbox"
    DUE_STEP = "due_step"
    WAITING_STEP = "waiting_step"
    PROJECT = "project"


@dataclasses.dataclass(frozen=True, slots=True)
class BrowserGroup:
    """One section of the browser and its notes.

    Attributes
    ----------
    section : BrowserSection
        Section that owns the notes.
    notes : tuple[VaultNote, ...]
        Notes in presentation order. The inbox is newest first; other sections
        are ordered by display title, identity, and path.
    label : CategoryLabel | None
        Category label for a references group, or ``None`` for every other
        group and for uncategorized references.
    """

    section: BrowserSection
    notes: tuple[VaultNote, ...]
    label: CategoryLabel | None = None

    @property
    def title(self) -> str:
        """Return the display heading for this group.

        Returns
        -------
        str
            ``References`` for the uncategorized group, the written label for a
            categorized references group, and a neutral section name for the
            other groups.
        """
        if self.section is not BrowserSection.REFERENCES:
            return self.section.value.replace("_", " ").title()
        if self.label is None:
            return "References"
        return self.label.value


@dataclasses.dataclass(frozen=True, slots=True)
class BrowserListing:
    """Every parsed note grouped for the browser, plus scan failures.

    Attributes
    ----------
    groups : tuple[BrowserGroup, ...]
        Groups in section order. References contribute one group per category
        label.
    failures : tuple[VaultFailure, ...]
        Notes the scan could not parse, in scan order.
    """

    groups: tuple[BrowserGroup, ...]
    failures: tuple[VaultFailure, ...]

    def group(self, section: BrowserSection) -> BrowserGroup:
        """Return the first browser group for a section.

        Parameters
        ----------
        section : BrowserSection
            Section to return. Every section is always present.

        Returns
        -------
        BrowserGroup
            First group for the requested section. For references this is the
            uncategorized group when it exists, otherwise the first label.
        """
        return next(group for group in self.groups if group.section is section)

    def groups_for(self, section: BrowserSection) -> tuple[BrowserGroup, ...]:
        """Return every group for one section.

        Parameters
        ----------
        section : BrowserSection
            Section to return.

        Returns
        -------
        tuple[BrowserGroup, ...]
            Groups for the requested section. References may produce several.
        """
        return tuple(group for group in self.groups if group.section is section)

    def filtered(self, query: str) -> Self:
        """Return a listing whose groups match a full-text query.

        Parameters
        ----------
        query : str
            Free text typed into the browser search field. Matching ignores
            case, Unicode form, and repeated whitespace. An empty query keeps
            every note.

        Returns
        -------
        BrowserListing
            Listing with the same groups and failures. Matching reads the
            snapshot's search text, which excludes step metadata comments.
        """
        return BrowserListing(
            groups=tuple(
                BrowserGroup(
                    section=group.section,
                    notes=Browser.filter_notes(group.notes, query),
                    label=group.label,
                )
                for group in self.groups
            ),
            failures=self.failures,
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ProjectSummary:
    """One project and the steps that advance it.

    Attributes
    ----------
    note : VaultNote
        Parsed project note.
    open_steps : tuple[ProjectStep, ...]
        Unchecked steps in document order.
    next_step : ProjectStep | None
        First unchecked step, or ``None`` when the project has no open step.
    """

    note: VaultNote
    open_steps: tuple[ProjectStep, ...]
    next_step: ProjectStep | None

    @property
    def open_count(self) -> int:
        """Return the number of open steps.

        Returns
        -------
        int
            Length of :attr:`open_steps`.
        """
        return len(self.open_steps)


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
        Whether the item is an inbox capture, a step, or a project.
    path : Path
        Absolute path of the capture or project note.
    project : ProjectSummary | None
        Project data for a step or project item; ``None`` for an inbox item.
    step : ProjectStep | None
        Step under review, or ``None`` for inbox and project items.
    """

    kind: ReviewItemKind
    path: Path
    project: ProjectSummary | None = None
    step: ProjectStep | None = None


class Browser:
    """Browser groups and full-text filtering over one snapshot.

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
            Section groups in fixed order plus parse failures. A note appears
            in exactly one group. Captures under the inbox appear only under
            ``Inbox``; references contribute one group per category label.
            Notes under ``trash/`` are already excluded by the scan.

        Notes
        -----
        This method performs no file I/O and never changes a note.
        """
        inbox = list(self._snapshot.inbox_notes())
        projects: list[VaultNote] = []
        misplaced: list[VaultNote] = []
        references: dict[CategoryLabel | None, list[VaultNote]] = {}
        for note in self._snapshot.notes:
            if note.is_inbox:
                continue
            if note.note_type is NoteType.PROJECT:
                projects.append(note)
            elif note.note_type is NoteType.REFERENCE:
                references.setdefault(note.category, []).append(note)
            elif note.is_misplaced:
                misplaced.append(note)
        groups: list[BrowserGroup] = [
            BrowserGroup(section=BrowserSection.INBOX, notes=tuple(inbox)),
            BrowserGroup(section=BrowserSection.PROJECTS, notes=self._sorted(projects)),
        ]
        groups.extend(
            BrowserGroup(
                section=BrowserSection.REFERENCES,
                notes=self._sorted(references[label]),
                label=label,
            )
            for label in sorted(references, key=Browser._label_order)
        )
        if not references:
            groups.append(BrowserGroup(section=BrowserSection.REFERENCES, notes=()))
        groups.append(
            BrowserGroup(section=BrowserSection.NEEDS_ATTENTION, notes=self._sorted(misplaced)),
        )
        return BrowserListing(groups=tuple(groups), failures=self._snapshot.failures)

    def filter(self, query: str) -> BrowserListing:
        """Return browser groups filtered by a full-text query.

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
        """Filter notes by display title, identity, or search text.

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
            Matching notes in the input order.
        """
        return tuple(note for note in notes if cls.matches(note, query))

    @staticmethod
    def matches(note: VaultNote, query: str) -> bool:
        """Return whether a note matches a full-text query.

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
            display title, identity, or search text. Step metadata comments are
            absent from the search text.
        """
        normalized_query = afanes.core.names.normalize_name(query)
        if not normalized_query:
            return True
        candidates = (note.title, note.name, note.search_text)
        return any(normalized_query in afanes.core.names.normalize_name(value) for value in candidates)

    @staticmethod
    def _label_order(label: CategoryLabel | None) -> tuple[int, str]:
        """Order uncategorized references first, then labels by folded value."""
        if label is None:
            return (0, "")
        return (1, label.key)

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
            path. Open steps keep document order; checked steps are excluded.

        Notes
        -----
        Membership is containment: a step belongs to the project whose body
        holds it. No reference or frontmatter key participates.
        """
        projects = [note for note in self._snapshot.notes if note.note_type is NoteType.PROJECT]
        summaries = [ProjectBoard._summary(project) for project in projects]
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

    @staticmethod
    def _summary(project: VaultNote) -> ProjectSummary:
        """Build one project summary from its body steps."""
        open_steps = project.open_steps
        return ProjectSummary(
            note=project,
            open_steps=open_steps,
            next_step=open_steps[0] if open_steps else None,
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
    today : datetime.date | None
        Calendar date used to decide which own steps are due. ``None`` uses
        the current local date.
    """

    def __init__(self, snapshot: VaultSnapshot, today: datetime.date | None = None) -> None:
        """Store the snapshot and reference date this planner queries.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Read-only scan result.
        today : datetime.date | None
            Calendar date used to decide which own steps are due.
        """
        self._snapshot = snapshot
        self._today = today or datetime.datetime.now(tz=datetime.UTC).astimezone().date()

    def queue(self) -> tuple[ReviewItem, ...]:
        """Build the ordered queue for one review session.

        Returns
        -------
        tuple[ReviewItem, ...]
            Pending inbox captures first, newest first; then due or overdue own
            steps; then waiting steps; then open projects with no open step;
            then healthy open projects. Closed projects are excluded.

        Notes
        -----
        The result is a snapshot. Work created or changed after this call is
        not appended to an existing queue; start a new session to include it.
        """
        return (
            *self._inbox_items(),
            *self._step_items(ReviewItemKind.DUE_STEP),
            *self._step_items(ReviewItemKind.WAITING_STEP),
            *self._project_items(stalled=True),
            *self._project_items(stalled=False),
        )

    def pending_count(self) -> int:
        """Count the work that needs attention before a review.

        Returns
        -------
        int
            Pending inbox captures, due or overdue own steps, waiting steps,
            and open projects with no open step. Healthy open projects do not
            contribute to the count.

        Notes
        -----
        This method performs no file I/O and never changes a note.
        """
        due = self.due_count()
        waiting = len(self._step_items(ReviewItemKind.WAITING_STEP))
        stalled = len(self._project_items(stalled=True))
        return len(self._inbox_items()) + due + waiting + stalled

    def due_count(self) -> int:
        """Count due or overdue own steps.

        Returns
        -------
        int
            Own, unchecked steps whose plan date is today or earlier.
        """
        return len(self._step_items(ReviewItemKind.DUE_STEP))

    def _inbox_items(self) -> tuple[ReviewItem, ...]:
        """Return pending inbox captures in newest-first order."""
        return tuple(ReviewItem(kind=ReviewItemKind.INBOX, path=note.path) for note in self._snapshot.inbox_notes())

    def _step_items(self, kind: ReviewItemKind) -> tuple[ReviewItem, ...]:
        """Return due own steps or waiting steps in project and document order."""
        items: list[ReviewItem] = []
        for summary in self._open_summaries():
            for step in summary.note.steps:
                if step.checked:
                    continue
                matches = (
                    not step.is_waiting and step.plan is not None and step.plan <= self._today
                    if kind is ReviewItemKind.DUE_STEP
                    else step.is_waiting
                )
                if matches:
                    items.append(
                        ReviewItem(
                            kind=kind,
                            path=summary.note.path,
                            project=summary,
                            step=step,
                        )
                    )
        return tuple(items)

    def _project_items(self, *, stalled: bool) -> tuple[ReviewItem, ...]:
        """Return stalled or healthy open projects in review order."""
        return tuple(
            ReviewItem(kind=ReviewItemKind.PROJECT, path=summary.note.path, project=summary)
            for summary in self._open_summaries()
            if (summary.next_step is None) is stalled
        )

    def _open_summaries(self) -> tuple[ProjectSummary, ...]:
        """Return open project summaries in board order."""
        return tuple(
            summary
            for group in ProjectBoard(self._snapshot).groups()
            if group.stage is not ProjectStage.CLOSED
            for summary in group.projects
        )
