"""Tests for vault page capture, creation, writing, recovery, and status."""

import hashlib
import os
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.core.vault.steps
from afanes.core.errors import (
    ContentChangedError,
    EmptyCaptureError,
    NameCollisionError,
    NoteParseError,
    VaultError,
    VaultPathError,
)
from afanes.core.frontmatter import NoteDocument
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


class TestWritePage:
    def test_writes_after_a_matching_hash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "notes" / "Ada.md", body="Old body\n")
        vault = afanes.core.vault.service.Vault(root)
        content = vault.read_page(path)
        new_text = "---\ntype: note\n---\n\n# New body\n"

        new_hash = afanes.core.vault.pages.VaultPages(vault).write_page(path, new_text, content.content_hash)

        assert path.read_text(encoding="utf-8") == new_text
        assert new_hash == hashlib.sha256(new_text.encode("utf-8")).hexdigest()
        assert vault.read_page(path).content_hash == new_hash

    def test_conflict_leaves_the_file_unchanged(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "notes" / "Ada.md", body="Old body\n")
        original = path.read_bytes()
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(ContentChangedError):
            afanes.core.vault.pages.VaultPages(vault).write_page(path, "replacement", "0" * 64)

        assert path.read_bytes() == original

    def test_missing_note_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultPathError):
            afanes.core.vault.pages.VaultPages(vault).write_page(Path("missing.md"), "body", "0" * 64)

    def test_path_outside_the_vault_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        outside = tmp_path / "outside.md"
        outside.write_text("body", encoding="utf-8")
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultPathError):
            afanes.core.vault.pages.VaultPages(vault).write_page(outside, "body", "0" * 64)

    def test_writes_crlf_text_as_provided(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "notes" / "Ada.md", body="Old body\n")
        vault = afanes.core.vault.service.Vault(root)
        content = vault.read_page(path)
        new_text = "---\r\ntype: note\r\n---\r\n\r\n# New\r\n"

        afanes.core.vault.pages.VaultPages(vault).write_page(path, new_text, content.content_hash)

        assert path.read_bytes() == new_text.encode("utf-8")


class TestCreatePage:
    def test_creates_the_exact_sanitized_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
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

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
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

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
            "Release 1.0", NoteType.PROJECT
        )

        assert path == root / "projects" / "Release 1.0.md"

    def test_rejects_a_name_used_in_the_same_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        _write_note(root / "notes" / "Quarterly budget.md", body="Existing\n")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
                "Quarterly budget", NoteType.REFERENCE
            )

        assert not (root / "reference" / "Quarterly budget.md").exists()
        assert not (root / "reference" / "Quarterly budget 2.md").exists()

    def test_rejects_a_case_variant_in_the_target_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        target = root / "reference"
        target.mkdir()
        (target / "quarterly budget.md").write_text("body", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
                "Quarterly budget", NoteType.REFERENCE
            )

    def test_allows_cross_scheme_reuse_in_another_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        _write_note(root / "projects" / "Ada.md", note_type="project")

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
            "Ada", NoteType.REFERENCE
        )

        assert path == root / "reference" / "Ada.md"
        assert path.exists()

    def test_creates_a_missing_category_directory(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
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
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
                "Ada",
                NoteType.NOTE,
                CategoryLabel("person"),
            )

    def test_writes_supplied_text_exactly(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = "---\ntype: reference\ncategory: person\ncustom: keep\n---\n\n# Ada\n\nBody.\n"

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
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
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
                "Ada", NoteType.REFERENCE, text=text
            )

    def test_rejects_invalid_supplied_text(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(NoteParseError):
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).create_page(
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
        vault = afanes.core.vault.service.Vault(root)

        content_hash = afanes.core.vault.pages.VaultPages(vault).recreate_page(path, text)

        assert path.read_text(encoding="utf-8") == text
        assert content_hash == hashlib.sha256(text.encode("utf-8")).hexdigest()

    def test_refuses_an_existing_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "reference" / "Ada.md", body="Existing\n")
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(ContentChangedError):
            afanes.core.vault.pages.VaultPages(vault).recreate_page(path, "replacement")

    def test_requires_an_existing_parent(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultError):
            afanes.core.vault.pages.VaultPages(vault).recreate_page(Path("missing/Ada.md"), "text")

    def test_rejects_a_path_outside_the_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultPathError):
            afanes.core.vault.pages.VaultPages(vault).recreate_page(tmp_path / "outside.md", "text")


