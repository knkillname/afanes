"""Tests for splitting a project body into prose and step-list blocks."""

import hypothesis
import hypothesis.strategies

from afanes.core.project_body import ProjectBody, ProseBlock, StepListBlock


def _steps(block: object) -> list[str]:
    assert isinstance(block, StepListBlock)
    return [entry.step.text for entry in block.entries]


class TestBlockOrder:
    def test_prose_and_steps_keep_document_order(self) -> None:
        body = "# Home\n\nIntro.\n\n- [ ] One\n- [ ] Two\n\nDone.\n"

        blocks = ProjectBody(body).blocks

        assert [type(block) for block in blocks] == [ProseBlock, ProseBlock, StepListBlock, ProseBlock]
        assert isinstance(blocks[0], ProseBlock)
        assert isinstance(blocks[1], ProseBlock)
        assert isinstance(blocks[3], ProseBlock)
        assert "# Home" in blocks[0].source
        assert "Intro." in blocks[1].source
        assert _steps(blocks[2]) == ["One", "Two"]
        assert "Done." in blocks[3].source

    def test_contiguous_task_list_is_one_card(self) -> None:
        body = "- [ ] One\n\n- [ ] Two\n"

        blocks = ProjectBody(body).blocks

        assert len(blocks) == 1
        assert _steps(blocks[0]) == ["One", "Two"]

    def test_adjacent_lists_with_blank_lines_merge(self) -> None:
        body = "- [ ] One\n\n1. [ ] Two\n"

        blocks = ProjectBody(body).blocks

        assert len(blocks) == 1
        assert _steps(blocks[0]) == ["One", "Two"]

    def test_a_project_with_no_steps_is_all_prose(self) -> None:
        body = "# Project\n\nJust prose.\n"

        blocks = ProjectBody(body).blocks

        assert all(isinstance(block, ProseBlock) for block in blocks)
        prose = [block for block in blocks if isinstance(block, ProseBlock)]
        assert "".join(block.source for block in prose) == body

    def test_empty_body_has_no_blocks(self) -> None:
        assert ProjectBody("").blocks == ()


class TestStepDetail:
    def test_nested_items_keep_their_depth(self) -> None:
        body = "- [x] Parent\n  - [ ] Child\n- [ ] Sibling\n"

        block = ProjectBody(body).blocks[0]

        assert isinstance(block, StepListBlock)
        assert [(entry.step.text, entry.depth) for entry in block.entries] == [
            ("Parent", 0),
            ("Child", 1),
            ("Sibling", 0),
        ]

    def test_indented_detail_belongs_to_its_step(self) -> None:
        body = "- [ ] Parent\n  Ask about the boiler\n  - [ ] Child\n    Child detail\n"

        block = ProjectBody(body).blocks[0]

        assert isinstance(block, StepListBlock)
        assert [entry.detail for entry in block.entries] == ["Ask about the boiler", "Child detail"]

    def test_step_metadata_is_parsed(self) -> None:
        body = "- [ ] Call <!-- {owners: [Ada], plan: 2026-11-20, tags: [phone]} -->\n"

        block = ProjectBody(body).blocks[0]

        assert isinstance(block, StepListBlock)
        step = block.entries[0].step
        assert step.owners == ("Ada",)
        assert step.plan is not None
        assert step.tags == ("phone",)


class TestFallback:
    def test_mixed_list_stays_prose(self) -> None:
        body = "- [ ] Task\n- Not a task\n"

        blocks = ProjectBody(body).blocks

        assert len(blocks) == 1
        assert isinstance(blocks[0], ProseBlock)
        assert blocks[0].source == body

    def test_blockquote_stays_prose(self) -> None:
        body = "> - [ ] Task\n"

        blocks = ProjectBody(body).blocks

        assert isinstance(blocks[0], ProseBlock)
        assert blocks[0].source == body

    def test_fenced_code_stays_prose(self) -> None:
        body = "```\n- [ ] Task\n```\n"

        blocks = ProjectBody(body).blocks

        assert isinstance(blocks[0], ProseBlock)
        assert blocks[0].source == body

    def test_table_stays_prose(self) -> None:
        body = "| a | b |\n| - | - |\n| 1 | 2 |\n"

        blocks = ProjectBody(body).blocks

        assert isinstance(blocks[0], ProseBlock)
        assert blocks[0].source == body


@hypothesis.given(body=hypothesis.strategies.text(alphabet="abc \n\r#-*[]x`>|", max_size=200))
def test_block_ranges_partition_every_line(body: str) -> None:
    blocks = ProjectBody(body).blocks

    lines = body.splitlines(keepends=True)
    if not lines:
        assert blocks == ()
        return
    position = 0
    for block in blocks:
        assert block.start_line == position
        position = block.end_line
    assert position == len(lines)


def test_crlf_prose_round_trips() -> None:
    body = "# Project\r\n\r\nIntro.\r\n"

    blocks = ProjectBody(body).blocks

    assert "".join(block.source for block in blocks if isinstance(block, ProseBlock)) == body


def test_lf_prose_round_trips() -> None:
    body = "# Project\n\nIntro.\n"

    blocks = ProjectBody(body).blocks

    assert "".join(block.source for block in blocks if isinstance(block, ProseBlock)) == body
