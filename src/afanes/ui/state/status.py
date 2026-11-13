# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared notice, busy, and session flags for the interface."""

import dataclasses
import logging
from enum import StrEnum

logger = logging.getLogger(__name__)


class NoticeAction(StrEnum):
    """Reversible action offered by a transient notice.

    Attributes
    ----------
    UNDO_TRASH : str
        Restore the note the current session just moved to trash.
    """

    UNDO_TRASH = "undo-trash"


@dataclasses.dataclass(frozen=True, slots=True)
class Notice:
    """One transient message for the interface.

    Attributes
    ----------
    message : str
        Short text shown to the user.
    action : NoticeAction | None
        Optional reversible action offered beside the message.
    """

    message: str
    action: NoticeAction | None = None


@dataclasses.dataclass(slots=True)
class UiStatus:
    """Cross-cutting status flags shared by the application collaborators.

    Attributes
    ----------
    notice : Notice | None
        Latest transient notice waiting for a view to consume it.
    busy : bool
        Whether a blocking command is in progress.
    session_active : bool
        Whether a presentation session currently drives the workspace.
    """

    notice: Notice | None = None
    busy: bool = False
    session_active: bool = False

    def show_notice(self, message: str, action: NoticeAction | None = None) -> None:
        """Store the latest transient notice, replacing any earlier one.

        Parameters
        ----------
        message : str
            Short text shown to the user.
        action : NoticeAction | None
            Optional reversible action offered beside the message.

        Notes
        -----
        Toasts are transient, so they do not need a queue. A second notice
        replaces the first and the latest one wins.
        """
        self.notice = Notice(message=message, action=action)

    def take_notice(self) -> Notice | None:
        """Return the waiting notice and clear it.

        Returns
        -------
        Notice | None
            The latest notice, or ``None`` when no notice is waiting.

        Notes
        -----
        A view consumes the notice once. Taking it makes the toast the only
        owner of the message, so a later repaint cannot show it twice.
        """
        notice = self.notice
        self.notice = None
        return notice

    def clear_notice(self) -> None:
        """Discard the waiting notice without showing it."""
        self.notice = None

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
        self.notice = None
        self.busy = False
        self.session_active = False
