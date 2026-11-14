"""Tests for processing outcomes, plans, and apply behavior."""

import datetime
import hashlib
from pathlib import Path

import pytest

import afanes.core.atomic
import afanes.core.processing
import afanes.core.template_cards
import afanes.core.vault.naming
import afanes.core.vault.naming_reports
import afanes.core.vault.pages
import afanes.core.vault.processing
import afanes.core.vault.service
import afanes.core.vault.snapshot
import afanes.core.vault.trash_metadata
from afanes.core.errors import NameCollisionError, ProcessingError, VaultError
from afanes.core.frontmatter import NoteDocument
from afanes.core.processing import AppendStepPlan, ProcessingOutcome, ProcessingPlan, ProcessingTarget
from afanes.core.steps import StepDocument
from afanes.models.note import CategoryLabel, NoteType, Status

HASH_A = "a" * 64
HASH_B = "b" * 64
SHA256_HEX_LENGTH = 64
TODAY = datetime.date(2026, 11, 14)
PLAN_DATE = datetime.date(2026, 11, 20)


def _plan(
    tmp_path: Path,
    *,
    outcome: ProcessingOutcome = ProcessingOutcome.PROJECT,
    target_type: NoteType = NoteType.PROJECT,
    target_status: Status | None = Status.ACTIVE,
    due_date: datetime.date | None = None,
    body_override: str | None = None,
    category: CategoryLabel | None = None,
    scaffold: str | None = None,
    source_hash: str = HASH_A,
    processed_hash: str = HASH_B,
    owner: str | None = None,
    asked_by: str | None = None,
) -> ProcessingPlan:
    if target_type is NoteType.REFERENCE and category is None:
        category = CategoryLabel("general")
    return ProcessingPlan(
        source_path=(tmp_path / "inbox" / "Foo.md").resolve(),
        target_path=(tmp_path / "projects" / "Foo.md").resolve(),
        outcome=outcome,
        target_type=target_type,
        target_status=target_status,
        due_date=due_date,
        body_override=body_override,
        category=category,
        scaffold=scaffold,
        source_hash=source_hash,
        processed_hash=processed_hash,
        reference_count=0,
        affected_notes=(),
        changes_scheme=False,
        owner=owner,
        asked_by=asked_by,
    )


def _capture(root: Path, text: str = "Call Ada") -> Path:
    return afanes.core.vault.pages.VaultPages(afanes.core.vault.service.Vault(root)).capture(text)


def _request(
    source: Path,
    outcome: ProcessingOutcome,
    *,
    status: Status | None = None,
    due_date: datetime.date | None = None,
    owner: str | None = None,
    asked_by: str | None = None,
    project: str | None = None,
    card: afanes.core.template_cards.TemplateCard | None = None,
    today: datetime.date | None = None,
    snapshot: afanes.core.vault.snapshot.VaultSnapshot | None = None,
) -> afanes.core.vault.processing.ProcessingRequest:
    return afanes.core.vault.processing.ProcessingRequest(
        outcome=outcome,
        note_path=source,
        status=status,
        due_date=due_date,
        owner=owner,
        asked_by=asked_by,
        project=project,
        card=card,
        today=today,
        snapshot=snapshot,
    )


def _card(
    *,
    category: str = "person",
    body: str = "## Contact\n\n- Email:\n",
) -> afanes.core.template_cards.TemplateCard:
    return afanes.core.template_cards.TemplateCard(
        relative_path=Path(f"{category}.md"),
        note_type=NoteType.REFERENCE,
        category=CategoryLabel(category),
        title=category.title(),
        description=None,
        body=body,
        text=f"---\ntype: reference\ncategory: {category}\n---\n\n{body}",
    )


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


class TestProcessingOutcome:
    def test_members_cover_the_canonical_contract(self) -> None:
        assert {member.value for member in ProcessingOutcome} == {
            "trash",
            "later",
            "reference",
            "project",
            "append_step",
            "done_now",
            "log",
        }

    def test_members_compare_as_strings(self) -> None:
        assert ProcessingOutcome.APPEND_STEP == "append_step"


