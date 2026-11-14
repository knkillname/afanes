# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only vault scan results and the storage layout they describe.

The scan result, failure, link, path, and page value objects live here so the
vault service and its write services can share them without importing each
other. The note value objects live in :mod:`afanes.core.vault.note`. The
module performs no file I/O.
"""

import dataclasses
from enum import StrEnum
from pathlib import Path

import afanes.core.names
import afanes.core.vault.note
from afanes.core.errors import DomainMessage
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import NameCatalog, ResolutionOutcome
from afanes.core.vault.note import VaultNote, VaultPath
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteDate, NoteType

# Public canonical note extension.
NOTE_SUFFIX = ".md"

# Public default storage layout.
INBOX_DIRECTORY = afanes.core.vault.note.INBOX_DIRECTORY
TRASH_DIRECTORY = Path("trash")
REFERENCE_DIRECTORY = Path("reference")
PROJECTS_DIRECTORY = Path("projects")
LOG_DIRECTORY = Path("log")
TEMPLATES_DIRECTORY = Path("templates")


@dataclasses.dataclass(frozen=True, slots=True)
class NotePath:
    """A scanned note path and its vault-relative form.

    Attributes
    ----------
    path : Path
        Absolute path to the note file.
    relative_path : Path
        Vault-relative path used for diagnostics.
    """

    path: Path
    relative_path: Path


@dataclasses.dataclass(frozen=True, slots=True)
class VaultFailure:
    """A note that could not be parsed during a scan.

    Attributes
    ----------
    path : Path
        Vault-relative path to the failing note.
    message : DomainMessage
        Stable diagnostic. The scan continues with the remaining notes.
    """

    path: Path
    message: DomainMessage


@dataclasses.dataclass(frozen=True, slots=True)
class PageFile:
    """One note file read from disk.

    Attributes
    ----------
    path : Path
        Absolute path to the note file.
    relative_path : Path
        Vault-relative path used for display and diagnostics.
    text : str
        Complete file text, including any frontmatter block.
    content_hash : str
        SHA-256 digest of the file bytes, captured when the note was read.
    """

    path: Path
    relative_path: Path
    text: str
    content_hash: str


@dataclasses.dataclass(frozen=True, slots=True)
class ParsedPage:
    """A page whose frontmatter parsed successfully.

    Attributes
    ----------
    file : PageFile
        Raw file content and identity.
    document : NoteDocument
        Parsed document with a declared note type.
    """

    file: PageFile
    document: NoteDocument

    @property
    def path(self) -> Path:
        """Return the absolute note path."""
        return self.file.path

    @property
    def relative_path(self) -> Path:
        """Return the vault-relative note path."""
        return self.file.relative_path

    @property
    def text(self) -> str:
        """Return the complete file text."""
        return self.file.text

    @property
    def content_hash(self) -> str:
        """Return the content hash captured at read time."""
        return self.file.content_hash


@dataclasses.dataclass(frozen=True, slots=True)
class UnparsedPage:
    """A page whose frontmatter or type could not be parsed.

    Attributes
    ----------
    file : PageFile
        Raw file content and identity.
    failure : DomainMessage
        Parse failure message. The raw text is retained so the page can open in
        raw rescue mode without losing the file's current content.
    """

    file: PageFile
    failure: DomainMessage

    @property
    def path(self) -> Path:
        """Return the absolute note path."""
        return self.file.path

    @property
    def relative_path(self) -> Path:
        """Return the vault-relative note path."""
        return self.file.relative_path

    @property
    def text(self) -> str:
        """Return the complete file text."""
        return self.file.text

    @property
    def content_hash(self) -> str:
        """Return the content hash captured at read time."""
        return self.file.content_hash


class LinkOutcome(StrEnum):
    """Outcome of routing an internal reference to a page.

    Attributes
    ----------
    RESOLVED : str
        Exactly one parsed note matches the reference.
    AMBIGUOUS : str
        Several parsed notes match the reference.
    BROKEN : str
        No parsed note matches, but one or more unparseable files share the
        reference name.
    MISSING : str
        No parsed note and no unparseable file matches the reference.
    """

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    BROKEN = "broken"
    MISSING = "missing"


@dataclasses.dataclass(frozen=True, slots=True)
class LinkTarget:
    """One routed internal reference and the page paths it reaches.

    Attributes
    ----------
    reference : NoteReference
        Reference that was routed.
    outcome : LinkOutcome
        Whether the reference resolved, was ambiguous, pointed at an
        unparseable file, or matched nothing.
    paths : tuple[Path, ...]
        Absolute paths for a resolved, ambiguous, or broken outcome. Empty for
        a missing outcome. Ambiguous and broken outcomes keep every candidate.
    """

    reference: NoteReference
    outcome: LinkOutcome
    paths: tuple[Path, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceSite:
    """References in one note that point at a target note.

    Attributes
    ----------
    path : Path
        Absolute path to the referring note.
    reference_count : int
        Number of references in that note that resolve to the target.
    """

    path: Path
    reference_count: int


@dataclasses.dataclass(frozen=True, slots=True)
class VaultSnapshot:
    """Read-only result of scanning a vault.

    Attributes
    ----------
    root : Path
        Resolved vault root.
    notes : tuple[VaultNote, ...]
        Successfully parsed notes in deterministic path order.
    failures : tuple[VaultFailure, ...]
        Notes that could not be parsed, in deterministic path order.
    catalog : NameCatalog
        Name catalog built from the parsed notes.
    fingerprint : tuple[tuple[str, int, int], ...]
        Change fingerprint of the files the scan walked, in the same
        ``(vault-relative path, mtime_ns, size)`` shape as
        :meth:`afanes.core.vault.service.Vault.scan_fingerprint`.
    """

    root: Path
    notes: tuple[VaultNote, ...]
    failures: tuple[VaultFailure, ...]
    catalog: NameCatalog
    fingerprint: tuple[tuple[str, int, int], ...] = ()

    def inbox_notes(self) -> tuple[VaultNote, ...]:
        """Return the notes currently in this vault's inbox.

        Returns
        -------
        tuple[VaultNote, ...]
            Notes under the vault's ``inbox/`` directory, including nested
            subdirectories, ordered by modification time newest first. Ties are
            broken by case-folded name and then vault-relative path.

        Notes
        -----
        The first path component is matched case-insensitively so the same
        vault behaves consistently on case-sensitive and case-insensitive
        filesystems. This method performs no file I/O.
        """
        notes = [note for note in self.notes if note.is_inbox]
        return tuple(sorted(notes, key=lambda note: note.inbox_order))

    def assignment_candidates(self, scheme: ReferenceScheme, query: str) -> tuple[VaultNote, ...]:
        """Return notes whose identity or display title contains a query.

        Parameters
        ----------
        scheme : ReferenceScheme
            Namespace to search, normally ``project``.
        query : str
            Free text typed by the user. Matching ignores case, Unicode form,
            and repeated whitespace. An empty query matches every note in the
            scheme.

        Returns
        -------
        tuple[VaultNote, ...]
            Matching notes ordered by display title, then identity, then
            vault-relative path. Empty when nothing matches.

        Notes
        -----
        This method performs no file I/O and no rescan. Identity and display
        title are normalized with :meth:`afanes.core.names.NamePolicy.normalize`, so
        matching follows the same rule as reference resolution. Display titles
        are only matched; they never become reference targets.
        """
        normalized_query = afanes.core.names.NamePolicy.normalize(query)
        matches = [
            note
            for note in self.notes
            if ReferenceScheme.for_note(note.note_type) is scheme
            and (
                normalized_query in afanes.core.names.NamePolicy.normalize(note.name)
                or normalized_query in afanes.core.names.NamePolicy.normalize(note.title)
            )
        ]
        return tuple(
            sorted(
                matches,
                key=lambda note: note.alphabetical_order,
            )
        )

    def link_target(self, reference: NoteReference) -> LinkTarget:
        """Route one internal reference to its page without reading the vault.

        Parameters
        ----------
        reference : NoteReference
            Internal reference to route. External destinations are classified
            before this method is called and are never passed here.

        Returns
        -------
        LinkTarget
            Resolved, ambiguous, broken, or missing outcome with every matching
            absolute path.

        Notes
        -----
        A broken outcome is reported when the catalog has no match but one or
        more unparseable files share the normalized reference name. Their
        vault-relative failure paths are resolved against :attr:`root` so the
        caller can open the file in raw rescue mode. This method performs no
        file I/O and never chooses among ambiguous candidates.
        """
        resolution = self.catalog.resolve(reference)
        if resolution.outcome is ResolutionOutcome.RESOLVED:
            return LinkTarget(reference=reference, outcome=LinkOutcome.RESOLVED, paths=resolution.targets)
        if resolution.outcome is ResolutionOutcome.AMBIGUOUS:
            return LinkTarget(reference=reference, outcome=LinkOutcome.AMBIGUOUS, paths=resolution.targets)

        normalized = afanes.core.names.NamePolicy.normalize(reference.name)
        broken = tuple(
            self.root / failure.path
            for failure in self.failures
            if afanes.core.names.NamePolicy.normalize(failure.path.stem) == normalized
        )
        if broken:
            return LinkTarget(reference=reference, outcome=LinkOutcome.BROKEN, paths=broken)
        return LinkTarget(reference=reference, outcome=LinkOutcome.MISSING)

    def find_note(self, source: Path) -> VaultNote | None:
        """Find a scanned note by path.

        Parameters
        ----------
        source : Path
            Note path, relative or absolute.

        Returns
        -------
        VaultNote | None
            Matching scanned note, or ``None`` when the path is not in this
            snapshot.
        """
        return next((note for note in self.notes if VaultPath.same(note.path, source)), None)

    def log_entry(self, date: NoteDate) -> VaultNote | None:
        """Return the log entry for one exact date.

        Parameters
        ----------
        date : NoteDate
            Date whose ISO text is the log entry's name.

        Returns
        -------
        VaultNote | None
            Matching log entry, or ``None`` when the date is free.

        Notes
        -----
        A log entry is unique per exact date. This method performs no file I/O
        and never chooses among duplicates; an external duplicate returns the
        first match in scan order.
        """
        candidates = self.catalog.candidates(ReferenceScheme.LOG, date.text)
        return next(
            (note for note in self.notes if note.note_type is NoteType.LOG and note.path in candidates),
            None,
        )

    def affected_sites(self, source: Path) -> tuple[ReferenceSite, ...]:
        """Collect per-note reference counts that resolve to a target note.

        Parameters
        ----------
        source : Path
            Target note path.

        Returns
        -------
        tuple[ReferenceSite, ...]
            Referring notes with per-note reference counts, in scan order.

        Notes
        -----
        Counts body references and metadata role references (project owner,
        requester, and step owners). An ambiguous reference is not attributed
        to any candidate.
        """
        sites: list[ReferenceSite] = []
        for note in self.notes:
            references = (*note.references, *note.metadata_references)
            count = sum(1 for reference in references if self.resolves_to(reference, source))
            if count:
                sites.append(ReferenceSite(path=note.path, reference_count=count))
        return tuple(sites)

    def resolves_to(self, reference: NoteReference, source: Path) -> bool:
        """Return whether a reference uniquely resolves to a target note.

        Parameters
        ----------
        reference : NoteReference
            Reference to resolve.
        source : Path
            Target note path.

        Returns
        -------
        bool
            ``True`` only for a unique resolution to ``source``.
        """
        resolution = self.catalog.resolve(reference)
        if resolution.outcome is not ResolutionOutcome.RESOLVED:
            return False
        return VaultPath.same(resolution.targets[0], source)

    def hash_for_note(self, path: Path) -> str:
        """Return the content hash captured for a scanned note.

        Parameters
        ----------
        path : Path
            Note path to find.

        Returns
        -------
        str
            SHA-256 digest captured during the scan.

        Raises
        ------
        StopIteration
            If the path is not part of this snapshot.
        """
        note = next(note for note in self.notes if VaultPath.same(note.path, path))
        return note.content_hash

    def referrers(self, note_path: Path) -> tuple[ReferenceSite, ...]:
        """Return notes whose references resolve to one target note.

        Parameters
        ----------
        note_path : Path
            Target note path, relative or absolute.

        Returns
        -------
        tuple[ReferenceSite, ...]
            Referring notes with per-note reference counts, in scan order.
            Empty when no reference resolves to the target.

        Notes
        -----
        Only unique resolution counts; an ambiguous reference is not attributed
        to any candidate. Body references and metadata role references both
        count. The result is computed from the snapshot and performs no file
        I/O.
        """
        return self.affected_sites(note_path)


type PageContent = ParsedPage | UnparsedPage
