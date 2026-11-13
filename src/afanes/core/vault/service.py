# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Vault scanning, path containment, atomic writes, and reference-safe edits."""

import dataclasses
import datetime
import hashlib
import os
from pathlib import Path
from typing import Self

import afanes.core.atomic
import afanes.core.links
import afanes.core.names
import afanes.core.steps
import afanes.core.templates
import afanes.core.vault.schema
import afanes.core.vault.snapshot
import afanes.models.step
from afanes.core.errors import (
    AfanesError,
    InvalidReferenceError,
    NoteParseError,
    TemplateCardWriteError,
    TemplateWriteError,
    VaultError,
    VaultMissingError,
    VaultNotDirectoryError,
    VaultNotEmptyError,
    VaultPathError,
    VaultUnreadableError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.core.labels import PageLabels
from afanes.core.links import CatalogEntry, NameCatalog
from afanes.core.template_cards import TemplateCard, TemplateCardCatalog
from afanes.core.vault.snapshot import (
    NotePath,
    PageContent,
    PageFile,
    ParsedPage,
    UnparsedPage,
    VaultFailure,
    VaultNote,
    VaultSnapshot,
)
from afanes.models.link import ReferenceScheme
from afanes.models.note import CategoryLabel, DatePrecision, NoteDate, NoteType, Status

# Public canonical note extension.
NOTE_SUFFIX = afanes.core.vault.snapshot.NOTE_SUFFIX

# Public default storage layout.
INBOX_DIRECTORY = afanes.core.vault.snapshot.INBOX_DIRECTORY
TRASH_DIRECTORY = afanes.core.vault.snapshot.TRASH_DIRECTORY
REFERENCE_DIRECTORY = afanes.core.vault.snapshot.REFERENCE_DIRECTORY
PROJECTS_DIRECTORY = afanes.core.vault.snapshot.PROJECTS_DIRECTORY
LOG_DIRECTORY = afanes.core.vault.snapshot.LOG_DIRECTORY
TEMPLATES_DIRECTORY = afanes.core.vault.snapshot.TEMPLATES_DIRECTORY


@dataclasses.dataclass(frozen=True, slots=True)
class Vault:
    """A resolved vault root and the operations scoped to it.

    Attributes
    ----------
    root : Path
        Absolute, resolved vault directory.
    """

    root: Path

    def __post_init__(self) -> None:
        """Resolve and validate the vault root.

        Raises
        ------
        VaultMissingError
            If the path does not exist.
        VaultNotDirectoryError
            If the path exists and is not a directory.
        """
        resolved = self.root.expanduser().resolve()
        if not resolved.exists():
            message = f"Vault root does not exist: {self.root}"
            raise VaultMissingError(message)
        if not resolved.is_dir():
            message = f"Vault root is not a directory: {self.root}"
            raise VaultNotDirectoryError(message)
        object.__setattr__(self, "root", resolved)

    @classmethod
    def open(cls, path: Path) -> Self:
        """Open an existing directory as a vault.

        Parameters
        ----------
        path : pathlib.Path
            Candidate vault directory. A relative path is resolved against the
            current working directory.

        Returns
        -------
        Vault
            Validated vault service for ``path``.

        Raises
        ------
        VaultMissingError
            If the path does not exist.
        VaultNotDirectoryError
            If the path exists and is not a directory.
        VaultUnreadableError
            If the directory cannot be read.
        VaultSchemaMissingError
            If the vault has no settings file.
        VaultSchemaInvalidError
            If the settings file does not match the current schema shape.
        VaultSchemaUnsupportedError
            If the settings file declares another schema version.

        Notes
        -----
        This method performs blocking filesystem checks and never writes. It
        reads ``afanes.yaml`` to validate the on-disk schema, so a valid
        read-only vault opens for browsing. It is the single validation path
        shared by the interface and the command line.
        """
        vault = cls(path)
        if not os.access(vault.root, os.R_OK):
            message = f"Vault root cannot be read: {path}"
            raise VaultUnreadableError(message)
        afanes.core.vault.schema.VaultSchemaStore(vault.root).require()
        return vault

    @classmethod
    def default_layout(cls) -> tuple[Path, ...]:
        """Return the default folders relative to a vault root.

        Returns
        -------
        tuple[pathlib.Path, ...]
            Canonical relative folders seeded when a vault is created, in the
            order a created vault reports them.

        Notes
        -----
        This method is a pure lookup. It reads no filesystem and creates
        nothing.
        """
        return (
            INBOX_DIRECTORY,
            TRASH_DIRECTORY,
            REFERENCE_DIRECTORY,
            PROJECTS_DIRECTORY,
            LOG_DIRECTORY,
        )

    @classmethod
    def create_directory(
        cls,
        path: Path,
        *,
        template: str | None = None,
        locale: str | None = None,
    ) -> "VaultCreation":
        """Create and seed a vault directory.

        Parameters
        ----------
        path : pathlib.Path
            Directory to create or seed. It must be missing or empty.
        template : str | None
            Bundled template identifier, or ``None`` for a vault with no
            starter content apart from the guide note.
        locale : str | None
            Locale used to resolve bundled content. ``None`` uses the base
            locale, and a missing locale falls back to it.

        Returns
        -------
        VaultCreation
            Created vault, the intermediate directories made for it, the
            default folders created inside it, the notes written into it, and
            the reference template cards seeded into it.

        Raises
        ------
        VaultNotDirectoryError
            If the path exists and is not a directory.
        VaultNotEmptyError
            If the directory exists and already contains entries.
        UnknownTemplateError
            If ``template`` names no catalog entry.
        TemplateContentError
            If the bundled content is missing or violates a vault validity rule.
        TemplateCardContentError
            If a bundled template card is invalid or missing.
        TemplateWriteError
            If a bundled note cannot be written. Notes written before the
            failure remain in place.
        TemplateCardWriteError
            If a bundled template card cannot be written. Cards written before
            the failure remain in place.
        VaultSchemaWriteError
            If the settings file cannot be written. The folder may exist, but
            no default folder or starter content is written.
        VaultError
            If a directory cannot be created or seeded.

        Notes
        -----
        Missing intermediate folders are created. The path is resolved before
        it is inspected, so a symlink cannot smuggle a populated directory past
        the emptiness check. Bundled content and the template cards are
        resolved and validated before the first directory is created, so a
        refused tree leaves the filesystem unchanged. Nothing is rolled back
        when seeding or writing fails partway: the directories and notes already
        created stay in place.
        """
        target = path.expanduser().resolve()
        try:
            if target.exists() and not target.is_dir():
                message = f"Vault path is not a directory: {path}"
                raise VaultNotDirectoryError(message)
            if target.is_dir() and any(target.iterdir()):
                message = f"Vault path is not empty: {path}"
                raise VaultNotEmptyError(message)
        except OSError as exc:
            message = f"Could not inspect the vault directory: {path}"
            raise VaultError(message) from exc

        bundle = afanes.core.templates.TemplateCatalog.bundled().bundle(template, locale)
        cards = TemplateCardCatalog.bundled().strict_cards()

        try:
            created = cls._missing_directories(target.parent)
            target.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            message = f"Could not create the vault directory: {path}"
            raise VaultError(message) from exc
        vault = cls(target)
        settings = afanes.core.vault.schema.VaultSchemaStore(vault.root)
        settings.create_current()
        try:
            seeded = vault._seed_layout()
        except OSError as exc:
            message = f"Could not seed the vault directory: {path}"
            raise VaultError(message) from exc
        written = vault._write_bundle(bundle)
        written_cards = vault._write_template_cards(cards)
        return VaultCreation(
            vault=vault,
            created_directories=created,
            seeded_directories=seeded,
            written_notes=written,
            written_cards=written_cards,
            template=bundle.template,
            settings_file=settings.settings_path,
        )

    def _write_bundle(self, bundle: afanes.core.templates.TemplateBundle) -> tuple[Path, ...]:
        """Write the guide and template notes into this new vault.

        Parameters
        ----------
        bundle : afanes.core.templates.TemplateBundle
            Validated content resolved for this creation.

        Returns
        -------
        tuple[pathlib.Path, ...]
            Absolute paths of the notes written, in creation order.

        Raises
        ------
        TemplateWriteError
            If a note cannot be written. The message names the failing note and
            the notes already written, which stay in place.
        """
        written: list[Path] = []
        for note in bundle.ordered_notes:
            target = self.contained(note.relative_path)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                afanes.core.atomic.write_text_atomic(target, note.text)
            except (OSError, VaultError) as exc:
                already = ", ".join(path.relative_to(self.root).as_posix() for path in written) or "none"
                message = (
                    f"Could not write bundled note {note.relative_path.as_posix()!r}; notes already written: {already}"
                )
                raise TemplateWriteError(message) from exc
            written.append(target)
        return tuple(written)

    def _write_template_cards(self, cards: tuple[TemplateCard, ...]) -> tuple[Path, ...]:
        """Write the bundled reference template cards into this new vault.

        Parameters
        ----------
        cards : tuple[TemplateCard, ...]
            Validated cards resolved for this creation, in title order.

        Returns
        -------
        tuple[pathlib.Path, ...]
            Absolute paths of the cards written, in creation order.

        Raises
        ------
        TemplateCardWriteError
            If a card cannot be written. The message names the failing card and
            the cards already written, which stay in place.
        """
        if not cards:
            return ()
        directory = self.templates_directory()
        written: list[Path] = []
        for card in cards:
            target = self.contained(directory / card.relative_path)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                afanes.core.atomic.write_text_atomic(target, card.text)
            except (OSError, VaultError) as exc:
                already = ", ".join(path.relative_to(self.root).as_posix() for path in written) or "none"
                message = (
                    f"Could not write template card {card.relative_path.as_posix()!r}; cards already written: {already}"
                )
                raise TemplateCardWriteError(message) from exc
            written.append(target)
        return tuple(written)

    @staticmethod
    def _missing_directories(start: Path) -> tuple[Path, ...]:
        """Return the missing ancestor directories of ``start``, outermost first."""
        missing: list[Path] = []
        current = start
        while not current.exists():
            missing.append(current)
            parent = current.parent
            if parent == current:
                break
            current = parent
        return tuple(reversed(missing))

    def _seed_layout(self) -> tuple[Path, ...]:
        """Create the default folders and return the ones that were made."""
        destinations = [
            self.directory_for(NoteType.NOTE),
            self.existing_directory(self.root, TRASH_DIRECTORY),
            self.directory_for(NoteType.REFERENCE),
            self.directory_for(NoteType.PROJECT),
            self.existing_directory(self.root, LOG_DIRECTORY),
        ]
        created: list[Path] = []
        for destination in destinations:
            if destination.is_dir():
                continue
            destination.mkdir(parents=True, exist_ok=True)
            created.append(destination)
        return tuple(created)

    def contained(self, candidate: Path) -> Path:
        """Resolve a path and verify that it stays inside this vault.

        Parameters
        ----------
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
        resolved = candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
        if not resolved.is_relative_to(self.root):
            message = f"Path escapes the vault: {candidate}"
            raise VaultPathError(message)
        return resolved

    def scan(self) -> VaultSnapshot:
        """Scan this vault without writing anything.

        Returns
        -------
        VaultSnapshot
            Parsed notes, failures, and the resulting name catalog.

        Notes
        -----
        Files are visited in deterministic path order. Directories whose names
        begin with a dot are skipped, as are symlinks that resolve outside the
        vault. A malformed note becomes a ``VaultFailure`` and does not abort
        the scan. This method performs blocking file I/O and never writes.
        """
        return self._scan()

    def scan_fingerprint(self) -> tuple[tuple[str, int, int], ...]:
        """Return a cheap change fingerprint for the files a scan would parse.

        Returns
        -------
        tuple[tuple[str, int, int], ...]
            One ``(vault-relative path, mtime_ns, size)`` entry per note file,
            in deterministic path order. The tuple is empty for a vault with no
            notes.

        Notes
        -----
        The walk is the same one :meth:`scan` uses, so ``trash/`` and hidden
        directories are excluded and the path policy stays in one place. Only
        filesystem metadata is read; no note is opened, parsed, or written.
        A file that cannot be stat'ed is skipped so a single unreadable entry
        cannot stall every refresh tick. Callers treat any change to the tuple
        as a reason to rescan, not as proof that the content is different.
        """
        entries: list[tuple[str, int, int]] = []
        for note_path in self._note_paths():
            try:
                stat = note_path.path.stat()
            except OSError:
                continue
            entries.append((note_path.relative_path.as_posix(), stat.st_mtime_ns, stat.st_size))
        return tuple(entries)

    def _scan(self) -> VaultSnapshot:
        """Scan this vault's notes and build the name catalog."""
        notes: list[VaultNote] = []
        failures: list[VaultFailure] = []
        reader = afanes.core.links.ReferenceReader()

        for note_path in self._note_paths():
            try:
                notes.append(Vault._read_note(note_path, reader))
            except (OSError, UnicodeDecodeError, AfanesError) as exc:
                failures.append(VaultFailure(path=note_path.relative_path, message=str(exc)))

        catalog = NameCatalog.from_entries(CatalogEntry(path=note.path, note_type=note.note_type) for note in notes)
        return VaultSnapshot(
            root=self.root,
            notes=tuple(notes),
            failures=tuple(failures),
            catalog=catalog,
            fingerprint=self.scan_fingerprint(),
        )

    def _note_paths(self) -> list[NotePath]:
        """Return note paths and their vault-relative paths in deterministic order."""
        paths: list[NotePath] = []
        excluded = {TRASH_DIRECTORY.name.casefold(), TEMPLATES_DIRECTORY.name.casefold()}
        for path in sorted(self.root.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(self.root)
            if relative.parts and relative.parts[0].casefold() in excluded:
                continue
            if any(part.startswith(".") for part in relative.parts[:-1]):
                continue
            if path.suffix.casefold() != NOTE_SUFFIX or not path.is_file():
                continue
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if not resolved.is_relative_to(self.root):
                continue
            paths.append(NotePath(path=path, relative_path=relative))
        return paths

    @staticmethod
    def _read_note(
        note_path: NotePath,
        reader: afanes.core.links.ReferenceReader,
    ) -> VaultNote:
        """Read and parse one note, raising on malformed input."""
        stat = note_path.path.stat()
        data = note_path.path.read_bytes()
        text = data.decode("utf-8")
        document = NoteDocument.from_text(text)
        if document.note_type is None:
            message = "Note has no type"
            raise NoteParseError(message)
        body_references = tuple(reader.extract(document.body))
        steps: tuple[afanes.models.step.ProjectStep, ...] = ()
        search_text = document.body
        if document.note_type is NoteType.PROJECT:
            step_document = afanes.core.steps.StepDocument(document.body)
            steps = step_document.steps
            search_text = step_document.search_text
        role_names = [name for name in (document.owner, document.asked_by) if name is not None]
        for step in steps:
            role_names.extend(step.owners)
        if role_names:
            search_text = "\n".join((search_text, *role_names))
        return VaultNote(
            path=note_path.path,
            relative_path=note_path.relative_path,
            name=note_path.path.stem,
            title=document.title or note_path.path.stem,
            note_type=document.note_type,
            category=document.category,
            status=document.status,
            due_date=document.due_date,
            date=document.date,
            content_hash=hashlib.sha256(data).hexdigest(),
            modified_ns=stat.st_mtime_ns,
            body_references=body_references,
            steps=steps,
            search_text=search_text,
            asked_by=document.asked_by,
            owner=document.owner,
        )

    def directory_for(self, note_type: NoteType, category: CategoryLabel | None = None) -> Path:
        """Return the default destination directory for a note kind.

        Parameters
        ----------
        note_type : NoteType
            Type of the note to file.
        category : CategoryLabel | None
            Reference category. Only valid when ``note_type`` is
            :attr:`afanes.models.note.NoteType.REFERENCE`; ``None`` files directly under
            ``reference/``.

        Returns
        -------
        Path
            Absolute default directory inside the vault. A categorized
            reference uses ``reference/<category-folder>/``, where the folder is
            derived through the cross-platform name policy. An existing
            directory whose name differs only by case is reused. The directory
            is not created by this method.

        Raises
        ------
        VaultError
            If a category is supplied for a non-reference note.
        """
        if category is not None and note_type is not NoteType.REFERENCE:
            message = "Only reference notes can declare a category"
            raise VaultError(message)
        if note_type is NoteType.LOG:
            message = "Log directories are selected by date; use log_directory"
            raise VaultError(message)
        if note_type is NoteType.PROJECT:
            return self.existing_directory(self.root, PROJECTS_DIRECTORY)
        if note_type is NoteType.REFERENCE:
            reference_root = self.existing_directory(self.root, REFERENCE_DIRECTORY)
            if category is None:
                return reference_root
            folder = Path(afanes.core.names.NamePolicy.safe_filename(category.value))
            return self.existing_directory(reference_root, folder)
        return self.existing_directory(self.root, INBOX_DIRECTORY)

    def log_directory(self, date: NoteDate) -> Path:
        """Return the default destination directory for a log entry.

        Parameters
        ----------
        date : NoteDate
            Date whose precision selects the folder.

        Returns
        -------
        Path
            Absolute ``log/<year>/`` folder for a year-precision date, or
            ``log/<year>/<month>/`` for a month- or day-precision date. An
            existing case variant is reused. The directory is not created by
            this method.

        Notes
        -----
        The result is a convention, not a requirement. A log entry stored
        elsewhere still appears in the Log section because the note type, not
        the folder, selects the view.
        """
        log_root = self.existing_directory(self.root, LOG_DIRECTORY)
        year = self.existing_directory(log_root, Path(f"{date.year:04d}"))
        if date.precision is DatePrecision.YEAR:
            return year
        return self.existing_directory(year, Path(f"{date.month:02d}"))

    def templates_directory(self) -> Path:
        """Return the reference template card folder without creating it.

        Returns
        -------
        pathlib.Path
            Absolute ``templates/`` folder inside this vault. An existing
            directory whose name differs only by case is reused, following the
            same rule as every other layout directory.

        Notes
        -----
        Opening or scanning a vault never creates this folder. A missing folder
        is returned as its canonical path so a caller can decide whether to
        write into it.
        """
        return self.existing_directory(self.root, TEMPLATES_DIRECTORY)

    def read_body(self, note_path: Path) -> str:
        """Read a note and return its Markdown body without frontmatter.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to a note inside this vault.

        Returns
        -------
        str
            Markdown body with the frontmatter block removed.

        Raises
        ------
        VaultPathError
            If the path escapes the vault root.
        NoteParseError
            If the note's frontmatter is malformed.
        InvalidReferenceError
            If a frontmatter reference is invalid.

        Notes
        -----
        This method performs blocking file I/O and never writes.
        """
        source = self.contained(note_path)
        text = source.read_text(encoding="utf-8")
        return NoteDocument.from_text(text).body

    def read_page(self, note_path: Path) -> PageContent:
        """Read one note for viewing or editing without writing anything.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to a note inside this vault.

        Returns
        -------
        PageContent
            Raw text, content hash, parsed document, and any parse failure.

        Raises
        ------
        VaultPathError
            If the path escapes the vault root, does not exist, or is a
            directory.
        OSError
            If the file cannot be read.
        UnicodeError
            If the file is not valid UTF-8.

        Notes
        -----
        A note with malformed frontmatter is returned as an
        :class:`afanes.core.vault.snapshot.UnparsedPage` with a diagnostic in ``failure``. The raw text is
        preserved so the page can offer raw rescue mode. This method performs
        blocking file I/O and never writes.
        """
        source = self.contained(note_path)
        try:
            data = source.read_bytes()
        except FileNotFoundError as exc:
            message = f"Note does not exist: {note_path}"
            raise VaultPathError(message) from exc
        except IsADirectoryError as exc:
            message = f"Not a note file: {note_path}"
            raise VaultPathError(message) from exc

        text = data.decode("utf-8")
        content_hash = hashlib.sha256(data).hexdigest()
        relative_path = source.relative_to(self.root)
        file = PageFile(path=source, relative_path=relative_path, text=text, content_hash=content_hash)
        try:
            document = NoteDocument.from_text(text)
        except (NoteParseError, InvalidReferenceError) as exc:
            return UnparsedPage(file=file, failure=str(exc))
        if document.note_type is None:
            return UnparsedPage(file=file, failure="Note has no type")
        return ParsedPage(file=file, document=document)

    def create(
        self,
        title: str,
        note_type: NoteType,
        *,
        category: CategoryLabel | None = None,
        directory: Path | None = None,
        body: str = "",
        status: Status | None = None,
    ) -> Path:
        """Create a note whose sanitized filename stem becomes its identity.

        Parameters
        ----------
        title : str
            Name to sanitize into the identity filename. The new note's display
            title is derived separately from its body.
        note_type : NoteType
            Declared type for the new note.
        category : CategoryLabel | None
            Reference category. Only valid when ``note_type`` is
            :attr:`afanes.models.note.NoteType.REFERENCE`; ``None`` creates an uncategorized
            reference.
        directory : Path | None
            Vault-relative or absolute classification directory. Defaults to
            the layout destination for ``note_type`` and ``category``. Missing
            directories are created.
        body : str
            Initial Markdown body. New files use LF and UTF-8 without a BOM.
        status : Status | None
            Initial status value. ``None`` omits the ``status`` key entirely.

        Returns
        -------
        Path
            Absolute path to the created note.

        Raises
        ------
        NoteParseError
            If a category is supplied for a non-reference note.
        VaultPathError
            If the target directory escapes the vault.
        VaultError
            If the target path is not a directory.
        """
        if category is not None and note_type is not NoteType.REFERENCE:
            message = "Only reference notes can declare a category"
            raise NoteParseError(message)

        target_directory = (
            self.contained(self.directory_for(note_type, category)) if directory is None else self.contained(directory)
        )
        if target_directory.exists() and not target_directory.is_dir():
            message = f"Note directory is not a directory: {target_directory}"
            raise VaultError(message)
        target_directory.mkdir(parents=True, exist_ok=True)

        snapshot = self.scan()
        scheme = ReferenceScheme.for_note(note_type)
        taken = {note.name for note in snapshot.notes if ReferenceScheme.for_note(note.note_type) is scheme}
        taken.update(entry.stem for entry in target_directory.iterdir())
        taken.update(entry.name for entry in target_directory.iterdir())
        name = afanes.core.names.NamePolicy.unique(afanes.core.names.NamePolicy.safe_filename(title), taken)

        document = self.new_note_document(
            note_type,
            category,
            status,
            body,
            date=NoteDate.from_date(self.today()),
        )
        path = target_directory / f"{name}{NOTE_SUFFIX}"
        afanes.core.atomic.write_text_atomic(path, document.to_text())
        return path

    @classmethod
    def today(cls) -> datetime.date:
        """Return the calendar date stamped on a newly created note.

        Returns
        -------
        datetime.date
            Current local calendar date.

        Notes
        -----
        This class method is the single time source for note creation. Tests
        patch it to make a creation deterministic; application code never
        passes a clock object around.
        """
        return datetime.datetime.now(tz=datetime.UTC).astimezone().date()

    @staticmethod
    def new_note_document(
        note_type: NoteType,
        category: CategoryLabel | None,
        status: Status | None,
        body: str,
        *,
        date: NoteDate | None = None,
    ) -> NoteDocument:
        """Build the canonical document for a newly created note.

        Parameters
        ----------
        note_type : NoteType
            Declared type for the new note.
        category : CategoryLabel | None
            Reference category, or ``None`` when the note has no category.
        status : Status | None
            Initial workflow status, or ``None`` to omit the key.
        body : str
            Initial Markdown body. CRLF and a leading BOM are normalized.
        date : NoteDate | None
            Initial note date, or ``None`` to omit the key.

        Returns
        -------
        NoteDocument
            Canonical document ready to serialize.
        """
        normalized_body = body.replace("\r\n", "\n").replace("\r", "\n").removeprefix("\ufeff")
        labels = PageLabels(
            note_type=note_type,
            category=category,
            status=status,
            date_text="" if date is None else date.text,
        )
        document = NoteDocument(
            raw={},
            body=normalized_body,
            newline="\n",
            has_frontmatter=True,
            note_type=None,
        )
        return labels.apply_to(document)

    @staticmethod
    def existing_directory(parent: Path, name: Path) -> Path:
        """Return an existing case variant of a directory, or the canonical path."""
        candidate = parent / name
        if candidate.is_dir() or not parent.is_dir():
            return candidate
        folded = name.name.casefold()
        matches = sorted(
            (child for child in parent.iterdir() if child.is_dir() and child.name.casefold() == folded),
            key=lambda child: child.name,
        )
        return matches[0] if matches else candidate


@dataclasses.dataclass(frozen=True, slots=True)
class VaultCreation:
    """Directories and notes produced by one vault creation.

    Attributes
    ----------
    vault : Vault
        The created and seeded vault.
    created_directories : tuple[pathlib.Path, ...]
        Intermediate directories created for the vault path, outermost first.
        The vault root itself is not included.
    seeded_directories : tuple[pathlib.Path, ...]
        Default folders created inside the vault, in layout order.
    written_notes : tuple[pathlib.Path, ...]
        Notes written into the vault, guide first, in creation order.
    written_cards : tuple[pathlib.Path, ...]
        Reference template cards written into ``templates/``, in title order.
    template : str | None
        Template identifier used for the notes, or ``None`` for a vault without
        starter content.
    settings_file : pathlib.Path
        Settings file written before the default folders and starter content.
    """

    vault: Vault
    created_directories: tuple[Path, ...]
    seeded_directories: tuple[Path, ...]
    written_notes: tuple[Path, ...]
    written_cards: tuple[Path, ...]
    template: str | None
    settings_file: Path
