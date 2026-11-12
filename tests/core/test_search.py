"""Tests for read-only browser, project, and review queries."""

from pathlib import Path

import afanes.core.search
import afanes.core.vault
from afanes.core.search import (
    BrowserSection,
    ProjectStage,
    ReviewItemKind,
)
from afanes.models.note import Status

THREE = 3
FIVE = 5


def _write(
    root: Path,
    relative: str,
    *,
    note_type: str = "note",
    status: str | None = None,
    due_date: str | None = None,
    project: str | None = None,
    category: str | None = None,
    body: str = "",
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
    if project is not None:
        lines.append(f'project: "{project}"')
    lines.extend(["---", body])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _scan(root: Path) -> afanes.core.vault.VaultSnapshot:
    return afanes.core.vault.Vault(root).scan()


def _names(notes: tuple[afanes.core.vault.VaultNote, ...]) -> list[str]:
    return [note.name for note in notes]


def _summary(snapshot: afanes.core.vault.VaultSnapshot, name: str) -> afanes.core.search.ProjectSummary:
    return next(
        summary for summary in afanes.core.search.ProjectBoard(snapshot).summaries() if summary.note.name == name
    )


class TestBrowseGroups:
    def test_groups_every_note_by_type(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "inbox/Capture.md")
        _write(root, "projects/Launch.md", note_type="project", status="active")
        _write(root, "actions/Call.md", note_type="action", status="active")
        _write(root, "reference/people/Ada.md", note_type="reference", category="person")
        _write(root, "reference/Reading list.md", note_type="reference")
        _write(root, "notes/Idea.md")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert _names(listing.group(BrowserSection.INBOX).notes) == ["Capture"]
        assert _names(listing.group(BrowserSection.PROJECTS).notes) == ["Launch"]
        assert _names(listing.group(BrowserSection.ACTIONS).notes) == ["Call"]
        assert _names(listing.group(BrowserSection.PEOPLE).notes) == ["Ada"]
        assert _names(listing.group(BrowserSection.REFERENCES).notes) == ["Reading list"]
        assert _names(listing.group(BrowserSection.NOTES).notes) == ["Idea"]

    def test_capture_appears_only_under_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "inbox/Capture.md")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert _names(listing.group(BrowserSection.INBOX).notes) == ["Capture"]
        assert listing.group(BrowserSection.NOTES).notes == ()

    def test_nested_inbox_folder_still_counts_as_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "inbox/day/Capture.md")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert _names(listing.group(BrowserSection.INBOX).notes) == ["Capture"]
        assert listing.group(BrowserSection.NOTES).notes == ()

    def test_trashed_notes_are_absent(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "trash/Old.md")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert all(group.notes == () for group in listing.groups)

    def test_unparseable_notes_are_reported_separately(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        broken = root / "reference" / "Broken.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert all(group.notes == () for group in listing.groups)
        assert [failure.path.as_posix() for failure in listing.failures] == ["reference/Broken.md"]

    def test_inbox_is_newest_first(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        older = _write(root, "inbox/Older.md")
        newer = _write(root, "inbox/Newer.md")
        older.touch()
        newer.touch()
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert _names(listing.group(BrowserSection.INBOX).notes) == ["Newer", "Older"]

    def test_other_sections_are_ordered_by_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "reference/Zulu.md", note_type="reference", body="# Alpha")
        _write(root, "reference/Alpha.md", note_type="reference", body="# Zulu")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert _names(listing.group(BrowserSection.REFERENCES).notes) == ["Zulu", "Alpha"]

    def test_browsing_performs_no_writes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "inbox/Capture.md")
        before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}

        listing = afanes.core.search.Browser(_scan(root)).groups()
        listing.filtered("capture")

        after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        assert after == before


