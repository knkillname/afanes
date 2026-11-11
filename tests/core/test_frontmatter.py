"""Tests for frontmatter parsing, serialization, and reference rewriting."""

import pytest

import afanes.models.note
from afanes.core.errors import InvalidReferenceError, NoteParseError
from afanes.core.frontmatter import NoteDocument
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory, Status

CUSTOM_VALUE = 42
SAMPLE = """---
type: action
status: active
people:
  - "person:Ada"
  - "person:Grace"
project: "project:Turing"
custom: 42
---

Body text.
"""


class TestParseDocument:
    def test_parses_metadata_body_and_references(self) -> None:
        document = NoteDocument.from_text(SAMPLE)
        assert document.note_type is NoteType.ACTION
        assert document.status is afanes.models.note.Status.ACTIVE
        assert document.has_frontmatter is True
        assert document.body == "\nBody text.\n"
        assert document.raw["status"] == "active"
        assert document.raw["custom"] == CUSTOM_VALUE
        assert document.references == (
            NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"),
            NoteReference(scheme=ReferenceScheme.PERSON, name="Grace"),
            NoteReference(scheme=ReferenceScheme.PROJECT, name="Turing"),
        )

    def test_absent_frontmatter_is_all_body(self) -> None:
        document = NoteDocument.from_text("Just a body.\n")
        assert document.raw == {}
        assert document.has_frontmatter is False
        assert document.note_type is None
        assert document.body == "Just a body.\n"
        assert document.references == ()

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
        document = NoteDocument.from_text("---\ntype: action\n---\n")
        assert document.note_type is NoteType.ACTION

    def test_missing_type_is_reported_as_absent(self) -> None:
        document = NoteDocument.from_text("---\nid: legacy\n---\n")
        assert document.note_type is None

    def test_person_is_no_longer_a_note_type(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: person\n---\n")

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
    def test_reference_accepts_a_person_category(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\ncategory: person\n---\n")

        assert document.category is ReferenceCategory.PERSON
        assert document.raw["category"] == "person"

    def test_uncategorized_reference_is_valid(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\n---\n")

        assert document.category is None

    def test_category_is_normalized_to_lowercase(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\ncategory: Person\n---\n")

        assert document.category is ReferenceCategory.PERSON
        assert "category: person" in document.to_text()

    def test_unknown_category_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: reference\ncategory: place\n---\n")

    def test_empty_category_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: reference\ncategory: ''\n---\n")

    def test_null_category_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: reference\ncategory: null\n---\n")

    def test_category_on_an_action_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: action\ncategory: person\n---\n")

    def test_category_on_a_note_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: note\ncategory: person\n---\n")

    def test_category_without_a_type_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ncategory: person\n---\n")

    def test_category_survives_a_round_trip(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\ncategory: person\n---\n")

        reparsed = NoteDocument.from_text(document.to_text())

        assert reparsed.category is ReferenceCategory.PERSON


class TestStatus:
    @pytest.mark.parametrize("status", ["active", "waiting", "done", "cancelled", "archived", "later"])
    def test_actions_accept_workflow_statuses(self, status: str) -> None:
        document = NoteDocument.from_text(f"---\ntype: action\nstatus: {status}\n---\n")

        assert document.status is Status(status)

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
            NoteDocument.from_text("---\ntype: action\nstatus: inbox\n---\n")

    def test_waiting_reference_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: reference\nstatus: waiting\n---\n")

    def test_status_without_a_type_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\nstatus: active\n---\n")

    def test_non_string_status_is_rejected(self) -> None:
        with pytest.raises(NoteParseError):
            NoteDocument.from_text("---\ntype: action\nstatus: 3\n---\n")

    def test_null_status_is_treated_as_absent(self) -> None:
        document = NoteDocument.from_text("---\ntype: action\nstatus: null\n---\n")

        assert document.status is None

    def test_status_survives_a_round_trip(self) -> None:
        document = NoteDocument.from_text("---\ntype: action\nstatus: waiting\n---\n")

        reparsed = NoteDocument.from_text(document.to_text())

        assert reparsed.status is Status.WAITING


class TestFrontmatterReferences:
    def test_accepts_a_people_list(self) -> None:
        document = NoteDocument.from_text('---\npeople: ["person:Ada", "person:Grace"]\n---\n')
        assert [reference.name for reference in document.references] == ["Ada", "Grace"]

    def test_rejects_a_bare_person_name(self) -> None:
        with pytest.raises(InvalidReferenceError):
            NoteDocument.from_text('---\npeople: ["Ada"]\n---\n')

    def test_rejects_a_wrong_scheme_in_people(self) -> None:
        with pytest.raises(InvalidReferenceError):
            NoteDocument.from_text('---\npeople: ["project:Ada"]\n---\n')

    def test_rejects_a_non_list_people_value(self) -> None:
        with pytest.raises(InvalidReferenceError):
            NoteDocument.from_text('---\npeople: "person:Ada"\n---\n')

    def test_rejects_a_null_people_value(self) -> None:
        with pytest.raises(InvalidReferenceError):
            NoteDocument.from_text("---\npeople: null\n---\n")

    def test_rejects_a_non_string_people_entry(self) -> None:
        with pytest.raises(InvalidReferenceError):
            NoteDocument.from_text("---\npeople: [3]\n---\n")

    def test_accepts_a_project_value(self) -> None:
        document = NoteDocument.from_text('---\nproject: "project:Turing Machine"\n---\n')
        assert document.references == (NoteReference(scheme=ReferenceScheme.PROJECT, name="Turing Machine"),)

    def test_rejects_a_wrong_scheme_in_project(self) -> None:
        with pytest.raises(InvalidReferenceError):
            NoteDocument.from_text('---\nproject: "person:Ada"\n---\n')

    def test_rejects_a_non_string_project_value(self) -> None:
        with pytest.raises(InvalidReferenceError):
            NoteDocument.from_text("---\nproject: [3]\n---\n")


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
        assert reparsed.references == document.references

    def test_round_trip_preserves_key_order(self) -> None:
        document = NoteDocument.from_text(SAMPLE)
        reparsed = NoteDocument.from_text(document.to_text())
        assert list(reparsed.raw) == list(document.raw)

    def test_round_trip_preserves_crlf(self) -> None:
        source = "---\r\ntype: note\r\n---\r\nBody\r\n"
        document = NoteDocument.from_text(source)
        assert document.to_text() == source


class TestWithMetadata:
    def test_replaces_metadata_and_preserves_the_body(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\ncustom: 42\n---\nBody\n")
        updated = document.with_metadata({"type": "action", "status": "waiting", "custom": 42})

        assert updated.note_type is NoteType.ACTION
        assert updated.status is Status.WAITING
        assert updated.raw["custom"] == CUSTOM_VALUE
        assert updated.body == document.body
        assert "type: action" in updated.to_text()
        assert "status: waiting" in updated.to_text()

    def test_revalidates_the_replacement(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n")

        with pytest.raises(NoteParseError):
            document.with_metadata({"type": "action", "status": "inbox"})

    def test_does_not_retain_the_caller_mapping(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\n---\n")
        raw: dict[str, object] = {"type": "action", "status": "active"}

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


class TestRewriteReferenceValues:
    def test_rewrites_matching_people_values_only(self) -> None:
        document = NoteDocument.from_text('---\ntype: note\npeople: ["person:Ada Lovelace", "person:Grace"]\n---\n')
        old = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada Lovelace")
        new = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King")
        rewritten, count = document.rewrite_references(old, new)
        assert count == 1
        assert rewritten.raw["people"] == ["person:Ada King", "person:Grace"]

    def test_rewrites_a_matching_project_value(self) -> None:
        document = NoteDocument.from_text('---\nproject: "project:Turing Machine"\n---\n')
        old = NoteReference(scheme=ReferenceScheme.PROJECT, name="Turing Machine")
        new = NoteReference(scheme=ReferenceScheme.PROJECT, name="Turing Engine")
        rewritten, count = document.rewrite_references(old, new)
        assert count == 1
        assert rewritten.raw["project"] == "project:Turing Engine"

    def test_keeps_unknown_keys_and_their_order(self) -> None:
        document = NoteDocument.from_text('---\ntype: note\nid: legacy\npeople: ["person:Ada"]\ncustom: 42\n---\n')
        old = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")
        new = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King")
        rewritten, _ = document.rewrite_references(old, new)
        assert list(rewritten.raw) == ["type", "id", "people", "custom"]
        assert rewritten.raw["id"] == "legacy"
        assert rewritten.raw["custom"] == CUSTOM_VALUE

    def test_no_match_returns_the_same_document(self) -> None:
        document = NoteDocument.from_text('---\npeople: ["person:Grace"]\n---\n')
        old = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")
        new = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King")
        rewritten, count = document.rewrite_references(old, new)
        assert rewritten is document
        assert count == 0

    def test_rewritten_document_reparses_to_updated_references(self) -> None:
        document = NoteDocument.from_text('---\npeople: ["person:Ada"]\n---\n')
        old = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")
        new = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King")
        rewritten, _ = document.rewrite_references(old, new)
        reparsed = NoteDocument.from_text(rewritten.to_text())
        assert reparsed.references == (new,)
