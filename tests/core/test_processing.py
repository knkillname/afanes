"""Tests for processing outcomes, plans, and apply behavior."""

import datetime
import hashlib
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.processing
import afanes.core.vault
from afanes.core.errors import NameCollisionError, ProcessingError, VaultError
from afanes.core.frontmatter import NoteDocument
from afanes.core.links import ResolutionOutcome
from afanes.core.processing import ProcessingOutcome, ProcessingPlan
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

HASH_A = "a" * 64
HASH_B = "b" * 64
SHA256_HEX_LENGTH = 64
CUSTOM_VALUE = 42


def _target_directory(target_type: NoteType) -> str:
    if target_type is NoteType.ACTION:
        return "actions"
    if target_type is NoteType.PROJECT:
        return "projects"
    return "reference"


def _plan(
    tmp_path: Path,
    *,
    outcome: ProcessingOutcome = ProcessingOutcome.ACTION,
    target_type: NoteType = NoteType.ACTION,
    target_category: ReferenceCategory | None = None,
    target_status: Status | None = Status.ACTIVE,
    due_date: datetime.date | None = None,
    people: tuple[NoteReference, ...] = (),
    project: NoteReference | None = None,
    source_hash: str = HASH_A,
    processed_hash: str = HASH_B,
) -> ProcessingPlan:
    return ProcessingPlan(
        source_path=(tmp_path / "inbox" / "Foo.md").resolve(),
        target_path=(tmp_path / _target_directory(target_type) / "Foo.md").resolve(),
        outcome=outcome,
        target_type=target_type,
        target_category=target_category,
        target_status=target_status,
        due_date=due_date,
        people=people,
        project=project,
        source_hash=source_hash,
        processed_hash=processed_hash,
        reference_count=0,
        affected_notes=(),
        changes_scheme=False,
        unresolved_references=(),
    )


class TestProcessingOutcome:
    def test_members_cover_the_canonical_contract(self) -> None:
        assert {member.value for member in ProcessingOutcome} == {
            "trash",
            "later",
            "reference",
            "action",
            "project",
        }

    def test_members_compare_as_strings(self) -> None:
        assert ProcessingOutcome.LATER == "later"


