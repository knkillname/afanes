# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only connection queries over a scanned vault snapshot.

The :class:`Connections` service derives inbound references, owned steps, and
requested projects from one :class:`afanes.core.vault.snapshot.VaultSnapshot`. It
performs no file I/O and never changes a note. The service is meant to be built
once per snapshot: :meth:`Connections.for_note` is a dictionary lookup that
returns a frozen value object.
"""

import dataclasses
from pathlib import Path

from afanes.core.links import ResolutionOutcome
from afanes.core.vault.snapshot import VaultNote, VaultSnapshot
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType
from afanes.models.step import ProjectStep


@dataclasses.dataclass(frozen=True, slots=True)
class OwnedProject:
    """One project with the steps a page owns.

    Attributes
    ----------
    project : VaultNote
        Open project whose steps name the page as an owner.
    open_steps : tuple[ProjectStep, ...]
        Unchecked owned steps in document order.
    completed_steps : tuple[ProjectStep, ...]
        Checked owned steps in document order.
    """

    project: VaultNote
    open_steps: tuple[ProjectStep, ...]
    completed_steps: tuple[ProjectStep, ...]

    @property
    def has_completed_steps(self) -> bool:
        """Return whether the project contributes completed steps.

        Returns
        -------
        bool
            ``True`` when at least one owned step is checked.
        """
        return bool(self.completed_steps)


@dataclasses.dataclass(frozen=True, slots=True)
class ConnectionSet:
    """Relationships that point at one note.

    Attributes
    ----------
    linked_from : tuple[VaultNote, ...]
        Parsed notes whose body references uniquely resolve to the note, each
        listed once and ordered by display title.
    owned_projects : tuple[OwnedProject, ...]
        Open projects with steps that name the note as an owner, ordered by
        display title.
    project_owner_projects : tuple[VaultNote, ...]
        Open projects whose ``owner`` value uniquely resolves to the note,
        ordered by display title.
    finished_project_owner_projects : tuple[VaultNote, ...]
        Finished projects whose ``owner`` value uniquely resolves to the note,
        ordered by display title.
    requested_projects : tuple[VaultNote, ...]
        Open projects whose ``asked_by`` value uniquely resolves to the note,
        ordered by display title.
    finished_projects : tuple[VaultNote, ...]
        Finished projects whose ``asked_by`` value uniquely resolves to the
        note, ordered by display title.
    """

    linked_from: tuple[VaultNote, ...] = ()
    owned_projects: tuple[OwnedProject, ...] = ()
    project_owner_projects: tuple[VaultNote, ...] = ()
    finished_project_owner_projects: tuple[VaultNote, ...] = ()
    requested_projects: tuple[VaultNote, ...] = ()
    finished_projects: tuple[VaultNote, ...] = ()

    @property
    def has_connections(self) -> bool:
        """Return whether any relationship points at the note.

        Returns
        -------
        bool
            ``True`` when at least one linked note, owned step project, owned
            project, requested project, or finished project is present.
        """
        return bool(
            self.linked_from
            or self.owned_projects
            or self.project_owner_projects
            or self.finished_project_owner_projects
            or self.requested_projects
            or self.finished_projects
        )

    @property
    def has_completed_steps(self) -> bool:
        """Return whether any owned project contributes completed steps.

        Returns
        -------
        bool
            ``True`` when at least one owned project has a checked step.
        """
        return any(project.has_completed_steps for project in self.owned_projects)


class Connections:
    """Connection indexes over one vault snapshot.

    Parameters
    ----------
    snapshot : VaultSnapshot
        Read-only scan result captured when the index is built.

    Notes
    -----
    Construction walks every parsed note once and builds the relationship
    indexes: inbound references, owned steps, project ownership, and requested
    projects. Only a unique name resolution attributes a relationship; missing
    and ambiguous names contribute nothing. The service never reads or writes a
    file.
    """

    def __init__(self, snapshot: VaultSnapshot) -> None:
        """Build the connection indexes for one snapshot.

        Parameters
        ----------
        snapshot : VaultSnapshot
            Read-only scan result to index.
        """
        self._snapshot = snapshot
        self._linked_from: dict[Path, tuple[VaultNote, ...]] = {}
        self._owned: dict[Path, tuple[OwnedProject, ...]] = {}
        self._project_owned: dict[Path, tuple[VaultNote, ...]] = {}
        self._finished_project_owned: dict[Path, tuple[VaultNote, ...]] = {}
        self._requested: dict[Path, tuple[VaultNote, ...]] = {}
        self._finished: dict[Path, tuple[VaultNote, ...]] = {}
        self._build()

    def for_note(self, path: Path) -> ConnectionSet:
        """Return every relationship that points at one note.

        Parameters
        ----------
        path : Path
            Note path, relative to the vault root or absolute. An unknown path
            returns an empty connection set.

        Returns
        -------
        ConnectionSet
            Inbound references, owned step projects, owned projects, requested
            projects, and finished projects for the note.

        Notes
        -----
        This method performs no file I/O and is a dictionary lookup per
        relationship kind.
        """
        target = path if path.is_absolute() else self._snapshot.root / path
        return ConnectionSet(
            linked_from=self._linked_from.get(target, ()),
            owned_projects=self._owned.get(target, ()),
            project_owner_projects=self._project_owned.get(target, ()),
            finished_project_owner_projects=self._finished_project_owned.get(target, ()),
            requested_projects=self._requested.get(target, ()),
            finished_projects=self._finished.get(target, ()),
        )

    def _build(self) -> None:
        """Build every index in one pass over the parsed notes."""
        linked: dict[Path, dict[Path, VaultNote]] = {}
        owned: dict[Path, list[OwnedProject]] = {}
        project_owned: dict[Path, dict[Path, VaultNote]] = {}
        finished_project_owned: dict[Path, dict[Path, VaultNote]] = {}
        requested: dict[Path, dict[Path, VaultNote]] = {}
        finished: dict[Path, dict[Path, VaultNote]] = {}

        for note in self._snapshot.notes:
            for reference in note.body_references:
                target = self._resolve_reference(reference)
                if target is None or target == note.path:
                    continue
                linked.setdefault(target, {})[note.path] = note
            self._index_project(note, owned, project_owned, finished_project_owned, requested, finished)

        self._linked_from = {
            target: tuple(sorted(notes.values(), key=lambda note: note.alphabetical_order))
            for target, notes in linked.items()
        }
        self._owned = {
            target: tuple(sorted(projects, key=lambda item: item.project.alphabetical_order))
            for target, projects in owned.items()
        }
        self._project_owned = {
            target: tuple(sorted(notes.values(), key=lambda note: note.alphabetical_order))
            for target, notes in project_owned.items()
        }
        self._finished_project_owned = {
            target: tuple(sorted(notes.values(), key=lambda note: note.alphabetical_order))
            for target, notes in finished_project_owned.items()
        }
        self._requested = {
            target: tuple(sorted(notes.values(), key=lambda note: note.alphabetical_order))
            for target, notes in requested.items()
        }
        self._finished = {
            target: tuple(sorted(notes.values(), key=lambda note: note.alphabetical_order))
            for target, notes in finished.items()
        }

    def _index_project(
        self,
        note: VaultNote,
        owned: dict[Path, list[OwnedProject]],
        project_owned: dict[Path, dict[Path, VaultNote]],
        finished_project_owned: dict[Path, dict[Path, VaultNote]],
        requested: dict[Path, dict[Path, VaultNote]],
        finished: dict[Path, dict[Path, VaultNote]],
    ) -> None:
        """Index one note's owned steps, owner, and requester values."""
        if note.note_type is not NoteType.PROJECT:
            return
        if note.is_open_project:
            self._index_owned_steps(note, owned)
        owner_target = self._resolve_name(note.owner) if note.owner is not None else None
        if owner_target is not None:
            owner_bucket = project_owned if note.is_open_project else finished_project_owned
            owner_bucket.setdefault(owner_target, {})[note.path] = note
        target = self._resolve_name(note.asked_by) if note.asked_by is not None else None
        if target is None:
            return
        bucket = requested if note.is_open_project else finished
        bucket.setdefault(target, {})[note.path] = note

    def _index_owned_steps(self, project: VaultNote, owned: dict[Path, list[OwnedProject]]) -> None:
        """Index open steps and completed steps of one open project."""
        steps_by_target: dict[Path, dict[int, ProjectStep]] = {}
        for step in project.steps:
            for owner in step.owners:
                target = self._resolve_name(owner)
                if target is None:
                    continue
                steps_by_target.setdefault(target, {})[step.line_index] = step
        for target, steps in steps_by_target.items():
            ordered = tuple(steps[index] for index in sorted(steps))
            owned.setdefault(target, []).append(
                OwnedProject(
                    project=project,
                    open_steps=tuple(step for step in ordered if not step.checked),
                    completed_steps=tuple(step for step in ordered if step.checked),
                )
            )

    def _resolve_name(self, name: str) -> Path | None:
        """Resolve one owner or requester name to a unique note path."""
        return self._resolve_reference(NoteReference(scheme=ReferenceScheme.NOTE, name=name))

    def _resolve_reference(self, reference: NoteReference) -> Path | None:
        """Resolve a reference to its unique target path, or ``None``."""
        resolution = self._snapshot.catalog.resolve(reference)
        if resolution.outcome is not ResolutionOutcome.RESOLVED:
            return None
        return resolution.targets[0]
