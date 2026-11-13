"""Tests for reference-safe naming, moves, repairs, and trash."""

import datetime
import hashlib
import os
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.steps
import afanes.core.vault.log_conversions
import afanes.core.vault.naming
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.core.vault.steps
from afanes.core.errors import (
    ContentChangedError,
    NameCollisionError,
    VaultError,
    VaultPathError,
)
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.vault.snapshot import ReferenceSite
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import CategoryLabel, NoteDate, NoteType

ONE = 1
TWO = 2
THREE_REFERENCES = 3
FOUR_REFERENCES = 4
YEAR_LENGTH = 4


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


class TestReferenceRepair:
    def test_plans_and_rewrites_every_referring_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        one = _write_note(root / "notes" / "One.md", body="[Q1](<note:Q1: Planning?>)\n")
        two = _write_note(root / "notes" / "Two.md", body="# Two\n\n[Q1](<note:Q1: Planning?>)\n")
        vault = afanes.core.vault.service.Vault(root)
        snapshot = vault.scan()

        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=snapshot)

        assert [(site.path, site.reference_count) for site in preview.sites] == [(one.resolve(), 1), (two.resolve(), 1)]
        assert set(preview.content_hashes) == {one.resolve(), two.resolve()}
        assert "Q1: Planning?" in one.read_text(encoding="utf-8")

        report = afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview, confirm=True)

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
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=vault.scan())

        afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview, confirm=True)

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
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=vault.scan())
        changed = second.read_text(encoding="utf-8") + "\nExternal edit.\n"
        second.write_text(changed, encoding="utf-8", newline="\n")

        report = afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview, confirm=True)

        assert report.updated == (first.resolve(),)
        assert report.skipped == (second.resolve(),)
        assert second.read_text(encoding="utf-8") == changed

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=vault.scan())

        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview)

    def test_rejects_a_cross_scheme_repair(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)

        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(
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
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=vault.scan())

        afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview, confirm=True)

        assert "note:Ada>" in path.read_text(encoding="utf-8")
        assert "note:Ada?>" not in path.read_text(encoding="utf-8")

    def test_counts_metadata_role_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = root / "projects/Review.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nasked_by: 'Q1: Planning?'\nowner: 'Q1: Planning?'\n---\n\n"
            "- [ ] Call <!-- {owners: ['Q1: Planning?']} -->\n",
            encoding="utf-8",
        )
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        vault = afanes.core.vault.service.Vault(root)

        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=vault.scan())

        assert [(site.path, site.reference_count) for site in preview.sites] == [(project, 3)]

    def test_repair_rewrites_metadata_role_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = root / "projects/Review.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nasked_by: 'Q1: Planning?'\nowner: 'Q1: Planning?'\n---\n\n"
            "- [ ] Call <!-- {owners: ['Q1: Planning?'], plan: 2026-01-02} -->\n",
            encoding="utf-8",
        )
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=vault.scan())

        afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview, confirm=True)

        text = project.read_text(encoding="utf-8")
        assert "asked_by: Q1 Planning\n" in text
        assert "owner: Q1 Planning\n" in text
        assert "owners: [Q1 Planning]" in text
        assert "Q1: Planning?" not in text
        assert "plan: 2026-01-02" in text

    def test_skips_a_metadata_referrer_changed_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = root / "projects/Review.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nasked_by: 'Q1: Planning?'\nowner: 'Q1: Planning?'\n---\n\n"
            "- [ ] Call <!-- {owners: ['Q1: Planning?']} -->\n",
            encoding="utf-8",
        )
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=vault.scan())
        changed = project.read_text(encoding="utf-8") + "\nExternal edit.\n"
        project.write_text(changed, encoding="utf-8", newline="\n")

        report = afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview, confirm=True)

        assert report.updated == ()
        assert report.skipped == (project.resolve(),)
        assert project.read_text(encoding="utf-8") == changed

    def test_reports_a_metadata_partial_failure_and_recovers_on_rerun(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        first = root / "projects/One.md"
        second = root / "projects/Two.md"
        for path in (first, second):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\ntype: project\nasked_by: 'Q1: Planning?'\nowner: 'Q1: Planning?'\n---\n\n"
                "- [ ] Call <!-- {owners: ['Q1: Planning?']} -->\n",
                encoding="utf-8",
            )
        old = NoteReference(ReferenceScheme.NOTE, "Q1: Planning?")
        new = NoteReference(ReferenceScheme.NOTE, "Q1 Planning")
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_reference_repair(old, new, snapshot=vault.scan())

        original_write = afanes.core.atomic.AtomicWriter.write_text_atomic
        state = {"failed": False}

        def flaky_write(path: Path, text: str) -> None:
            if path == first.resolve() and not state["failed"]:
                state["failed"] = True
                message = "disk full"
                raise OSError(message)
            original_write(path, text)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", flaky_write)
        first_report = afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview, confirm=True)
        assert [failure.path for failure in first_report.failed] == [first.resolve()]
        assert first_report.updated == (second.resolve(),)

        second_report = afanes.core.vault.naming.VaultNaming(vault).apply_reference_repair(preview, confirm=True)
        assert second_report.failed == ()
        assert first.resolve() in second_report.updated
        assert "owner: Q1 Planning" in first.read_text(encoding="utf-8")


