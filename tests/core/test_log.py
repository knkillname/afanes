"""Tests for the read-only Log timeline."""

from pathlib import Path

import afanes.core.log
import afanes.core.vault.service
from afanes.models.note import NoteDate

YEAR = 2025
MONTH = 10
DAY = 12
OCTOBER_DAYS = 31
TWO_ENTRIES = 2


def _write_note(
    path: Path,
    note_type: str = "log",
    body: str = "",
    *,
    date: str | None = None,
    category: str | None = None,
    owner: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"type: {note_type}"]
    if date is not None:
        lines.append(f"date: {date}")
    if category is not None:
        lines.append(f"category: {category}")
    if owner is not None:
        lines.append(f"owner: {owner}")
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _timeline(
    root: Path, mode: afanes.core.log.LogMode = afanes.core.log.LogMode.ENTRIES
) -> afanes.core.log.LogTimeline:
    return afanes.core.log.LogTimeline(afanes.core.vault.service.Vault(root).scan(), mode)


class TestLogTitle:
    def test_day_precision_uses_a_long_date(self) -> None:
        title = afanes.core.log.LogTitle.for_date(NoteDate.from_text("2026-11-13"))

        assert title.text == "November 13, 2026"

    def test_month_precision_names_the_month_and_year(self) -> None:
        title = afanes.core.log.LogTitle.for_date(NoteDate.from_text("2026-11"))

        assert title.text == "November 2026"

    def test_year_precision_is_the_year(self) -> None:
        title = afanes.core.log.LogTitle.for_date(NoteDate.from_text("2026"))

        assert title.text == "2026"

    def test_single_digit_day_has_no_leading_zero(self) -> None:
        title = afanes.core.log.LogTitle.for_date(NoteDate.from_text("2026-11-03"))

        assert title.text == "November 3, 2026"


class TestLogBuckets:
    def test_entries_mode_lists_only_log_notes(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12", body="# Tuesday\n")
        _write_note(root / "projects/Launch.md", "project", body="# Launch\n")

        timeline = _timeline(root)

        assert [note.name for note in timeline.entries()] == ["2025-10-12"]

    def test_everything_mode_lists_every_note(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12")
        _write_note(root / "projects/Launch.md", "project", date="2025-10-13")

        timeline = _timeline(root, afanes.core.log.LogMode.EVERYTHING)

        assert {note.name for note in timeline.entries()} == {"2025-10-12", "Launch"}

    def test_years_and_months_and_days(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/2025.md", date="2025", body="# Year\n")
        _write_note(root / "log/2025/10/2025-10.md", date="2025-10", body="# Month\n")
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12", body="# Day\n")

        timeline = _timeline(root)
        year = timeline.years()[0]

        assert year.year == YEAR
        assert [note.title for note in year.entries] == ["Year"]
        assert year.months[0].month == MONTH
        assert [note.title for note in year.months[0].entries] == ["Month"]
        assert year.months[0].days[0].day == DAY
        assert [note.title for note in year.months[0].days[0].entries] == ["Day"]

    def test_undated_notes_are_separate(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12")
        _write_note(root / "log/Undated.md", body="# No date\n")

        timeline = _timeline(root)

        assert [note.name for note in timeline.undated()] == ["Undated"]

    def test_empty_snapshot(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        timeline = _timeline(root)

        assert timeline.entries() == ()
        assert timeline.years() == ()
        assert timeline.undated() == ()


class TestCalendar:
    def test_day_cells_and_month_and_year_marks(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/2025.md", date="2025")
        _write_note(root / "log/2025/10/2025-10.md", date="2025-10")
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12")
        _write_note(root / "log/2025/10/2025-10-12 second.md", date="2025-10-12")
        _write_note(root / "log/2025/11/2025-11-01.md", date="2025-11-01")

        calendar = _timeline(root).calendar(YEAR, MONTH)

        assert calendar.days_in_month == OCTOBER_DAYS
        assert calendar.days[DAY - 1].count == TWO_ENTRIES
        assert calendar.days[0].count == 0
        assert calendar.month_count == 1
        assert calendar.year_count == 1
        assert calendar.has_month_entry is True
        assert calendar.has_year_entry is True

    def test_a_month_without_entries_is_empty(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()

        calendar = _timeline(root).calendar(YEAR, MONTH)

        assert all(day.count == 0 for day in calendar.days)
        assert calendar.has_month_entry is False
        assert calendar.has_year_entry is False


class TestSearch:
    def test_search_filters_the_tree(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12", body="# Dentist\n")
        _write_note(root / "log/2025/10/2025-10-13.md", date="2025-10-13", body="# Groceries\n")

        timeline = _timeline(root).with_query("dentist")

        assert [note.title for note in timeline.entries()] == ["Dentist"]
        calendar = timeline.calendar(YEAR, MONTH)
        assert calendar.days[11].count == 1
        assert calendar.days[DAY].count == 0

    def test_search_matches_a_log_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12", body="# Tuesday\n")

        timeline = _timeline(root).with_query("2025-10-12")

        assert [note.title for note in timeline.entries()] == ["Tuesday"]

    def test_search_matches_a_project_role_name_in_everything_mode(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12", body="# Tuesday\n")
        _write_note(
            root / "projects/Launch.md",
            "project",
            body="# Launch\n",
            date="2025-10-13",
            owner="Ada Lovelace",
        )

        timeline = _timeline(root, afanes.core.log.LogMode.EVERYTHING).with_query("Ada Lovelace")

        assert [note.name for note in timeline.entries()] == ["Launch"]
