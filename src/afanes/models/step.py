# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Immutable value objects for the steps inside a project body."""

import dataclasses
import datetime
from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class StepEditKind(StrEnum):
    """Metadata field changed by one page step edit.

    Attributes
    ----------
    PLAN : str
        The step's ``plan`` date.
    OWNERS : str
        The step's full ``owners`` list.
    """

    PLAN = "plan"
    OWNERS = "owners"


@dataclasses.dataclass(frozen=True, slots=True)
class StepEdit:
    """One requested change to a step's metadata.

    Attributes
    ----------
    line_index : int
        Zero-based body line of the step.
    kind : StepEditKind
        Field to change.
    plan : datetime.date | None
        New plan date when :attr:`kind` is :attr:`StepEditKind.PLAN`. ``None``
        clears the plan date.
    owners : tuple[str, ...]
        Complete owner list when :attr:`kind` is :attr:`StepEditKind.OWNERS`.
        An empty tuple clears the owners.
    """

    line_index: int
    kind: StepEditKind
    plan: datetime.date | None = None
    owners: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class StepMetadata:
    """Recognized metadata carried by one project step.

    Attributes
    ----------
    owners : tuple[str, ...]
        Owner names as written. A non-empty tuple means the step is waiting on
        those owners.
    plan : datetime.date | None
        Day the step was supposed to happen, or ``None`` when unplanned.
    actual : datetime.date | None
        Day the step was completed, or ``None`` while it is open.
    tags : tuple[str, ...]
        Free-form labels used only to filter the step list.
    raw : collections.abc.Mapping[str, object]
        Complete metadata mapping loaded from the trailing comment, including
        keys this object does not recognize. Rewrites re-emit it unchanged.

    Notes
    -----
    The value object is immutable. ``raw`` is exposed through a read-only
    mapping, but its nested values are the objects YAML produced.
    """

    owners: tuple[str, ...] = ()
    plan: datetime.date | None = None
    actual: datetime.date | None = None
    tags: tuple[str, ...] = ()
    raw: Mapping[str, object] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze the raw mapping so the value object stays immutable.

        Raises
        ------
        TypeError
            If ``raw`` is not a mapping.
        """
        if not isinstance(self.raw, Mapping):
            message = "Step metadata raw value must be a mapping"
            raise TypeError(message)
        object.__setattr__(self, "raw", MappingProxyType(dict(self.raw)))

    @property
    def is_waiting(self) -> bool:
        """Return whether the step waits on at least one owner.

        Returns
        -------
        bool
            ``True`` when :attr:`owners` is non-empty.
        """
        return bool(self.owners)


@dataclasses.dataclass(frozen=True, slots=True)
class ProjectStep:
    """One task list item in a project body.

    Attributes
    ----------
    text : str
        Step text without the list marker, checkbox, or metadata comment.
    checked : bool
        Whether the item is marked complete.
    line_index : int
        Zero-based line index of the item's first line in the project body.
    metadata : StepMetadata
        Parsed metadata, or an empty value when the item has none.

    Notes
    -----
    A step has no identity, filename, or catalog entry. It is reached only
    through the project whose body contains it.
    """

    text: str
    checked: bool
    line_index: int
    metadata: StepMetadata = dataclasses.field(default_factory=StepMetadata)

    @property
    def owners(self) -> tuple[str, ...]:
        """Return the owner names declared by this step.

        Returns
        -------
        tuple[str, ...]
            Owner names in written order.
        """
        return self.metadata.owners

    @property
    def plan(self) -> datetime.date | None:
        """Return the planned day, or ``None``.

        Returns
        -------
        datetime.date | None
            Planned calendar date.
        """
        return self.metadata.plan

    @property
    def actual(self) -> datetime.date | None:
        """Return the completed day, or ``None``.

        Returns
        -------
        datetime.date | None
            Actual completion date.
        """
        return self.metadata.actual

    @property
    def tags(self) -> tuple[str, ...]:
        """Return the step's free-form tags.

        Returns
        -------
        tuple[str, ...]
            Tags in written order.
        """
        return self.metadata.tags

    @property
    def is_waiting(self) -> bool:
        """Return whether the step is waiting on an owner.

        Returns
        -------
        bool
            ``True`` when the step declares at least one owner.
        """
        return self.metadata.is_waiting
