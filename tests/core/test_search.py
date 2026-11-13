"""Tests for browser groups, project summaries, and the review queue."""

import datetime
from pathlib import Path

import afanes.core.search
import afanes.core.vault.service
import afanes.core.vault.snapshot
from afanes.core.search import Browser, BrowserSection, ProjectBoard, ProjectStage, ReviewItemKind, ReviewPlanner
from afanes.core.vault.service import Vault
from afanes.models.note import CategoryLabel

TODAY = datetime.date(2026, 11, 14)
TOMORROW = datetime.date(2026, 11, 15)
TWO_STEPS = 2
FOUR_PENDING = 4


def _write_note(
    root: Path,
    relative: str,
    note_type: str,
    body: str = "",
    *,
    category: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    asked_by: str | None = None,
    owner: str | None = None,
) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if category is not None:
        lines.append(f"category: {category}")
    if status is not None:
        lines.append(f"status: {status}")
    if due_date is not None:
        lines.append(f"due_date: {due_date}")
    if asked_by is not None:
        lines.append(f"asked_by: {asked_by}")
    if owner is not None:
        lines.append(f"owner: {owner}")
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _snapshot(root: Path) -> afanes.core.vault.snapshot.VaultSnapshot:
    return Vault(root).scan()


class TestBrowserGroups:
    def test_project_appears_under_projects(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write_note(root, "projects/Home.md", "project", "# Home\n")

        listing = Browser(_snapshot(root)).groups()

        assert listing.group(BrowserSection.PROJECTS).notes[0].path == project

    def test_references_group_by_label(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "reference/people/Ada.md", "reference", "# Ada\n", category="person")
        _write_note(root, "reference/places/Paris.md", "reference", "# Paris\n", category="place")

        listing = Browser(_snapshot(root)).groups()
        groups = listing.groups_for(BrowserSection.REFERENCES)

        assert {group.label for group in groups} == {CategoryLabel("person"), CategoryLabel("place")}
        assert all(group.section is BrowserSection.REFERENCES for group in groups)

    def test_uncategorized_reference_uses_the_root_group(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "reference/Ada.md", "reference", "# Ada\n")

        groups = Browser(_snapshot(root)).groups().groups_for(BrowserSection.REFERENCES)

        assert len(groups) == 1
        assert groups[0].label is None
        assert groups[0].title == "References"

    def test_capture_appears_only_under_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        capture = _write_note(root, "inbox/Call.md", "note", "# Call\n")

        listing = Browser(_snapshot(root)).groups()

        locations = [group.section for group in listing.groups if any(note.path == capture for note in group.notes)]
        assert locations == [BrowserSection.INBOX]

    def test_misplaced_note_needs_attention(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        misplaced = _write_note(root, "notes/Later.md", "note", "# Later\n")

        listing = Browser(_snapshot(root)).groups()

        assert listing.group(BrowserSection.NEEDS_ATTENTION).notes[0].path == misplaced

    def test_trashed_note_is_absent(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "trash/Call.md", "note", "# Call\n")

        listing = Browser(_snapshot(root)).groups()

        assert all(not group.notes for group in listing.groups)

    def test_every_parsed_note_appears_once(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "inbox/Call.md", "note", "# Call\n")
        _write_note(root, "projects/Home.md", "project", "# Home\n")
        _write_note(root, "reference/Ada.md", "reference", "# Ada\n")
        _write_note(root, "notes/Misplaced.md", "note", "# Misplaced\n")

        snapshot = _snapshot(root)
        listing = Browser(snapshot).groups()
        paths = [note.path for group in listing.groups for note in group.notes]

        assert sorted(paths) == sorted(note.path for note in snapshot.notes)

    def test_inbox_capture_becomes_a_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        capture = _write_note(root, "inbox/Call.md", "note", "# Call\n")
        target = root / "projects/Call.md"
        target.parent.mkdir(parents=True)
        capture.replace(target)
        target.write_text("---\ntype: project\n---\n# Call\n", encoding="utf-8")

        listing = Browser(_snapshot(root)).groups()

        assert listing.group(BrowserSection.INBOX).notes == ()
        assert listing.group(BrowserSection.PROJECTS).notes[0].path == target


class TestBrowserFilter:
    def test_title_match_is_listed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home improvements\n")

        listing = Browser(_snapshot(root)).filter("improvements")

        assert len(listing.group(BrowserSection.PROJECTS).notes) == 1

    def test_identity_match_is_listed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home improvements\n")

        listing = Browser(_snapshot(root)).filter("home")

        assert len(listing.group(BrowserSection.PROJECTS).notes) == 1

    def test_body_match_is_listed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "reference/Ada.md", "reference", "# Ada\n\nCountess of Lovelace.\n")

        listing = Browser(_snapshot(root)).filter("countess")

        assert len(listing.group(BrowserSection.REFERENCES).notes) == 1

    def test_step_text_match_names_the_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n\n- [ ] Call the plumber\n")

        listing = Browser(_snapshot(root)).filter("plumber")

        assert len(listing.group(BrowserSection.PROJECTS).notes) == 1

    def test_metadata_is_not_searched(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Plumber], plan: 2026-11-20, tags: [plumbing]} -->\n",
        )

        listing = Browser(_snapshot(root)).filter("2026-11-20")

        assert listing.group(BrowserSection.PROJECTS).notes == ()

    def test_owner_match_names_the_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n", owner="Sam Rivera")

        listing = Browser(_snapshot(root)).filter("Sam Rivera")

        assert len(listing.group(BrowserSection.PROJECTS).notes) == 1

    def test_requester_match_names_the_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n", asked_by="Priya Nair")

        listing = Browser(_snapshot(root)).filter("Priya Nair")

        assert len(listing.group(BrowserSection.PROJECTS).notes) == 1

    def test_step_owner_match_names_the_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada Lovelace]} -->\n",
        )

        listing = Browser(_snapshot(root)).filter("Ada Lovelace")

        assert len(listing.group(BrowserSection.PROJECTS).notes) == 1

    def test_step_tags_are_not_searched(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {tags: [plumbing]} -->\n",
        )

        listing = Browser(_snapshot(root)).filter("plumbing")

        assert listing.group(BrowserSection.PROJECTS).notes == ()

    def test_matching_ignores_case_and_whitespace(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "reference/Ada.md", "reference", "# Ada,   Countess of Lovelace\n")

        listing = Browser(_snapshot(root)).filter("Ada,   Countess of Lovelace")

        assert len(listing.group(BrowserSection.REFERENCES).notes) == 1