class TestCaptureNote:
    def test_creates_a_minimal_note_in_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Buy milk")

        assert path == root / "inbox" / "Buy milk.md"
        assert [entry.name for entry in root.iterdir()] == ["inbox"]
        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw == {"type": "note"}
        assert document.body == "# Buy milk"

    def test_reuses_an_existing_inbox_case_variant(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Inbox").mkdir(parents=True)

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Buy milk")

        assert path == root / "Inbox" / "Buy milk.md"
        assert not (root / "inbox").exists()

    def test_uses_the_first_non_blank_line_as_the_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = "\n\nCall Ada\nabout the invoice\n"

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture(text)

        assert path.name == "Call Ada.md"
        assert NoteDocument.from_text(path.read_text(encoding="utf-8")).body == "\n\n# Call Ada\nabout the invoice\n"

    def test_leaves_an_existing_heading_alone(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = "# Call Ada\nabout the invoice\n"

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture(text)

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))

        assert document.body == text
        assert document.title == "Call Ada"

    def test_templates_a_sanitized_first_line_without_changing_it(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Q1: Planning?")

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert path.name == "Q1 Planning.md"
        assert document.body == "# Q1: Planning?"
        assert snapshot.notes[0].title == "Q1: Planning?"

    def test_rejects_whitespace_only_text(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(EmptyCaptureError):
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture(" \n\t\n")

        assert not (root / "inbox").exists()

    def test_creates_the_inbox_directory_on_demand(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Buy milk")

        assert (root / "inbox").is_dir()

    def test_repeated_captures_get_distinct_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        first = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Buy milk")
        second = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Buy milk")

        assert first.name == "Buy milk.md"
        assert second.name == "Buy milk 2.md"
        assert first.is_file()
        assert second.is_file()

    def test_sanitizes_the_first_line(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Q1: Planning?")

        assert path.name == "Q1 Planning.md"

    def test_does_not_modify_existing_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        existing = _write_note(root / "work/Existing.md", body="Do not touch")
        before = existing.read_bytes()

        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Buy milk")

        assert existing.read_bytes() == before

    def test_does_not_infer_references_or_due_dates(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        path = afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture(
            "Ask Ada about 2026-11-20"
        )

        document = NoteDocument.from_text(path.read_text(encoding="utf-8"))
        assert document.raw == {"type": "note"}
        snapshot = afanes.core.vault.service.Vault(root).scan()
        assert snapshot.notes[0].body_references == ()
        assert snapshot.notes[0].steps == ()

    def test_reports_a_blocking_inbox_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        (root / "inbox").write_text("not a directory", encoding="utf-8")

        with pytest.raises(VaultError, match="not a directory"):
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture("Buy milk")


class TestSetStatus:
    def test_sets_a_project_status_without_touching_other_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write_note(root / "projects/Machine.md", "project", status="active")
        other = _write_note(root / "reference/Build.md", "reference", body="# Build\n")
        other_bytes = other.read_bytes()
        vault = afanes.core.vault.service.Vault(root)

        afanes.core.vault.pages.VaultPages(vault).set_status(project, Status.DONE, confirm=True)

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert document.status is Status.DONE
        assert other.read_bytes() == other_bytes

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write_note(root / "projects/Machine.md", "project", status="active")

        with pytest.raises(VaultError):
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).set_status(project, Status.DONE)

        assert "status: active" in project.read_text(encoding="utf-8")

    def test_preserves_unknown_keys_and_newline_style(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = root / "projects" / "Machine.md"
        project.parent.mkdir(parents=True)
        project.write_bytes(b"---\r\ntype: project\r\nstatus: active\r\nx-custom: kept\r\n---\r\n# Machine\r\n")

        afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).set_status(
            project, Status.LATER, confirm=True
        )

        data = project.read_bytes()
        assert b"x-custom: kept" in data
        assert b"\r\n" in data
        assert b"status: later" in data

    def test_rejects_a_status_invalid_for_the_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "notes/Idea.md", "note")

        with pytest.raises(NoteParseError):
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).set_status(
                note, Status.ACTIVE, confirm=True
            )

    def test_rejects_a_file_changed_after_the_snapshot(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write_note(root / "projects/Machine.md", "project", status="active")
        snapshot = afanes.core.vault.service.Vault(root).scan()
        project.write_text("---\ntype: project\nstatus: waiting\n---\n", encoding="utf-8")

        with pytest.raises(ContentChangedError):
            afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).set_status(
                project, Status.DONE, snapshot=snapshot, confirm=True
            )
