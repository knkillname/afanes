# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Planning for log date changes and type conversions.

The service builds rename-shaped previews; applying them remains in
:class:`afanes.core.vault.naming.VaultNaming` so one code path owns the write,
move, and reference rewrite.
"""

import dataclasses
from pathlib import Path

import afanes.core.log
import afanes.core.names
import afanes.core.vault.snapshot
from afanes.core.errors import NameCollisionError, VaultError
from afanes.core.vault.naming import VaultNaming
from afanes.core.vault.naming_reports import RenamePreview, RenameReport
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import VaultPath, VaultSnapshot
from afanes.models.link import ReferenceScheme
from afanes.models.note import NoteDate, NoteType


@dataclasses.dataclass(frozen=True, slots=True)
class LogConversions:
    """Plan log date changes and type conversions for one vault.

    Attributes
    ----------
    vault : Vault
        Resolved vault that owns path containment and the storage layout.
    """

    vault: Vault

    def apply(self, preview: RenamePreview, *, confirm: bool = True) -> RenameReport:
        """Apply a log conversion preview.

        Parameters
        ----------
        preview : RenamePreview
            Preview produced by :meth:`plan_log_date_change` or
            :meth:`plan_type_change`.
        confirm : bool
            Explicit confirmation gate. It defaults to ``True`` because the
            product requires no extra prompt for a log date change.

        Returns
        -------
        RenameReport
            Renamed flag plus updated, skipped, unchanged, and failed notes.
        """
        return VaultNaming(self.vault).apply_rename(preview, confirm=confirm)

    def plan_log_date_change(
        self,
        note_path: Path,
        new_date: NoteDate,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> RenamePreview:
        """Plan a log entry date change without writing.

        Parameters
        ----------
        note_path : Path
            Existing log entry path, relative or absolute.
        new_date : NoteDate
            Replacement ISO date. Its precision selects the filename and folder.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        RenamePreview
            Rename-shaped preview carrying the new date, target path, affected
            references, and content hashes.

        Raises
        ------
        VaultError
            If the note is not part of the snapshot or is not a log entry.
        NameCollisionError
            If the target date already belongs to another log entry or the
            target file exists.

        Notes
        -----
        The source note is excluded from :attr:`afanes.core.vault.naming_reports.RenamePreview.affected` so a
        self-reference cannot be rewritten after the date write. The source
        hash is included in :attr:`afanes.core.vault.naming_reports.RenamePreview.content_hashes` so apply can
        detect an external edit before writing the date. A heading that equals
        the old generated date title follows the new date; any other heading is
        preserved.
        """
        source = self.vault.contained(note_path)
        vault = snapshot or self.vault.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)
        if note.note_type is not NoteType.LOG:
            message = "Only log notes use a date identity"
            raise VaultError(message)

        target_directory = self.vault.contained(self.vault.log_directory(new_date))
        target = target_directory / f"{new_date.text}{afanes.core.vault.snapshot.NOTE_SUFFIX}"
        existing = vault.catalog.candidates(ReferenceScheme.LOG, new_date.text)
        if any(not VaultPath.same(path, source) for path in existing):
            message = f"A log note named {new_date.text!r} already exists"
            raise NameCollisionError(message)
        if target.exists() and not VaultPath.same(target, source):
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)

        affected = tuple(site for site in vault.affected_sites(source) if not VaultPath.same(site.path, source))
        hashes = {site.path: vault.hash_for_note(site.path) for site in affected}
        hashes[source] = note.content_hash
        new_heading: str | None = None
        if note.date is not None and note.title == afanes.core.log.LogTitle.for_date(note.date).text:
            new_heading = afanes.core.log.LogTitle.for_date(new_date).text
        return RenamePreview(
            note_path=source,
            target_path=target,
            scheme=ReferenceScheme.LOG,
            old_name=note.name,
            new_name=new_date.text,
            heading_update=False,
            affected=affected,
            reference_count=sum(site.reference_count for site in affected),
            content_hashes=hashes,
            new_date=new_date,
            new_scheme=ReferenceScheme.LOG,
            new_type=NoteType.LOG,
            new_heading=new_heading,
        )

    def plan_type_change(
        self,
        note_path: Path,
        new_type: NoteType,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> RenamePreview:
        """Plan a type change that enters or leaves the log scheme.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        new_type : NoteType
            Replacement type. The current type must differ.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        RenamePreview
            Rename-shaped preview carrying the target type, scheme, path, and
            affected references.

        Raises
        ------
        VaultError
            If the note is not part of the snapshot, the type is unchanged, or
            a note without a date is changed to ``log``.
        NameCollisionError
            If the target name already belongs to another note or the target
            file exists.

        Notes
        -----
        The heading is preserved. A log entry leaving the log is renamed to its
        display title; any other note entering the log is renamed to its date.
        The source note is excluded from :attr:`afanes.core.vault.naming_reports.RenamePreview.affected` so the
        conversion write cannot conflict with its own rewrite.
        """
        source = self.vault.contained(note_path)
        vault = snapshot or self.vault.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)
        if note.note_type is new_type:
            message = "The note already has that type"
            raise VaultError(message)
        if new_type is NoteType.LOG and note.date is None:
            message = "Set a date before changing this note to a log entry"
            raise VaultError(message)

        new_scheme = ReferenceScheme.for_note(new_type)
        new_date = note.date
        if new_type is NoteType.LOG:
            if note.date is None:
                message = "Set a date before changing this note to a log entry"
                raise VaultError(message)
            new_name = note.date.text
            target_directory = self.vault.contained(self.vault.log_directory(note.date))
        else:
            new_name = afanes.core.names.NamePolicy.safe_filename(note.title)
            target_directory = self.vault.contained(self.vault.directory_for(new_type))
        target = target_directory / f"{new_name}{afanes.core.vault.snapshot.NOTE_SUFFIX}"

        existing = vault.catalog.candidates(new_scheme, new_name)
        if any(not VaultPath.same(path, source) for path in existing):
            message = f"A {new_scheme.value} note named {new_name!r} already exists"
            raise NameCollisionError(message)
        if target.exists() and not VaultPath.same(target, source):
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)

        affected = tuple(site for site in vault.affected_sites(source) if not VaultPath.same(site.path, source))
        hashes = {site.path: vault.hash_for_note(site.path) for site in affected}
        hashes[source] = note.content_hash
        return RenamePreview(
            note_path=source,
            target_path=target,
            scheme=ReferenceScheme.for_note(note.note_type),
            old_name=note.name,
            new_name=new_name,
            heading_update=False,
            affected=affected,
            reference_count=sum(site.reference_count for site in affected),
            content_hashes=hashes,
            new_date=new_date,
            new_scheme=new_scheme,
            new_type=new_type,
        )