class TestProjectBoard:
    def test_open_count_excludes_checked_steps(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] One\n- [x] Two\n- [ ] Three\n",
        )

        summary = ProjectBoard(_snapshot(root)).summaries()[0]

        assert summary.open_count == TWO_STEPS
        assert [step.text for step in summary.open_steps] == ["One", "Three"]

    def test_next_step_is_the_first_unchecked_step(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n\n- [x] One\n- [ ] Two\n- [ ] Three\n")

        summary = ProjectBoard(_snapshot(root)).summaries()[0]

        assert summary.next_step is not None
        assert summary.next_step.text == "Two"

    def test_dates_do_not_reorder_steps(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] One <!-- {plan: 2026-12-01} -->\n- [ ] Two <!-- {plan: 2026-11-01} -->\n",
        )

        summary = ProjectBoard(_snapshot(root)).summaries()[0]

        assert summary.next_step is not None
        assert summary.next_step.text == "One"

    def test_owned_next_step_is_marked_waiting(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada]} -->\n",
        )

        step = ProjectBoard(_snapshot(root)).summaries()[0].next_step

        assert step is not None
        assert step.is_waiting is True

    def test_zero_step_project_is_reported(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n")

        summary = ProjectBoard(_snapshot(root)).summaries()[0]

        assert summary.open_count == 0
        assert summary.next_step is None

    def test_closed_projects_are_grouped_separately(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n", status="done")
        _write_note(root, "projects/Work.md", "project", "# Work\n", status="active")

        groups = {group.stage: group for group in ProjectBoard(_snapshot(root)).groups()}

        assert [summary.note.name for summary in groups[ProjectStage.CLOSED].projects] == ["Home"]
        assert [summary.note.name for summary in groups[ProjectStage.ACTIVE].projects] == ["Work"]


class TestReviewQueue:
    def test_inbox_items_come_first(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "inbox/Capture.md", "note", "# Capture\n")
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {plan: 2026-11-01} -->\n",
        )

        queue = ReviewPlanner(_snapshot(root), today=TODAY).queue()

        assert queue[0].kind is ReviewItemKind.INBOX
        assert queue[-1].kind is ReviewItemKind.PROJECT

    def test_due_steps_precede_waiting_steps(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Due <!-- {plan: 2026-11-01} -->\n- [ ] Waiting <!-- {owners: [Ada]} -->\n",
        )

        queue = ReviewPlanner(_snapshot(root), today=TODAY).queue()

        assert [item.kind for item in queue] == [
            ReviewItemKind.DUE_STEP,
            ReviewItemKind.WAITING_STEP,
            ReviewItemKind.PROJECT,
        ]

    def test_waiting_steps_precede_stalled_projects(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Waiting.md",
            "project",
            "# Waiting\n\n- [ ] Call <!-- {owners: [Ada]} -->\n",
        )
        _write_note(root, "projects/Stalled.md", "project", "# Stalled\n")

        queue = ReviewPlanner(_snapshot(root), today=TODAY).queue()

        assert [item.kind for item in queue] == [
            ReviewItemKind.WAITING_STEP,
            ReviewItemKind.PROJECT,
            ReviewItemKind.PROJECT,
        ]

    def test_stalled_projects_precede_healthy_projects(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Healthy.md", "project", "# Healthy\n\n- [ ] One\n")
        _write_note(root, "projects/Stalled.md", "project", "# Stalled\n")

        queue = ReviewPlanner(_snapshot(root), today=TODAY).queue()

        assert [item.path.name for item in queue] == ["Stalled.md", "Healthy.md"]

    def test_checked_steps_are_not_reviewed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [x] Due <!-- {plan: 2026-11-01} -->\n- [x] Waiting <!-- {owners: [Ada]} -->\n",
        )

        queue = ReviewPlanner(_snapshot(root), today=TODAY).queue()

        assert [item.kind for item in queue] == [ReviewItemKind.PROJECT]

    def test_owned_due_step_is_waiting_not_due(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] Call <!-- {owners: [Ada], plan: 2026-11-01} -->\n",
        )

        queue = ReviewPlanner(_snapshot(root), today=TODAY).queue()

        assert [item.kind for item in queue] == [ReviewItemKind.WAITING_STEP, ReviewItemKind.PROJECT]

    def test_closed_projects_are_excluded(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n", status="done")

        queue = ReviewPlanner(_snapshot(root), today=TODAY).queue()

        assert queue == ()

    def test_queue_is_a_snapshot(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n")
        snapshot = _snapshot(root)
        queue = ReviewPlanner(snapshot, today=TODAY).queue()

        _write_note(root, "projects/Other.md", "project", "# Other\n")

        assert queue == ReviewPlanner(snapshot, today=TODAY).queue()


class TestPendingCount:
    def test_count_combines_every_source(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "inbox/Capture.md", "note", "# Capture\n")
        _write_note(
            root,
            "projects/Due.md",
            "project",
            "# Due\n\n- [ ] One <!-- {plan: 2026-11-01} -->\n",
        )
        _write_note(
            root,
            "projects/Waiting.md",
            "project",
            "# Waiting\n\n- [ ] One <!-- {owners: [Ada]} -->\n",
        )
        _write_note(root, "projects/Stalled.md", "project", "# Stalled\n")

        assert ReviewPlanner(_snapshot(root), today=TODAY).pending_count() == FOUR_PENDING

    def test_healthy_project_is_not_counted(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root, "projects/Home.md", "project", "# Home\n\n- [ ] One\n")

        assert ReviewPlanner(_snapshot(root), today=TODAY).pending_count() == 0

    def test_zero_state(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        assert ReviewPlanner(_snapshot(root), today=TODAY).pending_count() == 0

    def test_tomorrow_plan_is_not_due(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(
            root,
            "projects/Home.md",
            "project",
            "# Home\n\n- [ ] One <!-- {plan: 2026-11-15} -->\n",
        )

        assert ReviewPlanner(_snapshot(root), today=TODAY).pending_count() == 0
        assert ReviewPlanner(_snapshot(root), today=TOMORROW).pending_count() == 1
