# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Display label for one workflow status."""

import afanes.core.search
import afanes.i18n.ui
from afanes.models.note import Status


class StatusLabel:
    """Text shown for a workflow status.

    Parameters
    ----------
    status : Status | None
        Status to display, or ``None`` for an unstarted project.
    """

    def __init__(
        self,
        status: Status | None,
        *,
        copy: afanes.i18n.ui.UiCopy | None = None,
    ) -> None:
        """Store the status this label displays.

        Parameters
        ----------
        status : Status | None
            Status to display, or ``None`` for an unstarted project.
        """
        self._copy = afanes.i18n.ui.UiCopy.english() if copy is None else copy
        self._status = status

    @property
    def text(self) -> str:
        """Return the human-readable status label.

        Returns
        -------
        str
            Localized label for the status, or the active project label when
            the status is absent.
        """
        if self._status is None:
            return self._copy.PROJECT_GROUP_LABELS[afanes.core.search.ProjectStage.ACTIVE.value]
        return self._copy.PROCESSING_STATUS_LABELS[self._status.value]
