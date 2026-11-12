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
import afanes.core.vault
from afanes.core.errors import (
    ContentChangedError,
    EmptyCaptureError,
    NameCollisionError,
    NoteParseError,
    ProcessingError,
    VaultError,
    VaultMissingError,
    VaultNotDirectoryError,
    VaultNotEmptyError,
    VaultPathError,
    VaultUnreadableError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.processing import AppendStepPlan, ProcessingOutcome
from afanes.core.vault import LinkOutcome, NoteOrder, ParsedPage, ReferenceSite, UnparsedPage, VaultNote
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteType, Status

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
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _set_modified_ns(path: Path, modified_ns: int) -> None:
    os.utime(path, ns=(modified_ns, modified_ns))


class TestNoteOrder:
    def _note(
        self,
        *,
        name: str = "Note",
        title: str = "Note",
        due_date: datetime.date | None = None,
        status: Status | None = None,
        modified_ns: int = 0,
    ) -> VaultNote:
        return VaultNote(
            path=Path("/vault") / f"{name}.md",
            relative_path=Path(f"{name}.md"),
            name=name,
            title=title,
            note_type=NoteType.NOTE,
            category=None,
            status=status,
            due_date=due_date,
            content_hash="",
            modified_ns=modified_ns,
            body_references=(),
            steps=(),
            search_text="",
        )

    def test_dated_notes_sort_before_undated_notes(self) -> None:
        dated = self._note(name="Dated", due_date=datetime.date(2026, 1, 1)).order
        undated = self._note(name="Undated").order

        assert dated < undated

    def test_earlier_due_dates_sort_first(self) -> None:
        earlier = self._note(name="A", due_date=datetime.date(2026, 1, 1)).order
        later = self._note(name="Z", due_date=datetime.date(2026, 6, 1)).order

        assert earlier < later

    def test_alphabetical_order_ignores_due_date(self) -> None:
        titled = self._note(name="Alpha", title="Alpha")

        assert titled.alphabetical_order == NoteOrder(True, datetime.date.max, 0, "alpha", "alpha", "Alpha.md")

    def test_inbox_order_places_newer_notes_first(self) -> None:
        newer = self._note(name="Newer", modified_ns=2).inbox_order
        older = self._note(name="Older", modified_ns=1).inbox_order

        assert newer < older

    def test_equal_fields_produce_equal_keys(self) -> None:
        first = NoteOrder(False, datetime.date(2026, 1, 1), 0, "a", "a", "a.md")
        second = NoteOrder(False, datetime.date(2026, 1, 1), 0, "a", "a", "a.md")

        assert first == second


class TestVaultService:
    def test_resolves_a_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.Vault(root).root == root.resolve()

    def test_rejects_a_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "note.md"
        file_path.write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotDirectoryError):
            afanes.core.vault.Vault(file_path)

    def test_rejects_a_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultMissingError):
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


class TestVaultOpen:
    def test_opens_an_existing_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        vault = afanes.core.vault.Vault.open(root)

        assert vault.root == root.resolve()

    def test_rejects_a_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultMissingError):
            afanes.core.vault.Vault.open(tmp_path / "missing")

    def test_rejects_a_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "note.md"
        file_path.write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotDirectoryError):
            afanes.core.vault.Vault.open(file_path)

    def test_rejects_an_unreadable_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        monkeypatch.setattr(afanes.core.vault.os, "access", lambda _path, _mode: False)

        with pytest.raises(VaultUnreadableError):
            afanes.core.vault.Vault.open(root)

    def test_resolves_a_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        monkeypatch.chdir(tmp_path)

        vault = afanes.core.vault.Vault.open(Path("vault"))

        assert vault.root == root.resolve()


