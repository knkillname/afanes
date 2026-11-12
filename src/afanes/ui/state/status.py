# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared message, busy, and session flags for the interface."""

import dataclasses
import logging

logger = logging.getLogger(__name__)


@dataclasses.dataclass(slots=True)
class UiStatus:
    """Cross-cutting status flags shared by the application collaborators.

    Attributes
    ----------
    message : str | None
        Banner text for the current error or warning.
    busy : bool
        Whether a blocking command is in progress.
    session_active : bool
        Whether a presentation session currently drives the workspace.
    """

    message: str | None = None
    busy: bool = False
    session_active: bool = False

    def show_message(self, message: str | None) -> None:
        """Show a banner message, or clear it when ``None``.

        Parameters
        ----------
        message : str | None
            Text to show, or ``None`` to leave the banner empty.
        """
        self.message = message

    def clear_message(self) -> None:
        """Clear the banner message."""
        self.message = None

    def set_busy(self, *, busy: bool) -> None:
        """Set the busy indicator.

        Parameters
        ----------
        busy : bool
            Whether a blocking command is in progress.
        """
        self.busy = busy

    def begin_session(self) -> bool:
        """Claim the single active workspace session.

        Returns
        -------
        bool
            ``True`` when this caller became the active session, ``False``
            when another session already holds it.
        """
        if self.session_active:
            return False
        self.session_active = True
        return True

    def release_session(self) -> None:
        """Release the active workspace session."""
        self.session_active = False

    def reset(self) -> None:
        """Return every flag to its initial value."""
        self.message = None
        self.busy = False
        self.session_active = False
