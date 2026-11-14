# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reminder dismissal writes.

The service records the shown occurrence in the note's ``handled`` key through
the page write guard. It never changes the body, status, or schedule.
"""

import dataclasses
import datetime
from pathlib import Path

from afanes.core.errors import DomainMessage, MessageCode, VaultError, VaultPathError
from afanes.core.frontmatter import NoteDocument
from afanes.core.labels import PageLabels
from afanes.core.vault.pages import VaultPages
from afanes.core.vault.service import Vault
from afanes.core.vault.snapshot import VaultSnapshot


@dataclasses.dataclass(frozen=True, slots=True)
class VaultReminders:
    """Dismiss one reminder occurrence inside a vault.

    Attributes
    ----------
    vault : Vault
        Resolved vault that owns path containment and atomic writes.
    """

    vault: Vault

    def dismiss(
        self,
        note_path: Path,
        occurrence: datetime.datetime,
        *,
        snapshot: VaultSnapshot | None = None,
    ) -> str:
        """Record one shown occurrence as handled.

        Parameters
        ----------
        note_path : Path
            Relative or absolute path to the reminder note.
        occurrence : datetime.datetime
            Timezone-aware occurrence shown on the card.
        snapshot : VaultSnapshot | None
            Pre-built scan that owns the expected content hash, or ``None`` to
            scan the vault.

        Returns
        -------
        str
            SHA-256 digest of the written bytes, for a later comparison.

        Raises
        ------
        VaultPathError
            If the path escapes the vault or is not a note file.
        VaultError
            If the note is not part of the snapshot or has no reminder.
        ContentChangedError
            If the file changed after the snapshot was taken.
        NoteParseError
            If the note cannot be parsed.
        OSError
            If the note cannot be read or written.

        Notes
        -----
        Only the ``reminder.handled`` key is written. Unknown keys, the body,
        the status, the cadence, the times, and the zone are preserved. The
        write uses the content-hash guard, so an external edit aborts the
        dismissal and leaves the reminder due.
        """
        source = self.vault.contained(note_path)
        if not source.is_file():
            message = DomainMessage.of(MessageCode.NOT_A_NOTE_FILE, path=str(note_path))
            raise VaultPathError(message)
        scan = snapshot or self.vault.scan()
        note = scan.find_note(source)
        if note is None:
            message = DomainMessage.of(MessageCode.NOTE_NOT_IN_VAULT, path=str(note_path))
            raise VaultError(message)
        document = NoteDocument.from_text(source.read_text(encoding="utf-8"))
        reminder = document.reminder
        if reminder is None:
            message = DomainMessage.of(MessageCode.REMINDER_MISSING)
            raise VaultError(message)
        labels = PageLabels.from_document(document).with_reminder(reminder.with_handled(occurrence))
        text = labels.apply_to(document).to_text()
        return VaultPages(self.vault).write_page(source, text, note.content_hash)