class TestSearchFiltering:
    def test_title_match_is_listed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "reference/Ada.md", note_type="reference", body="# Ada, Countess of Lovelace")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        filtered = listing.filtered("Countess")

        assert _names(filtered.group(BrowserSection.REFERENCES).notes) == ["Ada"]

    def test_identity_match_is_listed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "reference/Ada Lovelace.md", note_type="reference", body="# A person")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        filtered = listing.filtered("lovelace")

        assert _names(filtered.group(BrowserSection.REFERENCES).notes) == ["Ada Lovelace"]

    def test_matching_ignores_case_and_repeated_whitespace(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "reference/Ada.md", note_type="reference", body="# Ada, Countess of Lovelace")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert _names(listing.filtered("ada").group(BrowserSection.REFERENCES).notes) == ["Ada"]
        assert _names(listing.filtered("Ada,   Countess of Lovelace").group(BrowserSection.REFERENCES).notes) == ["Ada"]

    def test_matching_ignores_unicode_form(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "reference/Emile.md", note_type="reference", body="# E\u0301mile")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        filtered = listing.filtered("\u00c9mile")

        assert _names(filtered.group(BrowserSection.REFERENCES).notes) == ["Emile"]

    def test_body_only_term_is_not_matched(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "reference/Ada.md", note_type="reference", body="# Ada\n\nAnalytical engine")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        filtered = listing.filtered("Analytical")

        assert all(group.notes == () for group in filtered.groups)

    def test_empty_query_keeps_every_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "reference/Ada.md", note_type="reference")
        _write(root, "reference/Grace.md", note_type="reference")
        listing = afanes.core.search.Browser(_scan(root)).groups()

        assert _names(listing.filtered("  ").group(BrowserSection.REFERENCES).notes) == ["Ada", "Grace"]

    def test_filter_preserves_input_order(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "reference/Zulu.md", note_type="reference", body="# Common")
        _write(root, "reference/Alpha.md", note_type="reference", body="# Common")
        snapshot = _scan(root)
        notes = tuple(reversed(snapshot.notes))

        assert _names(afanes.core.search.Browser.filter_notes(notes, "common")) == ["Zulu", "Alpha"]


class TestProjectGroups:
    def test_project_statuses_are_grouped(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Plain.md", note_type="project")
        _write(root, "projects/Now.md", note_type="project", status="active")
        _write(root, "projects/Blocked.md", note_type="project", status="waiting")
        _write(root, "projects/Someday.md", note_type="project", status="later")
        _write(root, "projects/Finished.md", note_type="project", status="done")
        _write(root, "projects/Dropped.md", note_type="project", status="cancelled")
        _write(root, "projects/Stored.md", note_type="project", status="archived")
        groups = {group.stage: group for group in afanes.core.search.ProjectBoard(_scan(root)).groups()}

        assert _names(tuple(summary.note for summary in groups[ProjectStage.ACTIVE].projects)) == ["Now", "Plain"]
        assert _names(tuple(summary.note for summary in groups[ProjectStage.WAITING].projects)) == ["Blocked"]
        assert _names(tuple(summary.note for summary in groups[ProjectStage.LATER].projects)) == ["Someday"]
        assert _names(tuple(summary.note for summary in groups[ProjectStage.CLOSED].projects)) == [
            "Dropped",
            "Finished",
            "Stored",
        ]

    def test_every_stage_is_present_even_when_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        groups = afanes.core.search.ProjectBoard(_scan(root)).groups()

        assert [group.stage for group in groups] == list(ProjectStage)
        assert all(group.projects == () for group in groups)

    def test_projects_are_ordered_by_due_date_then_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Zulu.md", note_type="project", status="active", due_date="2026-12-01")
        _write(root, "projects/Alpha.md", note_type="project", status="active")
        _write(root, "projects/Beta.md", note_type="project", status="active", due_date="2026-11-01")
        groups = {group.stage: group for group in afanes.core.search.ProjectBoard(_scan(root)).groups()}

        assert _names(tuple(summary.note for summary in groups[ProjectStage.ACTIVE].projects)) == [
            "Beta",
            "Zulu",
            "Alpha",
        ]


class TestProjectMembership:
    def test_project_reference_attributes_an_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "actions/Build.md", note_type="action", status="active", project="project:Machine")
        snapshot = _scan(root)

        summary = _summary(snapshot, "Machine")

        assert _names(summary.open_actions) == ["Build"]

    def test_body_link_does_not_attribute_an_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(
            root,
            "actions/Build.md",
            note_type="action",
            status="active",
            body="[Machine](<project:Machine>)",
        )
        snapshot = _scan(root)

        assert _summary(snapshot, "Machine").open_actions == ()

    def test_ambiguous_project_reference_attributes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "projects/archive/Machine.md", note_type="project", status="active")
        _write(root, "actions/Build.md", note_type="action", status="active", project="project:Machine")
        snapshot = _scan(root)

        summaries = [
            summary
            for summary in afanes.core.search.ProjectBoard(snapshot).summaries()
            if summary.note.name == "Machine"
        ]

        assert all(summary.open_actions == () for summary in summaries)

    def test_unresolved_project_reference_attributes_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "actions/Build.md", note_type="action", status="active", project="project:Missing")
        snapshot = _scan(root)

        assert afanes.core.search.ProjectBoard(snapshot).summaries() == ()

    def test_action_without_a_project_is_unassigned(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "actions/Build.md", note_type="action", status="active")
        snapshot = _scan(root)

        assert _summary(snapshot, "Machine").open_actions == ()

    def test_people_reference_does_not_attribute_an_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "reference/people/Ada.md", note_type="reference", category="person")
        _write(
            root,
            "actions/Build.md",
            note_type="action",
            status="active",
            body="[Ada](<person:Ada>)",
        )
        snapshot = _scan(root)

        assert _summary(snapshot, "Machine").open_actions == ()