class TestMoveNote:
    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).move(note, Path("work"))
        assert note.exists()

    def test_moves_without_rewriting_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        before = referring.read_bytes()
        moved = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).move(
            note, Path("work"), confirm=True
        )
        assert moved.parent == (root / "work").resolve()
        assert moved.name == "Ada.md"
        assert referring.read_bytes() == before

    def test_resolution_survives_a_move(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).move(
            note, Path("work"), confirm=True
        )
        snapshot = afanes.core.vault.service.Vault(root).scan()
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
        assert result.outcome is ResolutionOutcome.RESOLVED
        assert result.targets[0].parent.name == "work"

    def test_rejects_a_destination_collision(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "work/Ada.md", "person")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).move(
                note, Path("work"), confirm=True
            )

    def test_rejects_a_non_markdown_source(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        text = root / "notes.txt"
        text.write_text("body", encoding="utf-8")
        with pytest.raises(VaultPathError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).move(text, root, confirm=True)


class TestMetadataReferenceCharacterization:
    """Check how rename and trash count role names as metadata references."""

    def test_plan_counts_body_and_metadata_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        project = root / "projects/Review.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nasked_by: Ada\nowner: Ada\n---\n\n"
            "[Ada](<note:Ada>)\n\n- [ ] Call Ada <!-- {owners: [Ada], plan: 2026-01-02} -->\n",
            encoding="utf-8",
        )

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        assert preview.reference_count == FOUR_REFERENCES
        assert preview.affected == (ReferenceSite(path=project, reference_count=FOUR_REFERENCES),)

    def test_plan_counts_metadata_only_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        project = root / "projects/Review.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nasked_by: Ada\nowner: Ada\n---\n\n"
            "- [ ] Call Ada <!-- {owners: [Ada], plan: 2026-01-02} -->\n",
            encoding="utf-8",
        )

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        assert preview.reference_count == THREE_REFERENCES
        assert preview.affected == (ReferenceSite(path=project, reference_count=THREE_REFERENCES),)

    def test_apply_rewrites_metadata_role_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        project = root / "projects/Review.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nasked_by: Ada\nowner: Ada\n---\n\n"
            "[Ada](<note:Ada>)\n\n- [ ] Call Ada <!-- {owners: [Ada], plan: 2026-01-02} -->\n",
            encoding="utf-8",
        )
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_rename(note, "Ada King")

        afanes.core.vault.naming.VaultNaming(vault).apply_rename(preview, confirm=True)

        text = project.read_text(encoding="utf-8")
        assert "asked_by: Ada King\n" in text
        assert "owner: Ada King\n" in text
        assert "owners: [Ada King]" in text
        assert "note:Ada King" in text
        assert "asked_by: Ada\n" not in text

    def test_apply_updates_step_metadata_and_crlf(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        project = root / "projects/Review.md"
        project.parent.mkdir(parents=True)
        project.write_bytes(
            b"---\r\ntype: project\r\n---\r\n\r\n"
            b"[Ada](<note:Ada>)\r\n\r\n"
            b"- [ ] Call Ada <!-- {owners: [Ada], plan: 2026-01-02, "
            b"actual: 2026-01-03, tags: [review], custom: keep} -->\r\n"
        )
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_rename(note, "Ada King")

        afanes.core.vault.naming.VaultNaming(vault).apply_rename(preview, confirm=True)

        rewritten = project.read_bytes().decode("utf-8")
        assert "note:Ada King" in rewritten
        steps = afanes.core.steps.StepDocument(NoteDocument.from_text(rewritten).body).steps
        assert len(steps) == ONE
        assert steps[0].owners == ("Ada King",)
        assert steps[0].plan == datetime.date(2026, 1, 2)
        assert steps[0].actual == datetime.date(2026, 1, 3)
        assert steps[0].tags == ("review",)
        assert steps[0].metadata.raw["custom"] == "keep"
        assert "\n" not in rewritten.replace("\r\n", "")

    def test_rename_preserves_an_unknown_frontmatter_key(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        project = _write_note(
            root / "projects/Review.md",
            "project",
            "# Review\n\n[Ada](<note:Ada>)\n",
        )
        project.write_text(
            "---\ntype: project\nowner: Ada\ncustom: keep\n---\n\n[Ada](<note:Ada>)\n",
            encoding="utf-8",
        )
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_rename(note, "Ada King")

        afanes.core.vault.naming.VaultNaming(vault).apply_rename(preview, confirm=True)

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        assert document.owner == "Ada King"
        assert document.raw["custom"] == "keep"

    def test_rename_updates_multiple_step_owners_independently(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "people/Grace.md", "person")
        project = _write_note(
            root / "projects/Review.md",
            "project",
            "# Review\n\n- [ ] Call <!-- {owners: [Ada]} -->\n- [ ] Review <!-- {owners: [Grace]} -->\n",
        )
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_rename(note, "Ada King")

        afanes.core.vault.naming.VaultNaming(vault).apply_rename(preview, confirm=True)

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        steps = afanes.core.steps.StepDocument(document.body).steps
        assert steps[0].owners == ("Ada King",)
        assert steps[1].owners == ("Grace",)

    def test_trash_counts_body_and_metadata_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "projects/Review.md", "project", body="[Ada](<note:Ada>)\n")
        project = root / "projects/Review.md"
        project.write_text(
            "---\ntype: project\nasked_by: Ada\nowner: Ada\n---\n\n"
            "[Ada](<note:Ada>)\n\n- [ ] Call Ada <!-- {owners: [Ada], plan: 2026-01-02} -->\n",
            encoding="utf-8",
        )

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_trash(note)

        assert preview.reference_count == FOUR_REFERENCES
        assert len(preview.affected_notes) == ONE

    def test_trash_counts_metadata_only_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        project = root / "projects/Review.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nasked_by: Ada\nowner: Ada\n---\n\n"
            "- [ ] Call Ada <!-- {owners: [Ada], plan: 2026-01-02} -->\n",
            encoding="utf-8",
        )

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_trash(note)

        assert preview.reference_count == THREE_REFERENCES
        assert len(preview.affected_notes) == ONE


