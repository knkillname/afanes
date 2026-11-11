# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Vault scanning, path containment, atomic writes, and reference-safe edits."""

import contextlib
import dataclasses
import hashlib
import os
import tempfile
from pathlib import Path

import afanes.core.links
import afanes.core.names
from afanes.core.errors import (
    AfanesError,
    NameCollisionError,
    NoteParseError,
    ReferenceRewriteError,
    VaultError,
    VaultPathError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import NameCatalog, ResolutionOutcome
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType

# Public canonical note extension.
NOTE_SUFFIX = ".md"


@dataclasses.dataclass(frozen=True, slots=True)
class VaultNote:
    """One note discovered during a read-only vault scan.

    Attributes
    ----------
    path : Path
        Absolute path to the note file.
    relative_path : Path
        Vault-relative path used for diagnostics.
    name : str
        Filename stem, preserving display case. This is the note's identity and
        title.
    note_type : NoteType
        Declared type from frontmatter.
    content_hash : str
        SHA-256 digest of the file bytes, used as an optimistic write guard.
    body_references : tuple[NoteReference, ...]
        References extracted from the Markdown body.
    frontmatter_references : tuple[NoteReference, ...]
        References declared by ``people`` and ``project`` values.
    """

    path: Path
    relative_path: Path
    name: str
    note_type: NoteType
    content_hash: str
    body_references: tuple[NoteReference, ...]
    frontmatter_references: tuple[NoteReference, ...]

    @property
    def references(self) -> tuple[NoteReference, ...]:
        """Return body and frontmatter references in that order.

        Returns
        -------
        tuple[NoteReference, ...]
            Body references followed by frontmatter references.
        """
        return self.body_references + self.frontmatter_references


@dataclasses.dataclass(frozen=True, slots=True)
class VaultFailure:
    """A note that could not be parsed during a scan.

    Attributes
    ----------
    path : Path
        Vault-relative path to the failing note.
    message : str
        Concise diagnostic. The scan continues with the remaining notes.
    """

    path: Path
    message: str


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
    """

    root: Path
    notes: tuple[VaultNote, ...]
    failures: tuple[VaultFailure, ...]
    catalog: NameCatalog


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
    affected : tuple[ReferenceSite, ...]
        Referring notes and counts, in scan order.
    reference_count : int
        Total number of references that would be rewritten.
    content_hashes : dict[Path, str]
        Content hash captured at planning time for every affected note,
        including the renamed note when it refers to itself.
    """

    note_path: Path
    target_path: Path
    scheme: ReferenceScheme
    old_name: str
    new_name: str
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
class DeletionPreview:
    """Inbound references reported before deleting a note.

    Attributes
    ----------
    note_path : Path
        Absolute path to the note that would be deleted.
    reference_count : int
        Number of references that point to it.
    affected_notes : tuple[Path, ...]
        Notes containing at least one inbound reference.
    """

    note_path: Path
    reference_count: int
    affected_notes: tuple[Path, ...]


def resolve_vault_root(root: Path) -> Path:
    """Resolve and validate a vault root directory.

    Parameters
    ----------
    root : Path
        Candidate vault root. ``~`` is expanded.

    Returns
    -------
    Path
        Absolute, resolved directory path.

    Raises
    ------
    VaultError
        If the path does not exist or is not a directory.
    """
    resolved = root.expanduser().resolve()
    if not resolved.is_dir():
        message = f"Vault root is not a directory: {root}"
        raise VaultError(message)
    return resolved


def contained_path(vault_root: Path, candidate: Path) -> Path:
    """Resolve a path and verify that it stays inside the vault.

    Parameters
    ----------
    vault_root : Path
        Vault root, resolved by :func:`resolve_vault_root`.
    candidate : Path
        Relative or absolute candidate path.

    Returns
    -------
    Path
        Resolved candidate path inside the vault.

    Raises
    ------
    VaultPathError
        If the resolved candidate escapes the vault root.
    """
    root = resolve_vault_root(vault_root)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        message = f"Path escapes the vault: {candidate}"
        raise VaultPathError(message)
    return resolved


def scan_vault(root: Path) -> VaultSnapshot:
    """Scan a vault without writing anything.

    Parameters
    ----------
    root : Path
        Vault root directory.

    Returns
    -------
    VaultSnapshot
        Parsed notes, failures, and the resulting name catalog.

    Notes
    -----
    Files are visited in deterministic path order. Directories whose names
    begin with a dot are skipped, as are symlinks that resolve outside the
    vault. A malformed note becomes a :class:`VaultFailure` and does not abort
    the scan. This function performs blocking file I/O and never writes.
    """
    vault_root = resolve_vault_root(root)
    notes: list[VaultNote] = []
    failures: list[VaultFailure] = []

    for path, relative_path in _note_paths(vault_root):
        try:
            notes.append(_read_note(path, relative_path))
        except (OSError, UnicodeDecodeError, AfanesError) as exc:
            failures.append(VaultFailure(path=relative_path, message=str(exc)))

    catalog = NameCatalog.from_entries((note.path, note.note_type) for note in notes)
    return VaultSnapshot(root=vault_root, notes=tuple(notes), failures=tuple(failures), catalog=catalog)


def write_text_atomic(path: Path, text: str) -> None:
    """Write UTF-8 text through a temporary file and an atomic replace.

    Parameters
    ----------
    path : Path
        Destination file. Its parent directory must already exist.
    text : str
        Complete file contents. Newline style is the caller's responsibility.

    Raises
    ------
    VaultError
        If the parent directory does not exist.

    Notes
    -----
    The temporary file lives in the destination directory so the final
    ``os.replace`` stays on one filesystem. The file is flushed and fsynced
    before the replace, and the temporary file is removed when any step fails.
    """
    parent = path.parent
    if not parent.is_dir():
        message = f"Destination directory does not exist: {parent}"
        raise VaultError(message)

    data = text.encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(dir=parent, prefix=f".{path.name}.", suffix=".tmp")
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            temporary_path.unlink()
        raise


def create_note(
    vault_root: Path,
    title: str,
    note_type: NoteType,
    *,
    directory: Path | None = None,
    body: str = "",
    status: str = "inbox",
) -> Path:
    """Create a note whose sanitized filename stem becomes its title.

    Parameters
    ----------
    vault_root : Path
        Vault root directory.
    title : str
        Display title to sanitize into a filename.
    note_type : NoteType
        Declared type for the new note.
    directory : Path | None
        Vault-relative or absolute classification directory. Defaults to the
        vault root. Missing directories are created.
    body : str
        Initial Markdown body. New files use LF and UTF-8 without a BOM.
    status : str
        Initial status value. Defaults to ``inbox``.

    Returns
    -------
    Path
        Absolute path to the created note.

    Raises
    ------
    VaultPathError
        If the target directory escapes the vault.
    VaultError
        If the target path is not a directory.
    """
    root = resolve_vault_root(vault_root)
    target_directory = root if directory is None else contained_path(root, directory)
    if target_directory.exists() and not target_directory.is_dir():
        message = f"Note directory is not a directory: {target_directory}"
        raise VaultError(message)
    target_directory.mkdir(parents=True, exist_ok=True)

    snapshot = scan_vault(root)
    scheme = afanes.core.links.scheme_for_note_type(note_type)
    taken = {note.name for note in snapshot.notes if afanes.core.links.scheme_for_note_type(note.note_type) is scheme}
    taken.update(entry.stem for entry in target_directory.iterdir())
    taken.update(entry.name for entry in target_directory.iterdir())
    name = afanes.core.names.unique_name(afanes.core.names.safe_filename(title), taken)

    normalized_body = body.replace("\r\n", "\n").replace("\r", "\n").removeprefix("\ufeff")
    document = NoteDocument(
        raw={"type": note_type.value, "status": status},
        body=normalized_body,
        newline="\n",
        has_frontmatter=True,
        note_type=note_type,
        references=(),
    )
    path = target_directory / f"{name}{NOTE_SUFFIX}"
    write_text_atomic(path, document.to_text())
    return path


def move_note(
    vault_root: Path,
    note_path: Path,
    destination_directory: Path,
    *,
    confirm: bool = False,
) -> Path:
    """Move a note between classification directories without touching links.

    Parameters
    ----------
    vault_root : Path
        Vault root directory.
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
        If the note or destination escapes the vault, or the source is not a
        Markdown note.
    NameCollisionError
        If the destination already contains a file with the same name.
    """
    if not confirm:
        message = "Directory moves require explicit confirmation"
        raise VaultError(message)

    root = resolve_vault_root(vault_root)
    source = contained_path(root, note_path)
    if not source.is_file() or source.suffix.casefold() != NOTE_SUFFIX:
        message = f"Not a note file: {note_path}"
        raise VaultPathError(message)

    destination = contained_path(root, destination_directory)
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


def plan_rename(
    vault_root: Path,
    note_path: Path,
    new_title: str,
    *,
    snapshot: VaultSnapshot | None = None,
) -> RenamePreview:
    """Plan a rename without changing any file.

    Parameters
    ----------
    vault_root : Path
        Vault root directory.
    note_path : Path
        Existing note path, relative or absolute.
    new_title : str
        Requested title. It is sanitized before comparison and use.
    snapshot : VaultSnapshot | None
        Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

    Returns
    -------
    RenamePreview
        Target path, affected notes, reference count, and content hashes taken
        at planning time.

    Raises
    ------
    VaultError
        If the note is not part of the vault snapshot.
    NameCollisionError
        If the sanitized name is already used in the same scheme or the target
        filename already exists.
    """
    root = resolve_vault_root(vault_root)
    source = contained_path(root, note_path)
    vault = snapshot or scan_vault(root)
    note = _find_note(vault, source)
    if note is None:
        message = f"Note is not part of the vault: {note_path}"
        raise VaultError(message)

    new_name = afanes.core.names.safe_filename(new_title)
    scheme = afanes.core.links.scheme_for_note_type(note.note_type)
    target = source.with_name(f"{new_name}{NOTE_SUFFIX}")
    same_name = afanes.core.names.normalize_name(new_name) == afanes.core.names.normalize_name(note.name)

    if not same_name:
        existing = vault.catalog.candidates(scheme, new_name)
        if any(not _same_path(path, source) for path in existing):
            message = f"A {scheme.value} note named {new_name!r} already exists"
            raise NameCollisionError(message)
        if target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)

    affected = () if same_name else _affected_sites(vault, source)
    hashes = {site.path: _hash_for_note(vault, site.path) for site in affected}
    return RenamePreview(
        note_path=source,
        target_path=target,
        scheme=scheme,
        old_name=note.name,
        new_name=new_name,
        affected=affected,
        reference_count=sum(site.reference_count for site in affected),
        content_hashes=hashes,
    )


