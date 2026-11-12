"""Tests for frontmatter parsing and serialization."""

import datetime

import hypothesis
import hypothesis.strategies
import pytest

import afanes.models.note
from afanes.core.errors import NoteParseError, RetiredValueError
from afanes.core.frontmatter import FrontmatterSplit, NoteDocument
from afanes.models.note import CategoryLabel, NoteType, Status

CUSTOM_VALUE = 42
SAMPLE = """---
type: project
status: active
due_date: 2026-11-20
custom: 42
---

Body text.
"""


class TestParseDocument:
    def test_parses_metadata_body_and_labels(self) -> None:
        document = NoteDocument.from_text(SAMPLE)
        assert document.note_type is NoteType.PROJECT
        assert document.status is afanes.models.note.Status.ACTIVE
        assert document.due_date == datetime.date(2026, 11, 20)
        assert document.has_frontmatter is True
        assert document.body == "\nBody text.\n"
        assert document.raw["status"] == "active"
        assert document.raw["custom"] == CUSTOM_VALUE

    def test_absent_frontmatter_is_all_body(self) -> None:
        document = NoteDocument.from_text("Just a body.\n")
        assert document.raw == {}
        assert document.has_frontmatter is False
        assert document.note_type is None
        assert document.body == "Just a body.\n"

    def test_empty_frontmatter_is_valid(self) -> None:
        document = NoteDocument.from_text("---\n---\nBody\n")
        assert document.raw == {}
        assert document.has_frontmatter is True
        assert document.body == "Body\n"

    def test_body_may_begin_with_a_fence(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n---\nBody\n")
        assert document.body == "---\nBody\n"

    def test_crlf_is_detected_and_preserved_in_the_body(self) -> None:
        source = "---\r\ntype: note\r\n---\r\n\r\nBody\r\n"
        document = NoteDocument.from_text(source)
        assert document.newline == "\r\n"
        assert document.body == "\r\nBody\r\n"

    def test_unknown_keys_are_preserved(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\nid: legacy\n---\n")
        assert document.raw["id"] == "legacy"

    def test_declared_type_is_normalized_to_the_enum(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\n---\n")
        assert document.note_type is NoteType.REFERENCE

    def test_missing_type_is_reported_as_absent(self) -> None:
        document = NoteDocument.from_text("---\nid: legacy\n---\n")
        assert document.note_type is None

    def test_action_is_rejected_with_its_replacement(self) -> None:
        with pytest.raises(RetiredValueError, match="one-step project"):
            NoteDocument.from_text("---\ntype: action\n---\n")

    def test_person_is_rejected_with_its_replacement(self) -> None:
        with pytest.raises(RetiredValueError, match="category label"):
            NoteDocument.from_text("---\ntype: person\n---\n")

    def test_people_key_is_rejected_with_its_replacement(self) -> None:
        with pytest.raises(RetiredValueError, match="step owners"):
            NoteDocument.from_text('---\ntype: note\npeople: ["person:Ada"]\n---\n')

    def test_project_key_is_rejected_with_its_replacement(self) -> None:
        with pytest.raises(RetiredValueError, match="project body"):
            NoteDocument.from_text('---\ntype: note\nproject: "project:Turing"\n---\n')

    def test_malformed_yaml_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: [unclosed\n---\n")

    def test_non_mapping_frontmatter_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\n- one\n- two\n---\n")

    def test_unterminated_frontmatter_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: note\n")

    def test_non_string_type_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: 3\n---\n")

    def test_null_type_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: null\n---\n")

    def test_unknown_type_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: errand\n---\n")

    def test_non_string_key_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\n1: note\n---\n")


class TestCategory:
    def test_reference_accepts_an_arbitrary_label(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\ncategory: place\n---\n")

        assert document.category == CategoryLabel("place")
        assert document.raw["category"] == "place"

    def test_uncategorized_reference_is_valid(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\n---\n")

        assert document.category is None

    def test_written_case_is_preserved(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\ncategory: Person\n---\n")

        assert document.raw["category"] == "Person"
        assert document.category == CategoryLabel("person")
        assert "category: Person" in document.to_text()

    def test_empty_category_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: reference\ncategory: ''\n---\n")

    def test_null_category_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: reference\ncategory: null\n---\n")

    def test_path_separator_category_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text('---\ntype: reference\ncategory: "people/places"\n---\n')

    def test_category_on_a_project_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: project\ncategory: place\n---\n")

    def test_category_on_a_note_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: note\ncategory: person\n---\n")

    def test_category_without_a_type_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ncategory: person\n---\n")

    def test_category_survives_a_round_trip(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\ncategory: Place\n---\n")

        reparsed = NoteDocument.from_text(document.to_text())

        assert reparsed.category == CategoryLabel("Place")


class TestStatus:
    @pytest.mark.parametrize("status", ["active", "waiting", "done", "cancelled", "archived", "later"])
    def test_projects_accept_workflow_statuses(self, status: str) -> None:
        document = NoteDocument.from_text(f"---\ntype: project\nstatus: {status}\n---\n")

        assert document.status is Status(status)

    @pytest.mark.parametrize("status", ["later", "archived"])
    def test_references_accept_deferred_or_archived(self, status: str) -> None:
        document = NoteDocument.from_text(f"---\ntype: reference\nstatus: {status}\n---\n")

        assert document.status is Status(status)

    def test_notes_reject_a_status(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: note\nstatus: active\n---\n")

    def test_inbox_is_not_a_status(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: project\nstatus: inbox\n---\n")

    def test_waiting_reference_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: reference\nstatus: waiting\n---\n")

    def test_status_without_a_type_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\nstatus: active\n---\n")

    def test_non_string_status_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: project\nstatus: 3\n---\n")

    def test_null_status_is_treated_as_absent(self) -> None:
        document = NoteDocument.from_text("---\ntype: project\nstatus: null\n---\n")

        assert document.status is None

    def test_status_survives_a_round_trip(self) -> None:
        document = NoteDocument.from_text("---\ntype: project\nstatus: waiting\n---\n")

        reparsed = NoteDocument.from_text(document.to_text())

        assert reparsed.status is Status.WAITING


class TestDueDate:
    def test_project_accepts_a_calendar_date(self) -> None:
        document = NoteDocument.from_text("---\ntype: project\ndue_date: 2026-12-01\n---\n")

        assert document.due_date == datetime.date(2026, 12, 1)
        assert document.raw["due_date"] == datetime.date(2026, 12, 1)

    def test_quoted_iso_date_is_accepted(self) -> None:
        document = NoteDocument.from_text("---\ntype: project\ndue_date: '2026-12-01'\n---\n")

        assert document.due_date == datetime.date(2026, 12, 1)

    def test_absent_due_date_is_none(self) -> None:
        document = NoteDocument.from_text("---\ntype: project\n---\n")

        assert document.due_date is None

    def test_null_due_date_is_none(self) -> None:
        document = NoteDocument.from_text("---\ntype: project\ndue_date: null\n---\n")

        assert document.due_date is None

    def test_timestamp_is_rejected(self) -> None:
        with pytest.raises(NoteParseError, match="not a timestamp"):
            NoteDocument.from_text("---\ntype: project\ndue_date: 2026-11-20T10:00:00\n---\n")

    def test_invalid_calendar_date_is_rejected(self) -> None:
        with pytest.raises(NoteParseError, match="YYYY-MM-DD"):
            NoteDocument.from_text("---\ntype: project\ndue_date: '2026-13-40'\n---\n")

    def test_non_date_value_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: project\ndue_date: tomorrow\n---\n")

    def test_due_date_on_a_reference_is_rejected(self) -> None:
        with pytest.raises(NoteParseError, match="project notes"):
            NoteDocument.from_text("---\ntype: reference\ndue_date: 2026-12-01\n---\n")

    def test_due_date_without_a_type_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ndue_date: 2026-12-01\n---\n")

    def test_due_date_survives_a_round_trip(self) -> None:
        document = NoteDocument.from_text("---\ntype: project\ndue_date: 2026-12-01\n---\n")

        reparsed = NoteDocument.from_text(document.to_text())

        assert reparsed.due_date == datetime.date(2026, 12, 1)
        assert "due_date: 2026-12-01" in document.to_text()


class TestSerializeDocument:
    def test_with_body_replaces_only_the_body(self) -> None:
        document = NoteDocument.from_text(SAMPLE)
        replaced = document.with_body("New body.\n")
        assert replaced.body == "New body.\n"
        assert replaced.raw == document.raw
        assert document.body == "\nBody text.\n"

    def test_body_without_frontmatter_is_returned_as_is(self) -> None:
        document = NoteDocument.from_text("Body only.\n")
        assert document.to_text() == "Body only.\n"

    def test_round_trip_preserves_unknown_keys_and_body(self) -> None:
        document = NoteDocument.from_text(SAMPLE)
        reparsed = NoteDocument.from_text(document.to_text())
        assert reparsed.raw == document.raw
        assert reparsed.body == document.body

    def test_round_trip_preserves_key_order(self) -> None:
        document = NoteDocument.from_text(SAMPLE)
        reparsed = NoteDocument.from_text(document.to_text())
        assert list(reparsed.raw) == list(document.raw)

    def test_round_trip_preserves_crlf(self) -> None:
        source = "---\r\ntype: note\r\n---\r\nBody\r\n"
        document = NoteDocument.from_text(source)
        assert document.to_text() == source


@hypothesis.given(
    note_type=hypothesis.strategies.sampled_from(list(NoteType)),
    # CategoryLabel rejects "." and ".." as traversal segments; keep generated
    # labels inside the accepted contract.
    category=hypothesis.strategies.one_of(
        hypothesis.strategies.none(),
        hypothesis.strategies.from_regex(r"[^\s:/\\]{1,10}", fullmatch=True).filter(
            lambda label: label not in {".", ".."}
        ),
    ),
    status=hypothesis.strategies.one_of(hypothesis.strategies.none(), hypothesis.strategies.sampled_from(list(Status))),
    due_date=hypothesis.strategies.one_of(hypothesis.strategies.none(), hypothesis.strategies.dates()),
    unknown=hypothesis.strategies.text(
        alphabet=hypothesis.strategies.characters(blacklist_characters="\x85\u2028\u2029")
    ),
)
def test_frontmatter_round_trip_preserves_recognized_and_unknown_values(
    note_type: NoteType,
    category: str | None,
    status: Status | None,
    due_date: datetime.date | None,
    unknown: str,
) -> None:
    hypothesis.assume(status is None or status in note_type.allowed_statuses)
    raw: dict[str, object] = {"type": note_type.value, "custom": unknown}
    if note_type is NoteType.REFERENCE and category is not None:
        raw["category"] = category
    if status is not None:
        raw["status"] = status.value
    if note_type is NoteType.PROJECT and due_date is not None:
        raw["due_date"] = due_date
    document = NoteDocument.from_text("---\ntype: note\n---\n")
    candidate = document.with_metadata(raw)
    reparsed = NoteDocument.from_text(candidate.to_text())
    assert reparsed.raw == candidate.raw
    assert reparsed.note_type is candidate.note_type
    assert reparsed.category == candidate.category
    assert reparsed.status is candidate.status
    assert reparsed.due_date == candidate.due_date


class TestWithMetadata:
    def test_replaces_metadata_and_preserves_the_body(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\ncustom: 42\n---\nBody\n")
        updated = document.with_metadata({"type": "project", "status": "waiting", "custom": 42})

        assert updated.note_type is NoteType.PROJECT
        assert updated.status is Status.WAITING
        assert updated.raw["custom"] == CUSTOM_VALUE
        assert updated.body == document.body
        assert "type: project" in updated.to_text()
        assert "status: waiting" in updated.to_text()

    def test_revalidates_the_replacement(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n")

        with pytest.raises(NoteParseError):
            document.with_metadata({"type": "project", "status": "inbox"})

    def test_rejects_retired_keys(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n")

        with pytest.raises(RetiredValueError):
            document.with_metadata({"type": "note", "people": []})

    def test_does_not_retain_the_caller_mapping(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n")
        raw: dict[str, object] = {"type": "project", "status": "active"}

        updated = document.with_metadata(raw)
        raw["status"] = "done"

        assert updated.status is Status.ACTIVE


class TestDisplayTitle:
    def test_atx_heading_becomes_the_title(self) -> None:
        document = NoteDocument.from_text("# Ada\n")

        assert document.title == "Ada"

    def test_setext_heading_becomes_the_title(self) -> None:
        document = NoteDocument.from_text("Ada Lovelace\n===\n")

        assert document.title == "Ada Lovelace"

    def test_heading_after_introductory_text_becomes_the_title(self) -> None:
        document = NoteDocument.from_text("An introduction.\n\n# Ada\n")

        assert document.title == "Ada"

    def test_first_heading_wins(self) -> None:
        document = NoteDocument.from_text("# Ada\n\n# Grace\n")

        assert document.title == "Ada"

    def test_empty_first_heading_falls_back_and_does_not_search_later(self) -> None:
        document = NoteDocument.from_text("#\n\n# Ada\n")

        assert document.title is None

    def test_inline_formatting_is_flattened_to_plain_text(self) -> None:
        document = NoteDocument.from_text("# **Ada** *Lovelace* `Countess`\n")

        assert document.title == "Ada Lovelace Countess"

    def test_heading_inside_a_fenced_code_block_is_ignored(self) -> None:
        document = NoteDocument.from_text("```\n# Ada\n```\n")

        assert document.title is None

    def test_missing_heading_returns_no_title(self) -> None:
        document = NoteDocument.from_text("Just a body.\n")

        assert document.title is None

    def test_frontmatter_title_key_does_not_override_the_heading(self) -> None:
        document = NoteDocument.from_text("---\ntitle: Stored\n---\n# Heading\n")

        assert document.title == "Heading"

    def test_with_body_recomputes_the_title(self) -> None:
        document = NoteDocument.from_text("# Old\n")

        replaced = document.with_body("# New\n")

        assert replaced.title == "New"
        assert document.title == "Old"


class TestWithHeading:
    def test_replaces_an_atx_heading(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n\n# Ada\nBody.\n")

        updated = document.with_heading("Ada King")

        assert updated.body == "\n# Ada King\nBody.\n"
        assert updated.note_type is NoteType.NOTE

    def test_replaces_a_setext_heading_with_an_atx_heading(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n\nAda\n===\n\nBody.\n")

        updated = document.with_heading("Ada King")

        assert updated.body == "\n# Ada King\n\nBody.\n"

    def test_replaces_a_heading_after_introductory_text_in_place(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n\nIntro.\n\n# Ada\n\nBody.\n")

        updated = document.with_heading("Ada King")

        assert updated.body == "\nIntro.\n\n# Ada King\n\nBody.\n"

    def test_raises_when_no_heading_exists(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n\nBody.\n")

        with pytest.raises(NoteParseError):
            document.with_heading("Ada King")

    def test_ignores_a_heading_inside_a_code_block(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n\n```\n# Ada\n```\n")

        with pytest.raises(NoteParseError):
            document.with_heading("Ada King")

    def test_preserves_crlf_newlines(self) -> None:
        document = NoteDocument.from_text("---\r\ntype: note\r\n---\r\n\r\n# Ada\r\nBody.\r\n")

        updated = document.with_heading("Ada King")

        assert "\r\n# Ada King\r\n" in updated.body
        assert "\n" not in updated.to_text().replace("\r\n", "")

    def test_preserves_unknown_keys(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\ncustom: keep\n---\n\n# Ada\n")

        updated = document.with_heading("Ada King")

        assert updated.raw["custom"] == "keep"


class TestFrontmatterSplit:
    def test_keeps_raw_body_and_presence(self) -> None:
        split = FrontmatterSplit(
            raw={"type": "note"},
            body="Body\n",
            has_frontmatter=True,
        )

        assert split.raw == {"type": "note"}
        assert split.body == "Body\n"
        assert split.has_frontmatter is True

    def test_reports_absent_frontmatter(self) -> None:
        split = FrontmatterSplit(raw={}, body="Body\n", has_frontmatter=False)

        assert split.has_frontmatter is False