class TestProcessingPlan:
    def test_accepts_a_valid_action_plan(self, tmp_path: Path) -> None:
        person = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")
        plan = _plan(tmp_path, people=(person,))

        assert plan.outcome is ProcessingOutcome.ACTION
        assert plan.people == (person,)

    def test_accepts_a_valid_later_plan(self, tmp_path: Path) -> None:
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.LATER,
            target_type=NoteType.REFERENCE,
            target_status=Status.LATER,
        )

        assert plan.target_status is Status.LATER

    def test_accepts_a_valid_trash_plan(self, tmp_path: Path) -> None:
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.TRASH,
            target_type=NoteType.NOTE,
            target_status=None,
            processed_hash=HASH_A,
        )

        assert plan.outcome is ProcessingOutcome.TRASH

    def test_rejects_a_relative_path(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            ProcessingPlan(
                source_path=Path("inbox/Foo.md"),
                target_path=(tmp_path / "actions" / "Foo.md").resolve(),
                outcome=ProcessingOutcome.ACTION,
                target_type=NoteType.ACTION,
                target_category=None,
                target_status=Status.ACTIVE,
                due_date=None,
                people=(),
                project=None,
                source_hash=HASH_A,
                processed_hash=HASH_B,
                reference_count=0,
                affected_notes=(),
                changes_scheme=False,
                unresolved_references=(),
            )

    def test_rejects_the_same_source_and_destination(self, tmp_path: Path) -> None:
        path = (tmp_path / "inbox" / "Foo.md").resolve()
        with pytest.raises(ProcessingError):
            ProcessingPlan(
                source_path=path,
                target_path=path,
                outcome=ProcessingOutcome.ACTION,
                target_type=NoteType.ACTION,
                target_category=None,
                target_status=Status.ACTIVE,
                due_date=None,
                people=(),
                project=None,
                source_hash=HASH_A,
                processed_hash=HASH_B,
                reference_count=0,
                affected_notes=(),
                changes_scheme=False,
                unresolved_references=(),
            )

    def test_rejects_an_empty_hash(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, source_hash="")

    def test_rejects_a_person_with_the_wrong_scheme(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, people=(NoteReference(scheme=ReferenceScheme.PROJECT, name="Ada"),))

    def test_rejects_a_project_with_the_wrong_scheme(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, project=NoteReference(scheme=ReferenceScheme.PERSON, name="Launch"))

    def test_rejects_trash_with_metadata(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.TRASH,
                target_type=NoteType.NOTE,
                target_status=None,
                due_date=datetime.date(2026, 11, 11),
            )

    def test_rejects_later_with_the_wrong_status(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.LATER,
                target_type=NoteType.REFERENCE,
                target_status=Status.ARCHIVED,
            )

    def test_rejects_reference_with_a_status(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.REFERENCE,
                target_type=NoteType.REFERENCE,
                target_status=Status.LATER,
            )

    def test_rejects_action_with_the_wrong_type(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, target_type=NoteType.PROJECT)

    def test_rejects_project_with_a_project_reference(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.PROJECT,
                target_type=NoteType.PROJECT,
                project=NoteReference(scheme=ReferenceScheme.PROJECT, name="Launch"),
            )

    def test_rejects_a_category_on_an_action(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, target_category=ReferenceCategory.PERSON)

    def test_rejects_a_due_date_on_a_reference(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.REFERENCE,
                target_type=NoteType.REFERENCE,
                target_status=None,
                due_date=datetime.date(2026, 11, 11),
            )


def _capture(root: Path, text: str = "Call Ada") -> Path:
    return afanes.core.vault.Vault(root).capture(text)


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


class TestPlanProcessing:
    def test_plans_an_action_with_defaults(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = _capture(root)

        plan = afanes.core.vault.Vault(root).plan_processing(
            capture,
            ProcessingOutcome.ACTION,
        )

        assert plan.target_path == root / "actions" / "Call Ada.md"
        assert plan.target_type is NoteType.ACTION
        assert plan.target_status is Status.ACTIVE
        assert plan.changes_scheme is False
        assert len(plan.source_hash) == SHA256_HEX_LENGTH
        assert len(plan.processed_hash) == SHA256_HEX_LENGTH
        assert plan.processed_hash != plan.source_hash

    def test_plans_an_action_with_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        vault.create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)
        vault.create("Launch", NoteType.PROJECT)

        plan = vault.plan_processing(
            capture,
            ProcessingOutcome.ACTION,
            status=Status.WAITING,
            due_date=datetime.date(2026, 11, 20),
            people=("Ada",),
            project="Launch",
        )

        assert plan.target_status is Status.WAITING
        assert plan.due_date == datetime.date(2026, 11, 20)
        assert plan.people == (NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"),)
        assert plan.project == NoteReference(scheme=ReferenceScheme.PROJECT, name="Launch")
        assert plan.unresolved_references == ()

    def test_reports_unresolved_assignments(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = _capture(root)

        plan = afanes.core.vault.Vault(root).plan_processing(
            capture,
            ProcessingOutcome.ACTION,
            people=("Grace",),
            project="Missing",
        )

        assert [reference.name for reference in plan.unresolved_references] == ["Grace", "Missing"]

    def test_assigning_a_page_identity_resolves_it(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create(
            "Ada",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
            body="# Ada, Countess of Lovelace\n",
        )
        capture = _capture(root)

        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION, people=("Ada",))

        assert plan.people == (NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"),)
        assert plan.unresolved_references == ()

    def test_assigning_a_display_title_keeps_it_unresolved(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create(
            "Ada",
            NoteType.REFERENCE,
            category=ReferenceCategory.PERSON,
            body="# Ada, Countess of Lovelace\n",
        )
        capture = _capture(root)

        plan = vault.plan_processing(
            capture,
            ProcessingOutcome.ACTION,
            people=("Ada, Countess of Lovelace",),
        )

        assert plan.people == (NoteReference(scheme=ReferenceScheme.PERSON, name="Ada, Countess of Lovelace"),)
        assert plan.unresolved_references == plan.people

    def test_plans_a_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = _capture(root)

        plan = afanes.core.vault.Vault(root).plan_processing(capture, ProcessingOutcome.REFERENCE)

        assert plan.target_path == root / "reference" / "Call Ada.md"
        assert plan.target_type is NoteType.REFERENCE
        assert plan.target_category is None
        assert plan.target_status is None
        assert plan.changes_scheme is False

    def test_plans_a_later_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = _capture(root)

        plan = afanes.core.vault.Vault(root).plan_processing(capture, ProcessingOutcome.LATER)

        assert plan.target_path == root / "reference" / "Call Ada.md"
        assert plan.target_status is Status.LATER

    def test_plans_a_project_and_reports_the_scheme_change(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = _capture(root)

        plan = afanes.core.vault.Vault(root).plan_processing(capture, ProcessingOutcome.PROJECT)

        assert plan.target_path == root / "projects" / "Call Ada.md"
        assert plan.target_type is NoteType.PROJECT
        assert plan.target_status is Status.ACTIVE
        assert plan.changes_scheme is True

    def test_plans_trash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        vault.create("Note", NoteType.NOTE, body="[Call Ada](<note:Call Ada>)\n")

        plan = vault.plan_processing(capture, ProcessingOutcome.TRASH)

        assert plan.target_path == root / "trash" / "Call Ada.md"
        assert plan.target_type is NoteType.NOTE
        assert plan.reference_count == 1
        assert plan.processed_hash == plan.source_hash

    def test_plans_without_writing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = _capture(root)
        before = _tree_state(root)

        afanes.core.vault.Vault(root).plan_processing(capture, ProcessingOutcome.ACTION)

        assert _tree_state(root) == before

    def test_rejects_a_note_outside_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        action = afanes.core.vault.Vault(root).create("Call Ada", NoteType.ACTION)

        with pytest.raises(ProcessingError):
            afanes.core.vault.Vault(root).plan_processing(action, ProcessingOutcome.ACTION)

    def test_rejects_an_existing_action_destination_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        (root / "actions").mkdir()
        (root / "actions" / "Call Ada.md").write_text("---\ntype: project\n---\n", encoding="utf-8")
        capture = _capture(root)

        with pytest.raises(NameCollisionError):
            vault.plan_processing(capture, ProcessingOutcome.ACTION)

    def test_rejects_an_existing_note_scheme_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        (root / "actions").mkdir()
        (root / "actions" / "Call Ada.md").write_text("---\ntype: action\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            vault.plan_processing(capture, ProcessingOutcome.ACTION)

    def test_rejects_an_existing_project_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create("Call Ada", NoteType.PROJECT)
        capture = _capture(root)

        with pytest.raises(NameCollisionError):
            vault.plan_processing(capture, ProcessingOutcome.PROJECT)

    def test_rejects_a_due_date_on_a_reference_plan(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = _capture(root)

        with pytest.raises(ProcessingError):
            afanes.core.vault.Vault(root).plan_processing(
                capture,
                ProcessingOutcome.REFERENCE,
                due_date=datetime.date(2026, 11, 20),
            )

    def test_plan_source_hash_matches_the_capture(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        capture = _capture(root)

        plan = afanes.core.vault.Vault(root).plan_processing(capture, ProcessingOutcome.ACTION)

        assert plan.source_hash == hashlib.sha256(capture.read_bytes()).hexdigest()


class TestApplyProcessing:
    def test_moves_and_writes_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        capture.write_text("---\ntype: note\ncustom: 42\n---\nCall Ada\nbody\n", encoding="utf-8")
        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)

        target = vault.apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert target == root / "actions" / "Call Ada.md"
        assert not capture.exists()
        assert document.note_type is NoteType.ACTION
        assert document.status is Status.ACTIVE
        assert document.raw["custom"] == CUSTOM_VALUE
        assert document.body == "Call Ada\nbody\n"

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)

        with pytest.raises(ProcessingError):
            vault.apply_processing(plan)

        assert capture.exists()

    def test_rejects_a_changed_source(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)
        capture.write_text("---\ntype: note\n---\nChanged\n", encoding="utf-8")

        with pytest.raises(ProcessingError):
            vault.apply_processing(plan, confirm=True)

        assert capture.exists()
        assert not (root / "actions" / "Call Ada.md").exists()

    def test_rejects_a_destination_that_appeared_after_planning(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)
        (root / "actions").mkdir()
        (root / "actions" / "Call Ada.md").write_text("---\ntype: project\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            vault.apply_processing(plan, confirm=True)

        assert capture.exists()

    def test_write_failure_leaves_the_source(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)
        original = capture.read_bytes()

        def fail_write(_path: Path, _text: str) -> None:
            message = "disk full"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.atomic, "write_text_atomic", fail_write)
        with pytest.raises(VaultError):
            vault.apply_processing(plan, confirm=True)

        assert capture.read_bytes() == original
        assert not (root / "actions" / "Call Ada.md").exists()

    def test_move_failure_is_retryable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)
        original_replace = Path.replace
        calls = 0

        def fail_once(source: Path, target: Path) -> Path:
            nonlocal calls
            if calls == 0:
                calls += 1
                message = "move failed"
                raise OSError(message)
            return original_replace(source, target)

        monkeypatch.setattr(Path, "replace", fail_once)
        with pytest.raises(ProcessingError):
            vault.apply_processing(plan, confirm=True)

        assert capture.exists()
        assert NoteDocument.from_text(capture.read_text(encoding="utf-8")).note_type is NoteType.ACTION

        target = vault.apply_processing(plan, confirm=True)

        assert target.exists()
        assert not capture.exists()

    def test_trash_moves_the_file_without_rewriting_it(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        original = capture.read_bytes()
        plan = vault.plan_processing(capture, ProcessingOutcome.TRASH)

        target = vault.apply_processing(plan, confirm=True)

        assert target == root / "trash" / "Call Ada.md"
        assert target.read_bytes() == original
        assert not capture.exists()

    def test_applies_a_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.REFERENCE)

        target = vault.apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert target == root / "reference" / "Call Ada.md"
        assert document.note_type is NoteType.REFERENCE
        assert document.category is None
        assert document.status is None
        assert document.body == "# Call Ada"

    def test_applies_a_later_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.LATER)

        target = vault.apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.status is Status.LATER

    def test_applies_a_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.PROJECT)

        target = vault.apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert target == root / "projects" / "Call Ada.md"
        assert document.note_type is NoteType.PROJECT
        assert document.status is Status.ACTIVE
        assert "project" not in document.raw
        assert "category" not in document.raw

    def test_applies_action_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create("Ada", NoteType.REFERENCE, category=ReferenceCategory.PERSON)
        vault.create("Launch", NoteType.PROJECT)
        capture = _capture(root)
        plan = vault.plan_processing(
            capture,
            ProcessingOutcome.ACTION,
            status=Status.WAITING,
            due_date=datetime.date(2026, 11, 20),
            people=("Ada",),
            project="Launch",
        )

        target = vault.apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert document.status is Status.WAITING
        assert document.raw["due_date"] == "2026-11-20"
        assert document.raw["people"] == ["person:Ada"]
        assert document.raw["project"] == "project:Launch"

    def test_applies_an_action_with_unresolved_assignments(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        plan = vault.plan_processing(
            capture,
            ProcessingOutcome.ACTION,
            people=("Grace",),
            project="Missing",
        )

        target = vault.apply_processing(plan, confirm=True)
        note = next(note for note in vault.scan().notes if note.path == target)

        assert [reference.name for reference in note.frontmatter_references] == ["Grace", "Missing"]
        assert all(
            vault.scan().catalog.resolve(reference).outcome is ResolutionOutcome.UNRESOLVED
            for reference in note.frontmatter_references
        )

    def test_action_keeps_note_references_resolved(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create("Note", NoteType.NOTE, body="[Call Ada](<note:Call Ada>)\n")
        capture = _capture(root)
        plan = vault.plan_processing(capture, ProcessingOutcome.ACTION)

        target = vault.apply_processing(plan, confirm=True)
        resolution = vault.scan().catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Call Ada"))

        assert plan.changes_scheme is False
        assert resolution.outcome is ResolutionOutcome.RESOLVED
        assert resolution.targets == (target,)

    def test_project_reports_and_breaks_note_references(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        vault.create("Note", NoteType.NOTE, body="[Launch](<note:Launch>)\n")
        capture = _capture(root, "Launch")
        plan = vault.plan_processing(capture, ProcessingOutcome.PROJECT)

        target = vault.apply_processing(plan, confirm=True)
        snapshot = vault.scan()

        assert plan.changes_scheme is True
        assert plan.reference_count == 1
        assert snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Launch")).outcome is (
            ResolutionOutcome.UNRESOLVED
        )
        assert snapshot.catalog.resolve(NoteReference(scheme=ReferenceScheme.PROJECT, name="Launch")).targets == (
            target,
        )

    def test_trash_leaves_referring_notes_unchanged(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.Vault(root)
        capture = _capture(root)
        referring = vault.create("Note", NoteType.NOTE, body="[Call Ada](<note:Call Ada>)\n")
        before = referring.read_bytes()
        plan = vault.plan_processing(capture, ProcessingOutcome.TRASH)

        vault.apply_processing(plan, confirm=True)

        assert referring.read_bytes() == before
        assert (
            vault.scan().catalog.resolve(NoteReference(scheme=ReferenceScheme.NOTE, name="Call Ada")).outcome
            is ResolutionOutcome.UNRESOLVED
        )
