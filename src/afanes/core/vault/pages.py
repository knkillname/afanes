# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Page capture, creation, editing writes, recovery, and status changes.

Every write rechecks the content hash captured by the caller before it replaces
a file. Path containment and the atomic write primitive stay on
:class:`afanes.core.vault.service.Vault`.
"""

import dataclasses
import hashlib
from pathlib import Path

import afanes.core.atomic
import afanes.core.names
from afanes.core.errors import (
    ContentChangedError,
    EmptyCaptureError,
    NameCollisionError,
    NoteParseError,
    VaultError,
    VaultPathError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.core.labels import PageLabels
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import VaultSnapshot
from afanes.models.link import ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status


@dataclasses.dataclass(frozen=True, slots=True)
class VaultPages:
    """Capture, create, edit, recover, and status-change notes.

    Attributes
    ----------
    vault : Vault
        Resolved vault that owns path containment and the storage layout.
    """

    vault: Vault

    def write_page(self, note_path: Path, text: str, expected_hash: str) -> str:
        """Write a note after confirming that its content is unchanged.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to an existing note inside this vault.
        text : str
            Complete file text to write. The caller owns the newline style; the
            text is written as provided.
        expected_hash : str
            SHA-256 digest of the content read before editing.

        Returns
        -------
        str
            SHA-256 digest of the written bytes, for the next comparison.

        Raises
        ------
        VaultPathError
            If the path escapes the vault, does not exist, or is a directory.
        ContentChangedError
            If the file's current content differs from ``expected_hash``.
        VaultError
            If the destination directory is missing or the atomic write fails.
        OSError
            If the file cannot be read.

        Notes
        -----
        The current file is read and hashed immediately before the atomic
        replace. A concurrent write between the check and the replace is not
        detected; this is accepted for the local single-writer application.
        Nothing is written when the hash does not match.
        """
        source = self.vault.contained(note_path)
        try:
            data = source.read_bytes()
        except FileNotFoundError as exc:
            message = f"Note does not exist: {note_path}"
            raise VaultPathError(message) from exc
        except IsADirectoryError as exc:
            message = f"Not a note file: {note_path}"
            raise VaultPathError(message) from exc

        if hashlib.sha256(data).hexdigest() != expected_hash:
            message = f"Note changed on disk: {note_path}"
            raise ContentChangedError(message)

        afanes.core.atomic.AtomicWriter.write_text_atomic(source, text)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def create_page(
        self,
        reference_name: str,
        note_type: NoteType,
        category: CategoryLabel | None = None,
        *,
        body: str = "",
        text: str | None = None,
    ) -> Path:
        """Create a note under its exact name, without adding a suffix.

        Parameters
        ----------
        reference_name : str
            Name from the reference that requested the page. It is sanitized
            into the identity filename.
        note_type : NoteType
            Declared type for the new note.
        category : CategoryLabel | None
            Reference category. Only valid when ``note_type`` is
            :attr:`afanes.models.note.NoteType.REFERENCE`; ``None`` creates an uncategorized
            reference.
        body : str
            Initial Markdown body used when ``text`` is ``None``.
        text : str | None
            Complete note text to write exactly. When supplied, it takes
            precedence over ``body`` and must declare the requested type and
            category.

        Returns
        -------
        Path
            Absolute path to the created note.

        Raises
        ------
        NoteParseError
            If a category is supplied for a non-reference note, ``text`` does
            not parse, or ``text`` declares a different type or category.
        NameCollisionError
            If the exact name already belongs to a note in the same scheme or
            the target filename exists, including a case-insensitive sibling.
        VaultPathError
            If the target directory escapes the vault.
        VaultError
            If the target path is not a directory or the write fails.

        Notes
        -----
        Unlike :meth:`afanes.core.vault.service.Vault.create`, this method never changes the requested name. It
        is used for pages created from unresolved links, where a suffix would
        leave the link unresolved. Collision checks run before the destination
        directory is created and before any file is written.
        """
        if category is not None and note_type is not NoteType.REFERENCE:
            message = "Only reference notes can declare a category"
            raise NoteParseError(message)

        content: str
        if text is None:
            content = self.vault.new_note_document(
                note_type,
                category,
                None,
                body,
                date=NoteDate.from_date(self.vault.today()),
            ).to_text()
        else:
            parsed = NoteDocument.from_text(text)
            if parsed.note_type is not note_type or parsed.category != category:
                message = "Note text does not match the requested type and category"
                raise NoteParseError(message)
            if parsed.date is None and parsed.date_error is None:
                labels = PageLabels.from_document(parsed).with_date_text(NoteDate.from_date(self.vault.today()).text)
                parsed = labels.apply_to(parsed)
                text = parsed.to_text()
            content = text

        target_directory = self.vault.contained(self.vault.directory_for(note_type, category))
        if target_directory.exists() and not target_directory.is_dir():
            message = f"Note directory is not a directory: {target_directory}"
            raise VaultError(message)

        name = afanes.core.names.NamePolicy.safe_filename(reference_name)
        scheme = ReferenceScheme.for_note(note_type)
        snapshot = self.vault.scan()
        if snapshot.catalog.candidates(scheme, name):
            message = f"A {scheme.value} note named {name!r} already exists"
            raise NameCollisionError(message)

        target = target_directory / f"{name}{afanes.core.vault.snapshot.NOTE_SUFFIX}"
        folded_name = target.name.casefold()
        if target_directory.is_dir() and any(
            child.name.casefold() == folded_name for child in target_directory.iterdir()
        ):
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)

        target_directory.mkdir(parents=True, exist_ok=True)
        afanes.core.atomic.AtomicWriter.write_text_atomic(target, content)
        return target

    def create_log_entry(
        self,
        date: NoteDate,
        title: str,
        scaffold: str | None = None,
    ) -> Path:
        """Create a dated log entry under its ISO date name.

        Parameters
        ----------
        date : NoteDate
            Entry date. Its precision selects the filename and folder.
        title : str
            Display title written as the level-1 heading. It is trimmed and
            must not be blank.
        scaffold : str | None
            Starter body from a log card, or ``None`` for an empty entry.

        Returns
        -------
        Path
            Absolute path to the created note.

        Raises
        ------
        NoteParseError
            If the title is blank.
        NameCollisionError
            If another log entry already uses the date or the target file
            exists.
        VaultPathError
            If the target directory escapes the vault.
        VaultError
            If the target path is not a directory or the write fails.

        Notes
        -----
        The entry declares only ``type: log`` and ``date``. The starter body is
        placed below the title heading. The caller opens the returned page in
        edit mode.
        """
        display_title = title.strip()
        if not display_title:
            message = "A log entry needs a title"
            raise NoteParseError(message)
        starter = (scaffold or "").strip("\r\n")
        body = f"# {display_title}\n"
        if starter:
            body = f"{body}\n{starter}\n"

        snapshot = self.vault.scan()
        if snapshot.log_entry(date) is not None:
            message = f"A log entry already exists for {date.text}"
            raise NameCollisionError(message)

        target_directory = self.vault.contained(self.vault.log_directory(date))
        if target_directory.exists() and not target_directory.is_dir():
            message = f"Note directory is not a directory: {target_directory}"
            raise VaultError(message)
        target = target_directory / f"{date.text}{afanes.core.vault.snapshot.NOTE_SUFFIX}"
        if target.exists():
            message = f"Destination already exists: {target}"
            raise NameCollisionError(message)

        content = self.vault.new_note_document(
            NoteType.LOG,
            None,
            None,
            body,
            date=date,
        ).to_text()
        target_directory.mkdir(parents=True, exist_ok=True)
        afanes.core.atomic.AtomicWriter.write_text_atomic(target, content)
        return target

    def set_status(
        self,
        note_path: Path,
        status: Status | None,
        *,
        snapshot: VaultSnapshot | None = None,
        confirm: bool = False,
    ) -> str:
        """Change one note's workflow status without touching its body.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to an existing note inside this vault.
        status : Status | None
            New status, or ``None`` to remove the key.
        snapshot : VaultSnapshot | None
            Pre-built scan to avoid rescanning, or ``None`` to scan the vault.
        confirm : bool
            Explicit confirmation gate. The operation raises unless this is
            ``True``.

        Returns
        -------
        str
            SHA-256 digest of the written bytes, for a later comparison.

        Raises
        ------
        VaultError
            If confirmation is missing, the note is not part of the vault, or
            the destination directory is missing.
        VaultPathError
            If the path escapes the vault or is not a note file.
        ContentChangedError
            If the file changed after the supplied snapshot was taken.
        NoteParseError
            If the current note cannot be parsed or the status is not valid
            for its type.

        Notes
        -----
        Only the ``status`` key is modified. Unknown keys, the body, and the
        newline style are preserved, and the write is atomic.
        """
        if not confirm:
            message = "Changing a status requires explicit confirmation"
            raise VaultError(message)

        source = self.vault.contained(note_path)
        if not source.is_file() or source.suffix.casefold() != afanes.core.vault.snapshot.NOTE_SUFFIX:
            message = f"Not a note file: {note_path}"
            raise VaultPathError(message)
        vault = snapshot or self.vault.scan()
        note = vault.find_note(source)
        if note is None:
            message = f"Note is not part of the vault: {note_path}"
            raise VaultError(message)
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != note.content_hash:
            message = f"Note changed on disk: {note_path}"
            raise ContentChangedError(message)

        document = NoteDocument.from_text(data.decode("utf-8"))
        labels = dataclasses.replace(PageLabels.from_document(document), status=status)
        text = labels.apply_to(document).to_text()
        afanes.core.atomic.AtomicWriter.write_text_atomic(source, text)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def recreate_page(self, note_path: Path, text: str) -> str:
        """Recreate a note that disappeared after it was read for editing.

        Parameters
        ----------
        note_path : Path
            Original relative or absolute path of the missing note.
        text : str
            Complete text to write. It is written as provided and is not
            parsed, so a raw rescue draft can be recreated as typed.

        Returns
        -------
        str
            SHA-256 digest of the written bytes.

        Raises
        ------
        VaultPathError
            If the path escapes the vault.
        ContentChangedError
            If a file already exists at the path.
        VaultError
            If the destination directory is missing or the write fails.

        Notes
        -----
        This is an explicit recovery action, not a normal save: the caller has
        confirmed that the draft should replace the missing file. It never
        overwrites an existing file.
        """
        source = self.vault.contained(note_path)
        if source.exists():
            message = f"Note already exists: {note_path}"
            raise ContentChangedError(message)
        if not source.parent.is_dir():
            message = f"Destination directory does not exist: {source.parent}"
            raise VaultError(message)
        afanes.core.atomic.AtomicWriter.write_text_atomic(source, text)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def capture(self, text: str) -> Path:
        """Capture raw text as an unclassified note in this vault's inbox.

        Parameters
        ----------
        text : str
            Captured thought. The first non-blank line becomes the filename
            stem and receives a level-1 heading marker in the body.

        Returns
        -------
        Path
            Absolute path to the created note.

        Raises
        ------
        EmptyCaptureError
            If ``text`` contains no non-blank line.
        VaultPathError
            If the inbox directory escapes the vault.
        VaultError
            If the inbox path is not a directory or the note cannot be written.

        Notes
        -----
        The complete text becomes the Markdown body. ``# `` is inserted at the
        start of the first non-blank line unless its first non-whitespace
        character is already ``#``. All other text, including leading blank
        lines, is preserved. The note declares only ``type: note``; no status,
        project, people, due date, or references are inferred. The inbox
        directory is created on demand. This method performs blocking file I/O.
        """
        lines = text.splitlines(keepends=True)
        first_index = next((index for index, line in enumerate(lines) if line.strip()), None)
        if first_index is None:
            message = "A captured thought must contain text"
            raise EmptyCaptureError(message)
        first_line = lines[first_index]
        body_lines = list(lines)
        if not first_line.lstrip().startswith("#"):
            body_lines[first_index] = f"# {first_line}"
        return self.vault.create(
            first_line,
            NoteType.NOTE,
            body="".join(body_lines),
            status=None,
        )
