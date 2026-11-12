"""Tests for vault snapshot value types and read-only queries."""

import datetime
import os
from pathlib import Path

import afanes.core.vault.service
from afanes.core.vault.snapshot import LinkOutcome, NoteOrder, VaultNote
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteDate, NoteType, Status


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


def _set_modified_ns(path: Path, modified_ns: int) -> None:
    os.utime(path, ns=(modified_ns, modified_ns))


class TestNoteOrder:
    def _note(
        self,
        *,
        name: str = "Note",
        title: str = "Note",
        due_date: datetime.date | None = None,
        date: NoteDate | None = None,
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
            date=date,
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


class TestLinkTarget:
    def test_resolves_a_unique_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        path = _write_note(root / "reference" / "person" / "Ada.md", note_type="person")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Ada"))

        assert target.outcome is LinkOutcome.RESOLVED
        assert target.paths == (path.resolve(),)

    def test_reports_every_ambiguous_candidate(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        first = _write_note(root / "reference" / "person" / "Ada.md", note_type="person")
        second = _write_note(root / "notes" / "Ada.md", note_type="person")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Ada"))

        assert target.outcome is LinkOutcome.AMBIGUOUS
        assert set(target.paths) == {first.resolve(), second.resolve()}

    def test_reports_a_missing_reference(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        snapshot = afanes.core.vault.service.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Nobody"))

        assert target.outcome is LinkOutcome.MISSING
        assert target.paths == ()

    def test_routes_to_an_unparseable_file(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        broken = root / "reference" / "Broken.md"
        broken.parent.mkdir()
        broken.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        snapshot = afanes.core.vault.service.Vault(root).scan()

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
        snapshot = afanes.core.vault.service.Vault(root).scan()

        target = snapshot.link_target(NoteReference(ReferenceScheme.NOTE, "Broken"))

        assert target.outcome is LinkOutcome.BROKEN
        assert set(target.paths) == {first.resolve(), second.resolve()}

    def test_failure_matching_ignores_case(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        broken = root / "reference" / "ADA.md"
        broken.parent.mkdir()
        broken.write_text("---\ntype: refrence\n---\nBody\n", encoding="utf-8")
        snapshot = afanes.core.vault.service.Vault(root).scan()

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
        snapshot = afanes.core.vault.service.Vault(root).scan()

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
        snapshot = afanes.core.vault.service.Vault(root).scan()

        sites = snapshot.referrers(target)

        assert [(site.path, site.reference_count) for site in sites] == [(one.resolve(), 2), (two.resolve(), 1)]

    def test_ambiguous_references_are_not_attributed(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        first = _write_note(root / "reference" / "person" / "Ada.md", note_type="person")
        _write_note(root / "notes" / "Ada.md", note_type="person")
        _write_note(root / "notes" / "One.md", body="[Ada](<note:Ada>)\n")
        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.referrers(first) == ()


class TestInboxNotes:
    def test_lists_direct_inbox_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        first = _write_note(root / "inbox/A.md")
        second = _write_note(root / "inbox/B.md")
        _write_note(root / "work/C.md")
        _set_modified_ns(first, 1_700_000_000_000_000_000)
        _set_modified_ns(second, 1_700_000_001_000_000_000)

        snapshot = afanes.core.vault.service.Vault(root).scan()
        names = [note.name for note in snapshot.inbox_notes()]

        assert names == ["B", "A"]

    def test_lists_nested_inbox_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/2026/C.md")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert [note.name for note in snapshot.inbox_notes()] == ["C"]

    def test_excludes_notes_outside_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "D.md")
        _write_note(root / "inbox.md")
        _write_note(root / "work/E.md")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.inbox_notes() == ()

    def test_matches_the_inbox_directory_case_insensitively(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "Inbox/E.md")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert [note.name for note in snapshot.inbox_notes()] == ["E"]

    def test_orders_newest_first(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        old = _write_note(root / "inbox/Old.md")
        middle = _write_note(root / "inbox/Middle.md")
        new = _write_note(root / "inbox/New.md")
        _set_modified_ns(old, 1_700_000_000_000_000_000)
        _set_modified_ns(middle, 1_700_000_001_000_000_000)
        _set_modified_ns(new, 1_700_000_002_000_000_000)

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert [note.name for note in snapshot.inbox_notes()] == ["New", "Middle", "Old"]

    def test_equal_timestamps_use_a_case_folded_name_tie_breaker(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        upper = _write_note(root / "inbox/Beta.md")
        lower = _write_note(root / "inbox/alpha.md")
        _set_modified_ns(upper, 1_700_000_000_000_000_000)
        _set_modified_ns(lower, 1_700_000_000_000_000_000)

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert [note.name for note in snapshot.inbox_notes()] == ["alpha", "Beta"]

    def test_equal_names_use_a_path_tie_breaker(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        second = _write_note(root / "inbox/b/Same.md")
        first = _write_note(root / "inbox/a/Same.md")
        _set_modified_ns(first, 1_700_000_000_000_000_000)
        _set_modified_ns(second, 1_700_000_000_000_000_000)

        snapshot = afanes.core.vault.service.Vault(root).scan()

        paths = [note.relative_path.as_posix() for note in snapshot.inbox_notes()]
        assert paths == ["inbox/a/Same.md", "inbox/b/Same.md"]

    def test_empty_vault_returns_no_inbox_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.inbox_notes() == ()


class TestAssignmentCandidates:
    def test_matches_an_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project", body="# Home improvements\n")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "home")
        assert [note.name for note in candidates] == ["Home"]

    def test_matches_a_title(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project", body="# Home improvements\n")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "improvements")
        assert [note.name for note in candidates] == ["Home"]

    def test_matching_ignores_case_and_repeated_whitespace(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project", body="# Home,   improvements\n")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "home,   improvements")
        assert [note.name for note in candidates] == ["Home"]

    def test_duplicate_titles_are_distinguished_by_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project", body="# Home improvements\n")
        _write_note(root / "projects/Cabin.md", "project", body="# Home improvements\n")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "improvements")
        assert [note.name for note in candidates] == ["Cabin", "Home"]

    def test_filters_by_scheme(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "reference/Ada.md", "reference", body="# Ada\n")
        _write_note(root / "projects/Ada.md", "project", body="# Ada\n")

        snapshot = afanes.core.vault.service.Vault(root).scan()

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

        snapshot = afanes.core.vault.service.Vault(root).scan()

        candidates = snapshot.assignment_candidates(ReferenceScheme.PROJECT, "")
        assert [note.name for note in candidates] == ["Cabin", "Home"]

    def test_no_match_returns_nothing(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "projects/Home.md", "project")

        snapshot = afanes.core.vault.service.Vault(root).scan()

        assert snapshot.assignment_candidates(ReferenceScheme.PROJECT, "missing") == ()


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
        snapshot = afanes.core.vault.service.Vault(root).scan()
        by_name = {note.name: note for note in snapshot.notes}

        assert by_name["Open"].is_open_project is True
        assert by_name["Done"].is_open_project is False
        assert by_name["Ref"].is_open_project is False

    def test_is_misplaced_is_false_inside_the_inbox(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "inbox/Capture.md", "note")

        note = afanes.core.vault.service.Vault(root).scan().notes[0]

        assert note.is_misplaced is False
