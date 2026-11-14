"""Tests for project step parsing and line-level rewriting."""

import datetime

import hypothesis
import hypothesis.strategies
import pytest

from afanes.core.errors import StepEditError, StepMetadataError
from afanes.core.steps import StepDocument

TODAY = datetime.date(2026, 11, 14)
PLAN = datetime.date(2026, 11, 20)
WARNING_LINE = 3


class TestParsing:
    def test_open_checkbox_becomes_a_step(self) -> None:
        document = StepDocument("- [ ] Call the plumber\n")

        assert len(document.steps) == 1
        assert document.steps[0].text == "Call the plumber"
        assert document.steps[0].checked is False

    def test_checked_item_is_complete(self) -> None:
        document = StepDocument("- [x] Call the plumber\n")

        assert document.steps[0].checked is True

    def test_no_task_item_produces_no_steps(self) -> None:
        document = StepDocument("# Project\n\nJust prose.\n")

        assert document.steps == ()

    def test_nested_items_are_steps_in_document_order(self) -> None:
        body = "- [x] Parent\n  - [ ] Child\n- [ ] Sibling\n"
        document = StepDocument(body)

        assert [step.text for step in document.steps] == ["Parent", "Child", "Sibling"]
        assert [step.line_index for step in document.steps] == [0, 1, 2]

    def test_checkbox_in_a_fenced_code_block_is_not_a_step(self) -> None:
        document = StepDocument("```\n- [ ] Not a step\n```\n")

        assert document.steps == ()

    def test_ordered_list_item_is_a_step(self) -> None:
        document = StepDocument("1. [ ] First\n")

        assert document.steps[0].text == "First"

    def test_crlf_terminators_are_accepted(self) -> None:
        document = StepDocument("- [ ] Call the plumber\r\n")

        assert document.steps[0].text == "Call the plumber"
        assert document.newline == "\r\n"


class TestMetadata:
    def test_trailing_plan_comment_is_metadata(self) -> None:
        document = StepDocument("- [ ] Call <!-- {plan: 2026-11-20} -->\n")

        step = document.steps[0]
        assert step.plan == PLAN
        assert step.text == "Call"

    def test_owners_are_listed(self) -> None:
        document = StepDocument("- [ ] Call <!-- {owners: [Ada Lovelace, Grace]} -->\n")

        assert document.steps[0].owners == ("Ada Lovelace", "Grace")
        assert document.steps[0].is_waiting is True

    def test_plan_and_actual_are_kept(self) -> None:
        document = StepDocument("- [ ] Call <!-- {plan: 2026-11-20, actual: 2026-11-14} -->\n")

        assert document.steps[0].plan == PLAN
        assert document.steps[0].actual == TODAY

    def test_tags_are_listed(self) -> None:
        document = StepDocument("- [ ] Call <!-- {tags: [errands, phone]} -->\n")

        assert document.steps[0].tags == ("errands", "phone")

    def test_empty_object_is_valid(self) -> None:
        document = StepDocument("- [ ] Call <!-- {} -->\n")

        step = document.steps[0]
        assert step.owners == ()
        assert step.plan is None
        assert step.actual is None
        assert step.tags == ()
        assert step.text == "Call"

    def test_text_after_the_comment_is_prose(self) -> None:
        document = StepDocument("- [ ] Call <!-- {plan: 2026-11-20} --> and more\n")

        step = document.steps[0]
        assert step.plan is None
        assert "and more" in step.text

    def test_comment_without_a_mapping_is_prose(self) -> None:
        document = StepDocument("- [ ] Call <!-- a note to self -->\n")

        step = document.steps[0]
        assert step.plan is None
        assert "a note to self" in step.text

    def test_only_the_last_comment_is_metadata(self) -> None:
        document = StepDocument("- [ ] Call <!-- first --> <!-- {plan: 2026-11-20} -->\n")

        step = document.steps[0]
        assert step.plan == PLAN
        assert "first" in step.text

    def test_unknown_keys_are_preserved(self) -> None:
        document = StepDocument("- [ ] Call <!-- {priority: high} -->\n")

        assert document.steps[0].metadata.raw["priority"] == "high"

    def test_invalid_date_drops_only_that_key(self) -> None:
        document = StepDocument("- [ ] Call <!-- {priority: high, plan: 2026-13-40} -->\n")

        step = document.steps[0]
        assert step.plan is None
        assert step.metadata.raw["priority"] == "high"
        assert len(document.warnings) == 1
        assert document.warnings[0].line_index == 0
        assert "YYYY-MM-DD" in document.warnings[0].message

    def test_broken_yaml_keeps_the_note_readable(self) -> None:
        document = StepDocument("- [ ] Call <!-- {plan: -->\n")

        assert document.steps[0].text == "Call"
        assert document.steps[0].plan is None
        assert len(document.warnings) == 1

    def test_warning_line_number_is_one_based(self) -> None:
        document = StepDocument("# Project\n\n- [ ] Call <!-- {plan: 2026-13-40} -->\n")

        assert document.warnings[0].line_number == WARNING_LINE


