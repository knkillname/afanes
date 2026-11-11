"""Tests for vault scanning, containment, atomic writes, and reference-safe edits."""

import hashlib
from pathlib import Path

import pytest

import afanes.core.vault
from afanes.core.errors import NameCollisionError, VaultError, VaultPathError
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.vault import ReferenceSite
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType

ONE = 1
TWO = 2
FOUR_REFERENCES = 4


def _write_note(
    path: Path,
    note_type: str = "note",
    body: str = "",
    people: tuple[str, ...] = (),
    project: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}", "status: inbox"]
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


class TestVaultRoot:
    def test_resolves_a_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        assert afanes.core.vault.resolve_vault_root(root) == root.resolve()

    def test_rejects_a_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "note.md"
        file_path.write_text("body", encoding="utf-8")
        with pytest.raises(VaultError):
            afanes.core.vault.resolve_vault_root(file_path)

    def test_rejects_a_missing_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultError):
            afanes.core.vault.resolve_vault_root(tmp_path / "missing")


class TestContainedPath:
    def test_accepts_a_relative_path_inside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        assert afanes.core.vault.contained_path(root, Path("notes/Ada.md")) == (root / "notes/Ada.md").resolve()

    def test_accepts_an_absolute_path_inside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        candidate = root / "notes/Ada.md"
        assert afanes.core.vault.contained_path(root, candidate) == candidate.resolve()

    def test_rejects_relative_traversal(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        with pytest.raises(VaultPathError):
            afanes.core.vault.contained_path(root, Path("../outside.md"))

    def test_rejects_an_absolute_path_outside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        with pytest.raises(VaultPathError):
            afanes.core.vault.contained_path(root, tmp_path / "outside.md")

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
        with pytest.raises(VaultPathError):
            afanes.core.vault.contained_path(root, link)


class TestAtomicWrite:
    def test_writes_utf8_text(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.vault.write_text_atomic(path, "Ada\nLovelace\n")
        assert path.read_bytes() == b"Ada\nLovelace\n"

    def test_overwrites_an_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        path.write_text("old", encoding="utf-8")
        afanes.core.vault.write_text_atomic(path, "new")
        assert path.read_text(encoding="utf-8") == "new"

    def test_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.vault.write_text_atomic(path, "body")
        assert list(tmp_path.glob(".*.tmp")) == []

    def test_preserves_crlf_bytes(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.vault.write_text_atomic(path, "one\r\ntwo\r\n")
        assert path.read_bytes() == b"one\r\ntwo\r\n"

    def test_rejects_a_missing_parent_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultError):
            afanes.core.vault.write_text_atomic(tmp_path / "missing/note.md", "body")

    def test_cleans_up_after_replace_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "note.md"
        path.write_text("original", encoding="utf-8")

        def fail_replace(_source: object, _destination: object) -> None:
            message = "replace failed"
            raise OSError(message)

        monkeypatch.setattr(afanes.core.vault.os, "replace", fail_replace)
        with pytest.raises(OSError, match="replace failed"):
            afanes.core.vault.write_text_atomic(path, "replacement")
        assert path.read_text(encoding="utf-8") == "original"
        assert list(tmp_path.glob(".*.tmp")) == []


class TestScanVault:
    def test_finds_nested_notes_in_deterministic_order(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "z/Beta.md")
        _write_note(root / "a/Alpha.md")
        snapshot = afanes.core.vault.scan_vault(root)
        assert [note.name for note in snapshot.notes] == ["Alpha", "Beta"]

    def test_skips_dot_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / ".trash/Hidden.md")
        _write_note(root / "Visible.md")
        snapshot = afanes.core.vault.scan_vault(root)
        assert [note.name for note in snapshot.notes] == ["Visible"]

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
        snapshot = afanes.core.vault.scan_vault(root)
        assert snapshot.notes == ()

    def test_reports_a_malformed_note_without_aborting(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Good.md")
        bad = root / "Bad.md"
        bad.write_text("---\ntype: [unclosed\n---\n", encoding="utf-8")
        snapshot = afanes.core.vault.scan_vault(root)
        assert [note.name for note in snapshot.notes] == ["Good"]
        assert [failure.path.as_posix() for failure in snapshot.failures] == ["Bad.md"]

    def test_reports_a_note_without_a_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = root / "NoType.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nstatus: inbox\n---\n", encoding="utf-8")
        snapshot = afanes.core.vault.scan_vault(root)
        assert snapshot.notes == ()
        assert len(snapshot.failures) == ONE

    def test_records_the_content_hash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        path = _write_note(root / "Ada.md")
        snapshot = afanes.core.vault.scan_vault(root)
        assert snapshot.notes[0].content_hash == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_extracts_body_and_frontmatter_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root / "Note.md",
            body="[Ada](<person:Ada Lovelace>)",
            people=("person:Ada Lovelace",),
            project="project:Turing Machine",
        )
        snapshot = afanes.core.vault.scan_vault(root)
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

        monkeypatch.setattr(afanes.core.vault, "write_text_atomic", fail_write)
        afanes.core.vault.scan_vault(root)
        assert _tree_state(root) == before

    def test_catalog_keeps_duplicate_names_ambiguous(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "a/Ada.md", "person")
        _write_note(root / "b/Ada.md", "person")
        snapshot = afanes.core.vault.scan_vault(root)
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.AMBIGUOUS
        assert len(result.targets) == TWO