class TestPlanRename:
    def test_reports_zero_affected_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        assert preview.reference_count == 0
        assert preview.affected == ()

    def test_counts_references_in_one_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
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
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        assert preview.reference_count == THREE_REFERENCES
        assert len(preview.affected) == TWO

    def test_excludes_references_that_resolve_elsewhere(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "people/Grace.md", "person")
        _write_note(root / "inbox/Note.md", body="[Grace](<note:Grace>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        assert preview.affected == ()

    def test_excludes_ambiguous_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "archive/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        assert preview.affected == ()

    def test_rejects_a_same_scheme_collision(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "people/Grace.md", "person")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(note, "Grace")

    def test_allows_cross_scheme_name_reuse(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "work/Grace.md", "project")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(note, "Grace")
        assert preview.new_name == "Grace"

    def test_rejects_an_existing_target_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        target = root / "people/Ada King.md"
        target.write_text("---\ntype: errand\n---\n", encoding="utf-8")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(note, "Ada King")

    def test_sanitizes_the_requested_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada: King?"
        )
        assert preview.new_name == "Ada King"
        assert preview.target_path.name == "Ada King.md"

    def test_same_name_is_a_no_op(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(note, "Ada")
        assert preview.affected == ()
        assert preview.reference_count == 0
        assert preview.heading_update is False

    def test_records_a_matching_heading_update(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada\n")

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        assert preview.heading_update is True

    def test_does_not_update_a_custom_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada, Countess of Lovelace\n")

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        assert preview.heading_update is False

    def test_does_not_add_a_missing_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="Body.\n")

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        assert preview.heading_update is False

    def test_does_not_update_a_heading_inside_code(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="```\n# Ada\n```\n")

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        assert preview.heading_update is False

    def test_planning_writes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        before = _tree_state(root)
        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(note, "Ada King")
        assert _tree_state(root) == before


class TestApplyRename:
    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(preview)
        assert note.exists()

    def test_renames_and_rewrites_destinations_and_labels(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )
        assert report.renamed is True
        assert not note.exists()
        assert (root / "people/Ada King.md").exists()
        assert "[Ada King](<note:Ada King>)" in referring.read_text(encoding="utf-8")

    def test_preserves_a_custom_label(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[my colleague](<note:Ada>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(preview, confirm=True)
        assert "[my colleague](<note:Ada King>)" in referring.read_text(encoding="utf-8")

    def test_rewrites_body_values(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(
            root / "inbox/Note.md",
            body="[Ada](<note:Ada>)",
        )
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(preview, confirm=True)
        document = NoteDocument.from_text(referring.read_text(encoding="utf-8"))
        assert "[Ada King](<note:Ada King>)" in document.body

    def test_rewrites_a_self_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(preview, confirm=True)
        target = root / "people/Ada King.md"
        assert "[Ada King](<note:Ada King>)" in target.read_text(encoding="utf-8")

    def test_project_rename_leaves_note_scheme_role_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = root / "projects/Ada.md"
        project.parent.mkdir(parents=True)
        project.write_text(
            "---\ntype: project\nowner: Ada\nasked_by: Ada\n---\n\n- [ ] Call Ada <!-- {owners: [Ada]} -->\n",
            encoding="utf-8",
        )
        vault = afanes.core.vault.service.Vault(root)
        preview = afanes.core.vault.naming.VaultNaming(vault).plan_rename(project, "Ada King")

        afanes.core.vault.naming.VaultNaming(vault).apply_rename(preview, confirm=True)

        text = (root / "projects/Ada King.md").read_text(encoding="utf-8")
        assert "owner: Ada\n" in text
        assert "asked_by: Ada\n" in text
        assert "owners: [Ada]" in text

    def test_skips_a_file_changed_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        referring.write_text(referring.read_text(encoding="utf-8") + "\nEdited externally.\n", encoding="utf-8")
        report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )
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
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        original_write = afanes.core.atomic.AtomicWriter.write_text_atomic
        state = {"failed": False}

        def flaky_write(path: Path, text: str) -> None:
            if path == first and not state["failed"]:
                state["failed"] = True
                message = "disk full"
                raise OSError(message)
            original_write(path, text)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", flaky_write)
        first_report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )
        assert [failure.path for failure in first_report.failed] == [first]
        assert first_report.updated == (second,)

        second_report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )
        assert second_report.renamed is False
        assert second_report.failed == ()
        assert first in second_report.updated
        assert "[Ada King](<note:Ada King>)" in first.read_text(encoding="utf-8")

    def test_rerun_after_success_changes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(preview, confirm=True)
        before = referring.read_bytes()
        report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )
        assert report.renamed is False
        assert report.updated == ()
        assert referring.read_bytes() == before

    def test_updates_a_matching_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada\n\nBody.\n")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )

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
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(preview, confirm=True)

        target = root / "people/Ada King.md"
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.body == "\n# Ada, Countess of Lovelace\n\nBody.\n"

    def test_does_not_add_a_missing_heading(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="Body.\n")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(preview, confirm=True)

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
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )

        report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )

        target = root / "people/Ada King.md"
        text = target.read_text(encoding="utf-8")
        assert report.updated == (target,)
        assert "# Ada King" in text
        assert "note:Ada King" in text
        assert "note:Ada)" not in text

    def test_skips_a_heading_update_when_the_file_changed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada\n")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        note.write_text(
            "---\ntype: reference\ncategory: person\n---\n\n# Ada\n\nExternal edit.\n",
            encoding="utf-8",
            newline="\n",
        )

        report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )

        target = root / "people/Ada King.md"
        assert report.updated == ()
        assert report.skipped == (target,)
        assert "# Ada\n" in target.read_text(encoding="utf-8")

    def test_rerun_after_a_heading_update_changes_no_bytes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person", body="# Ada\n")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(preview, confirm=True)
        target = root / "people/Ada King.md"
        before = target.read_bytes()

        report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
            preview, confirm=True
        )

        assert report.updated == ()
        assert target.read_bytes() == before

    def test_rejects_a_target_created_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        (root / "people/Ada King.md").write_text("---\ntype: note\n---\n", encoding="utf-8")
        with pytest.raises(NameCollisionError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
                preview, confirm=True
            )

    def test_rejects_a_missing_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
            note, "Ada King"
        )
        note.unlink()
        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_rename(
                preview, confirm=True
            )


