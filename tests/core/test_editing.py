"""Tests for the pure page draft, label rules, and serialization."""

import datetime
import hashlib
from pathlib import Path

import pytest

from afanes.core.editing import DraftMode, PageDraft, PageLabels, due_date_text_from_raw, parse_due_date
from afanes.core.errors import InvalidReferenceError, NoteParseError
from afanes.core.frontmatter import NoteDocument
from afanes.core.vault import PageContent
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

ACTION_NOTE = """---
type: action
status: waiting
due_date: 2026-01-02
people:
  - "person:Ada"
project: "project:Release 1.0"
custom: keep
---

# Call Ada
Body.
"""

PERSON_NOTE = """---
type: reference
category: person
status: archived
due_date: 2026-05-06
people:
  - "person:Grace"
project: "project:Release 1.0"
---

# Ada, Countess of Lovelace
Mathematician.
"""


def _page(text: str, *, path: Path = Path("/vault/reference/Ada.md")) -> PageContent:
    document: NoteDocument | None = None
    failure: str | None = None
    try:
        parsed = NoteDocument.from_text(text)
        if parsed.note_type is None:
            failure = "Note has no type"
        else:
            document = parsed
    except (NoteParseError, InvalidReferenceError) as exc:
        failure = str(exc)
    return PageContent(
        path=path,
        relative_path=Path(path.name),
        text=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        document=document,
        failure=failure,
    )


class TestDueDate:
    def test_parses_an_iso_date(self) -> None:
        assert parse_due_date("2026-01-02") == datetime.date(2026, 1, 2)

    def test_blank_is_absent(self) -> None:
        assert parse_due_date("   ") is None

    def test_invalid_text_raises(self) -> None:
        with pytest.raises(NoteParseError):
            parse_due_date("January 2")

    def test_raw_date_becomes_iso_text(self) -> None:
        assert due_date_text_from_raw(datetime.date(2026, 1, 2)) == "2026-01-02"

    def test_raw_datetime_keeps_its_text(self) -> None:
        value = datetime.datetime(2026, 1, 2, 3, 4, tzinfo=datetime.UTC)

        assert due_date_text_from_raw(value) == value.isoformat()

    def test_raw_string_is_preserved(self) -> None:
        assert due_date_text_from_raw("next week") == "next week"

    def test_absent_value_is_blank(self) -> None:
        assert due_date_text_from_raw(None) == ""


class TestNewDraft:
    def test_note_reference_creates_a_reference_page(self) -> None:
        draft = PageDraft.new(NoteReference(ReferenceScheme.NOTE, "Quarterly budget"))

        assert draft.mode is DraftMode.NORMAL
        assert draft.is_new
        assert draft.identity == "Quarterly budget"
        assert draft.body == "# Quarterly budget\n\n"
        assert draft.labels is not None
        assert draft.labels.note_type is NoteType.REFERENCE
        assert draft.labels.category is None
        assert not draft.is_dirty

    def test_person_reference_sets_the_category(self) -> None:
        draft = PageDraft.new(NoteReference(ReferenceScheme.PERSON, "Ada"))

        assert draft.labels is not None
        assert draft.labels.note_type is NoteType.REFERENCE
        assert draft.labels.category is ReferenceCategory.PERSON
        assert draft.labels.scheme is ReferenceScheme.PERSON

    def test_project_reference_creates_a_project(self) -> None:
        draft = PageDraft.new(NoteReference(ReferenceScheme.PROJECT, "Release 1.0"))

        assert draft.labels is not None
        assert draft.labels.note_type is NoteType.PROJECT
        assert draft.labels.scheme is ReferenceScheme.PROJECT

    def test_heading_preserves_the_reference_wording(self) -> None:
        draft = PageDraft.new(NoteReference(ReferenceScheme.NOTE, "Q1: Planning?"))

        assert draft.identity == "Q1 Planning"
        assert draft.body == "# Q1: Planning?\n\n"

    def test_body_change_marks_the_draft_dirty(self) -> None:
        draft = PageDraft.new(NoteReference(ReferenceScheme.NOTE, "Quarterly budget"))

        changed = draft.with_body("# Quarterly budget\n\nNew text.\n")

        assert changed.is_dirty
        assert not changed.with_body("# Quarterly budget\n\n").is_dirty

    def test_label_change_marks_the_draft_dirty(self) -> None:
        draft = PageDraft.new(NoteReference(ReferenceScheme.NOTE, "Quarterly budget"))
        labels = draft.labels
        assert labels is not None

        changed = draft.with_labels(labels.with_type(NoteType.ACTION))

        assert changed.is_dirty
        assert not changed.with_labels(labels).is_dirty


