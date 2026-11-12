# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reference-safe renames, category moves, reference repair, moves, and trash.

Every operation in this module plans first and writes only after explicit
confirmation. Path containment and atomic writes stay on
:class:`afanes.core.vault.service.Vault`; this service owns only the naming workflows
that combine them.
"""

import dataclasses
import hashlib
from pathlib import Path

import afanes.core.atomic
import afanes.core.links
import afanes.core.names
import afanes.core.vault.snapshot
from afanes.core.errors import AfanesError, NameCollisionError, ReferenceRewriteError, VaultError, VaultPathError
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ReferenceKey
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import ReferenceSite, VaultPath, VaultSnapshot
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType


@dataclasses.dataclass(frozen=True, slots=True)
class ReferenceRepairPreview:
    """References that would be rewritten from one name to another.

    Attributes
    ----------
    old : NoteReference
        Reference name currently written in the vault.
    new : NoteReference
        Replacement reference name in the same scheme.
    sites : tuple[ReferenceSite, ...]
        Referring notes and their per-note reference counts, in scan order.
    content_hashes : dict[Path, str]
        Content hash captured at planning time for every referring note.
    """

    old: NoteReference
    new: NoteReference
    sites: tuple[ReferenceSite, ...]
    content_hashes: dict[Path, str]


@dataclasses.dataclass(frozen=True, slots=True)
class RenamePreview:
    """Planned rename and the references that would change.

    Attributes
    ----------
    note_path : Path
        Current absolute path of the note.
    target_path : Path
        Absolute path after the rename.
    scheme : ReferenceScheme
        Namespace of the note, used to match inbound references.
    old_name : str
        Current filename stem.
    new_name : str
        Sanitized replacement stem.
    heading_update : bool
        Whether the first level-1 heading currently matches the old identity
        and should be updated to the new one.
    affected : tuple[ReferenceSite, ...]
        Referring notes and counts, in scan order.
    reference_count : int
        Total number of references that would be rewritten.
    content_hashes : dict[Path, str]
        Content hash captured at planning time for every affected note,
        including the renamed note when it refers to itself or needs a heading
        update.
    """

    note_path: Path
    target_path: Path
    scheme: ReferenceScheme
    old_name: str
    new_name: str
    heading_update: bool
    affected: tuple[ReferenceSite, ...]
    reference_count: int
    content_hashes: dict[Path, str]


@dataclasses.dataclass(frozen=True, slots=True)
class RewriteFailure:
    """A referring note that could not be rewritten.

    Attributes
    ----------
    path : Path
        Absolute path to the note.
    message : str
        Concise failure reason.
    """

    path: Path
    message: str


@dataclasses.dataclass(frozen=True, slots=True)
class RewriteReport:
    """Outcome of applying a reference repair.

    Attributes
    ----------
    updated : tuple[Path, ...]
        Notes whose references were rewritten.
    skipped : tuple[Path, ...]
        Notes skipped because their content changed after planning.
    unchanged : tuple[Path, ...]
        Notes that no longer contained the old reference.
    failed : tuple[RewriteFailure, ...]
        Notes that could not be rewritten, with reasons.
    """

    updated: tuple[Path, ...]
    skipped: tuple[Path, ...]
    unchanged: tuple[Path, ...]
    failed: tuple[RewriteFailure, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class RenameReport:
    """Outcome of applying a rename preview.

    Attributes
    ----------
    renamed : bool
        Whether this call moved the file. ``False`` means a previous run had
        already renamed it and only reference rewrites remained.
    updated : tuple[Path, ...]
        Notes whose references were rewritten.
    skipped : tuple[Path, ...]
        Notes skipped because their content changed after planning.
    unchanged : tuple[Path, ...]
        Notes that no longer needed a rewrite.
    failed : tuple[RewriteFailure, ...]
        Notes that could not be rewritten, with reasons.
    """

    renamed: bool
    updated: tuple[Path, ...]
    skipped: tuple[Path, ...]
    unchanged: tuple[Path, ...]
    failed: tuple[RewriteFailure, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class TrashPreview:
    """Inbound references and destination reported before trashing a note.

    Attributes
    ----------
    note_path : Path
        Absolute path to the note that would be moved.
    trash_path : Path
        Absolute destination inside ``trash/``.
    reference_count : int
        Number of references that point to the note.
    affected_notes : tuple[Path, ...]
        Notes containing at least one inbound reference.
    """

    note_path: Path
    trash_path: Path
    reference_count: int
    affected_notes: tuple[Path, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class CategoryMovePreview:
    """A reference note's category change and its destination.

    Attributes
    ----------
    note_path : Path
        Absolute path to the reference before the change.
    target_path : Path
        Absolute destination inside ``reference/<label>/`` or ``reference/``.
    category : CategoryLabel | None
        Category to write, or ``None`` to remove it.
    """

    note_path: Path
    target_path: Path
    category: CategoryLabel | None


@dataclasses.dataclass(frozen=True, slots=True)
class VaultNaming:
    """Plan and apply renames, category moves, repairs, moves, and trash.

    Attributes
    ----------
    vault : Vault
        Resolved vault that owns path containment and the storage layout.
    """

    vault: Vault

    def move(
        self,
        note_path: Path,
        destination_directory: Path,
        *,
        confirm: bool = False,
    ) -> Path:
        """Move a note between directories without touching links.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        destination_directory : Path
            Classification directory inside the vault. Missing directories are
            created.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``; user interfaces ask the user first.

        Returns
        -------
        Path
            Absolute path to the moved note.

        Raises
        ------
        VaultError
            If confirmation is missing or the destination is not a directory.
        VaultPathError
            If the note or destination escapes the vault, or the source is not
            a Markdown note.
        NameCollisionError
            If the destination already contains a file with the same name.
        """
        if not confirm:
            message = "Directory moves require explicit confirmation"
            raise VaultError(message)

        source = self.vault.contained(note_path)
        if not source.is_file() or source.suffix.casefold() != afanes.core.vault.snapshot.NOTE_SUFFIX:
            message = f"Not a note file: {note_path}"
            raise VaultPathError(message)

        destination = self.vault.contained(destination_directory)
        if destination.exists() and not destination.is_dir():
            message = f"Move destination is not a directory: {destination}"
            raise VaultError(message)
        destination.mkdir(parents=True, exist_ok=True)

        target = destination / source.name
        if target.exists():
            message = f"Destination already contains a note named {source.name!r}"
            raise NameCollisionError(message)

        source.replace(target)
        return target

    def plan_category_move(
        self,
        note_path: Path,
        category: CategoryLabel | None,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> "CategoryMovePreview":
        """Plan moving a reference to its category folder without writing.

        Parameters
        ----------
        note_path : Path
            Path to an existing reference note, relative or absolute.
        category : CategoryLabel | None
            New category, or ``None`` to return the note to ``reference/``.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        CategoryMovePreview
            Current path, destination path, and the category to write.

        Raises
        ------
        VaultError
            If the note is missing from the snapshot or is not a reference.
        NameCollisionError
            If the destination already contains a file with the same name.
        VaultPathError
            If a path escapes the vault.
        """
        source = self.vault.contained(note_path)
        vault = snapshot or self.vault.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)
        if note.note_type is not NoteType.REFERENCE:
            message = "Only reference notes use a category folder"
            raise VaultError(message)
        target_directory = self.vault.directory_for(NoteType.REFERENCE, category)
        target = target_directory / source.name
        if not VaultPath.same(target, source) and target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)
        return CategoryMovePreview(note_path=source, target_path=target, category=category)

    def apply_category_move(
        self,
        preview: "CategoryMovePreview",
        *,
        confirm: bool = False,
    ) -> Path:
        """Write a new category and move the reference to its folder.

        Parameters
        ----------
        preview : CategoryMovePreview
            Plan produced by :meth:`plan_category_move`.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        Path
            Absolute path after the move.

        Raises
        ------
        VaultError
            If confirmation is missing or the move fails.
        NameCollisionError
            If the destination appeared after planning.
        NoteParseError
            If the note cannot be parsed.
        VaultPathError
            If a path escapes the vault.

        Notes
        -----
        The new frontmatter is written atomically before the file moves. If the
        move fails, the note keeps the new category in its old folder; grouping
        uses the label, so the drift is invisible and retryable.
        """
        if not confirm:
            message = "Moving a category requires explicit confirmation"
            raise VaultError(message)
        source = self.vault.contained(preview.note_path)
        target = self.vault.contained(preview.target_path)
        document = NoteDocument.from_text(source.read_text(encoding="utf-8"))
        raw = dict(document.raw)
        if preview.category is None:
            raw.pop("category", None)
        else:
            raw["category"] = preview.category.value
        afanes.core.atomic.write_text_atomic(source, document.with_metadata(raw).to_text())
        if VaultPath.same(source, target):
            return source
        if target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.replace(target)
        except OSError as exc:
            message = f"Could not move the note to its category folder: {source}"
            raise VaultError(message) from exc
        return target

    def plan_rename(
        self,
        note_path: Path,
        new_title: str,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> RenamePreview:
        """Plan a rename without changing any file.

        Parameters
        ----------
        note_path : Path
            Existing note path, relative or absolute.
        new_title : str
            Requested name for the note's identity. It is sanitized before
            comparison and use.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        RenamePreview
            Target path, affected notes, reference count, and content hashes
            taken at planning time.

        Raises
        ------
        VaultError
            If the note is not part of the vault snapshot.
        NameCollisionError
            If the sanitized name is already used in the same scheme or the
            target filename already exists.
        """
        source = self.vault.contained(note_path)
        vault = snapshot or self.vault.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)

        new_name = afanes.core.names.safe_filename(new_title)
        scheme = ReferenceScheme.for_note(note.note_type)
        target = source.with_name(f"{new_name}{afanes.core.vault.snapshot.NOTE_SUFFIX}")
        same_name = afanes.core.names.normalize_name(new_name) == afanes.core.names.normalize_name(note.name)

        if not same_name:
            existing = vault.catalog.candidates(scheme, new_name)
            if any(not VaultPath.same(path, source) for path in existing):
                message = f"A {scheme.value} note named {new_name!r} already exists"
                raise NameCollisionError(message)
            if target.exists():
                message = f"Destination already exists: {target}"
                raise NameCollisionError(message)

        affected = () if same_name else vault.affected_sites(source)
        hashes = {site.path: vault.hash_for_note(site.path) for site in affected}

        heading_update = False
        if not same_name:
            try:
                data = source.read_bytes()
                document = NoteDocument.from_text(data.decode("utf-8"))
            except (OSError, UnicodeDecodeError, AfanesError) as exc:
                message = f"Could not inspect the note before renaming: {source}"
                raise VaultError(message) from exc
            heading_update = document.title == note.name
            if heading_update:
                hashes[source] = hashlib.sha256(data).hexdigest()

        return RenamePreview(
            note_path=source,
            target_path=target,
            scheme=scheme,
            old_name=note.name,
            new_name=new_name,
            heading_update=heading_update,
            affected=affected,
            reference_count=sum(site.reference_count for site in affected),
            content_hashes=hashes,
        )

    def apply_rename(
        self,
        preview: RenamePreview,
        *,
        confirm: bool = False,
    ) -> RenameReport:
        """Apply a rename preview and rewrite resolving references.

        Parameters
        ----------
        preview : RenamePreview
            Plan produced by :meth:`plan_rename`. Re-applying the same preview
            is safe and completes any remaining rewrites.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        RenameReport
            Renamed flag plus the updated, skipped, unchanged, and failed
            notes.

        Raises
        ------
        VaultError
            If confirmation is missing or the note cannot be found.
        NameCollisionError
            If the target path appeared after planning.
        """
        if not confirm:
            message = "Renames require explicit confirmation"
            raise VaultError(message)

        source = self.vault.contained(preview.note_path)
        target = self.vault.contained(preview.target_path)
        renamed = False

        if source.exists():
            if target.exists() and not VaultPath.same(source, target):
                message = f"Destination already exists: {target}"
                raise NameCollisionError(message)
            source.replace(target)
            renamed = True
        elif not target.exists():
            message = f"Note no longer exists: {preview.note_path}"
            raise VaultError(message)

        old_reference = NoteReference(scheme=preview.scheme, name=preview.old_name)
        new_reference = NoteReference(scheme=preview.scheme, name=preview.new_name)
        updated: list[Path] = []
        skipped: list[Path] = []
        unchanged: list[Path] = []
        failed: list[RewriteFailure] = []

        if preview.heading_update:
            heading_updated, heading_skipped, heading_unchanged, heading_failed = self._apply_heading_update(
                preview, source, target, old_reference, new_reference
            )
            updated.extend(heading_updated)
            skipped.extend(heading_skipped)
            unchanged.extend(heading_unchanged)
            failed.extend(heading_failed)

        site_updated, site_skipped, site_unchanged, site_failed = self._apply_reference_sites(
            preview,
            source,
            target,
            old_reference,
            new_reference,
            skip_source=preview.heading_update,
        )
        updated.extend(site_updated)
        skipped.extend(site_skipped)
        unchanged.extend(site_unchanged)
        failed.extend(site_failed)

        return RenameReport(
            renamed=renamed,
            updated=tuple(updated),
            skipped=tuple(skipped),
            unchanged=tuple(unchanged),
            failed=tuple(failed),
        )

    def _apply_heading_update(
        self,
        preview: RenamePreview,
        source: Path,
        target: Path,
        old_reference: NoteReference,
        new_reference: NoteReference,
    ) -> tuple[tuple[Path, ...], tuple[Path, ...], tuple[Path, ...], tuple[RewriteFailure, ...]]:
        """Apply the heading update and classify the outcome."""
        try:
            data = target.read_bytes()
        except OSError as exc:
            return ((), (), (), (RewriteFailure(path=target, message=str(exc)),))
        if hashlib.sha256(data).hexdigest() != preview.content_hashes.get(source):
            return ((), (target,), (), ())
        try:
            changed = self._rewrite_renamed_note(
                target,
                data,
                old_reference,
                new_reference,
                preview.new_name,
            )
        except (OSError, UnicodeDecodeError, AfanesError) as exc:
            return ((), (), (), (RewriteFailure(path=target, message=str(exc)),))
        if changed:
            return ((target,), (), (), ())
        return ((), (), (target,), ())

    def _apply_reference_sites(
        self,
        preview: RenamePreview,
        source: Path,
        target: Path,
        old_reference: NoteReference,
        new_reference: NoteReference,
        *,
        skip_source: bool,
    ) -> tuple[list[Path], list[Path], list[Path], list[RewriteFailure]]:
        """Rewrite the preview's referring notes, optionally skipping the renamed note."""
        updated: list[Path] = []
        skipped: list[Path] = []
        unchanged: list[Path] = []
        failed: list[RewriteFailure] = []
        for site in preview.affected:
            if skip_source and VaultPath.same(site.path, source):
                continue
            read_path = target if VaultPath.same(site.path, source) else site.path
            try:
                data = read_path.read_bytes()
            except OSError as exc:
                failed.append(RewriteFailure(path=read_path, message=str(exc)))
                continue
            if hashlib.sha256(data).hexdigest() != preview.content_hashes.get(site.path):
                skipped.append(read_path)
                continue

            try:
                changed = self._rewrite_note(read_path, data, old_reference, new_reference)
            except (OSError, UnicodeDecodeError, AfanesError) as exc:
                failed.append(RewriteFailure(path=read_path, message=str(exc)))
                continue
            if changed:
                updated.append(read_path)
            else:
                unchanged.append(read_path)
        return updated, skipped, unchanged, failed

    def plan_reference_repair(
        self,
        old: NoteReference,
        new: NoteReference,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> ReferenceRepairPreview:
        """Plan a rewrite of one reference name to another without writing.

        Parameters
        ----------
        old : NoteReference
            Reference name currently written in the vault.
        new : NoteReference
            Replacement reference name. It must use the same scheme as ``old``.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

        Returns
        -------
        ReferenceRepairPreview
            Referring notes, per-note counts, and content hashes captured at
            planning time. Empty when no note contains the old reference.

        Raises
        ------
        VaultError
            If the two references use different schemes.

        Notes
        -----
        Matching compares reference keys (scheme and normalized name) rather
        than resolution. It therefore finds references to a name that has no
        page yet, which is exactly the unsafe-link repair case. This method
        performs blocking file I/O when it scans, and never writes.
        """
        if old.scheme is not new.scheme:
            message = "Reference repair must stay within one scheme"
            raise VaultError(message)

        vault = snapshot or self.vault.scan()
        old_key = ReferenceKey.from_reference(old)
        sites: list[ReferenceSite] = []
        hashes: dict[Path, str] = {}
        for note in vault.notes:
            count = sum(1 for reference in note.references if ReferenceKey.from_reference(reference) == old_key)
            if count:
                sites.append(ReferenceSite(path=note.path, reference_count=count))
                hashes[note.path] = note.content_hash
        return ReferenceRepairPreview(old=old, new=new, sites=tuple(sites), content_hashes=hashes)

    def apply_reference_repair(
        self,
        preview: ReferenceRepairPreview,
        *,
        confirm: bool = False,
    ) -> RewriteReport:
        """Apply a reference repair after confirmation.

        Parameters
        ----------
        preview : ReferenceRepairPreview
            Plan produced by :meth:`plan_reference_repair`.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        RewriteReport
            Updated, skipped, unchanged, and failed notes.

        Raises
        ------
        VaultError
            If confirmation is missing.

        Notes
        -----
        Each referring note is rewritten atomically only when its content still
        matches the hash captured at planning time. A changed note is skipped
        and reported. Re-applying the same preview is safe: notes already
        rewritten by an earlier run are skipped by the hash guard.
        """
        if not confirm:
            message = "Reference repairs require explicit confirmation"
            raise VaultError(message)

        updated: list[Path] = []
        skipped: list[Path] = []
        unchanged: list[Path] = []
        failed: list[RewriteFailure] = []
        for site in preview.sites:
            try:
                data = site.path.read_bytes()
            except OSError as exc:
                failed.append(RewriteFailure(path=site.path, message=str(exc)))
                continue
            if hashlib.sha256(data).hexdigest() != preview.content_hashes.get(site.path):
                skipped.append(site.path)
                continue
            try:
                changed = self._rewrite_note(site.path, data, preview.old, preview.new)
            except (OSError, UnicodeDecodeError, AfanesError) as exc:
                failed.append(RewriteFailure(path=site.path, message=str(exc)))
                continue
            if changed:
                updated.append(site.path)
            else:
                unchanged.append(site.path)
        return RewriteReport(
            updated=tuple(updated),
            skipped=tuple(skipped),
            unchanged=tuple(unchanged),
            failed=tuple(failed),
        )

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
        trash_name = afanes.core.names.unique_name(source.stem, taken)
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
    ) -> int:
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
        int
            Number of inbound references reported before trashing.

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
        return preview.reference_count

    @staticmethod
    def _rewrite_note(
        path: Path,
        data: bytes,
        old: NoteReference,
        new: NoteReference,
    ) -> bool:
        """Rewrite body references in one note atomically."""
        document = NoteDocument.from_text(data.decode("utf-8"))
        rewrite = afanes.core.links.MarkdownBody(document.body).rewrite_references(old, new)
        if rewrite.count == 0:
            return False

        final = document.with_body(rewrite.text)
        text = final.to_text()
        reader = afanes.core.links.ReferenceReader()
        VaultNaming._verify_rewrite(text, old, reader)
        afanes.core.atomic.write_text_atomic(path, text)
        return True

    @staticmethod
    def _rewrite_renamed_note(
        path: Path,
        data: bytes,
        old: NoteReference,
        new: NoteReference,
        new_title: str,
    ) -> bool:
        """Rewrite a renamed note's heading and body references atomically."""
        current = data.decode("utf-8")
        document = NoteDocument.from_text(current)
        rewrite = afanes.core.links.MarkdownBody(document.body).rewrite_references(old, new)
        final = document.with_body(rewrite.text).with_heading(new_title)
        text = final.to_text()
        if text == current:
            return False
        reader = afanes.core.links.ReferenceReader()
        VaultNaming._verify_rewrite(text, old, reader)
        afanes.core.atomic.write_text_atomic(path, text)
        return True

    @staticmethod
    def _verify_rewrite(
        text: str,
        old: NoteReference,
        reader: afanes.core.links.ReferenceReader,
    ) -> None:
        """Confirm that a rewritten note no longer names the old reference."""
        document = NoteDocument.from_text(text)
        old_key = ReferenceKey.from_reference(old)
        remaining = reader.extract(document.body)
        if any(ReferenceKey.from_reference(reference) == old_key for reference in remaining):
            message = "Rewritten note still contains the old reference"
            raise ReferenceRewriteError(message)
