"""End-to-end test for creation, linking, moving, and renaming notes."""

import os
from pathlib import Path

import afanes.core.vault
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.processing import ProcessingOutcome
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

ONE_REFERENCE = 1
FIRST_MODIFIED_NS = 1_700_000_000_000_000_000
SECOND_MODIFIED_NS = 1_700_000_001_000_000_000


class TestReferenceLifecycle:
    def test_link_survives_a_move_and_follows_a_rename(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        ada = afanes.core.vault.Vault(root).create(
            "Ada Lovelace",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
        )
        note = afanes.core.vault.Vault(root).create(
            "Prepare report",
            NoteType.NOTE,
            body="Ask [Ada Lovelace](<person:Ada Lovelace>).\n",
        )

        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada Lovelace")
        before = afanes.core.vault.Vault(root).scan()
        resolved = before.catalog.resolve(reference)
        assert resolved.outcome is ResolutionOutcome.RESOLVED
        assert resolved.targets == (ada,)

        moved = afanes.core.vault.Vault(root).move(ada, Path("work"), confirm=True)
        after_move = afanes.core.vault.Vault(root).scan()
        resolved_after_move = after_move.catalog.resolve(reference)
        assert resolved_after_move.outcome is ResolutionOutcome.RESOLVED
        assert resolved_after_move.targets == (moved,)

        preview = afanes.core.vault.Vault(root).plan_rename(moved, "Ada King")
        assert preview.reference_count == ONE_REFERENCE
        report = afanes.core.vault.Vault(root).apply_rename(preview, confirm=True)
        assert report.failed == ()
        assert "[Ada King](<person:Ada King>)" in note.read_text(encoding="utf-8")

        after_rename = afanes.core.vault.Vault(root).scan()
        renamed = after_rename.catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King"))
        assert renamed.outcome is ResolutionOutcome.RESOLVED
        assert renamed.targets[0].parent.name == "work"


class TestVaultLayoutAndTrash:
    def test_default_creation_uses_the_documented_layout(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)

        action = vault.create("Call Ada", NoteType.ACTION)
        project = vault.create("Launch", NoteType.PROJECT)
        reference = vault.create("Reading", NoteType.REFERENCE)
        person = vault.create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)

        assert action.parent == root / "actions"
        assert project.parent == root / "projects"
        assert reference.parent == root / "reference"
        assert person.parent == root / "reference" / "people"

    def test_trash_then_restore_updates_resolution(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        person = vault.create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)
        referring = vault.create("Note", NoteType.NOTE, body="[Ada](person:Ada)\n")
        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")

        count = vault.trash(person, confirm=True)

        assert count == ONE_REFERENCE
        assert not person.exists()
        assert (root / "trash" / "Ada.md").is_file()
        assert vault.scan().catalog.resolve(reference).outcome is ResolutionOutcome.UNRESOLVED

        restored = root / "reference" / "people" / "Ada.md"
        (root / "trash" / "Ada.md").replace(restored)

        assert vault.scan().catalog.resolve(reference).targets == (restored,)
        assert referring.exists()


class TestProcessingLifecycle:
    def test_capture_to_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Call Ada")

        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)
        target = vault.apply_processing(plan, confirm=True)
        snapshot = vault.scan()

        assert target == root / "actions" / "Call Ada.md"
        assert snapshot.inbox_notes() == ()
        assert [note.path for note in snapshot.notes] == [target]
        assert NoteDocument.from_text(target.read_text(encoding="utf-8")).body == "Call Ada"

    def test_capture_to_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Reading list")

        plan = vault.plan_processing(capture, ProcessingOutcome.REFERENCE)
        target = vault.apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))

        assert target == root / "reference" / "Reading list.md"
        assert document.note_type is NoteType.REFERENCE
        assert document.status is None
        assert vault.scan().inbox_notes() == ()

    def test_capture_to_later(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Maybe later")

        plan = vault.plan_processing(capture, ProcessingOutcome.LATER)
        target = vault.apply_processing(plan, confirm=True)
        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))

        assert document.status is Status.LATER
        assert vault.scan().inbox_notes() == ()

    def test_capture_to_project_with_a_linked_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Launch")

        plan = vault.plan_processing(capture, ProcessingOutcome.PROJECT)
        project = vault.apply_processing(plan, confirm=True)
        step = root / "actions" / "Draft brief.md"
        step.parent.mkdir(parents=True, exist_ok=True)
        step.write_text(
            '---\ntype: action\nstatus: active\nproject: "project:Launch"\n---\nDraft brief\n',
            encoding="utf-8",
        )

        snapshot = vault.scan()
        project_reference = NoteReference(scheme=ReferenceScheme.PROJECT, name="Launch")

        assert snapshot.catalog.resolve(project_reference).targets == (project,)
        assert [note.name for note in snapshot.notes] == ["Draft brief", "Launch"]

    def test_capture_to_trash_and_restore(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = vault.capture("Discard me")

        plan = vault.plan_processing(capture, ProcessingOutcome.TRASH)
        trashed = vault.apply_processing(plan, confirm=True)

        assert not capture.exists()
        assert trashed == root / "trash" / "Discard me.md"
        assert vault.scan().inbox_notes() == ()

        restored = root / "inbox" / "Discard me.md"
        trashed.replace(restored)

        assert [note.path for note in vault.scan().inbox_notes()] == [restored]


class TestInboxCapture:
    def test_capture_scan_list_and_preview_body(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        first = afanes.core.vault.Vault(root).capture("First thought\nwith detail")
        second = afanes.core.vault.Vault(root).capture("Second thought")
        os.utime(first, ns=(FIRST_MODIFIED_NS, FIRST_MODIFIED_NS))
        os.utime(second, ns=(SECOND_MODIFIED_NS, SECOND_MODIFIED_NS))

        snapshot = afanes.core.vault.Vault(root).scan()
        inbox = snapshot.inbox_notes()
        documents = [NoteDocument.from_text(note.path.read_text(encoding="utf-8")) for note in inbox]

        assert [note.name for note in inbox] == ["Second thought", "First thought"]
        assert [note.relative_path.as_posix() for note in inbox] == [
            "inbox/Second thought.md",
            "inbox/First thought.md",
        ]
        assert [document.body for document in documents] == ["Second thought", "First thought\nwith detail"]
        assert [document.raw for document in documents] == [{"type": "note"}, {"type": "note"}]
        assert all(note.path.parent.name == "inbox" for note in inbox)
