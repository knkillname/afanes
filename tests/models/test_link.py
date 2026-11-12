"""Tests for reference value objects."""

from dataclasses import FrozenInstanceError

import pytest

import afanes.models.link
from afanes.models.link import NoteReference, ReferenceScheme


class TestReferenceScheme:
    def test_members_are_the_two_internal_namespaces(self) -> None:
        assert {member.value for member in ReferenceScheme} == {"project", "note"}

    def test_projects_resolve_through_the_project_scheme(self) -> None:
        assert ReferenceScheme.for_note("project") is ReferenceScheme.PROJECT

    @pytest.mark.parametrize("note_type", ["note", "reference"])
    def test_documents_resolve_through_the_note_scheme(self, note_type: str) -> None:
        assert ReferenceScheme.for_note(note_type) is ReferenceScheme.NOTE

    def test_person_is_not_a_scheme(self) -> None:
        assert not hasattr(ReferenceScheme, "PERSON")


class TestNoteReference:
    def test_construction_keeps_scheme_name_and_label(self) -> None:
        reference = NoteReference(scheme=ReferenceScheme.NOTE, name="Ada Lovelace", label="Ada")
        assert reference.scheme is ReferenceScheme.NOTE
        assert reference.name == "Ada Lovelace"
        assert reference.label == "Ada"

    def test_label_defaults_to_none(self) -> None:
        reference = NoteReference(scheme=ReferenceScheme.PROJECT, name="Turing Machine")
        assert reference.label is None

    def test_equal_values_compare_equal(self) -> None:
        first = NoteReference(scheme=ReferenceScheme.NOTE, name="Call dentist")
        second = NoteReference(scheme=ReferenceScheme.NOTE, name="Call dentist")
        assert first == second

    def test_value_object_is_frozen(self) -> None:
        reference = NoteReference(scheme=ReferenceScheme.NOTE, name="Call dentist")
        attribute_name = "name"
        with pytest.raises(FrozenInstanceError):
            setattr(reference, attribute_name, "Other")

    def test_module_exports_the_value_object(self) -> None:
        assert afanes.models.link.NoteReference is NoteReference
