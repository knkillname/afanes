"""Tests for vault scanning, containment, atomic writes, and reference-safe edits."""

import datetime
import hashlib
import os
import tempfile
from pathlib import Path

import hypothesis
import hypothesis.strategies
import pytest

import afanes.core.atomic
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.core.vault.steps
from afanes.core.errors import (
    NoteParseError,
    VaultError,
    VaultMissingError,
    VaultNotDirectoryError,
    VaultNotEmptyError,
    VaultPathError,
    VaultUnreadableError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.vault.snapshot import ParsedPage, UnparsedPage
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status

ONE = 1
TWO = 2
THREE_REFERENCES = 3


def _write_note(
    path: Path,
    note_type: str = "note",
    body: str = "",
    *,
    category: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    date: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if note_type == "person":
        note_type = "reference"
        category = "person"
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    if date is not None:
        lines.append(f"date: {date}")
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _set_modified_ns(path: Path, modified_ns: int) -> None:
    os.utime(path, ns=(modified_ns, modified_ns))


class TestVaultService:
    def test_resolves_a_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.service.Vault(root).root == root.resolve()

    def test_rejects_a_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "note.md"
        file_path.write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotDirectoryError):
            afanes.core.vault.service.Vault(file_path)

    def test_rejects_a_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultMissingError):
            afanes.core.vault.service.Vault(tmp_path / "missing")

    def test_accepts_a_relative_path_inside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        assert vault.contained(Path("notes/Ada.md")) == (root / "notes/Ada.md").resolve()

    def test_rejects_relative_traversal(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultPathError):
            vault.contained(Path("../outside.md"))

    def test_rejects_a_symlink_that_escapes_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        outside = tmp_path / "outside.md"
        outside.write_text("body", encoding="utf-8")
        link = root / "Ada.md"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlinks are unavailable on this platform")
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultPathError):
            vault.contained(link)


class TestVaultOpen:
    def test_opens_an_existing_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        vault = afanes.core.vault.service.Vault.open(root)

        assert vault.root == root.resolve()

    def test_rejects_a_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultMissingError):
            afanes.core.vault.service.Vault.open(tmp_path / "missing")

    def test_rejects_a_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "note.md"
        file_path.write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotDirectoryError):
            afanes.core.vault.service.Vault.open(file_path)

    def test_rejects_an_unreadable_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        monkeypatch.setattr(afanes.core.vault.service.os, "access", lambda _path, _mode: False)

        with pytest.raises(VaultUnreadableError):
            afanes.core.vault.service.Vault.open(root)

    def test_resolves_a_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        monkeypatch.chdir(tmp_path)

        vault = afanes.core.vault.service.Vault.open(Path("vault"))

        assert vault.root == root.resolve()