class TestDirectoryFor:
    def test_note_uses_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.Vault(root).directory_for(NoteType.NOTE) == root / "inbox"

    def test_project_uses_projects(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.Vault(root).directory_for(NoteType.PROJECT) == root / "projects"

    def test_uncategorized_reference_uses_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert afanes.core.vault.Vault(root).directory_for(NoteType.REFERENCE) == root / "reference"

    def test_category_label_selects_a_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        directory = afanes.core.vault.Vault(root).directory_for(NoteType.REFERENCE, CategoryLabel("place"))

        assert directory == root / "reference" / "place"

    def test_reuses_an_existing_case_variant(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Inbox").mkdir(parents=True)
        (root / "reference" / "Place").mkdir(parents=True)

        vault = afanes.core.vault.Vault(root)
        assert vault.directory_for(NoteType.NOTE) == root / "Inbox"
        assert vault.directory_for(NoteType.REFERENCE, CategoryLabel("place")) == root / "reference" / "Place"

    def test_does_not_create_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        vault.directory_for(NoteType.NOTE)
        vault.directory_for(NoteType.PROJECT)
        vault.directory_for(NoteType.REFERENCE, CategoryLabel("place"))

        assert list(root.iterdir()) == []

    def test_rejects_a_category_on_a_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(VaultError):
            afanes.core.vault.Vault(root).directory_for(NoteType.NOTE, CategoryLabel("place"))


class TestVaultCreation:
    def test_creates_a_missing_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "vault"

        creation = afanes.core.vault.Vault.create_directory(target)

        assert creation.vault.root == target.resolve()
        assert target.is_dir()

    def test_creates_missing_intermediate_folders(self, tmp_path: Path) -> None:
        target = tmp_path / "notes" / "personal" / "vault"

        creation = afanes.core.vault.Vault.create_directory(target)

        assert creation.created_directories == (tmp_path / "notes", tmp_path / "notes" / "personal")
        assert target.is_dir()

    def test_seeds_an_empty_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "vault"
        target.mkdir()

        creation = afanes.core.vault.Vault.create_directory(target)

        assert creation.created_directories == ()
        assert creation.vault.root == target.resolve()

    def test_refuses_a_non_empty_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "vault"
        target.mkdir()
        (target / "photo.jpg").write_text("data", encoding="utf-8")

        with pytest.raises(VaultNotEmptyError):
            afanes.core.vault.Vault.create_directory(target)

        assert sorted(path.name for path in target.iterdir()) == ["photo.jpg"]

    def test_refuses_a_file(self, tmp_path: Path) -> None:
        target = tmp_path / "note.md"
        target.write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotDirectoryError):
            afanes.core.vault.Vault.create_directory(target)

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
            afanes.core.vault.Vault.create_directory(link)

    def test_seeds_every_default_folder(self, tmp_path: Path) -> None:
        layout = afanes.core.vault.Vault.default_layout()

        creation = afanes.core.vault.Vault.create_directory(tmp_path / "vault")

        root = creation.vault.root
        assert [path.relative_to(root) for path in creation.seeded_directories] == list(layout)
        assert all((root / relative).is_dir() for relative in layout)

    def test_seeded_paths_match_directory_for(self, tmp_path: Path) -> None:
        creation = afanes.core.vault.Vault.create_directory(tmp_path / "vault")
        vault = creation.vault
        expected = [
            vault.directory_for(NoteType.NOTE),
            vault.root / "trash",
            vault.directory_for(NoteType.REFERENCE),
            vault.directory_for(NoteType.PROJECT),
        ]

        assert list(creation.seeded_directories) == expected

    def test_creation_writes_only_the_guide(self, tmp_path: Path) -> None:
        creation = afanes.core.vault.Vault.create_directory(tmp_path / "vault")

        files = [
            path.relative_to(creation.vault.root).as_posix()
            for path in creation.vault.root.rglob("*")
            if path.is_file()
        ]
        assert files == ["reference/Getting started.md"]

    def test_refusal_writes_nothing(self, tmp_path: Path) -> None:
        target = tmp_path / "vault"
        target.mkdir()
        (target / "existing.md").write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotEmptyError):
            afanes.core.vault.Vault.create_directory(target)

        assert sorted(path.name for path in target.iterdir()) == ["existing.md"]
        assert [path.name for path in tmp_path.iterdir()] == ["vault"]

    @hypothesis.given(hypothesis.strategies.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6))
    def test_seeded_paths_stay_inside_the_created_root(self, name: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / f"vault-{name}"

            creation = afanes.core.vault.Vault.create_directory(target)

            root = creation.vault.root
            assert root == target.resolve()
            assert all(path.is_relative_to(root) for path in creation.seeded_directories)


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
        active = _write_note(root / "reference/person/Ada.md", "person")
        snapshot = afanes.core.vault.Vault(root).scan()

        resolution = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
        assert resolution.outcome is ResolutionOutcome.RESOLVED
        assert resolution.targets == (active,)

    def test_reference_to_a_trashed_note_is_unresolved(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "trash/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](note:Ada)")
        snapshot = afanes.core.vault.Vault(root).scan()

        resolution = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
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
        assert by_name["Ada"].category == CategoryLabel("person")
        assert by_name["Ada"].status is Status.LATER
        assert by_name["Launch"].category is None
        assert by_name["Launch"].status is Status.ACTIVE

    def test_reports_an_invalid_status(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Bad.md", "project", status="inbox")
        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_records_a_due_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", "project", due_date="2026-11-20")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes[0].due_date == datetime.date(2026, 11, 20)

    def test_absent_due_date_is_none(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", "project")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes[0].due_date is None

    def test_null_due_date_is_none(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", "project", due_date="null")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes[0].due_date is None

    def test_invalid_due_date_is_reported_as_a_failure(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Call.md", "project", due_date='"next Friday"')

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
        _write_note(root / "Bad.md", "project", category="person")
        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_records_the_content_hash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_note(root / "Ada.md")
        snapshot = afanes.core.vault.Vault(root).scan()
        assert snapshot.notes[0].content_hash == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_records_the_heading_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Ada.md", body="# Ada, Countess of Lovelace")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes[0].name == "Ada"
        assert snapshot.notes[0].title == "Ada, Countess of Lovelace"

    def test_title_falls_back_to_the_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Ada.md", body="No heading")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes[0].title == "Ada"

    def test_an_invalid_note_with_a_heading_is_still_reported(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        bad = root / "Ada.md"
        bad.parent.mkdir(parents=True)
        bad.write_text("---\ntype: [unclosed\n---\n# Ada\n", encoding="utf-8")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.notes == ()
        assert [failure.path.as_posix() for failure in snapshot.failures] == ["Ada.md"]

    def test_extracts_body_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Note.md", body="[Ada](<note:Ada Lovelace>)")
        snapshot = afanes.core.vault.Vault(root).scan()
        note = snapshot.notes[0]
        assert note.body_references == (NoteReference(scheme=ReferenceScheme.NOTE, name="Ada Lovelace", label="Ada"),)

    def test_project_note_derives_steps_and_search_text(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root / "projects/Home.md",
            "project",
            body="# Home\n\n- [ ] Call the plumber <!-- {owners: [Ada], plan: 2026-11-20} -->\n",
        )

        note = afanes.core.vault.Vault(root).scan().notes[0]

        assert [step.text for step in note.steps] == ["Call the plumber"]
        assert note.next_step is not None
        assert "Ada" not in note.search_text
        assert "Call the plumber" in note.search_text

    def test_reference_note_has_no_steps(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "reference/Errands.md", "reference", body="- [ ] Buy milk\n")

        note = afanes.core.vault.Vault(root).scan().notes[0]

        assert note.steps == ()

    def test_misplaced_note_is_flagged(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "notes/Later.md", "note")

        note = afanes.core.vault.Vault(root).scan().notes[0]

        assert note.is_misplaced is True

    def test_scan_performs_no_writes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Ada.md", body="[Grace](note:Grace)")
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
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
        assert result.outcome is ResolutionOutcome.AMBIGUOUS
        assert len(result.targets) == TWO


class TestReadPage:
    def test_reads_a_note_with_its_text_and_hash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "notes" / "Ada.md", body="# Ada\n")

        content = afanes.core.vault.Vault(root).read_page(path)

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

        content = afanes.core.vault.Vault(root).read_page(path)

        assert isinstance(content, UnparsedPage)
        assert content.failure
        assert content.text == text
        assert content.content_hash == hashlib.sha256(text.encode("utf-8")).hexdigest()

    def test_missing_note_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultPathError):
            vault.read_page(Path("missing.md"))

    def test_path_outside_the_vault_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        outside = tmp_path / "outside.md"
        outside.write_text("body", encoding="utf-8")
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultPathError):
            vault.read_page(outside)

    def test_directory_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        directory = root / "notes"
        directory.mkdir()
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultPathError):
            vault.read_page(directory)


class TestWritePage:
    def test_writes_after_a_matching_hash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "notes" / "Ada.md", body="Old body\n")
        vault = afanes.core.vault.Vault(root)
        content = vault.read_page(path)
        new_text = "---\ntype: note\n---\n\n# New body\n"

        new_hash = vault.write_page(path, new_text, content.content_hash)

        assert path.read_text(encoding="utf-8") == new_text
        assert new_hash == hashlib.sha256(new_text.encode("utf-8")).hexdigest()
        assert vault.read_page(path).content_hash == new_hash

    def test_conflict_leaves_the_file_unchanged(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "notes" / "Ada.md", body="Old body\n")
        original = path.read_bytes()
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(ContentChangedError):
            vault.write_page(path, "replacement", "0" * 64)

        assert path.read_bytes() == original

    def test_missing_note_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultPathError):
            vault.write_page(Path("missing.md"), "body", "0" * 64)

    def test_path_outside_the_vault_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        outside = tmp_path / "outside.md"
        outside.write_text("body", encoding="utf-8")
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultPathError):
            vault.write_page(outside, "body", "0" * 64)

    def test_writes_crlf_text_as_provided(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "notes" / "Ada.md", body="Old body\n")
        vault = afanes.core.vault.Vault(root)
        content = vault.read_page(path)
        new_text = "---\r\ntype: note\r\n---\r\n\r\n# New\r\n"

        vault.write_page(path, new_text, content.content_hash)

        assert path.read_bytes() == new_text.encode("utf-8")


