"""Tests for vault scanning, containment, atomic writes, and reference-safe edits."""

import hashlib
import os
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.vault
from afanes.core.errors import EmptyCaptureError, NameCollisionError, NoteParseError, VaultError, VaultPathError
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.vault import ReferenceSite
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

ONE = 1
TWO = 2
FOUR_REFERENCES = 4


def _write_note(
    path: Path,
    note_type: str = "note",
    body: str = "",
    people: tuple[str, ...] = (),
    project: str | None = None,
    *,
    category: str | None = None,
    status: str | None = None,
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
    if people:
        lines.append("people:")
        lines.extend(f'  - "{value}"' for value in people)
    if project is not None:
        lines.append(f'project: "{project}"')
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

        assert afanes.core.vault.Vault(root).root == root.resolve()

    def test_rejects_a_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "note.md"
        file_path.write_text("body", encoding="utf-8")

        with pytest.raises(VaultError):
            afanes.core.vault.Vault(file_path)

    def test_rejects_a_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultError):
            afanes.core.vault.Vault(tmp_path / "missing")

    def test_accepts_a_relative_path_inside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        assert vault.contained(Path("notes/Ada.md")) == (root / "notes/Ada.md").resolve()

    def test_rejects_relative_traversal(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

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
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultPathError):
            vault.contained(link)


