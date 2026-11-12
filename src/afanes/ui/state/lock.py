# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared command lock that serializes vault work across the controllers."""

import asyncio
import dataclasses
from types import TracebackType
from typing import Self


@dataclasses.dataclass(slots=True)
class CommandLock:
    """Serialize commands so two writes never target the same vault at once.

    Attributes
    ----------
    _lock : asyncio.Lock
        Underlying lock for the current event loop.
    """

    _lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)

    async def __aenter__(self) -> Self:
        """Acquire the command lock.

        Returns
        -------
        CommandLock
            This lock, after acquisition.
        """
        await self._lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release the command lock.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type raised inside the context, if any.
        exc_value : BaseException | None
            Exception instance raised inside the context, if any.
        traceback : types.TracebackType | None
            Traceback raised inside the context, if any.
        """
        self._lock.release()

    def locked(self) -> bool:
        """Return whether a command currently holds the lock.

        Returns
        -------
        bool
            ``True`` while another command is running.
        """
        return self._lock.locked()

    def replace(self) -> None:
        """Replace the underlying lock for the next event loop."""
        self._lock = asyncio.Lock()
