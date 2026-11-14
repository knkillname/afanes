# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only catalog of managed trash entries.

The catalog is deliberately separate from :class:`afanes.core.vault.snapshot.VaultSnapshot`.
Trashed notes never join the active note catalog, name resolution, references,
or counts. This module reads ``trash/`` on demand, returns managed entries, and
never writes a file.
"""

import dataclasses
import datetime
import hashlib
from pathlib import Path

import afanes.core.names
import afanes.core.vault.snapshot
from afanes.core.errors import AfanesError, VaultError
from afanes.core.vault.service import Vault
from afanes.core.vault.trash_metadata import TrashDocument, TrashMetadata


@dataclasses.dataclass(frozen=True, slots=True)
class TrashEntry:
    """One managed note stored under ``trash/``.

    Attributes
    ----------
    path : pathlib.Path
        Absolute path to the UUID or legacy trash file.
    entry_id : str
        Filename stem. New entries are canonical UUIDs; the value is storage
        identity only and is never shown to the user.
    birthplace : pathlib.Path
        Vault-relative path the note occupied before it was trashed.
    trashed_on : datetime.date | None
        Local calendar day recorded in frontmatter, or ``None`` when the value
        is missing or unusable.
    title : str
        Display title derived from the body heading, falling back to the
        birthplace stem.
    search_text : str
        Markdown body used by Trash search.
    content_hash : str
        SHA-256 digest of the file bytes captured when the entry was read.
    """

    path: Path
    entry_id: str
    birthplace: Path
    trashed_on: datetime.date | None
    title: str
    search_text: str
    content_hash: str

    @property
    def birthplace_text(self) -> str:
        """Return the birthplace as the POSIX text shown to the user.

        Returns
        -------
        str
            Vault-relative path with forward slashes.
        """
        return self.birthplace.as_posix()

    @property
    def order(self) -> tuple[str, str, str]:
        """Return the deterministic display order key.

        Returns
        -------
        tuple[str, str, str]
            Normalized title, birthplace text, and storage identity.
        """
        return (
            afanes.core.names.NamePolicy.normalize(self.title),
            self.birthplace_text,
            self.entry_id,
        )

    def matches(self, query: str) -> bool:
        """Return whether the entry matches a free-text query.

        Parameters
        ----------
        query : str
            Text typed into global search. Matching ignores case, Unicode
            form, and repeated whitespace.

        Returns
        -------
        bool
            ``True`` when the normalized query is contained in the display
            title, birthplace, or body text. An empty query matches every
            entry.
        """
        normalized_query = afanes.core.names.NamePolicy.normalize(query)
        if not normalized_query:
            return True
        candidates = (self.title, self.birthplace_text, self.search_text)
        return any(normalized_query in afanes.core.names.NamePolicy.normalize(value) for value in candidates)


@dataclasses.dataclass(frozen=True, slots=True)
class TrashSnapshot:
    """Read-only result of loading the trash folder.

    Attributes
    ----------
    entries : tuple[TrashEntry, ...]
        Managed entries in deterministic display order. Unmanaged files are
        absent.
    fingerprint : tuple[tuple[str, int, int], ...]
        Stat fingerprint of the files the catalog walked, in the same
        ``(vault-relative path, mtime_ns, size)`` shape as the active scan.
    """

    entries: tuple[TrashEntry, ...]
    fingerprint: tuple[tuple[str, int, int], ...] = ()

    @property
    def count(self) -> int:
        """Return the number of managed entries.

        Returns
        -------
        int
            Length of :attr:`entries`.
        """
        return len(self.entries)

    def find(self, path: Path) -> TrashEntry | None:
        """Return the managed entry stored at one path.

        Parameters
        ----------
        path : pathlib.Path
            Absolute trash path to find.

        Returns
        -------
        TrashEntry | None
            Matching entry, or ``None`` when the path is no longer managed.
        """
        return next((entry for entry in self.entries if entry.path == path), None)

    def search(self, query: str) -> tuple[TrashEntry, ...]:
        """Return managed entries matching a free-text query.

        Parameters
        ----------
        query : str
            Text typed into global search. An empty query returns every entry.

        Returns
        -------
        tuple[TrashEntry, ...]
            Matching entries in display order.
        """
        return tuple(entry for entry in self.entries if entry.matches(query))

    def expired(self, today: datetime.date) -> tuple[TrashEntry, ...]:
        """Return entries whose retention period has elapsed.

        Parameters
        ----------
        today : datetime.date
            Current local calendar day supplied by the caller.

        Returns
        -------
        tuple[TrashEntry, ...]
            Entries at or beyond the retention limit, in display order. An
            entry without a usable day is never included.
        """
        return tuple(
            entry
            for entry in self.entries
            if entry.trashed_on is not None
            and TrashMetadata(birthplace=entry.birthplace, trashed_on=entry.trashed_on).is_expired(today)
        )


class TrashCatalog:
    """Load managed trash entries without joining the active vault catalog.

    Parameters
    ----------
    vault : afanes.core.vault.service.Vault
        Resolved vault whose ``trash/`` folder should be read.

    Notes
    -----
    The catalog performs blocking reads and never writes. It skips symlinks,
    hidden directories, non-Markdown files, and files whose trash metadata is
    absent or unsafe.
    """

    def __init__(self, vault: Vault) -> None:
        """Store the vault this catalog reads.

        Parameters
        ----------
        vault : afanes.core.vault.service.Vault
            Resolved vault whose ``trash/`` folder should be read.
        """
        self._vault = vault

    def trash_directory(self) -> Path:
        """Return the trash folder, reusing an existing case variant.

        Returns
        -------
        pathlib.Path
            Absolute ``trash/`` path. A missing folder is returned as its
            canonical path and is not created.
        """
        return self._vault.existing_directory(
            self._vault.root,
            afanes.core.vault.snapshot.TRASH_DIRECTORY,
        )

    def load(self) -> TrashSnapshot:
        """Read every managed entry from the trash folder.

        Returns
        -------
        TrashSnapshot
            Managed entries and the current trash fingerprint. A missing folder
            yields an empty snapshot; an unreadable file is skipped as
            unmanaged.

        Notes
        -----
        Only direct children of ``trash/`` are considered. New entries are flat
        UUID files. A file without a safe birthplace, without UTF-8 text, or
        with unreadable frontmatter remains on disk but is invisible to the
        application.
        """
        directory = self.trash_directory()
        if not directory.is_dir():
            return TrashSnapshot(entries=(), fingerprint=())
        entries: list[TrashEntry] = []
        for candidate in directory.iterdir():
            entry = self._read_entry(candidate)
            if entry is not None:
                entries.append(entry)
        return TrashSnapshot(
            entries=tuple(sorted(entries, key=lambda entry: entry.order)),
            fingerprint=self.fingerprint(),
        )

    def fingerprint(self) -> tuple[tuple[str, int, int], ...]:
        """Return a cheap stat fingerprint for the trash folder.

        Returns
        -------
        tuple[tuple[str, int, int], ...]
            One ``(vault-relative path, mtime_ns, size)`` entry per direct
            Markdown file, in deterministic path order. A missing folder or an
            unreadable entry contributes nothing.
        """
        directory = self.trash_directory()
        if not directory.is_dir():
            return ()
        entries: list[tuple[str, int, int]] = []
        for candidate in sorted(directory.iterdir(), key=lambda item: item.name):
            if not self._is_candidate(candidate):
                continue
            try:
                stat = candidate.stat()
                relative = candidate.relative_to(self._vault.root).as_posix()
            except OSError:
                continue
            entries.append((relative, stat.st_mtime_ns, stat.st_size))
        return tuple(entries)

    def _read_entry(self, candidate: Path) -> TrashEntry | None:
        """Read one candidate file, returning ``None`` when it is unmanaged."""
        if not self._is_candidate(candidate):
            return None
        try:
            data = candidate.read_bytes()
            text = data.decode("utf-8")
            document = TrashDocument.from_text(text)
        except (OSError, UnicodeDecodeError, AfanesError):
            return None
        metadata = document.metadata
        if metadata is None:
            return None
        try:
            resolved = candidate.resolve()
            birthplace = self._vault.contained(metadata.birthplace)
        except (OSError, VaultError):
            return None
        if not resolved.is_relative_to(self._vault.root):
            return None
        return TrashEntry(
            path=resolved,
            entry_id=candidate.stem,
            birthplace=birthplace.relative_to(self._vault.root),
            trashed_on=metadata.trashed_on,
            title=document.title or metadata.birthplace.stem,
            search_text=document.body,
            content_hash=hashlib.sha256(data).hexdigest(),
        )

    @staticmethod
    def _is_candidate(candidate: Path) -> bool:
        """Return whether a directory child can hold a managed entry."""
        if candidate.suffix.casefold() != afanes.core.vault.snapshot.NOTE_SUFFIX:
            return False
        if candidate.is_symlink():
            return False
        try:
            return candidate.is_file()
        except OSError:
            return False


@dataclasses.dataclass(frozen=True, slots=True)
class TrashMaintenanceReport:
    """Outcome of one empty or retention pass.

    Attributes
    ----------
    deleted : int
        Number of managed entries permanently deleted.
    stamped : int
        Number of entries whose missing or malformed day was replaced with the
        supplied local day.
    failures : tuple[str, ...]
        One concise failure description per entry that could not be stamped or
        deleted. The messages never contain a trash UUID.
    """

    deleted: int = 0
    stamped: int = 0
    failures: tuple[str, ...] = ()

    @property
    def failed(self) -> bool:
        """Return whether any entry could not be maintained.

        Returns
        -------
        bool
            ``True`` when :attr:`failures` is non-empty.
        """
        return bool(self.failures)