class TestProcessingTarget:
    def test_reference_is_uncategorized_and_open(self) -> None:
        target = ProcessingTarget.from_outcome(ProcessingOutcome.REFERENCE, None)
        assert target.note_type is NoteType.REFERENCE
        assert target.status is None

    def test_later_forces_the_later_status(self) -> None:
        target = ProcessingTarget.from_outcome(ProcessingOutcome.LATER, None)
        assert target.note_type is NoteType.REFERENCE
        assert target.status is Status.LATER

    def test_later_rejects_another_status(self) -> None:
        with pytest.raises(ProcessingError):
            ProcessingTarget.from_outcome(ProcessingOutcome.LATER, Status.DONE)

    def test_project_defaults_to_active(self) -> None:
        target = ProcessingTarget.from_outcome(ProcessingOutcome.PROJECT, None)
        assert target.note_type is NoteType.PROJECT
        assert target.status is Status.ACTIVE

    def test_project_accepts_a_valid_status(self) -> None:
        target = ProcessingTarget.from_outcome(ProcessingOutcome.PROJECT, Status.WAITING)
        assert target.status is Status.WAITING

    def test_done_now_is_a_done_project(self) -> None:
        target = ProcessingTarget.from_outcome(ProcessingOutcome.DONE_NOW, None)
        assert target.note_type is NoteType.PROJECT
        assert target.status is Status.DONE

    def test_done_now_rejects_another_status(self) -> None:
        with pytest.raises(ProcessingError):
            ProcessingTarget.from_outcome(ProcessingOutcome.DONE_NOW, Status.ACTIVE)

    @pytest.mark.parametrize("outcome", [ProcessingOutcome.TRASH, ProcessingOutcome.APPEND_STEP])
    def test_non_note_outcomes_do_not_target_a_note(self, outcome: ProcessingOutcome) -> None:
        with pytest.raises(ProcessingError):
            ProcessingTarget.from_outcome(outcome, None)