class TestProjectCountsAndNextAction:
    def test_open_count_excludes_completed_and_deferred_actions(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "actions/One.md", note_type="action", status="active", project="project:Machine")
        _write(root, "actions/Two.md", note_type="action", status="waiting", project="project:Machine")
        _write(root, "actions/Three.md", note_type="action", project="project:Machine")
        _write(root, "actions/Done.md", note_type="action", status="done", project="project:Machine")
        _write(root, "actions/Later.md", note_type="action", status="later", project="project:Machine")
        snapshot = _scan(root)

        summary = _summary(snapshot, "Machine")

        assert summary.open_count == THREE
        assert summary.next_action is not None

    def test_project_with_only_later_actions_has_no_next_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "actions/Later.md", note_type="action", status="later", project="project:Machine")
        snapshot = _scan(root)

        summary = _summary(snapshot, "Machine")

        assert summary.open_count == 0
        assert summary.next_action is None

    def test_earliest_due_date_is_the_next_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(
            root,
            "actions/Later date.md",
            note_type="action",
            status="active",
            due_date="2026-12-01",
            project="project:Machine",
        )
        _write(
            root,
            "actions/Soon.md",
            note_type="action",
            status="waiting",
            due_date="2026-11-01",
            project="project:Machine",
        )
        snapshot = _scan(root)

        summary = _summary(snapshot, "Machine")
        assert summary.next_action is not None
        assert summary.next_action.name == "Soon"

    def test_active_ranks_before_waiting_without_due_dates(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "actions/Alpha waiting.md", note_type="action", status="waiting", project="project:Machine")
        _write(root, "actions/Zulu active.md", note_type="action", status="active", project="project:Machine")
        snapshot = _scan(root)

        summary = _summary(snapshot, "Machine")
        assert summary.next_action is not None
        assert summary.next_action.name == "Zulu active"

    def test_display_title_breaks_a_tie(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "actions/Zulu.md", note_type="action", status="active", body="# Build", project="project:Machine")
        _write(
            root, "actions/Alpha.md", note_type="action", status="active", body="# Assemble", project="project:Machine"
        )
        snapshot = _scan(root)

        summary = _summary(snapshot, "Machine")
        assert summary.next_action is not None
        assert summary.next_action.name == "Alpha"

    def test_no_open_action_means_no_next_action(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="active")
        snapshot = _scan(root)

        summary = _summary(snapshot, "Machine")

        assert summary.open_actions == ()
        assert summary.next_action is None


