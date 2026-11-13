# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Plan, move, and restore notes in the vault trash."""

import contextlib
import dataclasses
import os
import shutil
from pathlib import Path

import afanes.core.names
import afanes.core.vault.snapshot
from afanes.core.errors import NameCollisionError, VaultError
from afanes.core.vault.naming_reports import TrashPreview
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import VaultSnapshot


@dataclasses.dataclass(frozen=True, slots=True)
class TrashService:
    """Plan, move, and restore notes without rewriting their references.

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
    ) -> TrashPreview:
        """Report inbound references and the trash destination without writing.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        TrashPreview
            Destination inside ``trash/``, inbound reference count, and the
            notes that contain those references.

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

        trash_directory = self.vault.existing_directory(self.vault.root, afanes.core.vault.snapshot.TRASH_DIRECTORY)
        taken: set[str] = set()
        if trash_directory.is_dir():
            taken.update(entry.stem for entry in trash_directory.iterdir())
            taken.update(entry.name for entry in trash_directory.iterdir())
        trash_name = afanes.core.names.NamePolicy.unique(source.stem, taken)
        affected = vault.affected_sites(source)
        return TrashPreview(
            note_path=source,
            trash_path=trash_directory / f"{trash_name}{afanes.core.vault.snapshot.NOTE_SUFFIX}",
            reference_count=sum(site.reference_count for site in affected),
            affected_notes=tuple(site.path for site in affected),
        )

    def trash(
        self,
        note_path: Path,
        *,
        confirm: bool = False,
        snapshot: VaultSnapshot | None = None,
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
            Pre-built scan used to report inbound references, or ``None`` to
            scan the vault.

        Returns
        -------
        TrashPreview
            Destination that was used and the inbound-reference report taken
            at planning time.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not part of the vault, or
            the move fails.
        NameCollisionError
            If the trash destination appears after planning.
        """
        if not confirm:
            message = "Trashing requires explicit confirmation"
            raise VaultError(message)

        preview = self.plan_trash(note_path, snapshot=snapshot)
        if preview.trash_path.exists():
            message = f"Trash destination already exists: {preview.trash_path}"
            raise NameCollisionError(message)
        try:
            preview.trash_path.parent.mkdir(parents=True, exist_ok=True)
            preview.note_path.replace(preview.trash_path)
        except OSError as exc:
            message = f"Could not move the note to trash: {preview.note_path}"
            raise VaultError(message) from exc
        return preview

    def restore(self, preview: TrashPreview, *, confirm: bool = False) -> Path:
        """Restore a trashed note to its original path.

        Parameters
        ----------
        preview : TrashPreview
            Preview returned by :meth:`trash` or :meth:`plan_trash`.
        confirm : bool
            Explicit confirmation gate.

        Returns
        -------
        Path
            Absolute path of the restored note.

        Raises
        ------
        VaultError
            If confirmation is missing, the trash file is gone, or a path
            escapes the vault.
        NameCollisionError
            If the original path is occupied.

        Notes
        -----
        The restored file is published exclusively, so an occupied path is
        never overwritten. A hard link to the trashed file publishes it without
        rewriting its bytes; filesystems that cannot create hard links fall
        back to an exclusive binary copy. The trash copy is removed only after
        the restored file exists.
        """
        if not confirm:
            message = "Restoring a trashed note requires explicit confirmation"
            raise VaultError(message)

        source = self.vault.contained(preview.trash_path)
        target = self.vault.contained(preview.note_path)
        if not source.is_file():
            message = f"Trashed note no longer exists: {preview.trash_path}"
            raise VaultError(message)
        if target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            message = f"Could not create the destination directory: {target.parent}"
            raise VaultError(message) from exc

        try:
            self._publish_exclusive(source, target)
        except FileExistsError as exc:
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message) from exc
        except OSError as exc:
            message = f"Could not restore the trashed note: {source}"
            raise VaultError(message) from exc

        try:
            source.unlink()
        except OSError as exc:
            with contextlib.suppress(OSError):
                target.unlink()
            message = f"Could not remove the trashed note after restoring: {source}"
            raise VaultError(message) from exc
        return target

    @staticmethod
    def _publish_exclusive(source: Path, target: Path) -> None:
        """Publish a file at a path that must not already exist.

        Parameters
        ----------
        source : Path
            Existing file to publish.
        target : Path
            Destination path. It must not exist.

        Raises
        ------
        FileExistsError
            If the destination exists.
        OSError
            If neither a hard link nor an exclusive binary copy can be made.

        Notes
        -----
        A hard link keeps the bytes unchanged without a temporary file. When
        the filesystem refuses hard links, an exclusive binary copy preserves
        the bytes and refuses an occupied destination.
        """
        try:
            os.link(source, target)
        except FileExistsError:
            raise
        except OSError:
            pass
        else:
            return

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        descriptor = os.open(target, flags, 0o666)
        try:
            with source.open("rb") as reader, os.fdopen(descriptor, "wb") as writer:
                shutil.copyfileobj(reader, writer)
                writer.flush()
                os.fsync(writer.fileno())
        except BaseException:
            with contextlib.suppress(OSError):
                os.close(descriptor)
            with contextlib.suppress(OSError):
                target.unlink()
            raise