class TestRewriting:
    def test_tick_checks_the_step_and_records_today(self) -> None:
        document = StepDocument("- [ ] Call the plumber <!-- {plan: 2026-11-20} -->\n")
        rewritten = document.tick(document.steps[0], TODAY)

        assert rewritten == "- [x] Call the plumber <!-- {plan: 2026-11-20, actual: 2026-11-14} -->\n"

    def test_untick_removes_actual_and_keeps_plan(self) -> None:
        document = StepDocument("- [x] Call the plumber <!-- {plan: 2026-11-20, actual: 2026-11-14} -->\n")
        rewritten = document.untick(document.steps[0])

        assert rewritten == "- [ ] Call the plumber <!-- {plan: 2026-11-20} -->\n"

    def test_unknown_key_survives_a_tick(self) -> None:
        document = StepDocument("- [ ] Call <!-- {priority: high} -->\n")
        rewritten = document.tick(document.steps[0], TODAY)
        reparsed = StepDocument(rewritten)

        assert reparsed.steps[0].metadata.raw["priority"] == "high"
        assert reparsed.steps[0].actual == TODAY

    def test_setting_a_plan_date_adds_the_key(self) -> None:
        document = StepDocument("- [ ] Call\n")
        rewritten = document.with_plan(document.steps[0], PLAN)

        assert rewritten == "- [ ] Call <!-- {plan: 2026-11-20} -->\n"

    def test_removing_a_plan_date_drops_the_comment(self) -> None:
        document = StepDocument("- [ ] Call <!-- {plan: 2026-11-20} -->\n")
        rewritten = document.with_plan(document.steps[0], None)

        assert rewritten == "- [ ] Call\n"

    def test_replacing_owners(self) -> None:
        document = StepDocument("- [ ] Call <!-- {owners: [Ada]} -->\n")
        rewritten = document.with_owners(document.steps[0], ("Grace",))

        assert rewritten == "- [ ] Call <!-- {owners: [Grace]} -->\n"

    def test_clearing_owners_makes_the_step_own_again(self) -> None:
        document = StepDocument("- [ ] Call <!-- {owners: [Ada]} -->\n")
        rewritten = document.with_owners(document.steps[0], ())

        assert rewritten == "- [ ] Call\n"

    def test_rewrite_preserves_every_other_byte(self) -> None:
        body = "# Project\r\n\r\nIntro.\r\n\r\n- [ ] First\r\n- [ ] Second\r\n\r\nTrailing.\r\n"
        document = StepDocument(body)
        rewritten = document.tick(document.steps[1], TODAY)

        assert rewritten.startswith("# Project\r\n\r\nIntro.\r\n\r\n- [ ] First\r\n")
        assert "- [x] Second" in rewritten
        assert rewritten.endswith("\r\n\r\nTrailing.\r\n")

    def test_metadata_stays_on_one_line(self) -> None:
        owners = ("Ada Lovelace", "Grace Hopper", "Alan Turing", "Katherine Johnson", "Margaret Hamilton")
        document = StepDocument("- [ ] Call\n")
        rewritten = document.with_owners(document.steps[0], owners)
        line = rewritten.splitlines()[0]

        assert line.endswith(" -->")
        assert "<!--" in line
        assert "-->" in line
        assert "\n" not in line

    def test_double_dash_in_a_value_is_rejected(self) -> None:
        document = StepDocument("- [ ] Call\n")

        with pytest.raises(StepMetadataError, match="step-value-double-dash"):
            document.with_owners(document.steps[0], ("Ada--Grace",))

    def test_stale_step_line_raises(self) -> None:
        document = StepDocument("- [ ] Call\n")
        step = document.steps[0]
        edited = StepDocument("# Project\n")

        with pytest.raises(StepEditError):
            edited.tick(step, TODAY)


class TestAppend:
    def test_appends_an_unchecked_step(self) -> None:
        document = StepDocument("# Project\n")

        assert document.append("Call the plumber") == "# Project\n- [ ] Call the plumber\n"

    def test_appends_indented_detail(self) -> None:
        document = StepDocument("")

        rewritten = document.append("Call the plumber", "Ask about the boiler")

        assert rewritten == "- [ ] Call the plumber\n  Ask about the boiler\n"

    def test_blank_text_is_rejected(self) -> None:
        with pytest.raises(StepEditError):
            StepDocument("").append("   ")


class TestSearchText:
    def test_metadata_comment_is_removed(self) -> None:
        document = StepDocument("# Project\n\n- [ ] Call Ada <!-- {owners: [Ada], plan: 2026-11-20} -->\n")

        assert document.search_text == "# Project\n\n- [ ] Call Ada\n"

    def test_step_text_is_kept(self) -> None:
        document = StepDocument("- [ ] Call the plumber <!-- {plan: 2026-11-20} -->\n")

        assert "Call the plumber" in document.search_text
        assert "2026-11-20" not in document.search_text


@hypothesis.given(
    before=hypothesis.strategies.text(alphabet="abc \n#.-", max_size=40),
    step_text=hypothesis.strategies.text(alphabet="abc ", min_size=1, max_size=20),
    after=hypothesis.strategies.text(alphabet="abc \n#.-", max_size=40),
    priority=hypothesis.strategies.sampled_from(["high", "low", "medium"]),
)
def test_rewrite_round_trip_keeps_unrelated_lines(before: str, step_text: str, after: str, priority: str) -> None:
    step = step_text.strip()
    hypothesis.assume(step != "")
    hypothesis.assume("\n" not in step)
    body = f"{before}\n## Section\n- [ ] {step} <!-- {{priority: {priority}}} -->\n{after}\n"
    document = StepDocument(body)
    target = document.steps[0]

    ticked = document.tick(target, TODAY)
    ticked_document = StepDocument(ticked)
    unticked = ticked_document.untick(ticked_document.steps[0])

    original_lines = body.splitlines()
    for index, line in enumerate(original_lines):
        if index != target.line_index:
            assert ticked.splitlines()[index] == line
            assert unticked.splitlines()[index] == line
    assert step in unticked
    assert priority in unticked
    assert "actual" not in unticked
