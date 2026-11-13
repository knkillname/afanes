"""Tests for the editable page labels and the canonical label writer."""

import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from afanes.core.errors import NoteParseError
from afanes.core.frontmatter import NoteDocument
from afanes.core.labels import PageLabels
from afanes.models.note import CategoryLabel, NoteDate, NoteType, Status

PROJECT_SOURCE = """---
type: project
date: 2025-10
custom: keep
status: waiting
due_date: 2026-01-02
asked_by: Priya Nair
owner: Sam Rivera
---

# Call Ada

Body.
"""


def _note_text(note_type: NoteType) -> str:
    return f"---\ntype: {note_type.value}\n---\n\n# Example\n\nBody.\n"


class TestApplyTo:
    def test_writes_a_note_type_and_removes_workflow_labels(self) -> None:
        labels = PageLabels(note_type=NoteType.NOTE, date_text="2025-10")

        applied = labels.apply_to(NoteDocument.from_text(PROJECT_SOURCE))

        assert applied.note_type is NoteType.NOTE
        assert applied.raw["custom"] == "keep"
        assert applied.raw["date"] == "2025-10"
        assert "category" not in applied.raw
        assert "status" not in applied.raw
        assert "due_date" not in applied.raw
        assert "asked_by" not in applied.raw
        assert "owner" not in applied.raw

    def test_writes_a_reference_category_and_status(self) -> None:
        labels = PageLabels(
            note_type=NoteType.REFERENCE,
            category=CategoryLabel("Person"),
            status=Status.LATER,
        )

        applied = labels.apply_to(NoteDocument.from_text(PROJECT_SOURCE))

        assert applied.note_type is NoteType.REFERENCE
        assert applied.category == CategoryLabel("person")
        assert applied.status is Status.LATER
        assert "due_date" not in applied.raw
        assert "asked_by" not in applied.raw
        assert "owner" not in applied.raw

    def test_writes_project_status_due_date_and_requester(self) -> None:
        labels = PageLabels(
            note_type=NoteType.PROJECT,
            status=Status.ACTIVE,
            due_date_text="2027-03-04",
            asked_by_text="  Ada Lovelace  ",
            owner_text="  Grace Hopper  ",
        )

        applied = labels.apply_to(NoteDocument.from_text(PROJECT_SOURCE))

        assert applied.note_type is NoteType.PROJECT
        assert applied.status is Status.ACTIVE
        assert applied.due_date == datetime.date(2027, 3, 4)
        assert applied.asked_by == "Ada Lovelace"
        assert applied.owner == "Grace Hopper"
        assert "category" not in applied.raw

    def test_writes_a_log_type_and_removes_reference_labels(self) -> None:
        labels = PageLabels(note_type=NoteType.LOG, date_text="2025-10-12")

        applied = labels.apply_to(NoteDocument.from_text(PROJECT_SOURCE))

        assert applied.note_type is NoteType.LOG
        assert applied.date == NoteDate.from_text("2025-10-12")
        assert applied.raw["custom"] == "keep"
        assert "category" not in applied.raw
        assert "status" not in applied.raw
        assert "due_date" not in applied.raw
        assert "asked_by" not in applied.raw
        assert "owner" not in applied.raw

    def test_keeps_the_date_when_the_type_changes(self) -> None:
        document = NoteDocument.from_text(_note_text(NoteType.NOTE))

        for note_type in NoteType:
            applied = PageLabels(note_type=note_type, date_text="2025-10-12").apply_to(document)
            assert applied.date == NoteDate.from_text("2025-10-12"), note_type

    def test_removes_a_blank_date(self) -> None:
        applied = PageLabels(note_type=NoteType.PROJECT, date_text="").apply_to(NoteDocument.from_text(PROJECT_SOURCE))

        assert "date" not in applied.raw

    def test_leaves_a_malformed_date_for_correction(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\ndate: last Tuesday\n---\n\nBody\n")

        applied = PageLabels(note_type=NoteType.REFERENCE, date_text="last Tuesday").apply_to(document)

        assert applied.raw["date"] == "last Tuesday"
        assert applied.date is None
        assert applied.date_error is not None

    def test_appends_new_keys_in_documented_order(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\ncustom: keep\n---\n\n# Example\n")
        labels = PageLabels(
            note_type=NoteType.PROJECT,
            status=Status.ACTIVE,
            due_date_text="2026-01-02",
            asked_by_text="Priya Nair",
            owner_text="Sam Rivera",
            date_text="2025-10-12",
        )

        applied = labels.apply_to(document)

        assert list(applied.raw) == ["type", "custom", "date", "status", "due_date", "asked_by", "owner"]

    def test_appends_a_category_before_a_new_status(self) -> None:
        document = NoteDocument.from_text("---\ntype: note\ncustom: keep\n---\n\n# Example\n")
        labels = PageLabels(
            note_type=NoteType.REFERENCE,
            category=CategoryLabel("person"),
            status=Status.LATER,
            date_text="2025",
        )

        applied = labels.apply_to(document)

        assert list(applied.raw) == ["type", "custom", "date", "category", "status"]

    def test_keeps_existing_key_positions(self) -> None:
        document = NoteDocument.from_text("---\ntype: reference\nstatus: later\ncustom: keep\n---\n\n# Example\n")

        applied = PageLabels(note_type=NoteType.PROJECT, status=Status.ACTIVE).apply_to(document)

        assert list(applied.raw) == ["type", "status", "custom"]

    def test_preserves_the_body_and_crlf_newlines(self) -> None:
        text = "---\r\ntype: note\r\ncustom: keep\r\n---\r\n\r\n# Example\r\n\r\nBody.\r\n"
        document = NoteDocument.from_text(text)

        applied = PageLabels(
            note_type=NoteType.PROJECT,
            status=Status.ACTIVE,
            due_date_text="2026-01-02",
            asked_by_text="Priya Nair",
            owner_text="Sam Rivera",
        ).apply_to(document)
        written = applied.to_text()

        assert applied.body == document.body
        assert applied.newline == "\r\n"
        assert "\r\n" in written
        assert "\n" not in written.replace("\r\n", "")

    def test_rejects_a_status_invalid_for_the_type(self) -> None:
        labels = PageLabels(note_type=NoteType.NOTE, status=Status.ACTIVE)

        with pytest.raises(NoteParseError):
            labels.apply_to(NoteDocument.from_text(_note_text(NoteType.NOTE)))

    def test_rejects_a_category_on_a_non_reference(self) -> None:
        labels = PageLabels(note_type=NoteType.PROJECT, category=CategoryLabel("person"))

        applied = labels.apply_to(NoteDocument.from_text(_note_text(NoteType.PROJECT)))

        assert "category" not in applied.raw

    def test_removes_a_blank_owner(self) -> None:
        applied = PageLabels(note_type=NoteType.PROJECT, owner_text="   ").apply_to(
            NoteDocument.from_text(PROJECT_SOURCE)
        )

        assert "owner" not in applied.raw

    def test_a_type_change_clears_the_owner(self) -> None:
        labels = PageLabels(note_type=NoteType.PROJECT, owner_text="Sam Rivera")

        changed = labels.with_type(NoteType.REFERENCE)

        assert changed.owner_text == ""

    def test_with_owner_text_ignores_non_project_labels(self) -> None:
        labels = PageLabels(note_type=NoteType.REFERENCE)

        changed = labels.with_owner_text("Sam Rivera")

        assert changed.owner_text == ""

    def test_from_document_reads_the_owner(self) -> None:
        labels = PageLabels.from_document(NoteDocument.from_text(PROJECT_SOURCE))

        assert labels.owner_text == "Sam Rivera"


@st.composite
def _label_sets(draw: st.DrawFn) -> PageLabels:
    note_type = draw(st.sampled_from(list(NoteType)))
    allowed_statuses = sorted(note_type.allowed_statuses, key=lambda status: status.value)
    status = draw(st.sampled_from([None, *allowed_statuses]))
    category = draw(st.none() | st.text(alphabet="abcxyz", min_size=1)) if note_type is NoteType.REFERENCE else None
    due_date_text = draw(st.none() | st.dates().map(str)) if note_type is NoteType.PROJECT else ""
    asked_by_text = (
        draw(st.text(alphabet="abc XYZ", min_size=1).map(str.strip).filter(bool))
        if note_type is NoteType.PROJECT
        else ""
    )
    owner_text = (
        draw(st.text(alphabet="abc XYZ", min_size=1).map(str.strip).filter(bool))
        if note_type is NoteType.PROJECT
        else ""
    )
    date_text = draw(
        st.none()
        | st.dates().map(str)
        | st.integers(min_value=1, max_value=9999).map(lambda year: f"{year:04d}")
        | st.tuples(st.integers(min_value=1, max_value=9999), st.integers(min_value=1, max_value=12)).map(
            lambda parts: f"{parts[0]:04d}-{parts[1]:02d}"
        )
    )
    return PageLabels(
        note_type=note_type,
        category=None if category is None else CategoryLabel(category),
        status=status,
        due_date_text=due_date_text or "",
        asked_by_text=asked_by_text or "",
        owner_text=owner_text or "",
        date_text=date_text or "",
    )


class TestApplyToRoundTrip:
    @given(labels=_label_sets())
    def test_from_document_reproduces_the_valid_labels(self, labels: PageLabels) -> None:
        document = NoteDocument.from_text("---\ntype: note\ncustom: keep\n---\n\n# Example\n\nBody.\n")

        round_tripped = PageLabels.from_document(labels.apply_to(document))

        assert round_tripped == labels