class TestLoadDraft:
    def test_loads_body_and_labels(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))

        assert draft.mode is DraftMode.NORMAL
        assert not draft.is_new
        assert draft.path == Path("/vault/reference/Ada.md")
        assert draft.identity == "Ada"
        assert draft.body == "\n# Call Ada\nBody.\n"
        assert draft.labels is not None
        assert draft.labels.note_type is NoteType.ACTION
        assert draft.labels.status is Status.WAITING
        assert draft.labels.due_date == datetime.date(2026, 1, 2)
        assert draft.labels.people == ("Ada",)
        assert draft.labels.project == "Release 1.0"
        assert not draft.is_dirty

    def test_malformed_note_loads_in_raw_mode(self) -> None:
        text = "---\ntype: refrence\n---\nBody\n"

        draft = PageDraft.from_page(_page(text))

        assert draft.mode is DraftMode.RAW
        assert draft.labels is None
        assert draft.source is None
        assert draft.raw_text == text
        assert not draft.is_dirty

    def test_raw_text_change_marks_the_draft_dirty(self) -> None:
        draft = PageDraft.from_page(_page("---\ntype: refrence\n---\nBody\n"))

        assert draft.with_raw_text("changed").is_dirty


class TestLabelRules:
    def test_switching_to_note_clears_category_and_status(self) -> None:
        draft = PageDraft.from_page(_page(PERSON_NOTE))
        assert draft.labels is not None

        labels = draft.labels.with_type(NoteType.NOTE)

        assert labels.category is None
        assert labels.status is None

    def test_switching_to_reference_clears_an_invalid_status(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        assert draft.labels is not None
        done = draft.labels.with_status(Status.DONE)

        labels = done.with_type(NoteType.REFERENCE)

        assert labels.status is None

    def test_switching_between_action_and_project_keeps_a_valid_status(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        assert draft.labels is not None

        labels = draft.labels.with_type(NoteType.PROJECT)

        assert labels.status is Status.WAITING

    def test_invalid_status_for_the_type_is_rejected(self) -> None:
        draft = PageDraft.from_page(_page("---\ntype: note\n---\n\nBody\n"))
        assert draft.labels is not None

        with pytest.raises(NoteParseError):
            draft.labels.with_status(Status.ACTIVE)

    def test_category_is_ignored_for_a_non_reference(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        assert draft.labels is not None

        labels = draft.labels.with_category(ReferenceCategory.PERSON)

        assert labels.category is None

    def test_people_are_trimmed_and_blank_entries_dropped(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        assert draft.labels is not None

        labels = draft.labels.with_people(("  Ada  ", "", "Grace "))

        assert labels.people == ("Ada", "Grace")

    def test_blank_project_clears_it(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        assert draft.labels is not None

        labels = draft.labels.with_project("   ")

        assert labels.project is None

    def test_invalid_due_date_reports_an_error(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        assert draft.labels is not None

        labels = draft.labels.with_due_date_text("January 2")

        assert labels.due_date is None
        assert labels.due_date_error is not None


class TestSerialize:
    def test_preserves_unknown_keys_and_updates_owned_labels(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        assert draft.labels is not None
        labels = (
            draft.labels.with_status(Status.DONE)
            .with_due_date_text("2027-03-04")
            .with_people(("Ada", "Grace"))
            .with_project("Release 2.0")
        )
        draft = draft.with_body("# Call Ada\n\nNew body.\n").with_labels(labels)

        document = NoteDocument.from_text(draft.to_text())

        assert document.raw["custom"] == "keep"
        assert document.status is Status.DONE
        assert document.raw["due_date"] == "2027-03-04"
        assert document.raw["people"] == ["person:Ada", "person:Grace"]
        assert document.raw["project"] == "project:Release 2.0"
        assert document.body == "# Call Ada\n\nNew body.\n"

    def test_clearing_labels_removes_the_keys(self) -> None:
        draft = PageDraft.from_page(_page(PERSON_NOTE))
        assert draft.labels is not None
        labels = draft.labels.with_type(NoteType.NOTE).with_due_date_text("").with_people(()).with_project(None)

        document = NoteDocument.from_text(draft.with_labels(labels).to_text())

        assert document.note_type is NoteType.NOTE
        assert "category" not in document.raw
        assert "status" not in document.raw
        assert "due_date" not in document.raw
        assert "people" not in document.raw
        assert "project" not in document.raw

    def test_invalid_due_date_blocks_serialization(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        assert draft.labels is not None

        with pytest.raises(NoteParseError):
            draft.with_labels(draft.labels.with_due_date_text("January 2")).to_text()

    def test_preserves_crlf_newlines(self) -> None:
        text = "---\r\ntype: note\r\n---\r\n\r\n# Ada\r\nBody.\r\n"
        draft = PageDraft.from_page(_page(text))

        serialized = draft.with_body("# Ada\r\n\r\nNew body.\r\n").to_text()

        assert "\r\n" in serialized
        assert "\n" not in serialized.replace("\r\n", "")

    def test_raw_mode_returns_the_text_unchanged(self) -> None:
        text = "---\ntype: refrence\n---\nBody\n"
        draft = PageDraft.from_page(_page(text))

        assert draft.to_text() == text

    def test_raw_mode_has_no_labels(self) -> None:
        draft = PageDraft.from_page(_page("---\ntype: refrence\n---\nBody\n"))

        with pytest.raises(NoteParseError):
            draft.with_labels(PageLabels(note_type=NoteType.NOTE))


class TestAfterWrite:
    def test_normal_save_resets_the_baseline(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        changed = draft.with_body("# Call Ada\n\nNew body.\n")

        saved = changed.after_write(changed.to_text(), content_hash="new-hash")

        assert not saved.is_dirty
        assert saved.baseline_hash == "new-hash"
        assert saved.body == "# Call Ada\n\nNew body.\n"

    def test_display_title_follows_the_body(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))

        assert draft.display_title == "Call Ada"
        assert draft.with_body("# New title\n\nBody.\n").display_title == "New title"

    def test_raw_draft_display_title_is_the_identity(self) -> None:
        draft = PageDraft.from_page(_page("---\ntype: refrence\n---\n", path=Path("/vault/reference/Broken.md")))

        assert draft.display_title == "Broken"

    def test_as_new_clears_the_saved_baseline(self) -> None:
        draft = PageDraft.from_page(_page(ACTION_NOTE))
        saved = draft.after_write(draft.to_text(), content_hash="new-hash")

        new = saved.as_new()

        assert new.path is None
        assert new.body == saved.body
        assert new.is_dirty

    def test_new_draft_adopts_its_path(self) -> None:
        draft = PageDraft.new(NoteReference(ReferenceScheme.NOTE, "Quarterly budget"))
        text = draft.with_body("# Quarterly budget\n\nText.\n").to_text()

        saved = draft.with_body("# Quarterly budget\n\nText.\n").after_write(
            text,
            content_hash="new-hash",
            path=Path("/vault/reference/Quarterly budget.md"),
        )

        assert not saved.is_new
        assert saved.identity == "Quarterly budget"
        assert not saved.is_dirty

    def test_raw_save_that_still_fails_stays_raw(self) -> None:
        draft = PageDraft.from_page(_page("---\ntype: refrence\n---\nBody\n"))

        saved = draft.with_raw_text("still broken").after_write("still broken", content_hash="new-hash")

        assert saved.mode is DraftMode.RAW
        assert saved.raw_text == "still broken"
        assert saved.baseline_hash == "new-hash"
        assert not saved.is_dirty

    def test_raw_save_that_parses_upgrades_to_normal(self) -> None:
        draft = PageDraft.from_page(_page("---\ntype: refrence\n---\nBody\n"))
        fixed = "---\ntype: note\n---\n\n# Fixed\nBody.\n"

        saved = draft.with_raw_text(fixed).after_write(fixed, content_hash="new-hash")

        assert saved.mode is DraftMode.NORMAL
        assert saved.labels is not None
        assert saved.labels.note_type is NoteType.NOTE
        assert saved.body == "\n# Fixed\nBody.\n"
        assert saved.path == Path("/vault/reference/Ada.md")
        assert not saved.is_dirty

    def test_raw_save_without_a_type_stays_raw(self) -> None:
        draft = PageDraft.from_page(_page("---\ntype: refrence\n---\nBody\n"))
        text = "---\nstatus: active\n---\n\nBody\n"

        saved = draft.with_raw_text(text).after_write(text, content_hash="new-hash")

        assert saved.mode is DraftMode.RAW
