"""Tests for reference value objects."""

from dataclasses import FrozenInstanceError

import pytest

import afanes.models.link
from afanes.models.link import NoteReference, ReferenceScheme


class TestReferenceScheme:
    def test_members_are_the_three_internal_namespaces(self) -> None:
        assert {member.value for member in ReferenceScheme} == {"person", "project", "note"}


class TestNoteReference:
    def test_construction_keeps_scheme_name_and_label(self) -> None:
        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada Lovelace", label="Ada")
        assert reference.scheme is ReferenceScheme.PERSON
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
