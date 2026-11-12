# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Split one project body into prose blocks and interactive step lists.

A project body renders twice in the page pane: ordinary Markdown prose and the
task list items that make up its steps. :class:`ProjectBody` locates top-level
CommonMark blocks, keeps prose verbatim, and groups a contiguous task list into
one :class:`StepListBlock`. Any shape that cannot be separated safely, such as
a mixed list or a task list inside a blockquote, stays a prose block so no
content is dropped or rewritten.
"""

import dataclasses
import textwrap

from markdown_it import MarkdownIt
from markdown_it.token import Token

import afanes.core.steps
from afanes.models.step import ProjectStep

_LIST_TYPES = frozenset({"bullet_list_open", "ordered_list_open"})


@dataclasses.dataclass(frozen=True, slots=True)
class ProseBlock:
    """One top-level Markdown block rendered verbatim.

    Attributes
    ----------
    source : str
        Exact source lines for the block, including their line terminators.
    start_line : int
        Zero-based first body line covered by the block.
    end_line : int
        Zero-based line after the last covered line.
    """

    source: str
    start_line: int
    end_line: int


@dataclasses.dataclass(frozen=True, slots=True)
class StepEntry:
    """One task list item inside a step-list block.

    Attributes
    ----------
    step : ProjectStep
        Parsed step, including its text, checked state, and metadata.
    depth : int
        Zero-based nesting depth. A top-level item has depth ``0``.
    detail : str
        Markdown written beneath the step, excluding nested task items, with
        the item indentation removed.
    """

    step: ProjectStep
    depth: int
    detail: str


@dataclasses.dataclass(frozen=True, slots=True)
class StepListBlock:
    """One contiguous task list rendered as a card of step rows.

    Attributes
    ----------
    entries : tuple[StepEntry, ...]
        Steps in document order.
    start_line : int
        Zero-based first body line covered by the block.
    end_line : int
        Zero-based line after the last covered line.
    """

    entries: tuple[StepEntry, ...]
    start_line: int
    end_line: int


type BodyBlock = ProseBlock | StepListBlock


@dataclasses.dataclass(frozen=True, slots=True)
class _BlockSpec:
    """One top-level block before its final source range is assigned."""

    start_line: int
    end_line: int
    entries: tuple[StepEntry, ...] | None


@dataclasses.dataclass(frozen=True, slots=True)
class ProjectBody:
    """A project body split into ordered prose and step-list blocks.

    Parameters
    ----------
    body : str
        Project body without frontmatter. LF, CRLF, and mixed newlines are
        preserved in prose sources.

    Attributes
    ----------
    body : str
        Body exactly as supplied to the constructor.

    Notes
    -----
    Parsing is read-only and uses the same CommonMark parser as
    :class:`afanes.core.steps.StepDocument`. A top-level list becomes a
    step-list block only when every list item in it, including nested items, is
    a task list item. Every other top-level block stays prose.
    """

    body: str
    _lines: tuple[str, ...] = dataclasses.field(init=False, repr=False)
    _blocks: tuple[BodyBlock, ...] = dataclasses.field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Split the body once and cache the blocks."""
        lines = tuple(self.body.splitlines(keepends=True))
        object.__setattr__(self, "_lines", lines)
        object.__setattr__(self, "_blocks", self._split(lines))

    @property
    def blocks(self) -> tuple[BodyBlock, ...]:
        """Return every block in source order.

        Returns
        -------
        tuple[ProseBlock | StepListBlock, ...]
            Blocks whose line ranges partition the body exactly once.
        """
        return self._blocks

    @property
    def steps(self) -> tuple[StepEntry, ...]:
        """Return every step entry across the body.

        Returns
        -------
        tuple[StepEntry, ...]
            Steps in document order, including nested items.
        """
        entries: list[StepEntry] = []
        for block in self._blocks:
            if isinstance(block, StepListBlock):
                entries.extend(block.entries)
        return tuple(entries)

    def _split(self, lines: tuple[str, ...]) -> tuple[BodyBlock, ...]:
        """Build the ordered blocks for one body."""
        if not lines:
            return ()
        tokens = MarkdownIt("commonmark").parse(self.body)
        steps = {step.line_index: step for step in afanes.core.steps.StepDocument(self.body).steps}
        specs: list[_BlockSpec] = []
        for token in tokens:
            if token.level != 0 or token.map is None:
                continue
            start_line, end_line = token.map
            if token.type in _LIST_TYPES:
                entries = self._step_entries(tokens, start_line, end_line, steps)
                if entries is not None:
                    specs.append(_BlockSpec(start_line=start_line, end_line=end_line, entries=entries))
                    continue
            specs.append(_BlockSpec(start_line=start_line, end_line=end_line, entries=None))
        if not specs:
            return (ProseBlock(source=self.body, start_line=0, end_line=len(lines)),)
        return self._assign_ranges(self._merge_step_lists(specs, lines), lines)

    def _merge_step_lists(self, specs: list[_BlockSpec], lines: tuple[str, ...]) -> list[_BlockSpec]:
        """Join adjacent step lists separated only by blank lines."""
        merged: list[_BlockSpec] = []
        for spec in specs:
            previous = merged[-1] if merged else None
            if (
                previous is not None
                and previous.entries is not None
                and spec.entries is not None
                and self._blank_between(previous.end_line, spec.start_line, lines)
            ):
                merged[-1] = _BlockSpec(
                    start_line=previous.start_line,
                    end_line=spec.end_line,
                    entries=(*previous.entries, *spec.entries),
                )
            else:
                merged.append(spec)
        return merged

    @staticmethod
    def _blank_between(start: int, end: int, lines: tuple[str, ...]) -> bool:
        """Return whether every line in a range is blank."""
        return all(not lines[index].strip() for index in range(start, end))

    def _assign_ranges(
        self,
        specs: list[_BlockSpec],
        lines: tuple[str, ...],
    ) -> tuple[BodyBlock, ...]:
        """Assign every body line to exactly one block."""
        blocks: list[BodyBlock] = []
        previous_end = 0
        last_index = len(specs) - 1
        for index, spec in enumerate(specs):
            end_line = len(lines) if index == last_index else spec.end_line
            if spec.entries is None:
                blocks.append(
                    ProseBlock(
                        source="".join(lines[previous_end:end_line]),
                        start_line=previous_end,
                        end_line=end_line,
                    )
                )
            else:
                blocks.append(
                    StepListBlock(
                        entries=spec.entries,
                        start_line=previous_end,
                        end_line=end_line,
                    )
                )
            previous_end = end_line
        return tuple(blocks)

    def _step_entries(
        self,
        tokens: list[Token],
        start_line: int,
        end_line: int,
        steps: dict[int, ProjectStep],
    ) -> tuple[StepEntry, ...] | None:
        """Return step entries when every list item is a task item."""
        items = [
            token
            for token in tokens
            if token.type == "list_item_open" and token.map is not None and start_line <= token.map[0] < end_line
        ]
        if not items:
            return None
        if any(item.map is None or item.map[0] not in steps for item in items):
            return None
        entries: list[StepEntry] = []
        for item in items:
            item_map = item.map
            if item_map is None:
                return None
            item_start, item_end = item_map
            step = steps[item_start]
            depth = max(0, (item.level - 1) // 2)
            entries.append(
                StepEntry(
                    step=step,
                    depth=depth,
                    detail=self._detail_for(item_start, item_end, items),
                )
            )
        return tuple(entries)

    def _detail_for(self, start_line: int, end_line: int, items: list[Token]) -> str:
        """Return the Markdown written directly beneath one list item."""
        excluded: list[tuple[int, int]] = []
        for other in items:
            other_map = other.map
            if other_map is None:
                continue
            other_start, other_end = other_map
            if start_line < other_start and other_end <= end_line:
                excluded.append((other_start, other_end))
        pieces: list[str] = []
        for index in range(start_line + 1, end_line):
            if any(excluded_start <= index < excluded_end for excluded_start, excluded_end in excluded):
                continue
            pieces.append(self._lines[index].rstrip("\r\n"))
        if not pieces:
            return ""
        return textwrap.dedent("\n".join(pieces)).strip("\n")