class TestProjectStatusStability:
    def test_completing_all_actions_does_not_close_the_project(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        project = _write(root, "projects/Machine.md", note_type="project", status="active")
        _write(root, "actions/Done.md", note_type="action", status="done", project="project:Machine")
        before = project.read_bytes()
        snapshot = _scan(root)

        afanes.core.search.ProjectBoard(snapshot).groups()

        assert next(note for note in snapshot.notes if note.name == "Machine").status is Status.ACTIVE
        assert project.read_bytes() == before

    def test_closing_a_project_leaves_its_actions_unchanged(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Machine.md", note_type="project", status="done")
        action = _write(root, "actions/Build.md", note_type="action", status="active", project="project:Machine")
        before = action.read_bytes()
        snapshot = _scan(root)

        afanes.core.search.ProjectBoard(snapshot).groups()

        assert next(note for note in snapshot.notes if note.name == "Build").status is Status.ACTIVE
        assert action.read_bytes() == before


class TestReviewQueue:
    def test_pending_count_combines_inbox_and_stalled_projects(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        for index in range(3):
            _write(root, f"inbox/Capture {index}.md")
        _write(root, "projects/Stalled one.md", note_type="project", status="active")
        _write(root, "projects/Stalled two.md", note_type="project", status="waiting")
        _write(root, "projects/Healthy.md", note_type="project", status="active")
        _write(root, "actions/Build.md", note_type="action", status="active", project="project:Healthy")
        snapshot = _scan(root)

        assert afanes.core.search.ReviewPlanner(snapshot).pending_count() == FIVE

    def test_closed_projects_are_not_pending(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Finished.md", note_type="project", status="done")
        snapshot = _scan(root)

        assert afanes.core.search.ReviewPlanner(snapshot).pending_count() == 0

    def test_zero_pending_state_has_an_empty_queue(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        snapshot = _scan(root)

        assert afanes.core.search.ReviewPlanner(snapshot).pending_count() == 0
        assert afanes.core.search.ReviewPlanner(snapshot).queue() == ()

    def test_queue_orders_inbox_then_stalled_then_healthy(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "inbox/Capture.md")
        _write(root, "projects/Healthy.md", note_type="project", status="active")
        _write(root, "actions/Build.md", note_type="action", status="active", project="project:Healthy")
        _write(root, "projects/Stalled.md", note_type="project", status="waiting")
        _write(root, "projects/Finished.md", note_type="project", status="done")
        snapshot = _scan(root)

        queue = afanes.core.search.ReviewPlanner(snapshot).queue()

        assert [item.kind for item in queue] == [
            ReviewItemKind.INBOX,
            ReviewItemKind.PROJECT,
            ReviewItemKind.PROJECT,
        ]
        assert [item.path.stem for item in queue] == ["Capture", "Stalled", "Healthy"]

    def test_queue_excludes_closed_projects(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Finished.md", note_type="project", status="done")
        _write(root, "projects/Dropped.md", note_type="project", status="cancelled")
        _write(root, "projects/Stored.md", note_type="project", status="archived")
        snapshot = _scan(root)

        assert afanes.core.search.ReviewPlanner(snapshot).queue() == ()

    def test_queue_is_a_snapshot_of_the_scan(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "inbox/Capture.md")
        snapshot = _scan(root)
        queue = afanes.core.search.ReviewPlanner(snapshot).queue()

        _write(root, "inbox/Later.md")
        _write(root, "projects/New.md", note_type="project", status="active")

        assert queue == afanes.core.search.ReviewPlanner(snapshot).queue()
        assert len(queue) == 1
        assert len(afanes.core.search.ReviewPlanner(_scan(root)).queue()) == THREE

    def test_new_work_is_not_appended_to_an_existing_queue(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write(root, "projects/Stalled.md", note_type="project", status="active")
        snapshot = _scan(root)
        queue = afanes.core.search.ReviewPlanner(snapshot).queue()

        _write(root, "projects/Created during review.md", note_type="project", status="active")

        assert all(item.path.stem != "Created during review" for item in queue)