class TestTrash:
    def test_reports_inbound_references_and_destination(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        _write_note(root / "inbox/One.md", body="[Ada](<note:Ada>)")
        _write_note(root / "inbox/Two.md", body="[Ada](<note:Ada>)")

        preview = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_trash(note)

        assert preview.reference_count == TWO
        assert len(preview.affected_notes) == TWO
        assert preview.trash_path == root / "trash" / "Ada.md"
        assert not (root / "trash").exists()

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")

        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).trash(note)

        assert note.exists()

    def test_moves_to_trash_without_modifying_referring_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        referring = _write_note(root / "inbox/Note.md", body="[Ada](<note:Ada>)")
        note_bytes = note.read_bytes()
        referring_bytes = referring.read_bytes()

        count = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).trash(note, confirm=True)

        trashed = root / "trash" / "Ada.md"
        assert count == ONE
        assert not note.exists()
        assert trashed.read_bytes() == note_bytes
        assert referring.read_bytes() == referring_bytes

    def test_references_become_unresolved_after_trashing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).trash(note, confirm=True)
        snapshot = afanes.core.vault.service.Vault(root).scan()
        result = snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Ada"))
        assert result.outcome is ResolutionOutcome.UNRESOLVED

    def test_trashing_an_unreferenced_note_reports_zero(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "people/Ada.md", "person")
        assert (
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).trash(note, confirm=True) == 0
        )

    def test_reuses_an_existing_trash_case_variant(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "Trash").mkdir(parents=True)
        note = _write_note(root / "people/Ada.md", "person")

        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).trash(note, confirm=True)

        assert (root / "Trash" / "Ada.md").is_file()
        assert not (root / "trash").exists()

    def test_uses_a_unique_name_inside_trash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        (root / "trash").mkdir(parents=True)
        (root / "trash" / "Ada.md").write_text("older", encoding="utf-8")
        note = _write_note(root / "people/Ada.md", "person")

        afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).trash(note, confirm=True)

        assert (root / "trash" / "Ada 2.md").is_file()


