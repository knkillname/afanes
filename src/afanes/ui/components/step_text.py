# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only Markdown renderer for one step's text.

The component wraps Flet's Markdown control with the compact spacing and
GitHub-flavored extension set that step lines use, so the project page, review
cards, and project rows share one rendering path. It performs no parsing and no
vault I/O.
"""

from collections.abc import Awaitable, Callable

import flet as ft

type LinkHandler = Callable[[ft.Event[ft.Markdown]], Awaitable[None]]


class StepText:
    """One step text rendered as inline Markdown.

    Parameters
    ----------
    text : str
        Step text exactly as written in the note.
    text_style : flet.TextStyle
        Paragraph style for the surface that shows the step.
    selectable : bool
        Whether the rendered text can be selected, by default ``False``.
    expand : bool
        Whether the control fills the available horizontal space, by default
        ``False``.
    on_tap_link : LinkHandler | None
        Command that resolves a tapped link, or ``None`` when links are
        display-only.
    underline_links : bool
        Whether link text is underlined, by default ``True``.
    key : str | None
        Stable control key, or ``None`` for no key.
    """

    def __init__(
        self,
        text: str,
        text_style: ft.TextStyle,
        *,
        selectable: bool = False,
        expand: bool = False,
        on_tap_link: LinkHandler | None = None,
        underline_links: bool = True,
        key: str | None = None,
    ) -> None:
        """Store the step text and its surface options.

        Parameters
        ----------
        text : str
            Step text exactly as written in the note.
        text_style : flet.TextStyle
            Paragraph style for the surface that shows the step.
        selectable : bool
            Whether the rendered text can be selected, by default ``False``.
        expand : bool
            Whether the control fills the available horizontal space, by
            default ``False``.
        on_tap_link : LinkHandler | None
            Command that resolves a tapped link, or ``None`` when links are
            display-only.
        underline_links : bool
            Whether link text is underlined, by default ``True``.
        key : str | None
            Stable control key, or ``None`` for no key.
        """
        self._text = text
        self._text_style = text_style
        self._selectable = selectable
        self._expand = expand
        self._on_tap_link = on_tap_link
        self._underline_links = underline_links
        self._key = key

    def build(self) -> ft.Markdown:
        """Build the rendered Markdown control.

        Returns
        -------
        ft.Markdown
            GitHub-flavored Markdown with compact paragraph spacing and a link
            style derived from the paragraph style.
        """
        return ft.Markdown(
            value=self._text,
            selectable=self._selectable,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            auto_follow_links=False,
            on_tap_link=self._on_tap_link,
            expand=self._expand,
            key=self._key,
            md_style_sheet=ft.MarkdownStyleSheet(
                p_text_style=self._text_style,
                a_text_style=(
                    self._text_style.copy(decoration=ft.TextDecoration.UNDERLINE)
                    if self._underline_links
                    else self._text_style
                ),
                p_padding=0,
                block_spacing=0,
            ),
        )
