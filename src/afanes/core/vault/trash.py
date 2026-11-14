# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plan, move, browse-maintain, restore, and delete notes in the vault trash.

The service writes only through :class:`afanes.core.atomic.AtomicWriter` and
path containment on :class:`afanes.core.vault.service.Vault`. Trashed notes are
stored as flat UUID files under ``trash/`` and carry their birthplace and
retention day in frontmatter, so a restart never loses the origin.
"""

import contextlib
import dataclasses
import datetime
import hashlib
import uuid
from pathlib import Path

import afanes.core.atomic
import afanes.core.vault.snapshot
from afanes.core.errors import (
    AfanesError,
    ContentChangedError,
    NameCollisionError,
    VaultError,
)
from afanes.core.vault.naming_reports import TrashPreview
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import VaultSnapshot
from afanes.core.vault.trash_catalog import TrashCatalog, TrashEntry, TrashMaintenanceReport
from afanes.core.vault.trash_metadata import TrashDocument, TrashMetadata


@dataclasses.dataclass(frozen=True, slots=True)
class TrashService:
    """Move, restore, delete, and maintain durable trash entries.

    Attributes
    ----------
    vault : Vault
        Resolved vault that owns path containment and the storage layout.
    """

    vault: Vault

    def plan_trash(
        self,
        note_path: Path,
        *,
        snapshot: VaultSnapshot | None = None,
        today: datetime.date | None = None,
    ) -> TrashPreview:
        """Report inbound references and the trash destination without writing.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.
        today : datetime.date | None
            Local calendar day to record, or ``None`` to use the vault's
            creation time source.

        Returns
        -------
        TrashPreview
            UUID destination inside ``trash/``, birthplace, trashed day, source
            hash, inbound reference count, and the notes that contain those
            references.

        Raises
        ------
        VaultError
            If the note is not part of the vault snapshot.
        """
        source = self.vault.contained(note_path)
        vault = snapshot or self.vault.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)

        trash_directory = TrashCatalog(self.vault).trash_directory()
        affected = vault.affected_sites(source)
        return TrashPreview(
            note_path=source,
            trash_path=self._allocate(trash_directory),
            reference_count=sum(site.reference_count for site in affected),
            affected_notes=tuple(site.path for site in affected),
            trashed_on=today or self.vault.today(),
            source_hash=note.content_hash,
        )

    def trash(
        self,
        note_path: Path,
        *,
        confirm: bool = False,
        snapshot: VaultSnapshot | None = None,
        expected_hash: str | None = None,
        today: datetime.date | None = None,
    ) -> TrashPreview:
        """Move a note to ``trash/`` after confirmation without rewriting references.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.
        snapshot : VaultSnapshot | None
            Pre-built scan used to report inbound references and verify that the
            source is still the scanned note.
        expected_hash : str | None
            Content hash captured by an earlier plan, or ``None`` to compare
            only against the supplied snapshot.
        today : datetime.date | None
            Local calendar day to record, or ``None`` to use the vault's
            creation time source.

        Returns
        -------
        TrashPreview
            Destination that was used, the birthplace, the recorded day, and
            the inbound-reference report taken at planning time.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not part of the vault, or
            the metadata or move fails.
        ContentChangedError
            If the note changed after planning.
        """
        if not confirm:
            message = "Trashing requires explicit confirmation"
            raise VaultError(message)

        preview = self.plan_trash(note_path, snapshot=snapshot, today=today)
        if expected_hash is not None and preview.source_hash != expected_hash:
            message = f"Note changed on disk: {preview.note_path}"
            raise ContentChangedError(message)

        source = preview.note_path
        source_data = source.read_bytes()
        if hashlib.sha256(source_data).hexdigest() != preview.source_hash:
            message = f"Note changed on disk: {source}"
            raise ContentChangedError(message)

        relative_birthplace = source.relative_to(self.vault.root)
        metadata = TrashMetadata(
            birthplace=relative_birthplace,
            trashed_on=preview.trashed_on,
        )
        try:
            document = TrashDocument.from_text(source_data.decode("utf-8"))
            updated_text = document.with_metadata(metadata)
        except (AfanesError, UnicodeDecodeError, OSError) as exc:
            message = f"Could not add trash metadata to the note: {source}"
            raise VaultError(message) from exc

        trash_directory = preview.trash_path.parent
        try:
            trash_directory.mkdir(parents=True, exist_ok=True)
            afanes.core.atomic.AtomicWriter.write_text_atomic(source, updated_text)
        except (OSError, VaultError) as exc:
            message = f"Could not move the note to trash: {source}"
            raise VaultError(message) from exc

        trash_path = preview.trash_path
        if trash_path.exists():
            trash_path = self._allocate(trash_directory)
        try:
            source.replace(trash_path)
        except OSError as exc:
            with contextlib.suppress(OSError, VaultError):
                afanes.core.atomic.AtomicWriter.write_text_atomic(source, source_data.decode("utf-8"))
            message = f"Could not move the note to trash: {source}"
            raise VaultError(message) from exc

        return dataclasses.replace(preview, trash_path=trash_path)

    def restore(
        self,
        preview: TrashPreview,
        *,
        confirm: bool = False,
        overwrite: bool = False,
    ) -> Path:
        """Restore a note moved to trash by the current session.

        Parameters
        ----------
        preview : TrashPreview
            Preview returned by :meth:`trash` or :meth:`plan_trash`.
        confirm : bool
            Explicit confirmation gate.
        overwrite : bool
            Whether an occupied birthplace may be replaced permanently. Undo
            always passes ``False``.

        Returns
        -------
        Path
            Absolute path of the restored note.

        Raises
        ------
        VaultError
            If confirmation is missing, the trash file is gone, its metadata is
            unreadable, or a path escapes the vault.
        NameCollisionError
            If the birthplace is occupied and ``overwrite`` is ``False``.
        """
        if not confirm:
            message = "Restoring a trashed note requires explicit confirmation"
            raise VaultError(message)
        return self._restore_paths(preview.trash_path, preview.note_path, overwrite=overwrite)

    def restore_entry(
        self,
        entry: TrashEntry,
        *,
        confirm: bool = False,
        overwrite: bool = False,
    ) -> Path:
        """Restore one managed entry to its recorded birthplace.

        Parameters
        ----------
        entry : TrashEntry
            Managed entry selected in the Trash destination.
        confirm : bool
            Explicit confirmation gate.
        overwrite : bool
            Whether an occupied birthplace may be replaced permanently.

        Returns
        -------
        Path
            Absolute path of the restored note.

        Raises
        ------
        VaultError
            If confirmation is missing, the trash file is gone, its metadata is
            unreadable, or a path escapes the vault.
        NameCollisionError
            If the birthplace is occupied and ``overwrite`` is ``False``.
        """
        if not confirm:
            message = "Restoring a trashed note requires explicit confirmation"
            raise VaultError(message)
        return self._restore_paths(entry.path, entry.birthplace, overwrite=overwrite)

    def delete_entry(self, entry: TrashEntry) -> None:
        """Permanently delete one managed entry.

        Parameters
        ----------
        entry : TrashEntry
            Managed entry selected in the Trash destination.

        Raises
        ------
        VaultError
            If the file is no longer a managed regular file under ``trash/`` or
            cannot be removed.

        Notes
        -----
        The file is re-read before deletion so a file whose metadata disappeared
        after the catalog was loaded is left untouched.
        """
        source = self._managed_source(entry.path)
        try:
            self._require_managed_metadata(source)
            source.unlink()
        except OSError as exc:
            message = "Could not delete the trashed note"
            raise VaultError(message) from exc

    def empty(self) -> TrashMaintenanceReport:
        """Permanently delete every managed entry.

        Returns
        -------
        TrashMaintenanceReport
            Deleted count and one failure description per entry that could not
            be removed. Unmanaged files are never candidates.
        """
        snapshot = TrashCatalog(self.vault).load()
        deleted = 0
        failures: list[str] = []
        for entry in snapshot.entries:
            try:
                self.delete_entry(entry)
            except (AfanesError, OSError):
                failures.append("A trashed note could not be deleted")
            else:
                deleted += 1
        return TrashMaintenanceReport(deleted=deleted, failures=tuple(failures))

    def maintain(self, today: datetime.date) -> TrashMaintenanceReport:
        """Stamp missing days and delete entries at the retention limit.

        Parameters
        ----------
        today : datetime.date
            Current local calendar day. The caller supplies it so the pass is
            deterministic and core code keeps no hidden clock.

        Returns
        -------
        TrashMaintenanceReport
            Stamped and deleted counts plus one concise failure description per
            entry that could not be maintained.

        Notes
        -----
        An entry whose day cannot be written stays visible and never expires in
        this pass. A failed deletion stays visible. Unmanaged files are never
        read as candidates by the catalog.
        """
        snapshot = TrashCatalog(self.vault).load()
        stamped = 0
        deleted = 0
        failures: list[str] = []
        for entry in snapshot.entries:
            current = entry
            if current.trashed_on is None:
                try:
                    self._stamp(current, today)
                except (AfanesError, OSError, UnicodeDecodeError):
                    failures.append("A trashed note could not record its retention day")
                    continue
                current = dataclasses.replace(current, trashed_on=today)
                stamped += 1
            if current.trashed_on is None:
                continue
            metadata = TrashMetadata(birthplace=current.birthplace, trashed_on=current.trashed_on)
            if not metadata.is_expired(today):
                continue
            try:
                self.delete_entry(current)
            except (AfanesError, OSError):
                failures.append("An expired trashed note could not be deleted")
            else:
                deleted += 1
        return TrashMaintenanceReport(deleted=deleted, stamped=stamped, failures=tuple(failures))

    def _restore_paths(self, source_candidate: Path, target_candidate: Path, *, overwrite: bool) -> Path:
        """Publish a trashed file at its birthplace and remove the trash copy."""
        source, target, raw_target = self._restore_endpoints(source_candidate, target_candidate)
        restored_text = self._restored_text_for_restore(source)
        self._check_birthplace(target, raw_target, target_candidate, overwrite=overwrite)
        self._publish_restored(target, restored_text, target_candidate, overwrite=overwrite)
        self._remove_trash_copy(source)
        return target

    def _restore_endpoints(self, source_candidate: Path, target_candidate: Path) -> tuple[Path, Path, Path]:
        """Resolve and validate the trash source and birthplace endpoints."""
        raw_source = source_candidate if source_candidate.is_absolute() else self.vault.root / source_candidate
        raw_target = target_candidate if target_candidate.is_absolute() else self.vault.root / target_candidate
        if raw_source.is_symlink() or raw_target.is_symlink():
            message = "The trashed note cannot be restored"
            raise VaultError(message)
        source = self.vault.contained(source_candidate)
        target = self.vault.contained(target_candidate)
        if not source.is_file():
            message = "The trashed note no longer exists"
            raise VaultError(message)
        return source, target, raw_target

    def _restored_text_for_restore(self, source: Path) -> str:
        """Return the restored text or raise a concise failure."""
        try:
            return self._restored_text(source)
        except (AfanesError, UnicodeDecodeError, OSError) as exc:
            message = "The trashed note metadata cannot be read"
            raise VaultError(message) from exc

    @staticmethod
    def _check_birthplace(
        target: Path,
        raw_target: Path,
        target_candidate: Path,
        *,
        overwrite: bool,
    ) -> None:
        """Refuse a non-file birthplace and an occupied path without permission."""
        if not (target.exists() or raw_target.exists()):
            return
        if not target.is_file() or target.is_dir():
            message = "The birthplace is not a regular note file"
            raise VaultError(message)
        if not overwrite:
            message = f"Destination already exists: {target_candidate}"
            raise NameCollisionError(message)

    @staticmethod
    def _publish_restored(
        target: Path,
        restored_text: str,
        target_candidate: Path,
        *,
        overwrite: bool,
    ) -> None:
        """Write the restored note exclusively or replace after confirmation."""
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if overwrite:
                afanes.core.atomic.AtomicWriter.write_text_atomic(target, restored_text)
            else:
                afanes.core.atomic.AtomicWriter.write_text_exclusive(target, restored_text)
        except FileExistsError as exc:
            message = f"Destination already exists: {target_candidate}"
            raise NameCollisionError(message) from exc
        except (OSError, VaultError) as exc:
            message = "Could not restore the trashed note"
            raise VaultError(message) from exc

    @staticmethod
    def _remove_trash_copy(source: Path) -> None:
        """Remove the trash copy after a successful publication."""
        try:
            source.unlink()
        except OSError as exc:
            message = "The note was restored, but the trashed copy could not be removed"
            raise VaultError(message) from exc

    @staticmethod
    def _restored_text(source: Path) -> str:
        """Return the trashed note text with its metadata removed."""
        document = TrashDocument.from_text(source.read_bytes().decode("utf-8"))
        if document.metadata is None:
            message = "The trashed note has no usable birthplace"
            raise VaultError(message)
        return document.without_metadata()

    def _stamp(self, entry: TrashEntry, today: datetime.date) -> None:
        """Write today's date into one managed entry."""
        source = self._managed_source(entry.path)
        document = TrashDocument.from_text(source.read_bytes().decode("utf-8"))
        metadata = document.metadata
        if metadata is None:
            message = "The trashed note has no usable birthplace"
            raise VaultError(message)
        afanes.core.atomic.AtomicWriter.write_text_atomic(source, document.with_metadata(metadata.with_day(today)))

    def _require_managed_metadata(self, source: Path) -> None:
        """Raise unless a file still carries a safe birthplace."""
        document = TrashDocument.from_text(source.read_bytes().decode("utf-8"))
        if document.metadata is None:
            message = "The file is not a managed trash entry"
            raise VaultError(message)

    def _managed_source(self, candidate: Path) -> Path:
        """Resolve a managed file under the trash folder and refuse symlinks."""
        raw = candidate if candidate.is_absolute() else self.vault.root / candidate
        if raw.is_symlink():
            message = "The trashed note is not a regular file"
            raise VaultError(message)
        source = self.vault.contained(candidate)
        trash_directory = TrashCatalog(self.vault).trash_directory().resolve()
        if not source.is_relative_to(trash_directory) or not source.is_file():
            message = "The file is not a managed trash entry"
            raise VaultError(message)
        return source

    def _allocate(self, directory: Path) -> Path:
        """Return an unused UUID path inside the trash folder.

        Parameters
        ----------
        directory : Path
            Trash folder that may not exist yet.

        Returns
        -------
        Path
            Absolute path whose filename is a canonical lowercase UUID and
            whose file does not exist.
        """
        while True:
            candidate = directory / f"{uuid.uuid4()}{afanes.core.vault.snapshot.NOTE_SUFFIX}"
            if not candidate.exists():
                return candidate
