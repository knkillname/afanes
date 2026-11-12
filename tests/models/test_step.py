"""Tests for project step value objects."""

import dataclasses
import datetime

import pytest

from afanes.models.step import ProjectStep, StepMetadata

LINE_INDEX = 3


class TestStepMetadata:
    def test_defaults_are_empty(self) -> None:
        metadata = StepMetadata()
        assert metadata.owners == ()
        assert metadata.plan is None
        assert metadata.actual is None
        assert metadata.tags == ()
        assert dict(metadata.raw) == {}

    def test_owners_and_tags_are_kept_in_order(self) -> None:
        metadata = StepMetadata(owners=("Ada", "Grace"), tags=("errands", "phone"))
        assert metadata.owners == ("Ada", "Grace")
        assert metadata.tags == ("errands", "phone")

    def test_dates_are_calendar_dates(self) -> None:
        metadata = StepMetadata(
            plan=datetime.date(2026, 11, 20),
            actual=datetime.date(2026, 11, 14),
        )
        assert metadata.plan == datetime.date(2026, 11, 20)
        assert metadata.actual == datetime.date(2026, 11, 14)

    def test_waiting_follows_the_owner_list(self) -> None:
        assert not StepMetadata().is_waiting
        assert StepMetadata(owners=("Ada",)).is_waiting

    def test_raw_mapping_is_read_only(self) -> None:
        metadata = StepMetadata(raw={"priority": "high"})
        assert metadata.raw["priority"] == "high"
        with pytest.raises(TypeError):
            metadata.raw["priority"] = "low"  # type: ignore[index]

    def test_raw_mapping_is_copied(self) -> None:
        source = {"priority": "high"}
        metadata = StepMetadata(raw=source)
        source["priority"] = "low"
        assert metadata.raw["priority"] == "high"

    def test_value_object_is_frozen(self) -> None:
        metadata = StepMetadata()
        attribute_name = "plan"
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(metadata, attribute_name, datetime.date(2026, 11, 20))


class TestProjectStep:
    def test_fields_are_exposed(self) -> None:
        step = ProjectStep(text="Call the plumber", checked=False, line_index=LINE_INDEX)
        assert step.text == "Call the plumber"
        assert step.checked is False
        assert step.line_index == LINE_INDEX

    def test_metadata_defaults_to_empty(self) -> None:
        step = ProjectStep(text="Call the plumber", checked=False, line_index=0)
        assert step.metadata == StepMetadata()
        assert step.owners == ()
        assert step.plan is None
        assert step.actual is None
        assert step.tags == ()
        assert step.is_waiting is False

    def test_convenience_properties_read_the_metadata(self) -> None:
        metadata = StepMetadata(
            owners=("Ada",),
            plan=datetime.date(2026, 11, 20),
            tags=("phone",),
        )
        step = ProjectStep(text="Call the plumber", checked=True, line_index=2, metadata=metadata)
        assert step.owners == ("Ada",)
        assert step.plan == datetime.date(2026, 11, 20)
        assert step.tags == ("phone",)
        assert step.is_waiting is True

    def test_value_object_is_frozen(self) -> None:
        step = ProjectStep(text="Call the plumber", checked=False, line_index=0)
        attribute_name = "checked"
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(step, attribute_name, True)