class TestCategoryMoveErrors:
    def test_only_references_move_by_category(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        project = vault.create(afanes.core.vault.service.NoteDraft("Home", NoteType.PROJECT))

        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(vault).plan_category_move(project, CategoryLabel("place"))

    def test_collision_and_confirmation_are_reported(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        reference = vault.create(afanes.core.vault.service.NoteDraft("Ada", NoteType.REFERENCE))
        (root / "reference" / "place").mkdir(parents=True)
        (root / "reference" / "place" / "Ada.md").write_text("---\ntype: reference\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.naming.VaultNaming(vault).plan_category_move(reference, CategoryLabel("place"))

        preview = afanes.core.vault.naming.VaultNaming(vault).plan_category_move(reference, None)
        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(vault).apply_category_move(preview)


class TestNamingGuards:
    def test_move_rejects_a_destination_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        note = _write_note(root / "inbox" / "Buy.md")
        (root / "work").write_text("not a directory", encoding="utf-8")

        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).move(
                note, Path("work"), confirm=True
            )

    def test_category_move_rejects_a_missing_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_category_move(
                root / "reference" / "Gone.md", CategoryLabel("place")
            )

    def test_category_move_is_a_no_op_inside_the_same_folder(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        note = _write_note(root / "reference" / "person" / "Ada.md", note_type="person")
        naming = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root))
        preview = naming.plan_category_move(note, CategoryLabel("person"))

        assert naming.apply_category_move(preview, confirm=True) == note.resolve()

    def test_category_move_rejects_a_destination_created_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        note = _write_note(root / "reference" / "Ada.md", "reference")
        naming = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root))
        preview = naming.plan_category_move(note, CategoryLabel("place"))
        preview.target_path.parent.mkdir(parents=True)
        preview.target_path.write_text("---\ntype: reference\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            naming.apply_category_move(preview, confirm=True)

    def test_rename_rejects_a_missing_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_rename(
                root / "notes" / "Gone.md", "Ada"
            )

    def test_repair_reports_a_referring_note_deleted_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        old = NoteReference(ReferenceScheme.NOTE, "Q1")
        new = NoteReference(ReferenceScheme.NOTE, "Q2")
        referring = _write_note(root / "notes" / "One.md", body="[Q1](<note:Q1>)\n")
        vault = afanes.core.vault.service.Vault(root)
        naming = afanes.core.vault.naming.VaultNaming(vault)
        preview = naming.plan_reference_repair(old, new)
        referring.unlink()

        report = naming.apply_reference_repair(preview, confirm=True)

        assert len(report.failed) == 1
        assert report.failed[0].path == referring.resolve()

    def test_repair_reports_a_note_that_no_longer_names_the_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        note = _write_note(root / "notes" / "One.md", body="Plain body\n")
        old = NoteReference(ReferenceScheme.NOTE, "Q1")
        new = NoteReference(ReferenceScheme.NOTE, "Q2")
        resolved = note.resolve()
        preview = afanes.core.vault.naming.ReferenceRepairPreview(
            old=old,
            new=new,
            sites=(ReferenceSite(path=resolved, reference_count=1),),
            content_hashes={resolved: hashlib.sha256(note.read_bytes()).hexdigest()},
        )

        report = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).apply_reference_repair(
            preview, confirm=True
        )

        assert report.unchanged == (resolved,)

    def test_trash_rejects_a_missing_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        with pytest.raises(VaultError):
            afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root)).plan_trash(
                root / "notes" / "Gone.md"
            )

    def test_trash_rejects_a_destination_created_after_planning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        note = _write_note(root / "inbox" / "Buy.md")
        naming = afanes.core.vault.naming.VaultNaming(afanes.core.vault.service.Vault(root))
        preview = naming.plan_trash(note)
        preview.trash_path.parent.mkdir(parents=True)
        preview.trash_path.write_text("---\ntype: note\n---\n", encoding="utf-8")
        monkeypatch.setattr(
            afanes.core.vault.naming.VaultNaming,
            "plan_trash",
            lambda _self, _path, **_kwargs: preview,
        )

        with pytest.raises(NameCollisionError):
            naming.trash(note, confirm=True)