class TestProcessingPlan:
    def test_accepts_a_project_plan(self, tmp_path: Path) -> None:
        plan = _plan(tmp_path)
        assert plan.outcome is ProcessingOutcome.PROJECT

    def test_accepts_a_reference_plan(self, tmp_path: Path) -> None:
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.REFERENCE,
            target_type=NoteType.REFERENCE,
            target_status=None,
        )
        assert plan.target_type is NoteType.REFERENCE

    def test_accepts_a_trash_plan(self, tmp_path: Path) -> None:
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.TRASH,
            target_type=NoteType.NOTE,
            target_status=None,
        )
        assert plan.outcome is ProcessingOutcome.TRASH

    def test_rejects_a_relative_path(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            ProcessingPlan(
                source_path=Path("inbox/Foo.md"),
                target_path=(tmp_path / "projects/Foo.md").resolve(),
                outcome=ProcessingOutcome.PROJECT,
                target_type=NoteType.PROJECT,
                target_status=Status.ACTIVE,
                due_date=None,
                body_override=None,
                category=None,
                scaffold=None,
                source_hash=HASH_A,
                processed_hash=HASH_B,
                reference_count=0,
                affected_notes=(),
                changes_scheme=False,
            )

    def test_rejects_the_same_source_and_destination(self, tmp_path: Path) -> None:
        target = (tmp_path / "inbox/Foo.md").resolve()
        with pytest.raises(ProcessingError):
            ProcessingPlan(
                source_path=target,
                target_path=target,
                outcome=ProcessingOutcome.PROJECT,
                target_type=NoteType.PROJECT,
                target_status=Status.ACTIVE,
                due_date=None,
                body_override=None,
                category=None,
                scaffold=None,
                source_hash=HASH_A,
                processed_hash=HASH_B,
                reference_count=0,
                affected_notes=(),
                changes_scheme=False,
            )

    def test_rejects_an_empty_hash(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, source_hash="")

    def test_rejects_trash_with_a_due_date(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.TRASH,
                target_type=NoteType.NOTE,
                target_status=None,
                due_date=PLAN_DATE,
            )

    def test_rejects_later_with_the_wrong_status(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.LATER,
                target_type=NoteType.REFERENCE,
                target_status=Status.ACTIVE,
            )

    def test_rejects_reference_with_a_status(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.REFERENCE,
                target_type=NoteType.REFERENCE,
                target_status=Status.LATER,
            )

    def test_rejects_project_with_a_reference_type(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, target_type=NoteType.REFERENCE)

    def test_rejects_done_now_without_the_done_status(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, outcome=ProcessingOutcome.DONE_NOW, target_status=Status.ACTIVE)

    def test_rejects_a_due_date_on_a_reference(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.REFERENCE,
                target_type=NoteType.REFERENCE,
                target_status=None,
                due_date=PLAN_DATE,
            )

    @pytest.mark.parametrize(
        ("outcome", "target_type", "target_status"),
        [
            (ProcessingOutcome.REFERENCE, NoteType.REFERENCE, None),
            (ProcessingOutcome.LATER, NoteType.REFERENCE, Status.LATER),
            (ProcessingOutcome.LOG, NoteType.LOG, None),
            (ProcessingOutcome.TRASH, NoteType.NOTE, None),
        ],
    )
    def test_rejects_role_names_outside_project_outcomes(
        self,
        tmp_path: Path,
        outcome: ProcessingOutcome,
        target_type: NoteType,
        target_status: Status | None,
    ) -> None:
        with pytest.raises(ProcessingError, match="Only projects"):
            _plan(
                tmp_path,
                outcome=outcome,
                target_type=target_type,
                target_status=target_status,
                owner="Sam Rivera",
            )

    def test_rejects_a_blank_owner(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, owner="   ")

    def test_rejects_a_blank_requester(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, asked_by="   ")

    def test_rejects_an_append_outcome(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, outcome=ProcessingOutcome.APPEND_STEP)

    def test_accepts_a_reference_with_a_category_and_scaffold(self, tmp_path: Path) -> None:
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.REFERENCE,
            target_type=NoteType.REFERENCE,
            target_status=None,
            category=CategoryLabel("person"),
            scaffold="## Contact\n",
        )

        assert plan.category == CategoryLabel("person")
        assert plan.scaffold == "## Contact\n"

    def test_rejects_a_reference_without_a_category(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            ProcessingPlan(
                source_path=(tmp_path / "inbox" / "Foo.md").resolve(),
                target_path=(tmp_path / "reference" / "Foo.md").resolve(),
                outcome=ProcessingOutcome.REFERENCE,
                target_type=NoteType.REFERENCE,
                target_status=None,
                due_date=None,
                body_override=None,
                category=None,
                scaffold=None,
                source_hash=HASH_A,
                processed_hash=HASH_B,
                reference_count=0,
                affected_notes=(),
                changes_scheme=False,
            )

    def test_rejects_a_project_with_a_category(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(tmp_path, category=CategoryLabel("general"))

    def test_rejects_trash_with_a_scaffold(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            _plan(
                tmp_path,
                outcome=ProcessingOutcome.TRASH,
                target_type=NoteType.NOTE,
                target_status=None,
                scaffold="## Contact\n",
            )


class TestAppendStepPlan:
    def test_accepts_a_valid_plan(self, tmp_path: Path) -> None:
        plan = AppendStepPlan(
            capture_path=(tmp_path / "inbox/Call.md").resolve(),
            project_path=(tmp_path / "projects/Home.md").resolve(),
            step_text="Call the plumber",
            detail="Ask about the boiler",
            capture_hash=HASH_A,
            project_hash=HASH_B,
        )
        assert plan.step_text == "Call the plumber"

    def test_rejects_a_relative_path(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            AppendStepPlan(
                capture_path=Path("inbox/Call.md"),
                project_path=(tmp_path / "projects/Home.md").resolve(),
                step_text="Call",
                detail="",
                capture_hash=HASH_A,
                project_hash=HASH_B,
            )

    def test_rejects_the_same_file(self, tmp_path: Path) -> None:
        target = (tmp_path / "inbox/Call.md").resolve()
        with pytest.raises(ProcessingError):
            AppendStepPlan(
                capture_path=target,
                project_path=target,
                step_text="Call",
                detail="",
                capture_hash=HASH_A,
                project_hash=HASH_B,
            )

    def test_rejects_a_blank_step(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            AppendStepPlan(
                capture_path=(tmp_path / "inbox/Call.md").resolve(),
                project_path=(tmp_path / "projects/Home.md").resolve(),
                step_text="   ",
                detail="",
                capture_hash=HASH_A,
                project_hash=HASH_B,
            )

    def test_rejects_an_empty_hash(self, tmp_path: Path) -> None:
        with pytest.raises(ProcessingError):
            AppendStepPlan(
                capture_path=(tmp_path / "inbox/Call.md").resolve(),
                project_path=(tmp_path / "projects/Home.md").resolve(),
                step_text="Call",
                detail="",
                capture_hash="",
                project_hash=HASH_B,
            )


class TestProcessedText:
    def test_preserves_the_body_and_unknown_keys(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\ncustom: keep\n---\n# Call\n\nBody.\n")
        text = _plan(tmp_path).processed_text(document)
        reparsed = NoteDocument.from_text(text)

        assert reparsed.note_type is NoteType.PROJECT
        assert reparsed.raw["custom"] == "keep"
        assert reparsed.body == "# Call\n\nBody.\n"

    def test_writes_the_due_date(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n# Call\n")
        text = _plan(tmp_path, due_date=PLAN_DATE).processed_text(document)

        assert NoteDocument.from_text(text).due_date == PLAN_DATE

    def test_writes_the_owner_and_requester(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n# Call\n")
        text = _plan(tmp_path, owner="Sam Rivera", asked_by="Priya Nair").processed_text(document)
        reparsed = NoteDocument.from_text(text)

        assert reparsed.owner == "Sam Rivera"
        assert reparsed.asked_by == "Priya Nair"

    def test_trims_owner_and_requester_text(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n# Call\n")
        text = _plan(tmp_path, owner="  Sam Rivera  ", asked_by="  Priya Nair  ").processed_text(document)
        reparsed = NoteDocument.from_text(text)

        assert reparsed.raw["owner"] == "Sam Rivera"
        assert reparsed.raw["asked_by"] == "Priya Nair"

    def test_uses_a_body_override_for_done_now(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n# Call\n")
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.DONE_NOW,
            target_status=Status.DONE,
            body_override="# Call\n\n- [x] Call <!-- {actual: 2026-11-14} -->\n",
        )
        text = plan.processed_text(document)

        assert "- [x] Call" in text
        assert "status: done" in text

    def test_sets_the_reference_category(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n# Ada\n")
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.REFERENCE,
            target_type=NoteType.REFERENCE,
            target_status=None,
            category=CategoryLabel("person"),
        )
        text = plan.processed_text(document)

        assert NoteDocument.from_text(text).category == CategoryLabel("person")

    def test_appends_the_scaffold_below_the_capture(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n# Ada\n")
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.REFERENCE,
            target_type=NoteType.REFERENCE,
            target_status=None,
            category=CategoryLabel("person"),
            scaffold="## Contact\n\n- Email:\n",
        )
        reparsed = NoteDocument.from_text(plan.processed_text(document))

        assert reparsed.body == "# Ada\n\n## Contact\n\n- Email:\n"

    def test_the_capture_text_remains_a_prefix(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\ncustom: keep\n---\n# Ada\n\nBody.\n")
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.REFERENCE,
            target_type=NoteType.REFERENCE,
            target_status=None,
            category=CategoryLabel("person"),
            scaffold="## Contact\n",
        )
        reparsed = NoteDocument.from_text(plan.processed_text(document))

        assert reparsed.body.startswith("# Ada\n\nBody.\n")
        assert reparsed.raw["custom"] == "keep"

    def test_the_scaffold_follows_the_document_newline_style(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\r\ntype: note\r\n---\r\n# Ada\r\n")
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.REFERENCE,
            target_type=NoteType.REFERENCE,
            target_status=None,
            category=CategoryLabel("person"),
            scaffold="## Contact\n",
        )
        reparsed = NoteDocument.from_text(plan.processed_text(document))

        assert "\r\n## Contact\r\n" in reparsed.body
        assert reparsed.newline == "\r\n"

    def test_an_empty_scaffold_leaves_the_body(self, tmp_path: Path) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n# Ada\n")
        plan = _plan(
            tmp_path,
            outcome=ProcessingOutcome.REFERENCE,
            target_type=NoteType.REFERENCE,
            target_status=None,
            category=CategoryLabel("person"),
            scaffold="",
        )
        reparsed = NoteDocument.from_text(plan.processed_text(document))

        assert reparsed.body == "# Ada\n"


class TestPlanProcessing:
    def test_plans_a_project_with_defaults(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.target_type is NoteType.PROJECT
        assert plan.target_status is Status.ACTIVE
        assert plan.target_path == root / "projects" / source.name

    def test_plans_a_project_with_a_due_date(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(
                source,
                ProcessingOutcome.PROJECT,
                due_date=PLAN_DATE,
            )
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.due_date == PLAN_DATE

    def test_plans_a_project_with_role_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(
                source,
                ProcessingOutcome.PROJECT,
                owner="  Sam Rivera ",
                asked_by=" Priya Nair  ",
            )
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.owner == "Sam Rivera"
        assert plan.asked_by == "Priya Nair"

    def test_plans_a_done_now_project_with_role_names(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(
                source,
                ProcessingOutcome.DONE_NOW,
                today=TODAY,
                owner="Sam Rivera",
                asked_by="Priya Nair",
            )
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.owner == "Sam Rivera"
        assert plan.asked_by == "Priya Nair"
        assert plan.target_status is Status.DONE

    def test_plans_a_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.REFERENCE)
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.target_type is NoteType.REFERENCE
        assert plan.target_status is None
        assert plan.category == CategoryLabel("general")
        assert plan.scaffold is None
        assert plan.target_path == root / "reference" / "general" / source.name

    def test_plans_a_reference_from_a_card(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        card = _card()

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.REFERENCE, card=card)
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.category == CategoryLabel("person")
        assert plan.scaffold == "## Contact\n\n- Email:\n"
        assert plan.target_path == root / "reference" / "person" / source.name

    def test_a_card_with_an_empty_body_adds_no_scaffold(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.REFERENCE, card=_card(body=""))
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.scaffold is None

    def test_a_project_rejects_a_card(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
                _request(source, ProcessingOutcome.PROJECT, card=_card())
            )

    def test_planning_with_a_card_leaves_the_capture_unchanged(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        before = source.read_bytes()

        afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.REFERENCE, card=_card())
        )

        assert source.read_bytes() == before

    def test_plans_a_later_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.LATER)
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.target_status is Status.LATER

    def test_plans_done_now_with_a_ticked_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root, "Call the plumber\n\nAsk about the boiler")

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(
                source,
                ProcessingOutcome.DONE_NOW,
                today=TODAY,
            )
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.target_status is Status.DONE
        assert plan.body_override is not None
        steps = StepDocument(plan.body_override).steps
        assert [step.text for step in steps] == ["Call the plumber"]
        assert steps[0].checked is True
        assert steps[0].actual == TODAY

    def test_plans_trash(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.TRASH)
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.target_path.parent == root / "trash"
        assert plan.target_path.suffix == ".md"
        assert plan.target_path != root / "trash" / source.name

    def test_reports_a_scheme_change(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.changes_scheme is True

    def test_plans_without_writing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        before = _tree_state(root)

        afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )

        assert _tree_state(root) == before

    def test_rejects_a_note_outside_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = root / "notes" / "Call.md"
        source.parent.mkdir()
        source.write_text("---\ntype: note\n---\n# Call\n", encoding="utf-8")

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
                _request(source, ProcessingOutcome.PROJECT)
            )

    def test_rejects_an_existing_note_scheme_name(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        vault = afanes.core.vault.service.Vault(root)
        afanes.core.vault.pages.VaultPages(vault).create_page("Other", NoteType.REFERENCE)
        source = root / "inbox" / "Other.md"
        source.parent.mkdir()
        source.write_text("---\ntype: note\n---\n# Other\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
                _request(source, ProcessingOutcome.REFERENCE)
            )

    def test_rejects_an_existing_project_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        target = root / "projects" / source.name
        target.parent.mkdir()
        target.write_text("---\ntype: project\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
                _request(source, ProcessingOutcome.PROJECT)
            )

    def test_rejects_a_due_date_on_a_reference_plan(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
                _request(
                    source,
                    ProcessingOutcome.REFERENCE,
                    due_date=PLAN_DATE,
                )
            )

    def test_rejects_role_names_on_a_reference_plan(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        with pytest.raises(ProcessingError, match="Only projects"):
            afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
                _request(
                    source,
                    ProcessingOutcome.REFERENCE,
                    owner="Sam Rivera",
                )
            )

    def test_plan_source_hash_matches_the_capture(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        plan = afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )

        assert isinstance(plan, ProcessingPlan)
        assert plan.source_hash == hashlib.sha256(source.read_bytes()).hexdigest()
        assert plan.processed_hash != plan.source_hash
        assert len(plan.source_hash) == SHA256_HEX_LENGTH


class TestPlanAppend:
    def test_targets_a_project_by_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root, "Call the plumber\n\nAsk about the boiler")
        vault = afanes.core.vault.service.Vault(root)
        project = afanes.core.vault.pages.VaultPages(vault).create_page("Home", NoteType.PROJECT, body="# Home\n")

        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.APPEND_STEP, project="home")
        )

        assert isinstance(plan, AppendStepPlan)
        assert plan.project_path == project
        assert plan.step_text == "Call the plumber"
        assert "Ask about the boiler" in plan.detail

    def test_rejects_a_name_that_matches_no_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
                _request(
                    source,
                    ProcessingOutcome.APPEND_STEP,
                    project="Missing",
                )
            )

    def test_requires_a_target(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
                _request(source, ProcessingOutcome.APPEND_STEP)
            )

    def test_rejects_an_ambiguous_target(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        (root / "projects").mkdir()
        (root / "projects" / "Home.md").write_text("---\ntype: project\n---\n", encoding="utf-8")
        (root / "projects" / "home.md").write_text("---\ntype: project\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.processing.VaultProcessing(afanes.core.vault.service.Vault(root)).plan_processing(
                _request(
                    source,
                    ProcessingOutcome.APPEND_STEP,
                    project="Home",
                )
            )


class TestApplyProcessing:
    def test_moves_and_writes_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.PROJECT, due_date=PLAN_DATE)
        )

        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert target == root / "projects" / source.name
        assert not source.exists()
        assert document.note_type is NoteType.PROJECT
        assert document.status is Status.ACTIVE
        assert document.due_date == PLAN_DATE
        assert document.body == "# Call Ada"

    def test_requires_confirmation(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan)

        assert source.exists()

    def test_rejects_a_changed_source(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )
        source.write_text("---\ntype: note\n---\n# Changed\n", encoding="utf-8")

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

    def test_rejects_a_destination_that_appeared(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )
        assert isinstance(plan, ProcessingPlan)
        plan.target_path.parent.mkdir(parents=True)
        plan.target_path.write_text("---\ntype: project\n---\n", encoding="utf-8")

        with pytest.raises(NameCollisionError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

    def test_write_failure_leaves_the_source(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )
        before = source.read_bytes()

        def fail_write(_path: Path, _text: str) -> None:
            message = "disk full"
            raise OSError(message)

        monkeypatch.setattr(afanes.core.atomic.AtomicWriter, "write_text_atomic", fail_write)
        with pytest.raises(OSError, match="disk full"):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert source.read_bytes() == before
        assert not (root / "projects").exists()

    def test_move_failure_is_retryable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.PROJECT)
        )
        original_replace = Path.replace

        def fail_replace(self_path: Path, target: Path) -> Path:
            if self_path == source:
                message = "busy"
                raise OSError(message)
            return original_replace(self_path, target)

        monkeypatch.setattr(Path, "replace", fail_replace)
        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert source.exists()
        monkeypatch.setattr(Path, "replace", original_replace)
        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)
        assert target.exists()
        assert not source.exists()

    def test_done_now_writes_a_ticked_done_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root, "Call the plumber")
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.DONE_NOW, today=TODAY)
        )

        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        steps = StepDocument(document.body).steps
        assert document.status is Status.DONE
        assert steps[0].checked is True
        assert steps[0].actual == TODAY

    def test_trash_moves_the_file_and_records_metadata(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.TRASH)
        )

        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        document = afanes.core.vault.trash_metadata.TrashDocument.from_text(target.read_text(encoding="utf-8"))
        assert target.parent == root / "trash"
        assert not source.exists()
        assert document.metadata is not None
        assert document.metadata.birthplace == Path("inbox") / source.name
        assert document.body == "# Call Ada"

    def test_applies_a_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.REFERENCE)
        )

        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert target == root / "reference" / "general" / source.name
        assert document.note_type is NoteType.REFERENCE
        assert document.status is None

    def test_applies_a_reference_from_a_card(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.REFERENCE, card=_card())
        )

        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(target.read_text(encoding="utf-8"))
        assert target == root / "reference" / "person" / source.name
        assert document.category == CategoryLabel("person")
        assert document.body == "# Call Ada\n\n## Contact\n\n- Email:\n"

    def test_applies_a_later_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.LATER)
        )

        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert NoteDocument.from_text(target.read_text(encoding="utf-8")).status is Status.LATER

    def test_trash_leaves_referring_notes_unchanged(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        referring = root / "notes" / "Other.md"
        referring.parent.mkdir()
        referring.write_text("---\ntype: reference\n---\n[Call](<note:Call Ada>)\n", encoding="utf-8")
        before = referring.read_bytes()
        vault = afanes.core.vault.service.Vault(root)
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.TRASH)
        )

        afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert referring.read_bytes() == before