class TestDirectoryFor:
    def test_note_uses_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.Vault(root).directory_for(NoteType.NOTE) == root / "inbox"

    def test_action_uses_actions(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.Vault(root).directory_for(NoteType.ACTION) == root / "actions"

    def test_project_uses_projects(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.Vault(root).directory_for(NoteType.PROJECT) == root / "projects"

    def test_uncategorized_reference_uses_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.Vault(root).directory_for(NoteType.REFERENCE) == root / "reference"

    def test_person_reference_uses_people(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        directory = afanes.core.vault.Vault(root).directory_for(NoteType.REFERENCE, ReferenceCategory.PERSON)

        assert directory == root / "reference" / "people"

    def test_reuses_an_existing_case_variant(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Inbox").mkdir(parents=True)
        (root / "reference" / "People").mkdir(parents=True)

        vault = afanes.core.vault.Vault(root)
        assert vault.directory_for(NoteType.NOTE) == root / "Inbox"
        assert vault.directory_for(NoteType.REFERENCE, ReferenceCategory.PERSON) == root / "reference" / "People"

    def test_does_not_create_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        vault.directory_for(NoteType.NOTE)
        vault.directory_for(NoteType.ACTION)
        vault.directory_for(NoteType.PROJECT)
        vault.directory_for(NoteType.REFERENCE, ReferenceCategory.PERSON)

        assert list(root.iterdir()) == []

    def test_rejects_a_category_on_an_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(VaultError):
            afanes.core.vault.Vault(root).directory_for(NoteType.ACTION, ReferenceCategory.PERSON)


class TestScanVault:
    def test_finds_nested_notes_in_deterministic_order(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "z/Beta.md")
        _write_note(root / "a/Alpha.md")
        snapshot = afanes.core.vault.Vault(root).scan()
        assert [note.name for note in snapshot.notes] == ["Alpha", "Beta"]

    def test_skips_dot_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / ".trash/Hidden.md")
        _write_note(root / "Visible.md")
        snapshot = afanes.core.vault.Vault(root).scan()
        assert [note.name for note in snapshot.notes] == ["Visible"]

    def test_skips_the_trash_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "trash/Ada.md")
        _write_note(root / "Trash/Bob.md")
        _write_note(root / "Active.md")
        snapshot = afanes.core.vault.Vault(root).scan()

        assert [note.name for note in snapshot.notes] == ["Active"]

    def test_trashed_names_can_be_reused(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "trash/Ada.md", "person")
        active = _write_note(root / "reference/people/Ada.md", "person")
        snapshot = afanes.core.vault.Vault(root).scan()

        resolution = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert resolution.outcome is ResolutionOutcome.RESOLVED
        assert resolution.targets == (active,)

    def test_reference_to_a_trashed_note_is_unresolved(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "trash/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](person:Ada)")
        snapshot = afanes.core.vault.Vault(root).scan()

        resolution = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
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
        snapshot = afanes.core.vault.Vault(root).scan()
        assert snapshot.notes == ()

    def test_reports_a_malformed_note_without_aborting(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Good.md")
        bad = root / "Bad.md"
        bad.write_text("---\ntype: [unclosed\n---\n", encoding="utf-8")
        snapshot = afanes.core.vault.Vault(root).scan()
        assert [note.name for note in snapshot.notes] == ["Good"]
        assert [failure.path.as_posix() for failure in snapshot.failures] == ["Bad.md"]

    def test_reports_a_note_without_a_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = root / "NoType.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nid: legacy\n---\n", encoding="utf-8")
        snapshot = afanes.core.vault.Vault(root).scan()
        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_records_category_and_status(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "people/Ada.md", "reference", category="person", status="later")
        _write_note(root / "projects/Launch.md", "project", status="active")
        snapshot = afanes.core.vault.Vault(root).scan()

        by_name = {note.name: note for note in snapshot.notes}
        assert by_name["Ada"].category is ReferenceCategory.PERSON
        assert by_name["Ada"].status is Status.LATER
        assert by_name["Launch"].category is None
        assert by_name["Launch"].status is Status.ACTIVE

    def test_reports_an_invalid_status(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Bad.md", "action", status="inbox")
        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_reports_legacy_person_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = root / "Ada.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\ntype: person\n---\n", encoding="utf-8")
        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_reports_category_on_a_non_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Bad.md", "action", category="person")
        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_records_the_content_hash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_note(root / "Ada.md")
        snapshot = afanes.core.vault.Vault(root).scan()
        assert snapshot.notes[0].content_hash == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_extracts_body_and_frontmatter_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root / "Note.md",
            body="[Ada](<person:Ada Lovelace>)",
            people=("person:Ada Lovelace",),
            project="project:Turing Machine",
        )
        snapshot = afanes.core.vault.Vault(root).scan()
        note = snapshot.notes[0]
        assert note.body_references == (NoteReference(scheme=ReferenceScheme.PERSON, name="Ada Lovelace", label="Ada"),)
        assert [reference.scheme for reference in note.frontmatter_references] == [
            ReferenceScheme.PERSON,
            ReferenceScheme.PROJECT,
        ]

    def test_scan_performs_no_writes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Ada.md", body="[Grace](person:Grace)")
        before = _tree_state(root)

        def fail_write(_path: Path, _text: str) -> None:
            message = "scan must not write"
            raise AssertionError(message)

        monkeypatch.setattr(afanes.core.atomic, "write_text_atomic", fail_write)
        afanes.core.vault.Vault(root).scan()
        assert _tree_state(root) == before

    def test_catalog_keeps_duplicate_names_ambiguous(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "a/Ada.md", "person")
        _write_note(root / "b/Ada.md", "person")
        snapshot = afanes.core.vault.Vault(root).scan()
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.AMBIGUOUS
        assert len(result.targets) == TWO


class TestInboxNotes:
    def test_lists_direct_inbox_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        first = _write_note(root / "inbox/A.md")
        second = _write_note(root / "inbox/B.md")
        _write_note(root / "work/C.md")
        _set_modified_ns(first, 1_700_000_000_000_000_000)
        _set_modified_ns(second, 1_700_000_001_000_000_000)

        snapshot = afanes.core.vault.Vault(root).scan()
        names = [note.name for note in snapshot.inbox_notes()]

        assert names == ["B", "A"]

    def test_lists_nested_inbox_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/2026/C.md")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert [note.name for note in snapshot.inbox_notes()] == ["C"]

    def test_excludes_notes_outside_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "D.md")
        _write_note(root / "inbox.md")
        _write_note(root / "work/E.md")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.inbox_notes() == ()

    def test_matches_the_inbox_directory_case_insensitively(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Inbox/E.md")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert [note.name for note in snapshot.inbox_notes()] == ["E"]

    def test_orders_newest_first(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        old = _write_note(root / "inbox/Old.md")
        middle = _write_note(root / "inbox/Middle.md")
        new = _write_note(root / "inbox/New.md")
        _set_modified_ns(old, 1_700_000_000_000_000_000)
        _set_modified_ns(middle, 1_700_000_001_000_000_000)
        _set_modified_ns(new, 1_700_000_002_000_000_000)

        snapshot = afanes.core.vault.Vault(root).scan()

        assert [note.name for note in snapshot.inbox_notes()] == ["New", "Middle", "Old"]

    def test_equal_timestamps_use_a_case_folded_name_tie_breaker(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        upper = _write_note(root / "inbox/Beta.md")
        lower = _write_note(root / "inbox/alpha.md")
        _set_modified_ns(upper, 1_700_000_000_000_000_000)
        _set_modified_ns(lower, 1_700_000_000_000_000_000)

        snapshot = afanes.core.vault.Vault(root).scan()

        assert [note.name for note in snapshot.inbox_notes()] == ["alpha", "Beta"]

    def test_equal_names_use_a_path_tie_breaker(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        second = _write_note(root / "inbox/b/Same.md")
        first = _write_note(root / "inbox/a/Same.md")
        _set_modified_ns(first, 1_700_000_000_000_000_000)
        _set_modified_ns(second, 1_700_000_000_000_000_000)

        snapshot = afanes.core.vault.Vault(root).scan()

        paths = [note.relative_path.as_posix() for note in snapshot.inbox_notes()]
        assert paths == ["inbox/a/Same.md", "inbox/b/Same.md"]

    def test_empty_vault_returns_no_inbox_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.inbox_notes() == ()


class TestCreateNote:
    def test_sanitizes_the_title_into_the_filename(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.Vault(root).create("Q1: Planning?", NoteType.NOTE, body="Body")
        assert path.name == "Q1 Planning.md"
        assert NoteDocument.from_text(path.read_text(encoding="utf-8")).note_type is NoteType.NOTE

    def test_defaults_to_inbox_for_a_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create("Ada", NoteType.NOTE)

        assert path == root / "inbox" / "Ada.md"

    def test_defaults_to_actions_for_an_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create("Ada", NoteType.ACTION, status=Status.ACTIVE)

        assert path == root / "actions" / "Ada.md"

    def test_defaults_to_projects_for_a_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create("Ada", NoteType.PROJECT, status=Status.ACTIVE)

        assert path == root / "projects" / "Ada.md"

    def test_defaults_to_reference_for_an_uncategorized_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create("Ada", NoteType.REFERENCE)

        assert path == root / "reference" / "Ada.md"

    def test_defaults_to_people_for_a_person_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create(
            "Ada",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
        )

        assert path == root / "reference" / "people" / "Ada.md"

    def test_suffixes_a_collision_within_the_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        afanes.core.vault.Vault(root).create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)
        second = afanes.core.vault.Vault(root).create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)
        assert second.name == "Ada 2.md"

    def test_suffixes_a_collision_with_an_existing_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "reference" / "people").mkdir(parents=True)
        (root / "reference" / "people" / "Ada.txt").write_text("occupied", encoding="utf-8")
        path = afanes.core.vault.Vault(root).create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)
        assert path.name == "Ada 2.md"

    def test_allows_cross_scheme_reuse_in_different_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        person = afanes.core.vault.Vault(root).create(
            "Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON, directory=Path("people")
        )
        project = afanes.core.vault.Vault(root).create("Ada", NoteType.PROJECT, directory=Path("work"))
        assert person.name == "Ada.md"
        assert project.name == "Ada.md"

    def test_avoids_reserved_device_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.Vault(root).create("CON", NoteType.NOTE)
        assert path.name == "CON-note.md"

    def test_creates_a_missing_classification_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.Vault(root).create(
            "Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON, directory=Path("people")
        )
        assert path.parent.is_dir()

    def test_rejects_a_directory_that_escapes_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        with pytest.raises(VaultPathError):
            afanes.core.vault.Vault(root).create(
                "Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON, directory=Path("../outside")
            )

    def test_new_note_is_valid_markdown(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.Vault(root).create(
            "Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON, body="Hello\n"
        )
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.REFERENCE
        assert document.category is ReferenceCategory.PERSON
        assert "status" not in document.raw
        assert document.body == "Hello\n"

    def test_new_note_normalizes_line_endings_and_removes_a_bom(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.Vault(root).create("Ada", NoteType.NOTE, body="\ufeffone\r\ntwo\r")
        data = path.read_bytes()
        assert b"\r" not in data
        assert not data.startswith(b"\xef\xbb\xbf")
        assert data.endswith(b"one\ntwo\n")

    def test_default_omits_the_status_key(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.Vault(root).create("Ada", NoteType.NOTE)
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw == {"type": "note"}

    def test_explicit_status_is_written(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.Vault(root).create("Ada", NoteType.ACTION, status=Status.ACTIVE)
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.status is Status.ACTIVE

    def test_rejects_a_category_on_a_non_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(NoteParseError):
            afanes.core.vault.Vault(root).create(
                "Ada",
                NoteType.ACTION,
                category=ReferenceCategory.PERSON,
            )


class TestCaptureNote:
    def test_creates_a_minimal_note_in_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).capture("Buy milk")

        assert path == root / "inbox" / "Buy milk.md"
        assert [entry.name for entry in root.iterdir()] == ["inbox"]
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw == {"type": "note"}
        assert document.body == "Buy milk"

    def test_reuses_an_existing_inbox_case_variant(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Inbox").mkdir(parents=True)

        path = afanes.core.vault.Vault(root).capture("Buy milk")

        assert path == root / "Inbox" / "Buy milk.md"
        assert not (root / "inbox").exists()

    def test_uses_the_first_non_blank_line_as_the_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = "\n\nCall Ada\nabout the invoice\n"

        path = afanes.core.vault.Vault(root).capture(text)

        assert path.name == "Call Ada.md"
        assert NoteDocument.from_text(path.read_text(encoding="utf-8")).body == text

    def test_rejects_whitespace_only_text(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(EmptyCaptureError):
            afanes.core.vault.Vault(root).capture(" \n\t\n")

        assert not (root / "inbox").exists()

    def test_creates_the_inbox_directory_on_demand(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        afanes.core.vault.Vault(root).capture("Buy milk")

        assert (root / "inbox").is_dir()

    def test_repeated_captures_get_distinct_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        first = afanes.core.vault.Vault(root).capture("Buy milk")
        second = afanes.core.vault.Vault(root).capture("Buy milk")

        assert first.name == "Buy milk.md"
        assert second.name == "Buy milk 2.md"
        assert first.is_file()
        assert second.is_file()

    def test_sanitizes_the_first_line(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).capture("Q1: Planning?")

        assert path.name == "Q1 Planning.md"

    def test_does_not_modify_existing_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        existing = _write_note(root / "work/Existing.md", body="Do not touch")
        before = existing.read_bytes()

        afanes.core.vault.Vault(root).capture("Buy milk")

        assert existing.read_bytes() == before

    def test_does_not_infer_references_or_due_dates(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).capture("Ask Ada about 2026-11-20")

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw == {"type": "note"}
        assert document.references == ()
        snapshot = afanes.core.vault.Vault(root).scan()
        assert snapshot.notes[0].body_references == ()
        assert snapshot.notes[0].frontmatter_references == ()

    def test_reports_a_blocking_inbox_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        (root / "inbox").write_text("not a directory", encoding="utf-8")

        with pytest.raises(VaultError, match="not a directory"):
            afanes.core.vault.Vault(root).capture("Buy milk")


class TestMoveNote:
    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        with pytest.raises(VaultError):
            afanes.core.vault.Vault(root).move(note, Path("work"))
        assert note.exists()

    def test_moves_without_rewriting_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        before = referring.read_bytes()
        moved = afanes.core.vault.Vault(root).move(note, Path("work"), confirm=True)
        assert moved.parent == (root / "work").resolve()
        assert moved.name == "Ada.md"
        assert referring.read_bytes() == before

    def test_resolution_survives_a_move(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        afanes.core.vault.Vault(root).move(note, Path("work"), confirm=True)
        snapshot = afanes.core.vault.Vault(root).scan()
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.RESOLVED
        assert result.targets[0].parent.name == "work"

    def test_rejects_a_destination_collision(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "work/Ada.md", "person")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.Vault(root).move(note, Path("work"), confirm=True)

    def test_rejects_a_non_markdown_source(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = root / "notes.txt"
        text.write_text("body", encoding="utf-8")
        with pytest.raises(VaultPathError):
            afanes.core.vault.Vault(root).move(text, root, confirm=True)


class TestPlanRename:
    def test_reports_zero_affected_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert preview.reference_count == 0
        assert preview.affected == ()

    def test_counts_references_in_one_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert preview.reference_count == ONE
        assert preview.affected == (ReferenceSite(path=referring, reference_count=ONE),)

    def test_counts_many_references_across_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(
            root / "inbox/One.md",
            body="[Ada](<person:Ada>) and [again](<person:Ada>)",
            people=("person:Ada",),
        )
        _write_note(root / "inbox/Two.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert preview.reference_count == FOUR_REFERENCES
        assert len(preview.affected) == TWO

    def test_excludes_references_that_resolve_elsewhere(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "people/Grace.md", "person")
        _write_note(root / "inbox/Note.md", body="[Grace](<person:Grace>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert preview.affected == ()

    def test_excludes_ambiguous_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "archive/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert preview.affected == ()

    def test_rejects_a_same_scheme_collision(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "people/Grace.md", "person")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.Vault(root).plan_rename(note, "Grace")

    def test_allows_cross_scheme_name_reuse(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "work/Grace.md", "project")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Grace")
        assert preview.new_name == "Grace"

    def test_rejects_an_existing_target_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        target = root / "people/Ada King.md"
        target.write_text("---\ntype: errand\n---\n", encoding="utf-8")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

    def test_sanitizes_the_requested_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada: King?")
        assert preview.new_name == "Ada King"
        assert preview.target_path.name == "Ada King.md"

    def test_same_name_is_a_no_op(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada")
        assert preview.affected == ()
        assert preview.reference_count == 0

    def test_planning_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        before = _tree_state(root)
        afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert _tree_state(root) == before


class TestApplyRename:
    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        with pytest.raises(VaultError):
            afanes.core.vault.Vault(root).apply_rename(preview)
        assert note.exists()

    def test_renames_and_rewrites_destinations_and_labels(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert report.renamed is True
        assert not note.exists()
        assert (root / "people/Ada King.md").exists()
        assert "[Ada King](<person:Ada King>)" in referring.read_text(encoding="utf-8")

    def test_preserves_a_custom_label(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[my colleague](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert "[my colleague](<person:Ada King>)" in referring.read_text(encoding="utf-8")

    def test_rewrites_frontmatter_values(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(
            root / "inbox/Note.md",
            people=("person:Ada",),
            project="project:Turing",
        )
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        document = NoteDocument.from_text(referring.read_text(encoding="utf-8"))
        assert document.raw["people"] == ["person:Ada King"]
        assert document.raw["project"] == "project:Turing"

    def test_rewrites_a_self_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        target = root / "people/Ada King.md"
        assert "[Ada King](<person:Ada King>)" in target.read_text(encoding="utf-8")

    def test_skips_a_file_changed_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        referring.write_text(referring.read_text(encoding="utf-8") + "\nEdited externally.\n", encoding="utf-8")
        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert report.skipped == (referring,)
        assert report.updated == ()
        assert "[Ada](<person:Ada>)" in referring.read_text(encoding="utf-8")

    def test_reports_a_partial_failure_and_recovers_on_rerun(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        first = _write_note(root / "inbox/One.md", body="[Ada](<person:Ada>)")
        second = _write_note(root / "inbox/Two.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        original_write = afanes.core.atomic.write_text_atomic
        state = {"failed": False}

        def flaky_write(path: Path, text: str) -> None:
            if path == first and not state["failed"]:
                state["failed"] = True
                message = "disk full"
                raise OSError(message)
            original_write(path, text)

        monkeypatch.setattr(afanes.core.atomic, "write_text_atomic", flaky_write)
        first_report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert [failure.path for failure in first_report.failed] == [first]
        assert first_report.updated == (second,)

        second_report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert second_report.renamed is False
        assert second_report.failed == ()
        assert first in second_report.updated
        assert "[Ada King](<person:Ada King>)" in first.read_text(encoding="utf-8")

    def test_rerun_after_success_changes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        before = referring.read_bytes()
        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert report.renamed is False
        assert report.updated == ()
        assert referring.read_bytes() == before

    def test_rejects_a_target_created_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        (root / "people/Ada King.md").write_text("---\ntype: note\n---\n", encoding="utf-8")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)

    def test_rejects_a_missing_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        note.unlink()
        with pytest.raises(VaultError):
            afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)


class TestTrash:
    def test_reports_inbound_references_and_destination(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/One.md", body="[Ada](<person:Ada>)")
        _write_note(root / "inbox/Two.md", people=("person:Ada",))

        preview = afanes.core.vault.Vault(root).plan_trash(note)

        assert preview.reference_count == TWO
        assert len(preview.affected_notes) == TWO
        assert preview.trash_path == root / "trash" / "Ada.md"
        assert not (root / "trash").exists()

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")

        with pytest.raises(VaultError):
            afanes.core.vault.Vault(root).trash(note)

        assert note.exists()

    def test_moves_to_trash_without_modifying_referring_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        note_bytes = note.read_bytes()
        referring_bytes = referring.read_bytes()

        count = afanes.core.vault.Vault(root).trash(note, confirm=True)

        trashed = root / "trash" / "Ada.md"
        assert count == ONE
        assert not note.exists()
        assert trashed.read_bytes() == note_bytes
        assert referring.read_bytes() == referring_bytes

    def test_references_become_unresolved_after_trashing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        afanes.core.vault.Vault(root).trash(note, confirm=True)
        snapshot = afanes.core.vault.Vault(root).scan()
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.UNRESOLVED

    def test_trashing_an_unreferenced_note_reports_zero(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        assert afanes.core.vault.Vault(root).trash(note, confirm=True) == 0

    def test_reuses_an_existing_trash_case_variant(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Trash").mkdir(parents=True)
        note = _write_note(root / "people/Ada.md", "person")

        afanes.core.vault.Vault(root).trash(note, confirm=True)

        assert (root / "Trash" / "Ada.md").is_file()
        assert not (root / "trash").exists()

    def test_uses_a_unique_name_inside_trash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "trash").mkdir(parents=True)
        (root / "trash" / "Ada.md").write_text("older", encoding="utf-8")
        note = _write_note(root / "people/Ada.md", "person")

        afanes.core.vault.Vault(root).trash(note, confirm=True)

        assert (root / "trash" / "Ada 2.md").is_file()