class TestLogDateChange:
    def _log(
        self,
        root: Path,
        date: str = "2025-10-12",
        *,
        body: str = "# A quiet Tuesday\n",
    ) -> Path:
        year = date[:4]
        folder = root / "log" / year
        if len(date) > YEAR_LENGTH:
            folder = folder / date[5:7]
        return _write_note(folder / f"{date}.md", "log", body=body, date=date)

    def test_plans_a_day_to_day_change(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = self._log(root)
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        preview = naming.plan_log_date_change(source, NoteDate.from_text("2025-10-13"))

        assert preview.target_path == root / "log" / "2025" / "10" / "2025-10-13.md"
        assert preview.new_date == NoteDate.from_text("2025-10-13")
        assert preview.scheme is ReferenceScheme.LOG

    def test_plans_a_day_to_month_change(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = self._log(root)
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        preview = naming.plan_log_date_change(source, NoteDate.from_text("2025-10"))

        assert preview.target_path == root / "log" / "2025" / "10" / "2025-10.md"

    def test_plans_a_month_to_year_change(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = _write_note(root / "log" / "2025" / "10" / "2025-10.md", "log", date="2025-10")
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        preview = naming.plan_log_date_change(source, NoteDate.from_text("2025"))

        assert preview.target_path == root / "log" / "2025" / "2025.md"

    def test_rejects_an_occupied_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = self._log(root)
        self._log(root, "2025-10-13")
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        with pytest.raises(NameCollisionError):
            naming.plan_log_date_change(source, NoteDate.from_text("2025-10-13"))

    def test_applies_and_rewrites_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = self._log(root)
        referrer = _write_note(root / "reference" / "Entry.md", "reference", body="[Entry](<log:2025-10-12>)\n")
        vault = afanes.core.vault.service.Vault(root)
        naming = afanes.core.vault.log_conversions.LogConversions(vault)

        preview = naming.plan_log_date_change(source, NoteDate.from_text("2025-10-13"))
        report = naming.apply(preview)

        target = root / "log" / "2025" / "10" / "2025-10-13.md"
        assert report.renamed
        assert target.is_file()
        assert not source.exists()
        assert "log:2025-10-13" in referrer.read_text(encoding="utf-8")
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.date == NoteDate.from_text("2025-10-13")
        assert document.title == "A quiet Tuesday"

    def test_skips_a_changed_referrer(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = self._log(root)
        referrer = _write_note(root / "reference" / "Entry.md", "reference", body="[Entry](<log:2025-10-12>)\n")
        vault = afanes.core.vault.service.Vault(root)
        naming = afanes.core.vault.log_conversions.LogConversions(vault)

        preview = naming.plan_log_date_change(source, NoteDate.from_text("2025-10-13"))
        referrer.write_text("---\ntype: reference\n---\nchanged\n", encoding="utf-8")
        report = naming.apply(preview)

        assert referrer in report.skipped
        assert (root / "log" / "2025" / "10" / "2025-10-13.md").is_file()

    def test_skips_a_changed_source(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = self._log(root)
        vault = afanes.core.vault.service.Vault(root)
        naming = afanes.core.vault.log_conversions.LogConversions(vault)

        preview = naming.plan_log_date_change(source, NoteDate.from_text("2025-10-13"))
        source.write_text("---\ntype: log\ndate: 2025-10-12\n---\nchanged\n", encoding="utf-8")

        with pytest.raises(ContentChangedError):
            naming.apply(preview)

    def test_rerun_is_safe(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = self._log(root)
        vault = afanes.core.vault.service.Vault(root)
        naming = afanes.core.vault.log_conversions.LogConversions(vault)
        preview = naming.plan_log_date_change(source, NoteDate.from_text("2025-10-13"))

        naming.apply(preview)
        report = naming.apply(preview)

        assert not report.renamed
        assert (root / "log" / "2025" / "10" / "2025-10-13.md").is_file()

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = self._log(root)
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))
        preview = naming.plan_log_date_change(source, NoteDate.from_text("2025-10-13"))

        with pytest.raises(VaultError):
            naming.apply(preview, confirm=False)


class TestLogTypeChange:
    def test_reference_becomes_a_log_entry(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = _write_note(
            root / "reference" / "A quiet Tuesday.md",
            "reference",
            body="# A quiet Tuesday\n",
            date="2025-10-12",
        )
        referrer = _write_note(
            root / "inbox" / "Link.md",
            "note",
            body="[Entry](<note:A quiet Tuesday>)\n",
        )
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        preview = naming.plan_type_change(source, NoteType.LOG)
        naming.apply(preview)

        target = root / "log" / "2025" / "10" / "2025-10-12.md"
        assert target.is_file()
        assert not source.exists()
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.LOG
        assert document.date == NoteDate.from_text("2025-10-12")
        assert "category" not in document.raw
        assert "log:2025-10-12" in referrer.read_text(encoding="utf-8")

    def test_log_becomes_a_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = _write_note(
            root / "log" / "2025" / "10" / "2025-10-12.md",
            "log",
            body="# A quiet Tuesday\n",
            date="2025-10-12",
        )
        referrer = _write_note(
            root / "inbox" / "Link.md",
            "note",
            body="[Entry](<log:2025-10-12>)\n",
        )
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        preview = naming.plan_type_change(source, NoteType.REFERENCE)
        naming.apply(preview)

        target = root / "reference" / "A quiet Tuesday.md"
        assert target.is_file()
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.note_type is NoteType.REFERENCE
        assert document.date == NoteDate.from_text("2025-10-12")
        assert "note:A quiet Tuesday" in referrer.read_text(encoding="utf-8")

    def test_log_becomes_a_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = _write_note(
            root / "log" / "2025" / "10" / "2025-10-12.md",
            "log",
            body="# A quiet Tuesday\n",
            date="2025-10-12",
        )
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        preview = naming.plan_type_change(source, NoteType.PROJECT)
        naming.apply(preview)

        target = root / "projects" / "A quiet Tuesday.md"
        assert target.is_file()
        assert NoteDocument.from_text(target.read_text(encoding="utf-8")).note_type is NoteType.PROJECT

    def test_an_undated_note_cannot_become_a_log(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = _write_note(root / "reference" / "No date.md", "reference")
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        with pytest.raises(VaultError, match="Set a date"):
            naming.plan_type_change(source, NoteType.LOG)

    def test_an_occupied_date_refuses_the_change(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        source = _write_note(
            root / "reference" / "A quiet Tuesday.md",
            "reference",
            date="2025-10-12",
        )
        _write_note(
            root / "log" / "2025" / "10" / "2025-10-12.md",
            "log",
            date="2025-10-12",
        )
        naming = afanes.core.vault.log_conversions.LogConversions(afanes.core.vault.service.Vault(root))

        with pytest.raises(NameCollisionError):
            naming.plan_type_change(source, NoteType.LOG)