class TestDirectoryFor:
    def test_note_uses_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.service.Vault(root).directory_for(NoteType.NOTE) == root / "inbox"

    def test_project_uses_projects(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.service.Vault(root).directory_for(NoteType.PROJECT) == root / "projects"

    def test_uncategorized_reference_uses_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.service.Vault(root).directory_for(NoteType.REFERENCE) == root / "reference"

    def test_category_label_selects_a_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        directory = afanes.core.vault.service.Vault(root).directory_for(NoteType.REFERENCE, CategoryLabel("place"))

        assert directory == root / "reference" / "place"

    def test_reuses_an_existing_case_variant(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Inbox").mkdir(parents=True)
        (root / "reference" / "Place").mkdir(parents=True)

        vault = afanes.core.vault.service.Vault(root)
        assert vault.directory_for(NoteType.NOTE) == root / "Inbox"
        assert vault.directory_for(NoteType.REFERENCE, CategoryLabel("place")) == root / "reference" / "Place"

    def test_does_not_create_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        vault.directory_for(NoteType.NOTE)
        vault.directory_for(NoteType.PROJECT)
        vault.directory_for(NoteType.REFERENCE, CategoryLabel("place"))

        assert list(root.iterdir()) == []

    def test_rejects_a_category_on_a_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(VaultError):
            afanes.core.vault.service.Vault(root).directory_for(NoteType.NOTE, CategoryLabel("place"))

    def test_log_requires_a_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(VaultError, match="log_directory"):
            afanes.core.vault.service.Vault(root).directory_for(NoteType.LOG)


class TestLogDirectory:
    def test_year_precision_uses_the_year_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        directory = afanes.core.vault.service.Vault(root).log_directory(NoteDate.from_text("2025"))

        assert directory == root / "log" / "2025"

    @pytest.mark.parametrize("text", ["2025-10", "2025-10-12"])
    def test_month_and_day_precision_use_the_month_folder(self, tmp_path: Path, text: str) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        directory = afanes.core.vault.service.Vault(root).log_directory(NoteDate.from_text(text))

        assert directory == root / "log" / "2025" / "10"

    def test_reuses_existing_case_variants(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Log" / "2025" / "10").mkdir(parents=True)

        directory = afanes.core.vault.service.Vault(root).log_directory(NoteDate.from_text("2025-10-12"))

        assert directory == root / "Log" / "2025" / "10"

    def test_does_not_create_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        afanes.core.vault.service.Vault(root).log_directory(NoteDate.from_text("2025-10-12"))

        assert list(root.iterdir()) == []


class TestVaultCreation:
    def test_creates_a_missing_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "vault"

        creation = afanes.core.vault.service.Vault.create_directory(target)

        assert creation.vault.root == target.resolve()
        assert target.is_dir()

    def test_creates_missing_intermediate_folders(self, tmp_path: Path) -> None:
        target = tmp_path / "notes" / "personal" / "vault"

        creation = afanes.core.vault.service.Vault.create_directory(target)

        assert creation.created_directories == (tmp_path / "notes", tmp_path / "notes" / "personal")
        assert target.is_dir()

    def test_seeds_an_empty_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "vault"
        target.mkdir()

        creation = afanes.core.vault.service.Vault.create_directory(target)

        assert creation.created_directories == ()
        assert creation.vault.root == target.resolve()

    def test_refuses_a_non_empty_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "vault"
        target.mkdir()
        (target / "photo.jpg").write_text("data", encoding="utf-8")

        with pytest.raises(VaultNotEmptyError):
            afanes.core.vault.service.Vault.create_directory(target)

        assert sorted(path.name for path in target.iterdir()) == ["photo.jpg"]

    def test_refuses_a_file(self, tmp_path: Path) -> None:
        target = tmp_path / "note.md"
        target.write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotDirectoryError):
            afanes.core.vault.service.Vault.create_directory(target)

        assert target.read_text(encoding="utf-8") == "body"

    def test_refuses_a_symlink_to_a_populated_directory(self, tmp_path: Path) -> None:
        populated = tmp_path / "populated"
        populated.mkdir()
        (populated / "note.md").write_text("body", encoding="utf-8")
        link = tmp_path / "link"
        try:
            link.symlink_to(populated, target_is_directory=True)
        except OSError:
            pytest.skip("symlinks are unavailable on this platform")

        with pytest.raises(VaultNotEmptyError):
            afanes.core.vault.service.Vault.create_directory(link)

    def test_seeds_every_default_folder(self, tmp_path: Path) -> None:
        layout = afanes.core.vault.service.Vault.default_layout()

        creation = afanes.core.vault.service.Vault.create_directory(tmp_path / "vault")

        root = creation.vault.root
        assert [path.relative_to(root) for path in creation.seeded_directories] == list(layout)
        assert all((root / relative).is_dir() for relative in layout)

    def test_seeded_paths_match_directory_for(self, tmp_path: Path) -> None:
        creation = afanes.core.vault.service.Vault.create_directory(tmp_path / "vault")
        vault = creation.vault
        expected = [
            vault.directory_for(NoteType.NOTE),
            vault.root / "trash",
            vault.directory_for(NoteType.REFERENCE),
            vault.directory_for(NoteType.PROJECT),
            vault.root / "log",
        ]

        assert list(creation.seeded_directories) == expected

    def test_creation_writes_the_guide_and_the_eight_cards(self, tmp_path: Path) -> None:
        creation = afanes.core.vault.service.Vault.create_directory(tmp_path / "vault")

        files = [
            path.relative_to(creation.vault.root).as_posix()
            for path in sorted(creation.vault.root.rglob("*"))
            if path.is_file()
        ]
        assert files == [
            "reference/Getting started.md",
            "templates/daily.md",
            "templates/organization.md",
            "templates/person.md",
            "templates/place.md",
            "templates/process.md",
            "templates/source.md",
            "templates/team.md",
            "templates/topic.md",
        ]
        assert [path.name for path in creation.written_cards] == [
            "daily.md",
            "organization.md",
            "person.md",
            "place.md",
            "process.md",
            "source.md",
            "team.md",
            "topic.md",
        ]
        assert all(path.is_relative_to(creation.vault.root) for path in creation.written_cards)

    def test_refusal_writes_nothing(self, tmp_path: Path) -> None:
        target = tmp_path / "vault"
        target.mkdir()
        (target / "existing.md").write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotEmptyError):
            afanes.core.vault.service.Vault.create_directory(target)

        assert sorted(path.name for path in target.iterdir()) == ["existing.md"]
        assert [path.name for path in tmp_path.iterdir()] == ["vault"]

    @hypothesis.given(hypothesis.strategies.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6))
    def test_seeded_paths_stay_inside_the_created_root(self, name: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / f"vault-{name}"

            creation = afanes.core.vault.service.Vault.create_directory(target)

            root = creation.vault.root
            assert root == target.resolve()
            assert all(path.is_relative_to(root) for path in creation.seeded_directories)


class TestScanVault:
    def test_finds_nested_notes_in_deterministic_order(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "z/Beta.md")
        _write_note(root / "a/Alpha.md")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        assert [note.name for note in snapshot.notes] == ["Alpha", "Beta"]

    def test_skips_dot_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / ".trash/Hidden.md")
        _write_note(root / "Visible.md")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        assert [note.name for note in snapshot.notes] == ["Visible"]

    def test_skips_the_trash_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "trash/Ada.md")
        _write_note(root / "Trash/Bob.md")
        _write_note(root / "Active.md")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert [note.name for note in snapshot.notes] == ["Active"]

    def test_trashed_names_can_be_reused(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "trash/Ada.md", "person")
        active = _write_note(root / "reference/person/Ada.md", "person")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        resolution = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
        assert resolution.outcome is ResolutionOutcome.RESOLVED
        assert resolution.targets == (active,)

    def test_reference_to_a_trashed_note_is_unresolved(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "trash/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](note:Ada)")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        resolution = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
        assert resolution.outcome is ResolutionOutcome.UNRESOLVED

    def test_skips_the_templates_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "templates/person.md", "reference", category="person")
        _write_note(root / "Active.md")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert [note.name for note in snapshot.notes] == ["Active"]

    def test_skips_a_case_variant_of_templates(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Templates/person.md", "reference", category="person")
        _write_note(root / "Active.md")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert [note.name for note in snapshot.notes] == ["Active"]

    def test_a_template_name_does_not_collide_with_a_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "templates/Ada.md", "reference", category="person")
        vault = afanes.core.vault.service.Vault(root)

        path = afanes.core.vault.pages.VaultPages(vault).create_page("Ada", NoteType.REFERENCE)

        assert path == root / "reference" / "Ada.md"

    def test_a_reference_to_a_template_name_is_unresolved(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "templates/person.md", "reference", category="person")
        _write_note(root / "inbox/Note.md", body="[Person](note:person)")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        resolution = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="person"))
        assert resolution.outcome is ResolutionOutcome.UNRESOLVED

    def test_skips_a_symlink_that_escapes_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        outside = tmp_path / "outside.md"
        outside.write_text("---\ntype: note\n---\n", encoding="utf-8")
        link = root / "Link.md"
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip("symlinks are unavailable on this platform")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        assert snapshot.notes == ()

    def test_reports_a_malformed_note_without_aborting(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Good.md")
        bad = root / "Bad.md"
        bad.write_text("---\ntype: [unclosed\n---\n", encoding="utf-8")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        assert [note.name for note in snapshot.notes] == ["Good"]
        assert [failure.path.as_posix() for failure in snapshot.failures] == ["Bad.md"]

    def test_reports_a_note_without_a_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = root / "NoType.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nid: legacy\n---\n", encoding="utf-8")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_records_category_and_status(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "people/Ada.md", "reference", category="person", status="later")
        _write_note(root / "projects/Launch.md", "project", status="active")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        by_name = {note.name: note for note in snapshot.notes}
        assert by_name["Ada"].category == CategoryLabel("person")
        assert by_name["Ada"].status is Status.LATER
        assert by_name["Launch"].category is None
        assert by_name["Launch"].status is Status.ACTIVE

    def test_reports_an_invalid_status(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Bad.md", "project", status="inbox")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_records_a_due_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", "project", due_date="2026-11-20")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].due_date == datetime.date(2026, 11, 20)

    def test_records_a_day_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", date="2025-10-12")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].date == NoteDate.from_text("2025-10-12")

    def test_records_a_month_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", date="'2025-10'")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].date == NoteDate.from_text("2025-10")

    def test_records_a_year_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", date="2025")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].date == NoteDate.from_text("2025")

    def test_absent_date_is_none(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].date is None

    def test_malformed_date_stays_in_the_snapshot(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", date="'last Tuesday'")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert len(snapshot.notes) == ONE
        assert snapshot.notes[0].date is None
        assert snapshot.failures == ()

    def test_finds_a_log_entry_by_exact_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_note(root / "log/2025/10/2025-10-12.md", "log", date="2025-10-12")

        snapshot = afanes.core.vault.service.Vault(root).scan()
        found = snapshot.log_entry(NoteDate.from_text("2025-10-12"))

        assert found is not None
        assert found.path == path
        assert snapshot.log_entry(NoteDate.from_text("2025-10-13")) is None

    def test_absent_due_date_is_none(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", "project")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].due_date is None

    def test_null_due_date_is_none(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", "project", due_date="null")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].due_date is None

    def test_invalid_due_date_is_reported_as_a_failure(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", "project", due_date='"next Friday"')

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_reports_legacy_person_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = root / "Ada.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\ntype: person\n---\n", encoding="utf-8")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_reports_category_on_a_non_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Bad.md", "project", category="person")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_records_the_content_hash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_note(root / "Ada.md")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        assert snapshot.notes[0].content_hash == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_records_the_heading_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Ada.md", body="# Ada, Countess of Lovelace")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].name == "Ada"
        assert snapshot.notes[0].title == "Ada, Countess of Lovelace"

    def test_title_falls_back_to_the_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Ada.md", body="No heading")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes[0].title == "Ada"

    def test_an_invalid_note_with_a_heading_is_still_reported(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        bad = root / "Ada.md"
        bad.parent.mkdir(parents=True)
        bad.write_text("---\ntype: [unclosed\n---\n# Ada\n", encoding="utf-8")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.notes == ()
        assert [failure.path.as_posix() for failure in snapshot.failures] == ["Ada.md"]

    def test_extracts_body_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Note.md", body="[Ada](<note:Ada Lovelace>)")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        note = snapshot.notes[0]
        assert note.body_references == (NoteReference(scheme=ReferenceScheme.NOTE, name="Ada Lovelace", label="Ada"),)

    def test_project_note_derives_steps_and_search_text(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root / "projects/Home.md",
            "project",
            body="# Home\n\n- [ ] Call the plumber <!-- {owners: [Ada], plan: 2026-11-20} -->\n",
        )

        note = afanes.core.vault.service.Vault(root).scan().notes[0]

        assert [step.text for step in note.steps] == ["Call the plumber"]
        assert note.next_step is not None
        assert "Ada" not in note.search_text
        assert "Call the plumber" in note.search_text

    def test_reference_note_has_no_steps(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "reference/Errands.md", "reference", body="- [ ] Buy milk\n")

        note = afanes.core.vault.service.Vault(root).scan().notes[0]

        assert note.steps == ()

    def test_misplaced_note_is_flagged(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "notes/Later.md", "note")

        note = afanes.core.vault.service.Vault(root).scan().notes[0]

        assert note.is_misplaced is True

    def test_scan_performs_no_writes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Ada.md", body="[Grace](note:Grace)")
        before = _tree_state(root)

        def fail_write(_path: Path, _text: str) -> None:
            message = "scan must not write"
            raise AssertionError(message)

        monkeypatch.setattr(afanes.core.atomic, "write_text_atomic", fail_write)
        afanes.core.vault.service.Vault(root).scan()
        assert _tree_state(root) == before

    def test_scanning_undated_notes_creates_no_folders(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "notes" / "Undated.md")
        before = _tree_state(root)
        folders_before = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()}

        afanes.core.vault.service.Vault(root).scan()

        assert _tree_state(root) == before
        assert {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()} == folders_before
        assert not (root / "log").exists()

    def test_catalog_keeps_duplicate_names_ambiguous(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "a/Ada.md", "person")
        _write_note(root / "b/Ada.md", "person")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
        assert result.outcome is ResolutionOutcome.AMBIGUOUS
        assert len(result.targets) == TWO


class TestScanFingerprint:
    def test_fingerprint_is_stable_for_an_unchanged_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/Ada.md", body="# Ada\n")
        _write_note(root / "projects/Grace.md", "project", body="# Grace\n")
        vault = afanes.core.vault.service.Vault(root)
        assert vault.scan_fingerprint() == vault.scan_fingerprint()

    def test_fingerprint_changes_after_an_edit(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_note(root / "inbox/Ada.md", body="# Ada\n")
        vault = afanes.core.vault.service.Vault(root)
        before = vault.scan_fingerprint()
        _set_modified_ns(path, 1_000_000_000_000)
        path.write_text("---\ntype: note\n---\n\n# Ada edited\n", encoding="utf-8", newline="\n")
        _set_modified_ns(path, 2_000_000_000_000)
        assert vault.scan_fingerprint() != before

    def test_fingerprint_changes_after_an_addition(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/Ada.md", body="# Ada\n")
        vault = afanes.core.vault.service.Vault(root)
        before = vault.scan_fingerprint()
        _write_note(root / "inbox/Grace.md", body="# Grace\n")
        assert vault.scan_fingerprint() != before

    def test_fingerprint_changes_after_a_removal(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/Ada.md", body="# Ada\n")
        path = _write_note(root / "inbox/Grace.md", body="# Grace\n")
        vault = afanes.core.vault.service.Vault(root)
        before = vault.scan_fingerprint()
        path.unlink()
        assert vault.scan_fingerprint() != before

    def test_fingerprint_ignores_the_trash_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/Ada.md", body="# Ada\n")
        vault = afanes.core.vault.service.Vault(root)
        before = vault.scan_fingerprint()
        _write_note(root / "trash/Grace.md", body="# Grace\n")
        assert vault.scan_fingerprint() == before

    def test_fingerprint_ignores_hidden_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/Ada.md", body="# Ada\n")
        vault = afanes.core.vault.service.Vault(root)
        before = vault.scan_fingerprint()
        _write_note(root / ".obsidian/Grace.md", body="# Grace\n")
        assert vault.scan_fingerprint() == before

    def test_fingerprint_is_empty_for_a_vault_without_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        assert afanes.core.vault.service.Vault(root).scan_fingerprint() == ()


class TestReadPage:
    def test_reads_a_note_with_its_text_and_hash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "notes" / "Ada.md", body="# Ada\n")

        content = afanes.core.vault.service.Vault(root).read_page(path)

        assert content.path == path.resolve()
        assert content.relative_path == Path("notes/Ada.md")
        assert content.text == path.read_text(encoding="utf-8")
        assert content.content_hash == hashlib.sha256(path.read_bytes()).hexdigest()
        assert isinstance(content, ParsedPage)
        assert content.document.body == "\n# Ada\n"

    def test_malformed_note_keeps_the_raw_text(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = root / "reference" / "Broken.md"
        path.parent.mkdir()
        text = "---\ntype: refrence\n---\nBody\n"
        path.write_text(text, encoding="utf-8")

        content = afanes.core.vault.service.Vault(root).read_page(path)

        assert isinstance(content, UnparsedPage)
        assert content.failure
        assert content.text == text
        assert content.content_hash == hashlib.sha256(text.encode("utf-8")).hexdigest()

    def test_missing_note_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultPathError):
            vault.read_page(Path("missing.md"))

    def test_path_outside_the_vault_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        outside = tmp_path / "outside.md"
        outside.write_text("body", encoding="utf-8")
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultPathError):
            vault.read_page(outside)

    def test_directory_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        directory = root / "notes"
        directory.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultPathError):
            vault.read_page(directory)


class TestCreateNote:
    def test_sanitizes_the_title_into_the_filename(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.service.Vault(root).create("Q1: Planning?", NoteType.NOTE, body="Body")
        assert path.name == "Q1 Planning.md"
        assert NoteDocument.from_text(path.read_text(encoding="utf-8")).note_type is NoteType.NOTE

    def test_defaults_to_inbox_for_a_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.service.Vault(root).create("Ada", NoteType.NOTE)

        assert path == root / "inbox" / "Ada.md"

    def test_defaults_to_projects_for_a_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.service.Vault(root).create("Ada", NoteType.PROJECT, status=Status.ACTIVE)

        assert path == root / "projects" / "Ada.md"

    def test_defaults_to_reference_for_an_uncategorized_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.service.Vault(root).create("Ada", NoteType.REFERENCE)

        assert path == root / "reference" / "Ada.md"

    def test_defaults_to_the_category_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.service.Vault(root).create(
            "Ada",
            NoteType.REFERENCE,
            category=CategoryLabel("person"),
        )

        assert path == root / "reference" / "person" / "Ada.md"

    def test_suffixes_a_collision_within_the_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        afanes.core.vault.service.Vault(root).create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))
        second = afanes.core.vault.service.Vault(root).create(
            "Ada", NoteType.REFERENCE, category=CategoryLabel("person")
        )
        assert second.name == "Ada 2.md"

    def test_suffixes_a_collision_with_an_existing_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "reference" / "person").mkdir(parents=True)
        (root / "reference" / "person" / "Ada.txt").write_text("occupied", encoding="utf-8")
        path = afanes.core.vault.service.Vault(root).create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))
        assert path.name == "Ada 2.md"

    def test_allows_cross_scheme_reuse_in_different_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        person = afanes.core.vault.service.Vault(root).create(
            "Ada", NoteType.REFERENCE, category=CategoryLabel("person"), directory=Path("people")
        )
        project = afanes.core.vault.service.Vault(root).create("Ada", NoteType.PROJECT, directory=Path("work"))
        assert person.name == "Ada.md"
        assert project.name == "Ada.md"

    def test_avoids_reserved_device_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.service.Vault(root).create("CON", NoteType.NOTE)
        assert path.name == "CON-note.md"

    def test_creates_a_missing_classification_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.service.Vault(root).create(
            "Ada", NoteType.REFERENCE, category=CategoryLabel("person"), directory=Path("people")
        )
        assert path.parent.is_dir()

    def test_rejects_a_directory_that_escapes_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        with pytest.raises(VaultPathError):
            afanes.core.vault.service.Vault(root).create(
                "Ada", NoteType.REFERENCE, category=CategoryLabel("person"), directory=Path("../outside")
            )

    def test_new_note_is_valid_markdown(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.service.Vault(root).create(
            "Ada", NoteType.REFERENCE, category=CategoryLabel("person"), body="Hello\n"
        )
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.REFERENCE
        assert document.category == CategoryLabel("person")
        assert "status" not in document.raw
        assert document.body == "Hello\n"

    def test_new_note_normalizes_line_endings_and_removes_a_bom(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.service.Vault(root).create("Ada", NoteType.NOTE, body="\ufeffone\r\ntwo\r")
        data = path.read_bytes()
        assert b"\r" not in data
        assert not data.startswith(b"\xef\xbb\xbf")
        assert data.endswith(b"one\ntwo\n")

    def test_default_omits_the_status_key(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.service.Vault(root).create("Ada", NoteType.NOTE)
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw["type"] == "note"
        assert document.date is not None
        assert "status" not in document.raw

    def test_explicit_status_is_written(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.service.Vault(root).create("Ada", NoteType.PROJECT, status=Status.ACTIVE)
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.status is Status.ACTIVE

    def test_rejects_a_category_on_a_non_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(NoteParseError):
            afanes.core.vault.service.Vault(root).create(
                "Ada",
                NoteType.NOTE,
                category=CategoryLabel("person"),
            )


class TestTemplatesDirectory:
    def test_a_missing_folder_is_not_created(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        directory = vault.templates_directory()
        vault.scan()

        assert directory == root / "templates"
        assert not directory.exists()

    def test_the_canonical_folder_is_returned(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "templates").mkdir(parents=True)
        vault = afanes.core.vault.service.Vault(root)

        assert vault.templates_directory() == root / "templates"

    def test_a_case_variant_is_reused(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Templates").mkdir(parents=True)
        vault = afanes.core.vault.service.Vault(root)

        assert vault.templates_directory() == root / "Templates"
