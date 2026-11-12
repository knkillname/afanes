"""Tests for the note vocabulary."""

import pytest

import afanes.models.note
from afanes.models.note import CategoryLabel, NoteType, Status


class TestNoteType:
    def test_members_cover_the_canonical_contract(self) -> None:
        assert {member.value for member in NoteType} == {"note", "project", "reference"}

    def test_members_compare_as_strings(self) -> None:
        assert NoteType.REFERENCE == "reference"

    def test_action_is_not_a_note_type(self) -> None:
        assert not hasattr(NoteType, "ACTION")

    def test_person_is_not_a_note_type(self) -> None:
        assert not hasattr(NoteType, "PERSON")

    def test_enum_is_exported_from_its_module(self) -> None:
        assert afanes.models.note.NoteType is NoteType


class TestCategoryLabel:
    def test_arbitrary_label_is_accepted(self) -> None:
        assert CategoryLabel("place").value == "place"

    def test_written_case_is_preserved(self) -> None:
        assert CategoryLabel("Place").value == "Place"

    def test_labels_compare_case_insensitively(self) -> None:
        assert CategoryLabel("Place") == CategoryLabel("place")

    def test_case_variants_share_a_hash(self) -> None:
        assert hash(CategoryLabel("Place")) == hash(CategoryLabel("place"))

    @pytest.mark.parametrize("value", ["", "   "])
    def test_empty_label_is_rejected(self, value: str) -> None:
        with pytest.raises(ValueError, match="empty"):
            CategoryLabel(value)

    @pytest.mark.parametrize("value", ["people/places", "people\\places"])
    def test_path_separator_is_rejected(self, value: str) -> None:
        with pytest.raises(ValueError, match="single path segment"):
            CategoryLabel(value)

    @pytest.mark.parametrize("value", [".", ".."])
    def test_traversal_segment_is_rejected(self, value: str) -> None:
        with pytest.raises(ValueError, match="traversal"):
            CategoryLabel(value)


class TestStatus:
    def test_members_cover_the_canonical_contract(self) -> None:
        assert {member.value for member in Status} == {"active", "waiting", "done", "cancelled", "archived", "later"}

    def test_members_compare_as_strings(self) -> None:
        assert Status.LATER == "later"


class TestAllowedStatuses:
    def test_projects_allow_workflow_states(self) -> None:
        assert NoteType.PROJECT.allowed_statuses == {
            Status.ACTIVE,
            Status.WAITING,
            Status.DONE,
            Status.CANCELLED,
            Status.ARCHIVED,
            Status.LATER,
        }

    def test_references_allow_only_deferred_or_archived(self) -> None:
        assert NoteType.REFERENCE.allowed_statuses == {Status.LATER, Status.ARCHIVED}

    def test_notes_allow_no_status(self) -> None:
        assert NoteType.NOTE.allowed_statuses == frozenset()
