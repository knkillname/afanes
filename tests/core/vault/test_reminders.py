"""Tests for reminder dismissal writes."""

import datetime
import hashlib
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.vault.reminders
import afanes.core.vault.service
from afanes.core.errors import ContentChangedError, VaultError
from afanes.core.frontmatter import NoteDocument
from afanes.models.note import Status

OCCURRENCE = datetime.datetime(2026, 11, 14, 15, 0, tzinfo=datetime.UTC)


def _write_reminder(root: Path, name: str = "Ada.md", *, status: str | None = None) -> Path:
    path = root / "reference" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", "type: project" if status is not None else "type: reference"]
    if status is not None:
        lines.append(f"status: {status}")
    lines.extend(
        [
            "reminder:",
            "  zone: America/Mexico_City",
            "  recurrence:",
            "    kind: daily",
            '    times: ["09:00"]',
            "  label: keep",
            "---",
            "",
            "# Ada",
            "",
            "Body.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


class TestDismiss:
    def test_records_handled_without_changing_the_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_reminder(root, status="active")
        before = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert before.reminder is not None
        vault = afanes.core.vault.service.Vault(root)
        snapshot = vault.scan()

        digest = afanes.core.vault.reminders.VaultReminders(vault).dismiss(
            path,
            OCCURRENCE,
            snapshot=snapshot,
        )

        after = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert after.reminder is not None
        assert after.reminder.handled == OCCURRENCE
        assert after.body == before.body
        assert after.status is Status.ACTIVE
        assert after.reminder.schedule == before.reminder.schedule
        assert digest == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_preserves_unknown_nested_keys(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_reminder(root)
        vault = afanes.core.vault.service.Vault(root)

        afanes.core.vault.reminders.VaultReminders(vault).dismiss(
            path,
            OCCURRENCE,
            snapshot=vault.scan(),
        )

        after = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert after.reminder is not None
        assert dict(after.reminder.extra) == {"label": "keep"}

    def test_a_changed_file_aborts_the_dismissal(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_reminder(root)
        vault = afanes.core.vault.service.Vault(root)
        snapshot = vault.scan()
        path.write_text(path.read_text(encoding="utf-8") + "\nExternal.\n", encoding="utf-8")

        with pytest.raises(ContentChangedError):
            afanes.core.vault.reminders.VaultReminders(vault).dismiss(
                path,
                OCCURRENCE,
                snapshot=snapshot,
            )

        assert "handled" not in path.read_text(encoding="utf-8")

    def test_a_missing_reminder_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = root / "reference" / "Ada.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\ntype: reference\n---\n\n# Ada\n", encoding="utf-8")
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultError, match="reminder-missing"):
            afanes.core.vault.reminders.VaultReminders(vault).dismiss(
                path,
                OCCURRENCE,
                snapshot=vault.scan(),
            )

    def test_a_failed_write_leaves_the_reminder_due(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "vault"
        path = _write_reminder(root)
        vault = afanes.core.vault.service.Vault(root)
        snapshot = vault.scan()

        def fail_write(_path: Path, _text: str) -> None:
            message = "permission denied"
            raise PermissionError(message)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", fail_write)
        with pytest.raises(PermissionError):
            afanes.core.vault.reminders.VaultReminders(vault).dismiss(
                path,
                OCCURRENCE,
                snapshot=snapshot,
            )

        assert "handled" not in path.read_text(encoding="utf-8")
