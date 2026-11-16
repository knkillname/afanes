# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Live-region wrapper for messages that appear without a focus change."""

import flet as ft


class LiveRegion:
    """One live region whose visible text is the announced message.

    Parameters
    ----------
    content : flet.Control
        Message surface. Its visible text supplies the accessible name.
    """

    def __init__(self, content: ft.Control) -> None:
        """Store the message surface.

        Parameters
        ----------
        content : flet.Control
            Message surface shown to the user.
        """
        self._content = content

    def build(self) -> ft.Semantics:
        """Build the live region around the message surface.

        Returns
        -------
        ft.Semantics
            Live region carrying the visible message.
        """
        return ft.Semantics(live_region=True, content=self._content)