class TestCreateNote:
    def test_sanitizes_the_title_into_the_filename(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.create_note(root, "Q1: Planning?", NoteType.NOTE, body="Body")
        assert path.name == "Q1 Planning.md"
        assert NoteDocument.from_text(path.read_text(encoding="utf-8")).note_type is NoteType.NOTE

    def test_suffixes_a_collision_within_the_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        afanes.core.vault.create_note(root, "Ada", NoteType.PERSON)
        second = afanes.core.vault.create_note(root, "Ada", NoteType.PERSON)
        assert second.name == "Ada 2.md"

    def test_suffixes_a_collision_with_an_existing_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        (root / "Ada.txt").write_text("occupied", encoding="utf-8")
        path = afanes.core.vault.create_note(root, "Ada", NoteType.PERSON)
        assert path.name == "Ada 2.md"

    def test_allows_cross_scheme_reuse_in_different_directories(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        person = afanes.core.vault.create_note(root, "Ada", NoteType.PERSON, directory=Path("people"))
        project = afanes.core.vault.create_note(root, "Ada", NoteType.PROJECT, directory=Path("work"))
        assert person.name == "Ada.md"
        assert project.name == "Ada.md"

    def test_avoids_reserved_device_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.create_note(root, "CON", NoteType.NOTE)
        assert path.name == "CON-note.md"

    def test_creates_a_missing_classification_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.create_note(root, "Ada", NoteType.PERSON, directory=Path("people"))
        assert path.parent.is_dir()

    def test_rejects_a_directory_that_escapes_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        with pytest.raises(VaultPathError):
            afanes.core.vault.create_note(root, "Ada", NoteType.PERSON, directory=Path("../outside"))

    def test_new_note_is_valid_markdown(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.create_note(root, "Ada", NoteType.PERSON, body="Hello\n")
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.PERSON
        assert document.raw["status"] == "inbox"
        assert document.body == "Hello\n"

    def test_new_note_normalizes_line_endings_and_removes_a_bom(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = afanes.core.vault.create_note(root, "Ada", NoteType.NOTE, body="\ufeffone\r\ntwo\r")
        data = path.read_bytes()
        assert b"\r" not in data
        assert not data.startswith(b"\xef\xbb\xbf")
        assert data.endswith(b"one\ntwo\n")


class TestMoveNote:
    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        with pytest.raises(VaultError):
            afanes.core.vault.move_note(root, note, Path("work"))
        assert note.exists()

    def test_moves_without_rewriting_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        before = referring.read_bytes()
        moved = afanes.core.vault.move_note(root, note, Path("work"), confirm=True)
        assert moved.parent == (root / "work").resolve()
        assert moved.name == "Ada.md"
        assert referring.read_bytes() == before

    def test_resolution_survives_a_move(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        afanes.core.vault.move_note(root, note, Path("work"), confirm=True)
        snapshot = afanes.core.vault.scan_vault(root)
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.RESOLVED
        assert result.targets[0].parent.name == "work"

    def test_rejects_a_destination_collision(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "work/Ada.md", "person")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.move_note(root, note, Path("work"), confirm=True)

    def test_rejects_a_non_markdown_source(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = root / "notes.txt"
        text.write_text("body", encoding="utf-8")
        with pytest.raises(VaultPathError):
            afanes.core.vault.move_note(root, text, root, confirm=True)


class TestPlanRename:
    def test_reports_zero_affected_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        assert preview.reference_count == 0
        assert preview.affected == ()

    def test_counts_references_in_one_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
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
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        assert preview.reference_count == FOUR_REFERENCES
        assert len(preview.affected) == TWO

    def test_excludes_references_that_resolve_elsewhere(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "people/Grace.md", "person")
        _write_note(root / "inbox/Note.md", body="[Grace](<person:Grace>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        assert preview.affected == ()

    def test_excludes_ambiguous_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "archive/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        assert preview.affected == ()

    def test_rejects_a_same_scheme_collision(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "people/Grace.md", "person")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.plan_rename(root, note, "Grace")

    def test_allows_cross_scheme_name_reuse(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "work/Grace.md", "project")
        preview = afanes.core.vault.plan_rename(root, note, "Grace")
        assert preview.new_name == "Grace"

    def test_rejects_an_existing_target_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        target = root / "people/Ada King.md"
        target.write_text("---\ntype: errand\n---\n", encoding="utf-8")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.plan_rename(root, note, "Ada King")

    def test_sanitizes_the_requested_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.plan_rename(root, note, "Ada: King?")
        assert preview.new_name == "Ada King"
        assert preview.target_path.name == "Ada King.md"

    def test_same_name_is_a_no_op(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada")
        assert preview.affected == ()
        assert preview.reference_count == 0

    def test_planning_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        before = _tree_state(root)
        afanes.core.vault.plan_rename(root, note, "Ada King")
        assert _tree_state(root) == before


class TestApplyRename:
    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        with pytest.raises(VaultError):
            afanes.core.vault.apply_rename(root, preview)
        assert note.exists()

    def test_renames_and_rewrites_destinations_and_labels(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        report = afanes.core.vault.apply_rename(root, preview, confirm=True)
        assert report.renamed is True
        assert not note.exists()
        assert (root / "people/Ada King.md").exists()
        assert "[Ada King](<person:Ada King>)" in referring.read_text(encoding="utf-8")

    def test_preserves_a_custom_label(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[my colleague](<person:Ada>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        afanes.core.vault.apply_rename(root, preview, confirm=True)
        assert "[my colleague](<person:Ada King>)" in referring.read_text(encoding="utf-8")

    def test_rewrites_frontmatter_values(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(
            root / "inbox/Note.md",
            people=("person:Ada",),
            project="project:Turing",
        )
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        afanes.core.vault.apply_rename(root, preview, confirm=True)
        document = NoteDocument.from_text(referring.read_text(encoding="utf-8"))
        assert document.raw["people"] == ["person:Ada King"]
        assert document.raw["project"] == "project:Turing"

    def test_rewrites_a_self_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        afanes.core.vault.apply_rename(root, preview, confirm=True)
        target = root / "people/Ada King.md"
        assert "[Ada King](<person:Ada King>)" in target.read_text(encoding="utf-8")

    def test_skips_a_file_changed_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        referring.write_text(referring.read_text(encoding="utf-8") + "\nEdited externally.\n", encoding="utf-8")
        report = afanes.core.vault.apply_rename(root, preview, confirm=True)
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
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")

        original_write = afanes.core.vault.write_text_atomic
        state = {"failed": False}

        def flaky_write(path: Path, text: str) -> None:
            if path == first and not state["failed"]:
                state["failed"] = True
                message = "disk full"
                raise OSError(message)
            original_write(path, text)

        monkeypatch.setattr(afanes.core.vault, "write_text_atomic", flaky_write)
        first_report = afanes.core.vault.apply_rename(root, preview, confirm=True)
        assert [failure.path for failure in first_report.failed] == [first]
        assert first_report.updated == (second,)

        second_report = afanes.core.vault.apply_rename(root, preview, confirm=True)
        assert second_report.renamed is False
        assert second_report.failed == ()
        assert first in second_report.updated
        assert "[Ada King](<person:Ada King>)" in first.read_text(encoding="utf-8")

    def test_rerun_after_success_changes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        afanes.core.vault.apply_rename(root, preview, confirm=True)
        before = referring.read_bytes()
        report = afanes.core.vault.apply_rename(root, preview, confirm=True)
        assert report.renamed is False
        assert report.updated == ()
        assert referring.read_bytes() == before

    def test_rejects_a_target_created_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        (root / "people/Ada King.md").write_text("---\ntype: note\n---\n", encoding="utf-8")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.apply_rename(root, preview, confirm=True)

    def test_rejects_a_missing_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.plan_rename(root, note, "Ada King")
        note.unlink()
        with pytest.raises(VaultError):
            afanes.core.vault.apply_rename(root, preview, confirm=True)


class TestDeletion:
    def test_reports_inbound_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/One.md", body="[Ada](<person:Ada>)")
        _write_note(root / "inbox/Two.md", people=("person:Ada",))
        preview = afanes.core.vault.plan_deletion(root, note)
        assert preview.reference_count == TWO
        assert len(preview.affected_notes) == TWO

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        with pytest.raises(VaultError):
            afanes.core.vault.delete_note(root, note)
        assert note.exists()

    def test_deletes_without_modifying_referring_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<person:Ada>)")
        before = referring.read_bytes()
        count = afanes.core.vault.delete_note(root, note, confirm=True)
        assert count == ONE
        assert not note.exists()
        assert referring.read_bytes() == before

    def test_references_become_unresolved_after_deletion(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        afanes.core.vault.delete_note(root, note, confirm=True)
        snapshot = afanes.core.vault.scan_vault(root)
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.UNRESOLVED

    def test_deleting_an_unreferenced_note_reports_zero(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        assert afanes.core.vault.delete_note(root, note, confirm=True) == 0