def apply_rename(
    vault_root: Path,
    preview: RenamePreview,
    *,
    confirm: bool = False,
) -> RenameReport:
    """Apply a rename preview and rewrite resolving references.

    Parameters
    ----------
    vault_root : Path
        Vault root directory.
    preview : RenamePreview
        Plan produced by :func:`plan_rename`. Re-applying the same preview is
        safe and completes any remaining rewrites.
    confirm : bool
        Explicit confirmation gate. The operation raises unless this is
        ``True``.

    Returns
    -------
    RenameReport
        Renamed flag plus the updated, skipped, unchanged, and failed notes.

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

    root = resolve_vault_root(vault_root)
    source = contained_path(root, preview.note_path)
    target = contained_path(root, preview.target_path)
    renamed = False

    if source.exists():
        if target.exists() and not _same_path(source, target):
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

    for site in preview.affected:
        read_path = target if _same_path(site.path, source) else site.path
        try:
            data = read_path.read_bytes()
        except OSError as exc:
            failed.append(RewriteFailure(path=read_path, message=str(exc)))
            continue
        if hashlib.sha256(data).hexdigest() != preview.content_hashes.get(site.path):
            skipped.append(read_path)
            continue

        try:
            changed = _rewrite_note(read_path, data, old_reference, new_reference)
        except (OSError, UnicodeDecodeError, AfanesError) as exc:
            failed.append(RewriteFailure(path=read_path, message=str(exc)))
            continue
        if changed:
            updated.append(read_path)
        else:
            unchanged.append(read_path)

    return RenameReport(
        renamed=renamed,
        updated=tuple(updated),
        skipped=tuple(skipped),
        unchanged=tuple(unchanged),
        failed=tuple(failed),
    )


def plan_deletion(
    vault_root: Path,
    note_path: Path,
    *,
    snapshot: VaultSnapshot | None = None,
) -> DeletionPreview:
    """Report inbound references without changing any file.

    Parameters
    ----------
    vault_root : Path
        Vault root directory.
    note_path : Path
        Existing note path, relative or absolute.
    snapshot : VaultSnapshot | None
        Pre-built scan to avoid rescanning, or ``None`` to scan the vault.

    Returns
    -------
    DeletionPreview
        Number of inbound references and the notes that contain them.

    Raises
    ------
    VaultError
        If the note is not part of the vault snapshot.
    """
    root = resolve_vault_root(vault_root)
    source = contained_path(root, note_path)
    vault = snapshot or scan_vault(root)
    note = _find_note(vault, source)
    if note is None:
        message = f"Note is not part of the vault: {note_path}"
        raise VaultError(message)

    affected = _affected_sites(vault, source)
    return DeletionPreview(
        note_path=source,
        reference_count=sum(site.reference_count for site in affected),
        affected_notes=tuple(site.path for site in affected),
    )


def delete_note(
    vault_root: Path,
    note_path: Path,
    *,
    confirm: bool = False,
    snapshot: VaultSnapshot | None = None,
) -> int:
    """Delete a note after confirmation without rewriting inbound references.

    Parameters
    ----------
    vault_root : Path
        Vault root directory.
    note_path : Path
        Existing note path, relative or absolute.
    confirm : bool
        Explicit confirmation gate. The operation raises unless this is
        ``True``.
    snapshot : VaultSnapshot | None
        Pre-built scan used to report inbound references, or ``None`` to scan
        the vault.

    Returns
    -------
    int
        Number of inbound references reported before deletion.

    Raises
    ------
    VaultError
        If confirmation is missing or the note is not part of the vault.
    """
    if not confirm:
        message = "Deletion requires explicit confirmation"
        raise VaultError(message)

    preview = plan_deletion(vault_root, note_path, snapshot=snapshot)
    preview.note_path.unlink()
    return preview.reference_count


def _note_paths(root: Path) -> list[tuple[Path, Path]]:
    """Return note paths and their vault-relative paths in deterministic order."""
    paths: list[tuple[Path, Path]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts[:-1]):
            continue
        if path.suffix.casefold() != NOTE_SUFFIX or not path.is_file():
            continue
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if not resolved.is_relative_to(root):
            continue
        paths.append((path, relative))
    return paths


def _read_note(path: Path, relative_path: Path) -> VaultNote:
    """Read and parse one note, raising on malformed input."""
    data = path.read_bytes()
    text = data.decode("utf-8")
    document = NoteDocument.from_text(text)
    if document.note_type is None:
        message = "Note has no type"
        raise NoteParseError(message)
    body_references = tuple(afanes.core.links.extract_references(document.body))
    return VaultNote(
        path=path,
        relative_path=relative_path,
        name=path.stem,
        note_type=document.note_type,
        content_hash=hashlib.sha256(data).hexdigest(),
        body_references=body_references,
        frontmatter_references=document.references,
    )


def _find_note(snapshot: VaultSnapshot, source: Path) -> VaultNote | None:
    """Find a scanned note by path."""
    return next((note for note in snapshot.notes if _same_path(note.path, source)), None)


def _affected_sites(snapshot: VaultSnapshot, source: Path) -> tuple[ReferenceSite, ...]:
    """Collect per-note reference counts that resolve to a target note."""
    sites: list[ReferenceSite] = []
    for note in snapshot.notes:
        count = sum(1 for reference in note.references if _resolves_to(snapshot, reference, source))
        if count:
            sites.append(ReferenceSite(path=note.path, reference_count=count))
    return tuple(sites)


def _resolves_to(snapshot: VaultSnapshot, reference: NoteReference, source: Path) -> bool:
    """Return whether a reference uniquely resolves to a target note."""
    resolution = snapshot.catalog.resolve(reference)
    if resolution.outcome is not ResolutionOutcome.RESOLVED:
        return False
    return _same_path(resolution.targets[0], source)


def _hash_for_note(snapshot: VaultSnapshot, path: Path) -> str:
    """Return the content hash captured for a scanned note."""
    note = next(note for note in snapshot.notes if _same_path(note.path, path))
    return note.content_hash


def _same_path(left: Path, right: Path) -> bool:
    """Compare two paths after resolving filesystem aliases."""
    return left.resolve() == right.resolve()


def _rewrite_note(
    path: Path,
    data: bytes,
    old: NoteReference,
    new: NoteReference,
) -> bool:
    """Rewrite body and frontmatter references in one note atomically."""
    document = NoteDocument.from_text(data.decode("utf-8"))
    body, body_count = afanes.core.links.rewrite_body_references(document.body, old, new)
    rewritten, frontmatter_count = document.rewrite_references(old, new)
    if body_count + frontmatter_count == 0:
        return False

    final = rewritten.with_body(body)
    text = final.to_text()
    _verify_rewrite(text, old)
    write_text_atomic(path, text)
    return True


def _verify_rewrite(text: str, old: NoteReference) -> None:
    """Confirm that a rewritten note no longer names the old reference."""
    document = NoteDocument.from_text(text)
    old_key = afanes.core.links.reference_key(old)
    body_references = afanes.core.links.extract_references(document.body)
    remaining = body_references + list(document.references)
    if any(afanes.core.links.reference_key(reference) == old_key for reference in remaining):
        message = "Rewritten note still contains the old reference"
        raise ReferenceRewriteError(message)