class TestApplyAppend:
    def test_writes_the_step_and_trashes_the_capture(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root, "Call the plumber\n\nAsk about the boiler")
        vault = afanes.core.vault.service.Vault(root)
        project = afanes.core.vault.pages.VaultPages(vault).create_page("Home", NoteType.PROJECT, body="# Home\n")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.APPEND_STEP, project="Home")
        )

        target = afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        document = NoteDocument.from_text(project.read_text(encoding="utf-8"))
        steps = StepDocument(document.body).steps
        assert target == project
        assert [step.text for step in steps] == ["Call the plumber"]
        assert "Ask about the boiler" in document.body
        assert not source.exists()
        trashed = list((root / "trash").glob("*.md"))
        assert len(trashed) == 1
        trashed_document = afanes.core.vault.trash_metadata.TrashDocument.from_text(
            trashed[0].read_text(encoding="utf-8")
        )
        assert trashed_document.metadata is not None
        assert trashed_document.metadata.birthplace == Path("inbox") / source.name

    def test_changed_target_aborts_and_keeps_the_capture(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        project = afanes.core.vault.pages.VaultPages(vault).create_page("Home", NoteType.PROJECT, body="# Home\n")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.APPEND_STEP, project="Home")
        )
        project.write_text("---\ntype: project\n---\n# Home\n\nChanged.\n", encoding="utf-8")
        before = project.read_bytes()

        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert source.exists()
        assert project.read_bytes() == before

    def test_retry_does_not_duplicate_the_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        project = afanes.core.vault.pages.VaultPages(vault).create_page("Home", NoteType.PROJECT, body="# Home\n")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.APPEND_STEP, project="Home")
        )

        def fail_trash(
            _self: afanes.core.vault.naming.VaultNaming,
            *_args: object,
            **_kwargs: object,
        ) -> afanes.core.vault.naming_reports.TrashPreview:
            message = "busy"
            raise VaultError(message)

        monkeypatch.setattr(afanes.core.vault.naming.VaultNaming, "trash", fail_trash)
        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)
        assert source.exists()

        monkeypatch.undo()
        afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        steps = StepDocument(NoteDocument.from_text(project.read_text(encoding="utf-8")).body).steps
        assert [step.text for step in steps] == ["Call Ada"]
        assert not source.exists()

    def test_missing_target_aborts(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        source = _capture(root)
        vault = afanes.core.vault.service.Vault(root)
        project = afanes.core.vault.pages.VaultPages(vault).create_page("Home", NoteType.PROJECT, body="# Home\n")
        plan = afanes.core.vault.processing.VaultProcessing(vault).plan_processing(
            _request(source, ProcessingOutcome.APPEND_STEP, project="Home")
        )

        project.unlink()
        with pytest.raises(ProcessingError):
            afanes.core.vault.processing.VaultProcessing(vault).apply_processing(plan, confirm=True)

        assert source.exists()
