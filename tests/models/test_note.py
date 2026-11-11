"""Tests for the note vocabulary."""

import afanes.models.note
from afanes.models.note import NoteType, ReferenceCategory, Status


class TestNoteType:
    def test_members_cover_the_canonical_contract(self) -> None:
        assert {member.value for member in NoteType} == {"note", "action", "project", "reference"}

    def test_members_compare_as_strings(self) -> None:
        assert NoteType.REFERENCE == "reference"

    def test_person_is_no_longer_a_note_type(self) -> None:
        assert not hasattr(NoteType, "PERSON")

    def test_enum_is_exported_from_its_module(self) -> None:
        assert afanes.models.note.NoteType is NoteType


class TestReferenceCategory:
    def test_members_cover_the_canonical_contract(self) -> None:
        assert {member.value for member in ReferenceCategory} == {"person"}

    def test_members_compare_as_strings(self) -> None:
        assert ReferenceCategory.PERSON == "person"


class TestStatus:
    def test_members_cover_the_canonical_contract(self) -> None:
        assert {member.value for member in Status} == {"active", "waiting", "done", "cancelled", "archived", "later"}

    def test_members_compare_as_strings(self) -> None:
        assert Status.LATER == "later"


class TestAllowedStatuses:
    def test_actions_allow_workflow_states(self) -> None:
        assert afanes.models.note.allowed_statuses(NoteType.ACTION) == {
            Status.ACTIVE,
            Status.WAITING,
            Status.DONE,
            Status.CANCELLED,
            Status.ARCHIVED,
            Status.LATER,
        }

    def test_projects_allow_workflow_states(self) -> None:
        assert afanes.models.note.allowed_statuses(NoteType.PROJECT) == {
            Status.ACTIVE,
            Status.WAITING,
            Status.DONE,
            Status.CANCELLED,
            Status.ARCHIVED,
            Status.LATER,
        }

    def test_references_allow_only_deferred_or_archived(self) -> None:
        assert afanes.models.note.allowed_statuses(NoteType.REFERENCE) == {Status.LATER, Status.ARCHIVED}

    def test_notes_allow_no_status(self) -> None:
        assert afanes.models.note.allowed_statuses(NoteType.NOTE) == frozenset()
