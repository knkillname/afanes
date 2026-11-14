"""Tests for durable trash metadata, catalog, writes, restore, and retention."""

import datetime
import hashlib
import uuid
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.vault.naming
import afanes.core.vault.service
import afanes.core.vault.trash
import afanes.core.vault.trash_catalog
import afanes.core.vault.trash_metadata
from afanes.core.errors import (
    ContentChangedError,
    NameCollisionError,
    NoteParseError,
    VaultError,
)
from afanes.core.vault.naming_reports import TrashPreview
from afanes.core.vault.trash_catalog import TrashEntry
from afanes.core.vault.trash_metadata import (
    TrashDocument,
    TrashMetadata,
)

TODAY = datetime.date(2026, 11, 13)
THIRTY_DAYS = 30


def _write_note(
    path: Path,
    note_type: str = "note",
    body: str = "# Note\n",
    *,
    extra: str = "",
    newline: str = "\n",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"---{newline}type: {note_type}{newline}{extra}{newline}---{newline}{newline}{body}"
    path.write_text(text, encoding="utf-8", newline="")
    return path


def _vault(root: Path) -> afanes.core.vault.service.Vault:
    root.mkdir(parents=True, exist_ok=True)
    (root / "afanes.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    return afanes.core.vault.service.Vault.open(root)


def _trash_file(root: Path, name: str, text: str) -> Path:
    path = root / "trash" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    return path


class TestTrashMetadata:
    def test_round_trip_preserves_body_unknown_keys_and_order(self) -> None:
        text = "---\ntype: project\nowner: Ada\ncustom: keep\ntrashed_on: 2026-01-01\n---\n\n# Build\n"
        document = TrashDocument.from_text(text)
        metadata = TrashMetadata(birthplace=Path("projects/Build.md"), trashed_on=TODAY)

        written = TrashDocument.from_text(document.with_metadata(metadata))

        assert written.raw["owner"] == "Ada"
        assert written.raw["custom"] == "keep"
        assert list(written.raw) == ["type", "owner", "custom", "trashed_on", "trashed_from"]
        assert written.body == "\n# Build\n"
        assert written.metadata == metadata

    def test_round_trip_preserves_crlf(self) -> None:
        text = "---\r\ntype: note\r\n---\r\n\r\n# Ada\r\n"
        document = TrashDocument.from_text(text)
        metadata = TrashMetadata(birthplace=Path("inbox/Ada.md"), trashed_on=TODAY)

        written = document.with_metadata(metadata)

        assert "\r\n" in written
        assert "\n" not in written.replace("\r\n", "")
        assert TrashDocument.from_text(written).metadata == metadata

    def test_without_metadata_removes_only_the_trash_keys(self) -> None:
        text = (
            "---\ntype: reference\ncategory: person\ntrashed_from: reference/Ada.md\n"
            "trashed_on: 2026-11-13\ncustom: keep\n---\n\n# Ada\n"
        )
        document = TrashDocument.from_text(text)

        restored = TrashDocument.from_text(document.without_metadata())

        assert "trashed_from" not in restored.raw
        assert "trashed_on" not in restored.raw
        assert restored.raw["category"] == "person"
        assert restored.raw["custom"] == "keep"
        assert restored.body == "\n# Ada\n"

    def test_a_document_without_the_keys_is_unchanged(self) -> None:
        text = "---\ntype: note\n---\n\n# Ada\n"

        assert TrashDocument.from_text(text).without_metadata() == text

    def test_missing_birthplace_is_unmanaged(self) -> None:
        raw: dict[str, object] = {"type": "note", "trashed_on": TODAY}

        assert TrashMetadata.from_raw(raw) is None

    @pytest.mark.parametrize(
        "birthplace",
        [
            "/outside/Ada.md",
            "~/Ada.md",
            "../Outside.md",
            "inbox/../../Outside.md",
            "trash/Ada.md",
            "Trash/Ada.md",
            "templates/Ada.md",
            ".hidden/Ada.md",
            "inbox/.Ada.md",
            "inbox/Ada.txt",
            "C:/Ada.md",
            "inbox/CON.md",
        ],
    )
    def test_unsafe_birthplaces_are_unmanaged(self, birthplace: str) -> None:
        assert TrashMetadata.from_raw({"trashed_from": birthplace}) is None

    def test_missing_day_is_kept_as_none(self) -> None:
        metadata = TrashMetadata.from_raw({"trashed_from": "inbox/Ada.md"})

        assert metadata is not None
        assert metadata.trashed_on is None

    @pytest.mark.parametrize("value", ["not-a-date", True, 20260101, "2026-13-01"])
    def test_malformed_day_is_unusable(self, value: object) -> None:
        metadata = TrashMetadata.from_raw({"trashed_from": "inbox/Ada.md", "trashed_on": value})

        assert metadata is not None
        assert metadata.trashed_on is None

    def test_iso_day_string_is_accepted(self) -> None:
        metadata = TrashMetadata.from_raw({"trashed_from": "inbox/Ada.md", "trashed_on": "2026-11-13"})

        assert metadata is not None
        assert metadata.trashed_on == TODAY

    def test_expiry_boundary(self) -> None:
        metadata = TrashMetadata(birthplace=Path("inbox/Ada.md"), trashed_on=TODAY)

        assert not metadata.is_expired(TODAY + datetime.timedelta(days=29))
        assert metadata.is_expired(TODAY + datetime.timedelta(days=30))

    def test_unclosed_frontmatter_raises(self) -> None:
        with pytest.raises(NoteParseError):
            TrashDocument.from_text("---\ntype: note\n")


class TestTrashCatalog:
    def test_lists_managed_entries_with_title_and_birthplace(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        trash = root / "trash"
        trash.mkdir()
        entry = trash / f"{uuid.uuid4()}.md"
        entry.write_text(
            "---\ntype: project\ntrashed_from: projects/Build shed.md\ntrashed_on: 2026-11-13\n---\n\n# Build a shed\n",
            encoding="utf-8",
        )

        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        assert snapshot.count == 1
        assert snapshot.entries[0].title == "Build a shed"
        assert snapshot.entries[0].birthplace == Path("projects/Build shed.md")
        assert snapshot.entries[0].trashed_on == TODAY

    def test_title_falls_back_to_birthplace_stem(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        _trash_file(
            root,
            f"{uuid.uuid4()}.md",
            "---\ntype: note\ntrashed_from: inbox/Buy milk.md\n---\n\nNo heading\n",
        )

        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        assert snapshot.entries[0].title == "Buy milk"

    def test_unmanaged_files_are_hidden(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        _trash_file(root, f"{uuid.uuid4()}.md", "---\ntype: note\n---\n\n# Legacy\n")
        _trash_file(root, "Legacy named.md", "---\ntype: note\ntrashed_from: templates/Old.md\n---\n\n# Old\n")

        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        assert snapshot.count == 0

    @pytest.mark.parametrize(
        "birthplace",
        ["../Outside.md", "trash/Ada.md", "templates/Ada.md", ".hidden/Ada.md"],
    )
    def test_unsafe_birthplaces_are_hidden(self, tmp_path: Path, birthplace: str) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        _trash_file(
            root,
            f"{uuid.uuid4()}.md",
            f"---\ntype: note\ntrashed_from: {birthplace}\n---\n\n# Hidden\n",
        )

        assert afanes.core.vault.trash_catalog.TrashCatalog(vault).load().count == 0

    def test_symlinks_are_hidden(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        outside = tmp_path / "outside.md"
        outside.write_text(
            "---\ntype: note\ntrashed_from: inbox/Outside.md\n---\n\n# Outside\n",
            encoding="utf-8",
        )
        trash = root / "trash"
        trash.mkdir()
        (trash / f"{uuid.uuid4()}.md").symlink_to(outside)

        assert afanes.core.vault.trash_catalog.TrashCatalog(vault).load().count == 0

    def test_a_missing_trash_folder_is_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)

        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        assert snapshot.count == 0
        assert snapshot.fingerprint == ()

    def test_entries_are_sorted_by_title_then_birthplace(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        _trash_file(root, "a.md", "---\ntype: note\ntrashed_from: inbox/Zeta.md\n---\n\n# Alpha\n")
        _trash_file(root, "b.md", "---\ntype: note\ntrashed_from: inbox/Alpha.md\n---\n\n# Alpha\n")
        _trash_file(root, "c.md", "---\ntype: note\ntrashed_from: inbox/Middle.md\n---\n\n# Beta\n")

        entries = afanes.core.vault.trash_catalog.TrashCatalog(vault).load().entries

        assert [entry.birthplace_text for entry in entries] == ["inbox/Alpha.md", "inbox/Zeta.md", "inbox/Middle.md"]

    def test_fingerprint_is_stable_until_a_file_changes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        path = _trash_file(
            root,
            f"{uuid.uuid4()}.md",
            "---\ntype: note\ntrashed_from: inbox/Ada.md\n---\n\n# Ada\n",
        )
        catalog = afanes.core.vault.trash_catalog.TrashCatalog(vault)

        first = catalog.fingerprint()
        second = catalog.fingerprint()
        path.write_text(path.read_text(encoding="utf-8") + "more\n", encoding="utf-8")

        assert first == second
        assert catalog.fingerprint() != first

    def test_search_matches_title_birthplace_and_body(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        _trash_file(
            root,
            f"{uuid.uuid4()}.md",
            "---\ntype: note\ntrashed_from: projects/Build shed.md\n---\n\n# Timber frame\n\nCedar boards\n",
        )
        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        assert snapshot.search("timber")[0].title == "Timber frame"
        assert snapshot.search("shed")[0].birthplace_text == "projects/Build shed.md"
        assert snapshot.search("cedar")[0].title == "Timber frame"
        assert snapshot.search("  CEDAR  ")[0].title == "Timber frame"
        assert snapshot.search("missing") == ()

    def test_search_ignores_unmanaged_files(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        _trash_file(root, f"{uuid.uuid4()}.md", "---\ntype: note\n---\n\n# Unmanaged cedar\n")

        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        assert snapshot.search("cedar") == ()


class TestTrashWrite:
    def test_moves_to_a_uuid_path_and_records_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "projects" / "Build shed.md", "project", "# Build shed\n", extra="owner: Ada\n")
        service = afanes.core.vault.trash.TrashService(vault)

        preview = service.trash(note, confirm=True, today=TODAY)

        assert preview.trash_path.parent == root / "trash"
        uuid.UUID(preview.trash_path.stem)
        document = TrashDocument.from_text(preview.trash_path.read_text(encoding="utf-8"))
        assert document.metadata is not None
        assert document.metadata.birthplace == Path("projects/Build shed.md")
        assert document.metadata.trashed_on == TODAY
        assert document.raw["owner"] == "Ada"
        assert document.body == "\n# Build shed\n"
        assert not note.exists()

    def test_plan_reports_an_unused_uuid_path(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md")
        service = afanes.core.vault.trash.TrashService(vault)

        first = service.plan_trash(note, today=TODAY)
        second = service.plan_trash(note, today=TODAY)

        assert first.trash_path != second.trash_path
        assert not first.trash_path.exists()
        assert not second.trash_path.exists()

    def test_a_taken_uuid_is_not_overwritten(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md")
        service = afanes.core.vault.trash.TrashService(vault)
        preview = service.plan_trash(note, today=TODAY)
        preview.trash_path.parent.mkdir(parents=True)
        preview.trash_path.write_text("---\ntype: note\n---\n\n# Existing\n", encoding="utf-8")

        def plan(*_args: object, **_kwargs: object) -> TrashPreview:
            return preview

        monkeypatch.setattr(afanes.core.vault.trash.TrashService, "plan_trash", plan)

        applied = service.trash(note, confirm=True)

        assert applied.trash_path != preview.trash_path
        assert preview.trash_path.read_text(encoding="utf-8") == "---\ntype: note\n---\n\n# Existing\n"

    def test_a_changed_source_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md")
        service = afanes.core.vault.trash.TrashService(vault)
        snapshot = vault.scan()
        note.write_text("---\ntype: note\n---\n\n# Changed\n", encoding="utf-8")

        with pytest.raises(ContentChangedError):
            service.trash(note, confirm=True, snapshot=snapshot)

        assert note.exists()

    def test_an_unwritable_note_keeps_its_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md")

        message = "read only"

        def fail(*_args: object, **_kwargs: object) -> None:
            raise OSError(message)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", fail)

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).trash(note, confirm=True)

        assert note.exists()
        assert note.read_text(encoding="utf-8").startswith("---\ntype: note\n")

    def test_a_rename_failure_restores_the_original_text(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md")
        original = note.read_text(encoding="utf-8")

        message = "rename failed"

        def fail_replace(self: Path, _target: Path) -> None:
            if self == note:
                raise OSError(message)
            raise AssertionError(message)

        monkeypatch.setattr(Path, "replace", fail_replace)

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).trash(note, confirm=True)

        assert note.exists()
        assert note.read_text(encoding="utf-8") == original


class TestTrashRestore:
    def _trashed(self, tmp_path: Path) -> tuple[afanes.core.vault.service.Vault, Path, TrashPreview]:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(
            root / "projects" / "Build shed.md",
            "project",
            "# Build shed\n",
            extra="owner: Ada\ncustom: keep\n",
        )
        service = afanes.core.vault.trash.TrashService(vault)
        preview = service.trash(note, confirm=True, today=TODAY)
        return vault, preview.trash_path, preview

    def test_restore_returns_to_the_birthplace_and_removes_metadata(self, tmp_path: Path) -> None:
        vault, trash_path, preview = self._trashed(tmp_path)
        entry = afanes.core.vault.trash_catalog.TrashCatalog(vault).load().entries[0]

        restored = afanes.core.vault.trash.TrashService(vault).restore_entry(entry, confirm=True)

        assert restored == tmp_path / "vault" / "projects" / "Build shed.md"
        assert not trash_path.exists()
        document = TrashDocument.from_text(restored.read_text(encoding="utf-8"))
        assert document.metadata is None
        assert document.raw["owner"] == "Ada"
        assert document.raw["custom"] == "keep"
        assert preview.trash_path.exists() is False

    def test_restore_creates_missing_parents(self, tmp_path: Path) -> None:
        vault, _trash_path, preview = self._trashed(tmp_path)
        preview.note_path.parent.rmdir()

        restored = afanes.core.vault.trash.TrashService(vault).restore(preview, confirm=True)

        assert restored.parent.is_dir()
        assert restored.is_file()

    def test_restore_preserves_crlf(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md", newline="\r\n")
        service = afanes.core.vault.trash.TrashService(vault)
        preview = service.trash(note, confirm=True, today=TODAY)

        restored = service.restore(preview, confirm=True)

        assert b"\r\n" in restored.read_bytes()
        assert restored.read_bytes().decode("utf-8").replace("\r\n", "\n") == "---\ntype: note\n---\n\n# Note\n"

    def test_an_occupied_birthplace_requires_overwrite_permission(self, tmp_path: Path) -> None:
        vault, trash_path, preview = self._trashed(tmp_path)
        preview.note_path.write_text("---\ntype: project\n---\n\n# Occupant\n", encoding="utf-8")
        trashed = trash_path.read_bytes()

        with pytest.raises(NameCollisionError):
            afanes.core.vault.trash.TrashService(vault).restore(preview, confirm=True)

        assert preview.note_path.read_text(encoding="utf-8") == "---\ntype: project\n---\n\n# Occupant\n"
        assert trash_path.read_bytes() == trashed

    def test_confirmed_restore_overwrites_the_occupant(self, tmp_path: Path) -> None:
        vault, trash_path, preview = self._trashed(tmp_path)
        preview.note_path.write_text("---\ntype: project\n---\n\n# Occupant\n", encoding="utf-8")

        restored = afanes.core.vault.trash.TrashService(vault).restore(preview, confirm=True, overwrite=True)

        assert restored.read_text(encoding="utf-8").endswith("# Build shed\n")
        assert "# Occupant" not in restored.read_text(encoding="utf-8")
        assert not trash_path.exists()

    def test_a_directory_is_not_overwritten(self, tmp_path: Path) -> None:
        vault, trash_path, preview = self._trashed(tmp_path)
        preview.note_path.mkdir()

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).restore(preview, confirm=True, overwrite=True)

        assert preview.note_path.is_dir()
        assert trash_path.is_file()

    def test_a_birthplace_symlink_is_not_followed(self, tmp_path: Path) -> None:
        vault, trash_path, preview = self._trashed(tmp_path)
        outside = tmp_path / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        preview.note_path.symlink_to(outside)

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).restore(preview, confirm=True, overwrite=True)

        assert outside.read_text(encoding="utf-8") == "outside"
        assert trash_path.is_file()

    def test_a_missing_trash_file_is_reported(self, tmp_path: Path) -> None:
        vault, trash_path, preview = self._trashed(tmp_path)
        trash_path.unlink()

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).restore(preview, confirm=True)


class TestTrashDelete:
    def test_delete_removes_only_the_selected_entry(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        service = afanes.core.vault.trash.TrashService(vault)
        first = service.trash(_write_note(root / "inbox" / "Ada.md"), confirm=True, today=TODAY)
        second = service.trash(_write_note(root / "inbox" / "Grace.md"), confirm=True, today=TODAY)
        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        service.delete_entry(snapshot.entries[0])

        remaining = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()
        assert remaining.count == 1
        assert remaining.entries[0].path in (first.trash_path, second.trash_path)

    def test_empty_deletes_managed_entries_and_keeps_unmanaged_files(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        service = afanes.core.vault.trash.TrashService(vault)
        service.trash(_write_note(root / "inbox" / "Ada.md"), confirm=True, today=TODAY)
        legacy = _trash_file(root, "Legacy.md", "---\ntype: note\n---\n\n# Legacy\n")

        report = service.empty()

        assert report.deleted == 1
        assert not report.failed
        assert legacy.is_file()
        assert afanes.core.vault.trash_catalog.TrashCatalog(vault).load().count == 0

    def test_delete_reports_a_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        service = afanes.core.vault.trash.TrashService(vault)
        service.trash(_write_note(root / "inbox" / "Ada.md"), confirm=True, today=TODAY)

        message = "no"

        def fail(_self: object, _entry: object) -> None:
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.trash.TrashService, "delete_entry", fail)

        report = service.empty()

        assert report.deleted == 0
        assert report.failed


class TestTrashRetention:
    def _entry(self, tmp_path: Path, day: datetime.date | None) -> tuple[afanes.core.vault.service.Vault, Path]:
        root = tmp_path / "vault"
        vault = _vault(root)
        lines = ["---", "type: note", "trashed_from: inbox/Ada.md"]
        if day is not None:
            lines.append(f"trashed_on: {day.isoformat()}")
        lines.extend(["---", "", "# Ada", ""])
        path = _trash_file(root, f"{uuid.uuid4()}.md", "\n".join(lines))
        return vault, path

    def test_an_entry_expires_at_thirty_days(self, tmp_path: Path) -> None:
        vault, path = self._entry(tmp_path, TODAY - datetime.timedelta(days=THIRTY_DAYS))

        report = afanes.core.vault.trash.TrashService(vault).maintain(TODAY)

        assert report.deleted == 1
        assert not path.exists()

    def test_an_entry_at_twenty_nine_days_remains(self, tmp_path: Path) -> None:
        vault, path = self._entry(tmp_path, TODAY - datetime.timedelta(days=29))

        report = afanes.core.vault.trash.TrashService(vault).maintain(TODAY)

        assert report.deleted == 0
        assert path.is_file()

    def test_a_missing_day_is_stamped_with_today(self, tmp_path: Path) -> None:
        vault, path = self._entry(tmp_path, None)

        report = afanes.core.vault.trash.TrashService(vault).maintain(TODAY)

        assert report.stamped == 1
        assert report.deleted == 0
        metadata = TrashDocument.from_text(path.read_text(encoding="utf-8")).metadata
        assert metadata is not None
        assert metadata.trashed_on == TODAY

    def test_a_malformed_day_is_stamped_with_today(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        path = _trash_file(
            root,
            f"{uuid.uuid4()}.md",
            "---\ntype: note\ntrashed_from: inbox/Ada.md\ntrashed_on: not-a-date\n---\n\n# Ada\n",
        )

        report = afanes.core.vault.trash.TrashService(vault).maintain(TODAY)

        assert report.stamped == 1
        metadata = TrashDocument.from_text(path.read_text(encoding="utf-8")).metadata
        assert metadata is not None
        assert metadata.trashed_on == TODAY

    def test_a_failed_stamp_keeps_the_entry_visible(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        vault, path = self._entry(tmp_path, None)

        message = "read only"

        def fail(*_args: object, **_kwargs: object) -> None:
            raise OSError(message)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", fail)

        report = afanes.core.vault.trash.TrashService(vault).maintain(TODAY)

        assert report.failed
        assert path.is_file()
        assert afanes.core.vault.trash_catalog.TrashCatalog(vault).load().count == 1

    def test_a_failed_delete_is_reported_and_keeps_the_entry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault, path = self._entry(tmp_path, TODAY - datetime.timedelta(days=THIRTY_DAYS))

        message = "no"

        def fail(_self: object, _entry: object) -> None:
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.trash.TrashService, "delete_entry", fail)

        report = afanes.core.vault.trash.TrashService(vault).maintain(TODAY)

        assert report.failed
        assert path.is_file()

    def test_retention_does_not_delete_unmanaged_files(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        legacy = _trash_file(
            root,
            "Legacy.md",
            "---\ntype: note\ntrashed_on: 2020-01-01\n---\n\n# Legacy\n",
        )

        report = afanes.core.vault.trash.TrashService(vault).maintain(TODAY)

        assert report.deleted == 0
        assert legacy.is_file()


class TestTrashUndo:
    def test_undo_restores_a_free_birthplace_and_removes_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md", extra="custom: keep\n")
        service = afanes.core.vault.trash.TrashService(vault)
        preview = service.trash(note, confirm=True, today=TODAY)

        restored = service.restore(preview, confirm=True)

        document = TrashDocument.from_text(restored.read_text(encoding="utf-8"))
        assert document.metadata is None
        assert document.raw["custom"] == "keep"

    def test_undo_refuses_an_occupied_birthplace_and_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md")
        service = afanes.core.vault.trash.TrashService(vault)
        preview = service.trash(note, confirm=True, today=TODAY)
        note.write_text("---\ntype: note\n---\n\n# Occupant\n", encoding="utf-8")
        trashed = preview.trash_path.read_bytes()

        with pytest.raises(NameCollisionError):
            service.restore(preview, confirm=True)

        assert note.read_text(encoding="utf-8").endswith("# Occupant\n")
        assert preview.trash_path.read_bytes() == trashed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestTrashMetadataEdges:
    def test_to_raw_includes_only_a_usable_day(self) -> None:
        with_day = TrashMetadata(birthplace=Path("inbox/Ada.md"), trashed_on=TODAY)
        without_day = TrashMetadata(birthplace=Path("inbox/Ada.md"), trashed_on=None)

        assert with_day.to_raw() == {"trashed_from": "inbox/Ada.md", "trashed_on": TODAY}
        assert without_day.to_raw() == {"trashed_from": "inbox/Ada.md"}

    def test_a_timestamp_is_not_a_calendar_day(self) -> None:
        raw: dict[str, object] = {
            "trashed_from": "inbox/Ada.md",
            "trashed_on": datetime.datetime(2026, 11, 13, 12, 0, tzinfo=datetime.UTC),
        }

        metadata = TrashMetadata.from_raw(raw)

        assert metadata is not None
        assert metadata.trashed_on is None

    def test_a_document_without_frontmatter_round_trips_unchanged(self) -> None:
        text = "# Plain body\n"

        document = TrashDocument.from_text(text)

        assert document.has_frontmatter is False
        assert document.without_metadata() == text
        assert document.metadata is None

    def test_malformed_yaml_raises(self) -> None:
        with pytest.raises(NoteParseError):
            TrashDocument.from_text("---\ntrashed_from: [unclosed\n---\n")

    def test_a_non_mapping_frontmatter_raises(self) -> None:
        with pytest.raises(NoteParseError):
            TrashDocument.from_text("---\n- one\n- two\n---\n")

    def test_a_non_string_key_raises(self) -> None:
        with pytest.raises(NoteParseError):
            TrashDocument.from_text("---\n1: one\n---\n")

    def test_writing_a_day_can_remove_the_key(self) -> None:
        document = TrashDocument.from_text("---\ntrashed_from: inbox/Ada.md\ntrashed_on: 2026-11-13\n---\n\n# Ada\n")
        metadata = document.metadata
        assert metadata is not None

        text = document.with_metadata(TrashMetadata(birthplace=metadata.birthplace, trashed_on=None))

        assert "trashed_on" not in TrashDocument.from_text(text).raw


class TestTrashCatalogEdges:
    def _entry(self, root: Path, body: str = "# Ada\n") -> afanes.core.vault.service.Vault:
        _trash_file(
            root,
            f"{uuid.uuid4()}.md",
            f"---\ntype: note\ntrashed_from: inbox/Ada.md\ntrashed_on: 2026-11-13\n---\n\n{body}",
        )
        return _vault(root)

    def test_an_empty_query_matches_every_entry(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = self._entry(root)

        entry = afanes.core.vault.trash_catalog.TrashCatalog(vault).load().entries[0]

        assert entry.matches("") is True

    def test_expired_returns_only_old_entries(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = self._entry(root)
        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        assert snapshot.expired(TODAY + datetime.timedelta(days=29)) == ()
        assert snapshot.expired(TODAY + datetime.timedelta(days=30)) == snapshot.entries

    def test_find_returns_the_entry_or_none(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = self._entry(root)
        snapshot = afanes.core.vault.trash_catalog.TrashCatalog(vault).load()

        assert snapshot.find(snapshot.entries[0].path) == snapshot.entries[0]
        assert snapshot.find(tmp_path / "other.md") is None

    def test_malformed_unreadable_and_non_markdown_files_are_hidden(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        vault = _vault(root)
        _trash_file(root, f"{uuid.uuid4()}.md", "---\ntype: note\n---\n\n# No metadata\n")
        _trash_file(root, f"{uuid.uuid4()}.md", "---\ninvalid: [\n---\n")
        _trash_file(root, "notes.txt", "not a note")

        assert afanes.core.vault.trash_catalog.TrashCatalog(vault).load().count == 0


class TestTrashServiceEdges:
    def _trashed_entry(self, tmp_path: Path) -> tuple[afanes.core.vault.service.Vault, TrashEntry]:
        root = tmp_path / "vault"
        vault = _vault(root)
        note = _write_note(root / "inbox" / "Ada.md")
        afanes.core.vault.trash.TrashService(vault).trash(note, confirm=True, today=TODAY)
        entry = afanes.core.vault.trash_catalog.TrashCatalog(vault).load().entries[0]
        return vault, entry

    def test_restore_entry_requires_confirmation(self, tmp_path: Path) -> None:
        vault, entry = self._trashed_entry(tmp_path)

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).restore_entry(entry)

        assert entry.path.is_file()

    def test_delete_refuses_a_symlink(self, tmp_path: Path) -> None:
        vault, entry = self._trashed_entry(tmp_path)
        outside = tmp_path / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        entry.path.unlink()
        entry.path.symlink_to(outside)

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).delete_entry(entry)

        assert outside.read_text(encoding="utf-8") == "outside"

    def test_delete_refuses_a_file_that_lost_its_metadata(self, tmp_path: Path) -> None:
        vault, entry = self._trashed_entry(tmp_path)
        entry.path.write_text("---\ntype: note\n---\n\n# Ada\n", encoding="utf-8")

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).delete_entry(entry)

        assert entry.path.is_file()

    def test_restore_refuses_a_file_that_lost_its_metadata(self, tmp_path: Path) -> None:
        vault, entry = self._trashed_entry(tmp_path)
        entry.path.write_text("---\ntype: note\n---\n\n# Ada\n", encoding="utf-8")

        with pytest.raises(VaultError):
            afanes.core.vault.trash.TrashService(vault).restore_entry(entry, confirm=True)

        assert entry.path.is_file()
