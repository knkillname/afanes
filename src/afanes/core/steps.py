# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Parse and rewrite the checkbox steps inside one project body.

:class:`StepDocument` owns a Markdown body. It locates task list items through
the CommonMark parser, reads optional trailing metadata comments, and rewrites
only the affected line. Every transformation returns a new body; the original
string is never mutated.
"""

import dataclasses
import datetime
import re
from collections.abc import Iterable

import yaml
from markdown_it import MarkdownIt
from yaml import YAMLError

from afanes.core.errors import StepEditError, StepMetadataError
from afanes.models.step import ProjectStep, StepMetadata

_TASK_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>[-*+]|\d{1,9}[.)])(?P<gap>[ \t]+)"
    r"\[(?P<check>[ xX])\](?P<rest>.*)$",
)
_DATE_SCALAR_PATTERN = re.compile(r"(?<![\w'\"])(\d{4}-\d{1,2}-\d{1,2})(?![\w'\"])")
_METADATA_WIDTH = 10_000
# Public keys recognized in a step metadata comment.
STEP_METADATA_KEYS = frozenset({"owners", "plan", "actual", "tags"})


@dataclasses.dataclass(frozen=True, slots=True)
class StepWarning:
    """One readable note problem tied to a project body line.

    Attributes
    ----------
    line_index : int
        Zero-based line index in the project body.
    message : str
        Actionable description of the ignored value.
    """

    line_index: int
    message: str

    @property
    def line_number(self) -> int:
        """Return the one-based line number for display.

        Returns
        -------
        int
            ``line_index + 1``.
        """
        return self.line_index + 1


@dataclasses.dataclass(frozen=True, slots=True)
class _ParsedLine:
    """One task list item located in the body."""

    step: ProjectStep
    has_metadata: bool
    warning: StepWarning | None


class StepDocument:
    """A Markdown body that owns its task list items.

    Parameters
    ----------
    body : str
        Project body without frontmatter. LF, CRLF, and mixed newlines are
        preserved by every rewrite.

    Notes
    -----
    Parsing is read-only. The CommonMark parser locates list items, so a
    checkbox inside a fenced or indented code block is not a step. Rewrites
    replace one line and leave every other byte untouched.
    """

    def __init__(self, body: str) -> None:
        """Store the body this document owns.

        Parameters
        ----------
        body : str
            Project body without frontmatter.
        """
        self._body = body
        self._newline = "\r\n" if "\r\n" in body else "\n"

    @property
    def body(self) -> str:
        """Return the complete body text.

        Returns
        -------
        str
            Body exactly as supplied to the constructor.
        """
        return self._body

    @property
    def newline(self) -> str:
        r"""Return the dominant newline sequence.

        Returns
        -------
        str
            ``\\r\\n`` when the body contains it, otherwise ``\\n``.
        """
        return self._newline

    @property
    def steps(self) -> tuple[ProjectStep, ...]:
        """Return every task list item in document order.

        Returns
        -------
        tuple[ProjectStep, ...]
            Steps identified by line index. Nested items are included in the
            order the parser emits them.
        """
        return tuple(parsed.step for parsed in self._parsed_lines())

    @property
    def warnings(self) -> tuple[StepWarning, ...]:
        """Return the warnings produced while reading metadata.

        Returns
        -------
        tuple[StepWarning, ...]
            One warning for each line whose metadata was only partly readable,
            in document order.
        """
        return tuple(parsed.warning for parsed in self._parsed_lines() if parsed.warning is not None)

    @property
    def search_text(self) -> str:
        """Return the body with metadata comments removed.

        Returns
        -------
        str
            Body text that keeps step prose while dropping the trailing
            metadata comment from every step line.
        """
        lines = self._body.splitlines(keepends=True)
        for parsed in self._parsed_lines():
            if not parsed.has_metadata:
                continue
            line = lines[parsed.step.line_index]
            replacement = self._line_without_metadata(line, parsed.step.text)
            if replacement is not None:
                lines[parsed.step.line_index] = replacement
        return "".join(lines)

    def tick(self, step: ProjectStep, completed_on: datetime.date) -> str:
        """Return a body with one step checked and its actual date recorded.

        Parameters
        ----------
        step : ProjectStep
            Step to complete. It must come from this document.
        completed_on : datetime.date
            Calendar date written as ``actual``.

        Returns
        -------
        str
            New body with only the step line changed.

        Raises
        ------
        StepEditError
            If the step line no longer matches the document.
        StepMetadataError
            If the metadata cannot be written as one valid HTML comment.
        """
        raw = dict(step.metadata.raw)
        raw["actual"] = completed_on
        return self._rewrite(step, checked=True, raw=raw)

    def untick(self, step: ProjectStep) -> str:
        """Return a body with one step unchecked and its actual date removed.

        Parameters
        ----------
        step : ProjectStep
            Step to reopen. It must come from this document.

        Returns
        -------
        str
            New body with only the step line changed. ``plan`` is preserved.

        Raises
        ------
        StepEditError
            If the step line no longer matches the document.
        StepMetadataError
            If the metadata cannot be written as one valid HTML comment.
        """
        raw = dict(step.metadata.raw)
        raw.pop("actual", None)
        return self._rewrite(step, checked=False, raw=raw)

    def with_plan(self, step: ProjectStep, plan: datetime.date | None) -> str:
        """Return a body with one step's plan date replaced or removed.

        Parameters
        ----------
        step : ProjectStep
            Step to update. It must come from this document.
        plan : datetime.date | None
            New plan date, or ``None`` to remove the key.

        Returns
        -------
        str
            New body with only the step line changed.

        Raises
        ------
        StepEditError
            If the step line no longer matches the document.
        StepMetadataError
            If the metadata cannot be written as one valid HTML comment.
        """
        raw = dict(step.metadata.raw)
        if plan is None:
            raw.pop("plan", None)
        else:
            raw["plan"] = plan
        return self._rewrite(step, checked=step.checked, raw=raw)

    def with_owners(self, step: ProjectStep, owners: Iterable[str]) -> str:
        """Return a body with one step's owner list replaced.

        Parameters
        ----------
        step : ProjectStep
            Step to update. It must come from this document.
        owners : Iterable[str]
            Owner names. Whitespace-only entries are dropped and order is
            preserved. An empty result removes the ``owners`` key, so the step
            becomes the user's own work again.

        Returns
        -------
        str
            New body with only the step line changed.

        Raises
        ------
        StepEditError
            If the step line no longer matches the document.
        StepMetadataError
            If the metadata cannot be written as one valid HTML comment.
        """
        cleaned = tuple(name.strip() for name in owners if name.strip())
        raw = dict(step.metadata.raw)
        if cleaned:
            raw["owners"] = list(cleaned)
        else:
            raw.pop("owners", None)
        return self._rewrite(step, checked=step.checked, raw=raw)

    def append(self, text: str, detail: str = "") -> str:
        """Return a body with one unchecked step appended.

        Parameters
        ----------
        text : str
            Step text. Only the first non-blank line becomes the step; any
            remaining lines are treated as detail.
        detail : str
            Optional prose written beneath the step, indented by two spaces.

        Returns
        -------
        str
            New body with the task list item appended at the end.

        Raises
        ------
        StepEditError
            If the step text is blank.
        """
        lines = text.strip().splitlines()
        if not lines:
            message = "A step needs text"
            raise StepEditError(message)
        step_text = lines[0].strip()
        extra_detail = "\n".join(part for part in (*lines[1:],) if part.strip())
        detail_text = "\n".join(part for part in (extra_detail, detail.strip()) if part)
        additions = [f"- [ ] {step_text}"]
        if detail_text:
            additions.extend(f"  {line}" if line.strip() else "" for line in detail_text.splitlines())
        body = self._body
        if body and not body.endswith(("\n", "\r")):
            body = f"{body}{self._newline}"
        block = self._newline.join(additions)
        return f"{body}{block}{self._newline}"

    def _parsed_lines(self) -> tuple[_ParsedLine, ...]:
        """Return every task list item located by the CommonMark parser."""
        lines = self._body.splitlines()
        parsed: list[_ParsedLine] = []
        for token in MarkdownIt("commonmark").parse(self._body):
            if token.type != "list_item_open" or token.map is None:
                continue
            start = token.map[0]
            if start < 0 or start >= len(lines):
                continue
            item = self._parse_line(lines[start], start)
            if item is not None:
                parsed.append(item)
        return tuple(parsed)

    def _parse_line(self, line: str, line_index: int) -> _ParsedLine | None:
        """Parse one line as a task list item, or return ``None``."""
        match = _TASK_PATTERN.match(line.rstrip("\r\n"))
        if match is None:
            return None
        rest = match.group("rest")
        metadata, text, has_metadata, warning = self._read_comment(rest, line_index)
        step = ProjectStep(
            text=text,
            checked=match.group("check") in {"x", "X"},
            line_index=line_index,
            metadata=metadata,
        )
        return _ParsedLine(step=step, has_metadata=has_metadata, warning=warning)

    def _read_comment(
        self,
        rest: str,
        line_index: int,
    ) -> tuple[StepMetadata, str, bool, StepWarning | None]:
        """Read a trailing metadata comment from one item's content."""
        trimmed = rest.rstrip()
        if not trimmed.endswith("-->"):
            return StepMetadata(), rest.strip(), False, None
        opening = trimmed.rfind("<!--")
        if opening < 0:
            return StepMetadata(), rest.strip(), False, None
        inner = trimmed[opening + 4 : -3]
        text = trimmed[:opening].strip()
        loaded = self._load_mapping(inner)
        if loaded is None:
            warning = StepWarning(line_index=line_index, message="The step metadata is not valid YAML and was ignored")
            return StepMetadata(), text, True, warning
        if not isinstance(loaded, dict):
            return StepMetadata(), rest.strip(), False, None
        return self._metadata_from_mapping(loaded, text, line_index)

    def _load_mapping(self, source: str) -> object:
        """Load a metadata comment with safe YAML, salvaging invalid dates."""
        try:
            return yaml.safe_load(source)
        except (YAMLError, ValueError, TypeError):
            pass
        try:
            return yaml.safe_load(_DATE_SCALAR_PATTERN.sub(r"'\1'", source))
        except (YAMLError, ValueError, TypeError):
            return None

    def _metadata_from_mapping(
        self,
        loaded: dict[object, object],
        text: str,
        line_index: int,
    ) -> tuple[StepMetadata, str, bool, StepWarning | None]:
        """Validate a loaded mapping, dropping only invalid known keys."""
        raw: dict[str, object] = {}
        warnings: list[StepWarning] = []
        for key, value in loaded.items():
            if not isinstance(key, str):
                warnings.append(
                    StepWarning(line_index=line_index, message="A metadata key is not a string and was ignored")
                )
                continue
            raw[key] = value

        owners = self._read_names(raw, "owners", line_index, warnings)
        tags = self._read_names(raw, "tags", line_index, warnings)
        plan = self._read_date(raw, "plan", line_index, warnings)
        actual = self._read_date(raw, "actual", line_index, warnings)
        warning = warnings[0] if warnings else None
        metadata = StepMetadata(
            owners=owners,
            plan=plan,
            actual=actual,
            tags=tags,
            raw=raw,
        )
        return metadata, text, True, warning

    def _read_names(
        self,
        raw: dict[str, object],
        key: str,
        line_index: int,
        warnings: list[StepWarning],
    ) -> tuple[str, ...]:
        """Read an optional list-of-names key, dropping it when invalid."""
        if key not in raw:
            return ()
        value = raw[key]
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return tuple(item.strip() for item in value if item.strip())
        raw.pop(key, None)
        warnings.append(
            StepWarning(line_index=line_index, message=f"The step {key} must be a list of names and was ignored")
        )
        return ()

    def _read_date(
        self,
        raw: dict[str, object],
        key: str,
        line_index: int,
        warnings: list[StepWarning],
    ) -> datetime.date | None:
        """Read an optional ISO date key, dropping it when invalid."""
        if key not in raw:
            return None
        value = raw[key]
        normalized = self._normalize_date(value)
        if normalized is None:
            raw.pop(key, None)
            warning = StepWarning(
                line_index=line_index,
                message=f"The step {key} date must be written as YYYY-MM-DD and was ignored",
            )
            warnings.append(warning)
            return None
        raw[key] = normalized
        return normalized

    @staticmethod
    def _normalize_date(value: object) -> datetime.date | None:
        """Return a calendar date for an ISO value, or ``None``."""
        if isinstance(value, datetime.datetime):
            return None
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, str):
            try:
                return datetime.date.fromisoformat(value.strip())
            except ValueError:
                return None
        return None

    def _rewrite(self, step: ProjectStep, *, checked: bool, raw: dict[str, object]) -> str:
        """Replace one step line with a new checkbox and metadata comment."""
        lines = self._body.splitlines(keepends=True)
        if step.line_index < 0 or step.line_index >= len(lines):
            message = "The step line no longer exists in this project"
            raise StepEditError(message)
        line = lines[step.line_index]
        match = _TASK_PATTERN.match(line.rstrip("\r\n"))
        if match is None:
            message = "The line changed and is no longer a task list item"
            raise StepEditError(message)
        ending = self._line_ending(line)
        comment = self._comment_for(raw)
        gap = match.group("gap")
        suffix = f" {comment}" if comment else ""
        replacement = (
            f"{match.group('indent')}{match.group('marker')}{gap}"
            f"[{'x' if checked else ' '}] {step.text}{suffix}{ending}"
        )
        lines[step.line_index] = replacement
        return "".join(lines)

    def _comment_for(self, raw: dict[str, object]) -> str:
        """Serialize metadata as one valid trailing HTML comment, or empty."""
        if not raw:
            return ""
        try:
            serialized = yaml.safe_dump(
                dict(raw),
                default_flow_style=True,
                allow_unicode=True,
                sort_keys=False,
                width=_METADATA_WIDTH,
            )
        except YAMLError as exc:
            message = "The step metadata could not be written as YAML"
            raise StepMetadataError(message) from exc
        serialized = " ".join(serialized.splitlines()).strip()
        if not serialized:
            return ""
        if "--" in serialized:
            message = "A step value contains '--', which cannot appear inside an HTML comment; rename the value first"
            raise StepMetadataError(message)
        return f"<!-- {serialized} -->"

    @staticmethod
    def _line_ending(line: str) -> str:
        """Return one line's terminator, or an empty string."""
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith(("\n", "\r")):
            return line[-1]
        return ""

    def _line_without_metadata(self, line: str, text: str) -> str | None:
        """Return a step line with its metadata comment removed."""
        match = _TASK_PATTERN.match(line.rstrip("\r\n"))
        if match is None:
            return None
        ending = self._line_ending(line)
        return f"{match.group('indent')}{match.group('marker')}{match.group('gap')}[{'x' if match.group('check') in {'x', 'X'} else ' '}] {text}{ending}"

    def with_metadata(self, step: ProjectStep, raw: dict[str, object]) -> str:
        """Return a body with one step's metadata mapping replaced verbatim.

        Parameters
        ----------
        step : ProjectStep
            Step to update. It must come from this document.
        raw : dict[str, object]
            Complete metadata mapping to write, including unknown keys.

        Returns
        -------
        str
            New body with only the step line changed.

        Raises
        ------
        StepEditError
            If the step line no longer matches the document.
        StepMetadataError
            If the metadata cannot be written as one valid HTML comment.
        """
        return self._rewrite(step, checked=step.checked, raw=raw)
