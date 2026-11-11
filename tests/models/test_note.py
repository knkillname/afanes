"""Tests for the note type vocabulary."""

import afanes.models.note
from afanes.models.note import NoteType


class TestNoteType:
    def test_members_cover_the_canonical_contract(self) -> None:
        assert {member.value for member in NoteType} == {"note", "action", "project", "reference", "person"}

    def test_members_compare_as_strings(self) -> None:
        assert NoteType.PERSON == "person"

    def test_enum_is_exported_from_its_module(self) -> None:
        assert afanes.models.note.NoteType is NoteType