class TestLinkTarget:
    def test_resolves_a_unique_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "reference" / "person" / "Ada.md", note_type="person")
        snapshot = afanes.core.vault.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Ada"))

        assert target.outcome is LinkOutcome.RESOLVED
        assert target.paths == (path.resolve(),)

    def test_reports_every_ambiguous_candidate(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        first = _write_note(root / "reference" / "person" / "Ada.md", note_type="person")
        second = _write_note(root / "notes" / "Ada.md", note_type="person")
        snapshot = afanes.core.vault.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Ada"))

        assert target.outcome is LinkOutcome.AMBIGUOUS
        assert set(target.paths) == {first.resolve(), second.resolve()}

    def test_reports_a_missing_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        snapshot = afanes.core.vault.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Nobody"))

        assert target.outcome is LinkOutcome.MISSING
        assert target.paths == ()

    def test_routes_to_an_unparseable_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        broken = root / "reference" / "Broken.md"
        broken.parent.mkdir()
        broken.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        snapshot = afanes.core.vault.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Broken"))

        assert target.outcome is LinkOutcome.BROKEN
        assert target.paths == (broken.resolve(),)

    def test_reports_every_unparseable_candidate(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        first = root / "reference" / "Broken.md"
        first.parent.mkdir()
        first.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        second = root / "notes" / "Broken.md"
        second.parent.mkdir()
        second.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        snapshot = afanes.core.vault.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Broken"))

        assert target.outcome is LinkOutcome.BROKEN
        assert set(target.paths) == {first.resolve(), second.resolve()}

    def test_failure_matching_ignores_case(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        broken = root / "reference" / "ADA.md"
        broken.parent.mkdir()
        broken.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        snapshot = afanes.core.vault.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "ada"))

        assert target.outcome is LinkOutcome.BROKEN
        assert target.paths == (broken.resolve(),)

    def test_a_resolved_note_wins_over_a_failure(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        valid = _write_note(root / "reference" / "Ada.md", body="# Ada\n")
        broken = root / "notes" / "Ada.md"
        broken.parent.mkdir()
        broken.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        snapshot = afanes.core.vault.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Ada"))

        assert target.outcome is LinkOutcome.RESOLVED
        assert target.paths == (valid.resolve(),)


class TestReferrers:
    def test_counts_unique_inbound_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        target = _write_note(root / "reference" / "person" / "Ada.md", note_type="person")
        one = _write_note(root / "notes" / "One.md", body="[Ada](<note:Ada>)\n[ada](<note:ada>)\n")
        two = _write_note(root / "notes" / "Two.md", body="[Ada](<note:Ada>)\n")
        snapshot = afanes.core.vault.Vault(root).scan()

        sites = snapshot.referrers(target)

        assert [(site.path, site.reference_count) for site in sites] == [(one.resolve(), 2), (two.resolve(), 1)]

    def test_ambiguous_references_are_not_attributed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        first = _write_note(root / "reference" / "person" / "Ada.md", note_type="person")
        _write_note(root / "notes" / "Ada.md", note_type="person")
        _write_note(root / "notes" / "One.md", body="[Ada](<note:Ada>)\n")
        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.referrers(first) == ()


class TestReferenceRepair:
    def test_plans_and_rewrites_every_referring_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        one = _write_note(root / "notes" / "One.md", body="[Q1](<note:Q1: Planning?>)\n")
        two = _write_note(root / "notes" / "Two.md", body="# Two\n\n[Q1](<note:Q1: Planning?>)\n")
        vault = afanes.core.vault.Vault(root)
        snapshot = vault.scan()

        preview = vault.plan_reference_repair(old, new, snapshot=snapshot)

        assert [(site.path, site.reference_count) for site in preview.sites] == [(one.resolve(), 1), (two.resolve(), 1)]
        assert set(preview.content_hashes) == {one.resolve(), two.resolve()}
        assert "Q1: Planning?" in one.read_text(encoding="utf-8")

        report = vault.apply_reference_repair(preview, confirm=True)

        assert set(report.updated) == {one.resolve(), two.resolve()}
        assert report.skipped == ()
        assert report.failed == ()
        assert "note:Q1 Planning" in one.read_text(encoding="utf-8")
        assert "note:Q1 Planning" in two.read_text(encoding="utf-8")
        assert "Q1: Planning?" not in one.read_text(encoding="utf-8")

    def test_preserves_custom_labels_and_leaves_safe_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        path = _write_note(
            root / "notes" / "One.md",
            body="[Quarterly plan](<note:Q1: Planning?>)\n[Safe](<note:Q1 Planning>)\n",
        )
        vault = afanes.core.vault.Vault(root)
        preview = vault.plan_reference_repair(old, new, snapshot=vault.scan())

        vault.apply_reference_repair(preview, confirm=True)

        text = path.read_text(encoding="utf-8")
        assert "Quarterly plan" in text
        assert "note:Q1 Planning" in text
        assert "note:Q1: Planning?" not in text

    def test_skips_a_file_changed_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        first = _write_note(root / "notes" / "One.md", body="[Q1](<note:Q1: Planning?>)\n")
        second = _write_note(root / "notes" / "Two.md", body="[Q1](<note:Q1: Planning?>)\n")
        vault = afanes.core.vault.Vault(root)
        preview = vault.plan_reference_repair(old, new, snapshot=vault.scan())
        changed = second.read_text(encoding="utf-8") + "\nExternal edit.\n"
        second.write_text(changed, encoding="utf-8", newline="\n")

        report = vault.apply_reference_repair(preview, confirm=True)

        assert report.updated == (first.resolve(),)
        assert report.skipped == (second.resolve(),)
        assert second.read_text(encoding="utf-8") == changed

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        vault = afanes.core.vault.Vault(root)
        preview = vault.plan_reference_repair(old, new, snapshot=vault.scan())

        with pytest.raises(VaultError):
            vault.apply_reference_repair(preview)

    def test_rejects_a_cross_scheme_repair(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultError):
            vault.plan_reference_repair(
                NoteReference(ReferenceScheme.NOTE, "Ada"),
                NoteReference(ReferenceScheme.PROJECT, "Ada"),
                snapshot=vault.scan(),
            )

    def test_repairs_body_values(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        old = NoteReference(ReferenceScheme.NOTE, "Ada?")
        new = NoteReference(ReferenceScheme.NOTE, "Ada")
        path = _write_note(root / "notes" / "Call.md", body="[Ada](<note:Ada?>)")
        vault = afanes.core.vault.Vault(root)
        preview = vault.plan_reference_repair(old, new, snapshot=vault.scan())

        vault.apply_reference_repair(preview, confirm=True)

        assert "note:Ada>" in path.read_text(encoding="utf-8")
        assert "note:Ada?>" not in path.read_text(encoding="utf-8")


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


class TestAssignmentCandidates:
    def test_matches_an_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project", body="# Home improvements\n")

        snapshot = afanes.core.vault.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "home")
        assert [note.name for note in candidates] == ["Home"]

    def test_matches_a_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project", body="# Home improvements\n")

        snapshot = afanes.core.vault.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "improvements")
        assert [note.name for note in candidates] == ["Home"]

    def test_matching_ignores_case_and_repeated_whitespace(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project", body="# Home,   improvements\n")

        snapshot = afanes.core.vault.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "home,   improvements")
        assert [note.name for note in candidates] == ["Home"]

    def test_duplicate_titles_are_distinguished_by_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project", body="# Home improvements\n")
        _write_note(root / "projects/Cabin.md", "project", body="# Home improvements\n")

        snapshot = afanes.core.vault.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "improvements")
        assert [note.name for note in candidates] == ["Cabin", "Home"]

    def test_filters_by_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "reference/Ada.md", "reference", body="# Ada\n")
        _write_note(root / "projects/Ada.md", "project", body="# Ada\n")

        snapshot = afanes.core.vault.Vault(root).scan()

        notes = snapshot.assignment_candidates(ReferenceScheme.NOTE, "ada")
        projects = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "ada")
        assert [note.name for note in notes] == ["Ada"]
        assert [note.name for note in projects] == ["Ada"]
        assert notes[0].note_type is NoteType.REFERENCE
        assert projects[0].note_type is NoteType.PROJECT

    def test_empty_query_returns_every_note_in_the_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Cabin.md", "project", body="# Cabin\n")
        _write_note(root / "projects/Home.md", "project", body="# Home\n")
        _write_note(root / "reference/Launch.md", "reference", body="# Launch\n")

        snapshot = afanes.core.vault.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "")
        assert [note.name for note in candidates] == ["Cabin", "Home"]

    def test_no_match_returns_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project")

        snapshot = afanes.core.vault.Vault(root).scan()

        assert snapshot.assignment_candidates(ReferenceScheme.PROJECT, "missing") == ()


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

    def test_defaults_to_the_category_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create(
            "Ada",
            NoteType.REFERENCE,
            category=CategoryLabel("person"),
        )

        assert path == root / "reference" / "person" / "Ada.md"

    def test_suffixes_a_collision_within_the_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        afanes.core.vault.Vault(root).create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))
        second = afanes.core.vault.Vault(root).create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))
        assert second.name == "Ada 2.md"

    def test_suffixes_a_collision_with_an_existing_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "reference" / "person").mkdir(parents=True)
        (root / "reference" / "person" / "Ada.txt").write_text("occupied", encoding="utf-8")
        path = afanes.core.vault.Vault(root).create("Ada", NoteType.REFERENCE, category=CategoryLabel("person"))
        assert path.name == "Ada 2.md"

    def test_allows_cross_scheme_reuse_in_different_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        person = afanes.core.vault.Vault(root).create(
            "Ada", NoteType.REFERENCE, category=CategoryLabel("person"), directory=Path("people")
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
            "Ada", NoteType.REFERENCE, category=CategoryLabel("person"), directory=Path("people")
        )
        assert path.parent.is_dir()

    def test_rejects_a_directory_that_escapes_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        with pytest.raises(VaultPathError):
            afanes.core.vault.Vault(root).create(
                "Ada", NoteType.REFERENCE, category=CategoryLabel("person"), directory=Path("../outside")
            )

    def test_new_note_is_valid_markdown(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.Vault(root).create(
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
        path = afanes.core.vault.Vault(root).create("Ada", NoteType.PROJECT, status=Status.ACTIVE)
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.status is Status.ACTIVE

    def test_rejects_a_category_on_a_non_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(NoteParseError):
            afanes.core.vault.Vault(root).create(
                "Ada",
                NoteType.NOTE,
                category=CategoryLabel("person"),
            )


class TestCreatePage:
    def test_creates_the_exact_sanitized_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create_page(
            "Q1: Planning?",
            NoteType.REFERENCE,
            body="# Q1: Planning?\n",
        )

        assert path == root / "reference" / "Q1 Planning.md"
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.REFERENCE
        assert document.body == "# Q1: Planning?\n"
        assert "status" not in document.raw
        assert "category" not in document.raw

    def test_categorized_page_uses_the_label_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create_page(
            "Ada",
            NoteType.REFERENCE,
            CategoryLabel("person"),
        )

        assert path == root / "reference" / "person" / "Ada.md"
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.category == CategoryLabel("person")

    def test_project_page_uses_the_projects_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create_page("Release 1.0", NoteType.PROJECT)

        assert path == root / "projects" / "Release 1.0.md"

    def test_rejects_a_name_used_in_the_same_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        _write_note(root / "notes" / "Quarterly budget.md", body="Existing\n")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.Vault(root).create_page("Quarterly budget", NoteType.REFERENCE)

        assert not (root / "reference" / "Quarterly budget.md").exists()
        assert not (root / "reference" / "Quarterly budget 2.md").exists()

    def test_rejects_a_case_variant_in_the_target_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        target = root / "reference"
        target.mkdir()
        (target / "quarterly budget.md").write_text("body", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.Vault(root).create_page("Quarterly budget", NoteType.REFERENCE)

    def test_allows_cross_scheme_reuse_in_another_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        _write_note(root / "projects" / "Ada.md", note_type="project")

        path = afanes.core.vault.Vault(root).create_page("Ada", NoteType.REFERENCE)

        assert path == root / "reference" / "Ada.md"
        assert path.exists()

    def test_creates_a_missing_category_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).create_page(
            "Ada",
            NoteType.REFERENCE,
            CategoryLabel("person"),
        )

        assert path.parent == root / "reference" / "person"
        assert path.parent.is_dir()

    def test_rejects_a_category_on_a_non_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(NoteParseError):
            afanes.core.vault.Vault(root).create_page(
                "Ada",
                NoteType.NOTE,
                CategoryLabel("person"),
            )

    def test_writes_supplied_text_exactly(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = "---\ntype: reference\ncategory: person\ncustom: keep\n---\n\n# Ada\n\nBody.\n"

        path = afanes.core.vault.Vault(root).create_page(
            "Ada",
            NoteType.REFERENCE,
            CategoryLabel("person"),
            text=text,
        )

        assert path.read_text(encoding="utf-8") == text

    def test_rejects_supplied_text_with_a_different_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = "---\ntype: project\n---\n\n# Ada\n"

        with pytest.raises(NoteParseError):
            afanes.core.vault.Vault(root).create_page("Ada", NoteType.REFERENCE, text=text)

    def test_rejects_invalid_supplied_text(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(NoteParseError):
            afanes.core.vault.Vault(root).create_page(
                "Ada",
                NoteType.REFERENCE,
                text="---\ntype: refrence\n---\n",
            )


class TestRecreatePage:
    def test_recreates_a_missing_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = root / "reference" / "Ada.md"
        path.parent.mkdir()
        text = "---\ntype: reference\n---\n\n# Ada\n"
        vault = afanes.core.vault.Vault(root)

        content_hash = vault.recreate_page(path, text)

        assert path.read_text(encoding="utf-8") == text
        assert content_hash == hashlib.sha256(text.encode("utf-8")).hexdigest()

    def test_refuses_an_existing_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "reference" / "Ada.md", body="Existing\n")
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(ContentChangedError):
            vault.recreate_page(path, "replacement")

    def test_requires_an_existing_parent(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultError):
            vault.recreate_page(Path("missing/Ada.md"), "text")

    def test_rejects_a_path_outside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        with pytest.raises(VaultPathError):
            vault.recreate_page(tmp_path / "outside.md", "text")


class TestCaptureNote:
    def test_creates_a_minimal_note_in_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).capture("Buy milk")

        assert path == root / "inbox" / "Buy milk.md"
        assert [entry.name for entry in root.iterdir()] == ["inbox"]
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw == {"type": "note"}
        assert document.body == "# Buy milk"

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
        assert NoteDocument.from_text(path.read_text(encoding="utf-8")).body == "\n\n# Call Ada\nabout the invoice\n"

    def test_leaves_an_existing_heading_alone(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = "# Call Ada\nabout the invoice\n"

        path = afanes.core.vault.Vault(root).capture(text)

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))

        assert document.body == text
        assert document.title == "Call Ada"

    def test_templates_a_sanitized_first_line_without_changing_it(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.Vault(root).capture("Q1: Planning?")

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        snapshot = afanes.core.vault.Vault(root).scan()

        assert path.name == "Q1 Planning.md"
        assert document.body == "# Q1: Planning?"
        assert snapshot.notes[0].title == "Q1: Planning?"

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
        snapshot = afanes.core.vault.Vault(root).scan()
        assert snapshot.notes[0].body_references == ()
        assert snapshot.notes[0].steps == ()

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
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
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
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
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
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert preview.reference_count == ONE
        assert preview.affected == (ReferenceSite(path=referring, reference_count=ONE),)

    def test_counts_many_references_across_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(
            root / "inbox/One.md",
            body="[Ada](<note:Ada>) and [again](<note:Ada>)",
        )
        _write_note(root / "inbox/Two.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert preview.reference_count == THREE_REFERENCES
        assert len(preview.affected) == TWO

    def test_excludes_references_that_resolve_elsewhere(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "people/Grace.md", "person")
        _write_note(root / "inbox/Note.md", body="[Grace](<note:Grace>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        assert preview.affected == ()

    def test_excludes_ambiguous_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "archive/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
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
        _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada")
        assert preview.affected == ()
        assert preview.reference_count == 0
        assert preview.heading_update is False

    def test_records_a_matching_heading_update(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada\n")

        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        assert preview.heading_update is True

    def test_does_not_update_a_custom_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada, Countess of Lovelace\n")

        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        assert preview.heading_update is False

    def test_does_not_add_a_missing_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="Body.\n")

        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        assert preview.heading_update is False

    def test_does_not_update_a_heading_inside_code(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="```\n# Ada\n```\n")

        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        assert preview.heading_update is False

    def test_planning_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
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
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert report.renamed is True
        assert not note.exists()
        assert (root / "people/Ada King.md").exists()
        assert "[Ada King](<note:Ada King>)" in referring.read_text(encoding="utf-8")

    def test_preserves_a_custom_label(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[my colleague](<note:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert "[my colleague](<note:Ada King>)" in referring.read_text(encoding="utf-8")

    def test_rewrites_body_values(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(
            root / "inbox/Note.md",
            body="[Ada](<note:Ada>)",
        )
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        document = NoteDocument.from_text(referring.read_text(encoding="utf-8"))
        assert "[Ada King](<note:Ada King>)" in document.body

    def test_rewrites_a_self_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        target = root / "people/Ada King.md"
        assert "[Ada King](<note:Ada King>)" in target.read_text(encoding="utf-8")

    def test_skips_a_file_changed_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        referring.write_text(referring.read_text(encoding="utf-8") + "\nEdited externally.\n", encoding="utf-8")
        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert report.skipped == (referring,)
        assert report.updated == ()
        assert "[Ada](<note:Ada>)" in referring.read_text(encoding="utf-8")

    def test_reports_a_partial_failure_and_recovers_on_rerun(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        first = _write_note(root / "inbox/One.md", body="[Ada](<note:Ada>)")
        second = _write_note(root / "inbox/Two.md", body="[Ada](<note:Ada>)")
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
        assert "[Ada King](<note:Ada King>)" in first.read_text(encoding="utf-8")

    def test_rerun_after_success_changes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        before = referring.read_bytes()
        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert report.renamed is False
        assert report.updated == ()
        assert referring.read_bytes() == before

    def test_updates_a_matching_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada\n\nBody.\n")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)

        target = root / "people/Ada King.md"
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert report.updated == (target,)
        assert document.body == "\n# Ada King\n\nBody.\n"

    def test_preserves_a_custom_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(
            root / "people/Ada.md",
            "person",
            body="# Ada, Countess of Lovelace\n\nBody.\n",
        )
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)

        target = root / "people/Ada King.md"
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.body == "\n# Ada, Countess of Lovelace\n\nBody.\n"

    def test_does_not_add_a_missing_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="Body.\n")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)

        target = root / "people/Ada King.md"
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.body == "\nBody.\n"
        assert document.title is None

    def test_updates_heading_and_self_reference_together(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(
            root / "people/Ada.md",
            "person",
            body="# Ada\n\n[Ada](<note:Ada>)\n",
        )
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")

        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)

        target = root / "people/Ada King.md"
        text = target.read_text(encoding="utf-8")
        assert report.updated == (target,)
        assert "# Ada King" in text
        assert "note:Ada King" in text
        assert "note:Ada)" not in text

    def test_skips_a_heading_update_when_the_file_changed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada\n")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        note.write_text(
            "---\ntype: reference\ncategory: person\n---\n\n# Ada\n\nExternal edit.\n",
            encoding="utf-8",
            newline="\n",
        )

        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)

        target = root / "people/Ada King.md"
        assert report.updated == ()
        assert report.skipped == (target,)
        assert "# Ada\n" in target.read_text(encoding="utf-8")

    def test_rerun_after_a_heading_update_changes_no_bytes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada\n")
        preview = afanes.core.vault.Vault(root).plan_rename(note, "Ada King")
        afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        target = root / "people/Ada King.md"
        before = target.read_bytes()

        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)

        assert report.updated == ()
        assert target.read_bytes() == before

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
        _write_note(root / "inbox/One.md", body="[Ada](<note:Ada>)")
        _write_note(root / "inbox/Two.md", body="[Ada](<note:Ada>)")

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
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
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
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
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


class TestSetStatus:
    def test_sets_a_project_status_without_touching_other_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write_note(root / "projects/Machine.md", "project", status="active")
        other = _write_note(root / "reference/Build.md", "reference", body="# Build\n")
        other_bytes = other.read_bytes()
        vault = afanes.core.vault.Vault(root)

        vault.set_status(project, Status.DONE, confirm=True)

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert document.status is Status.DONE
        assert other.read_bytes() == other_bytes

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write_note(root / "projects/Machine.md", "project", status="active")

        with pytest.raises(VaultError):
            afanes.core.vault.Vault(root).set_status(project, Status.DONE)

        assert "status: active" in project.read_text(encoding="utf-8")

    def test_preserves_unknown_keys_and_newline_style(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = root / "projects" / "Machine.md"
        project.parent.mkdir(parents=True)
        project.write_bytes(b"---\r\ntype: project\r\nstatus: active\r\nx-custom: kept\r\n---\r\n# Machine\r\n")

        afanes.core.vault.Vault(root).set_status(project, Status.LATER, confirm=True)

        data = project.read_bytes()
        assert b"x-custom: kept" in data
        assert b"\r\n" in data
        assert b"status: later" in data

    def test_rejects_a_status_invalid_for_the_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "notes/Idea.md", "note")

        with pytest.raises(NoteParseError):
            afanes.core.vault.Vault(root).set_status(note, Status.ACTIVE, confirm=True)

    def test_rejects_a_file_changed_after_the_snapshot(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write_note(root / "projects/Machine.md", "project", status="active")
        snapshot = afanes.core.vault.Vault(root).scan()
        project.write_text("---\ntype: project\nstatus: waiting\n---\n", encoding="utf-8")

        with pytest.raises(ContentChangedError):
            afanes.core.vault.Vault(root).set_status(project, Status.DONE, snapshot=snapshot, confirm=True)


class TestNoteHelpers:
    def test_due_date_from_raw_accepts_dates_and_iso_strings(self) -> None:
        assert VaultNote.due_date_from_raw(datetime.date(2026, 11, 20)) == datetime.date(2026, 11, 20)
        assert VaultNote.due_date_from_raw("2026-11-20") == datetime.date(2026, 11, 20)
        assert VaultNote.due_date_from_raw(" not-a-date ") is None
        assert VaultNote.due_date_from_raw(datetime.datetime(2026, 11, 20, 10, 0, tzinfo=datetime.UTC)) is None
        assert VaultNote.due_date_from_raw(3) is None

    def test_is_open_project_follows_the_status(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Open.md", "project", status="active")
        _write_note(root / "projects/Done.md", "project", status="done")
        _write_note(root / "reference/Ref.md", "reference")
        snapshot = afanes.core.vault.Vault(root).scan()
        by_name = {note.name: note for note in snapshot.notes}

        assert by_name["Open"].is_open_project is True
        assert by_name["Done"].is_open_project is False
        assert by_name["Ref"].is_open_project is False

    def test_is_misplaced_is_false_inside_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/Capture.md", "note")

        note = afanes.core.vault.Vault(root).scan().notes[0]

        assert note.is_misplaced is False


class TestStepWrites:
    def _project(self, tmp_path: Path) -> tuple[afanes.core.vault.Vault, Path]:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n\n- [ ] One\n- [ ] Two\n")
        return vault, project

    def test_tick_and_untick_rewrite_one_line(self, tmp_path: Path) -> None:
        vault, project = self._project(tmp_path)
        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        steps = afanes.core.steps.StepDocument(document.body).steps

        vault.tick_step(project, steps[0].line_index, datetime.date(2026, 11, 14), confirm=True)
        ticked = NoteDocument.from_text(project.read_text(encoding="utf-8"))

        assert "- [x] One" in ticked.body
        assert "- [ ] Two" in ticked.body
        assert "actual: 2026-11-14" in ticked.body

        vault.untick_step(project, steps[0].line_index, confirm=True)
        unticked = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert "- [ ] One" in unticked.body
        assert "actual" not in unticked.body

    def test_plan_and_owners_rewrite_one_line(self, tmp_path: Path) -> None:
        vault, project = self._project(tmp_path)
        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        index = afanes.core.steps.StepDocument(document.body).steps[0].line_index

        vault.plan_step(project, index, datetime.date(2026, 12, 1), confirm=True)
        vault.set_step_owners(project, index, ("Ada",), confirm=True)
        written = NoteDocument.from_text(project.read_text(encoding="utf-8"))

        assert "plan: 2026-12-01" in written.body
        assert "owners: [Ada]" in written.body

    def test_step_writes_require_confirmation_and_a_project(self, tmp_path: Path) -> None:
        vault, project = self._project(tmp_path)
        reference = vault.create("Ref", NoteType.REFERENCE)
        index = 2

        with pytest.raises(VaultError):
            vault.tick_step(project, index, datetime.date(2026, 11, 14))
        with pytest.raises(VaultError):
            vault.tick_step(reference, index, datetime.date(2026, 11, 14), confirm=True)
        with pytest.raises(VaultError):
            vault.tick_step(project, 99, datetime.date(2026, 11, 14), confirm=True)

    def test_append_step_requires_confirmation_and_a_project(self, tmp_path: Path) -> None:
        vault, project = self._project(tmp_path)
        reference = vault.create("Ref", NoteType.REFERENCE)

        with pytest.raises(VaultError):
            vault.append_step(project, "Three")
        with pytest.raises(VaultError):
            vault.append_step(reference, "Three", confirm=True)

        vault.append_step(project, "Three", "Detail", confirm=True)
        assert "- [ ] Three" in project.read_text(encoding="utf-8")


class TestCategoryMoveErrors:
    def test_only_references_move_by_category(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        project = vault.create("Home", NoteType.PROJECT)

        with pytest.raises(VaultError):
            vault.plan_category_move(project, CategoryLabel("place"))

    def test_collision_and_confirmation_are_reported(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        reference = vault.create("Ada", NoteType.REFERENCE)
        (root / "reference" / "place").mkdir(parents=True)
        (root / "reference" / "place" / "Ada.md").write_text("---\ntype: reference\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            vault.plan_category_move(reference, CategoryLabel("place"))

        preview = vault.plan_category_move(reference, None)
        with pytest.raises(VaultError):
            vault.apply_category_move(preview)


class TestProcessingEdgeCases:
    def test_done_now_ticks_an_existing_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Plan\n\n- [ ] One\n- [ ] Two\n")

        plan = vault.plan_processing(capture, ProcessingOutcome.DONE_NOW, today=datetime.date(2026, 11, 14))
        target = vault.apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        steps = afanes.core.steps.StepDocument(document.body).steps

        assert steps[0].checked is True
        assert steps[1].checked is False

    def test_append_aborts_when_the_capture_changed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n")
        capture = vault.capture("Call")
        plan = vault.plan_processing(capture, ProcessingOutcome.APPEND_STEP, project="Home")
        capture.write_text("---\ntype: note\n---\n# Changed\n", encoding="utf-8")

        with pytest.raises(ProcessingError):
            vault.apply_processing(plan, confirm=True)

        assert capture.exists()
        assert "- [ ] Call" not in project.read_text(encoding="utf-8")

    def test_apply_rejects_a_missing_capture(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Call")
        plan = vault.plan_processing(capture, ProcessingOutcome.PROJECT)
        capture.unlink()

        with pytest.raises(ProcessingError):
            vault.apply_processing(plan, confirm=True)

    def test_capture_step_falls_back_to_the_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        project = vault.create("Home", NoteType.PROJECT, body="# Home\n")
        capture = vault.create("Blank", NoteType.NOTE)
        capture.write_text("---\ntype: note\n---\n", encoding="utf-8")
        plan = vault.plan_processing(capture, ProcessingOutcome.APPEND_STEP, project="Home")

        assert isinstance(plan, AppendStepPlan)
        assert plan.step_text == "Blank"
        assert project.is_file()
