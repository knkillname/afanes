# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inline confirmation panels for the page pane.

Each component owns one self-contained confirmation block. The page view keeps
the refresh logic and forwards the callbacks that confirm or cancel the action.
"""

from collections.abc import Awaitable, Callable

import flet as ft

import afanes.i18n.ui
import afanes.ui.theme
from afanes.ui.components.panel import Panel

_ENGLISH_COPY = afanes.i18n.ui.UiCopy.english()


class ConflictPanel:
    """Choose how to resolve a page that changed on disk."""

    def __init__(
        self,
        on_reload: Callable[[], Awaitable[None]],
        on_overwrite: Callable[[], Awaitable[None]],
        on_recreate: Callable[[], Awaitable[None]],
        on_discard: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy = _ENGLISH_COPY,
    ) -> None:
        """Build the disk-conflict panel.

        Parameters
        ----------
        on_reload : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Reload the page from disk.
        on_overwrite : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Overwrite the page with the draft.
        on_recreate : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Recreate a page that disappeared.
        on_discard : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Discard the draft.
        """
        self.text = ft.Text("", selectable=True)
        self.reload = ft.FilledButton(
            content=copy.PAGE_CONFLICT_RELOAD,
            on_click=on_reload,
        )
        self.overwrite = ft.OutlinedButton(
            content=copy.PAGE_CONFLICT_OVERWRITE,
            on_click=on_overwrite,
        )
        self.recreate = ft.OutlinedButton(
            content=copy.PAGE_CONFLICT_RECREATE,
            on_click=on_recreate,
        )
        self.discard = ft.TextButton(
            content=copy.PAGE_CONFLICT_DISCARD,
            on_click=on_discard,
        )
        self.panel = Panel(
            copy.PAGE_CONFLICT_TITLE,
            self.text,
            [self.reload, self.overwrite, self.recreate, self.discard],
        ).build()
        self.panel.visible = False


class AmbiguousPanel:
    """Choose one page when a reference matches several notes."""

    def __init__(
        self,
        on_cancel: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy = _ENGLISH_COPY,
    ) -> None:
        """Build the ambiguous-reference panel.

        Parameters
        ----------
        on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Close the panel without choosing a page.
        """
        self.list = ft.Column(controls=[], spacing=afanes.ui.theme.NO_GAP)
        self.cancel = ft.TextButton(
            content=copy.PAGE_CANCEL,
            on_click=on_cancel,
        )
        self.panel = Panel(
            copy.PAGE_AMBIGUOUS_TITLE,
            ft.Column(
                controls=[
                    ft.Text(copy.PAGE_AMBIGUOUS_BODY, selectable=True),
                    self.list,
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
            [self.cancel],
        ).build()
        self.panel.visible = False


class RepairPanel:
    """Choose how to repair links that use an unsafe old name."""

    def __init__(
        self,
        on_rewrite: Callable[[], Awaitable[None]],
        on_keep: Callable[[], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy = _ENGLISH_COPY,
    ) -> None:
        """Build the link-repair panel.

        Parameters
        ----------
        on_rewrite : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Rewrite the old links.
        on_keep : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Keep the old links.
        on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Cancel the creation.
        """
        self.text = ft.Text("", selectable=True)
        self.rewrite = ft.FilledButton(
            content=copy.PAGE_REPAIR_REWRITE,
            on_click=on_rewrite,
        )
        self.keep = ft.TextButton(
            content=copy.PAGE_REPAIR_KEEP,
            on_click=on_keep,
        )
        self.cancel = ft.TextButton(
            content=copy.PAGE_REPAIR_CANCEL,
            on_click=on_cancel,
        )
        self.panel = Panel(
            copy.PAGE_REPAIR_TITLE,
            self.text,
            [self.cancel, self.keep, self.rewrite],
        ).build()
        self.panel.visible = False


class TypeChangePanel:
    """Confirm a note-type change that can break references."""

    def __init__(
        self,
        on_confirm: Callable[[], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy = _ENGLISH_COPY,
    ) -> None:
        """Build the type-change panel.

        Parameters
        ----------
        on_confirm : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Change the note type.
        on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Keep the current type.
        """
        self.text = ft.Text("", selectable=True)
        self.confirm = ft.FilledButton(
            content=copy.PAGE_TYPE_CHANGE_CONFIRM,
            on_click=on_confirm,
        )
        self.cancel = ft.TextButton(
            content=copy.PAGE_CANCEL,
            on_click=on_cancel,
        )
        self.panel = Panel(
            copy.PAGE_TYPE_CHANGE_TITLE,
            self.text,
            [self.cancel, self.confirm],
        ).build()
        self.panel.visible = False


class CategoryMovePanel:
    """Confirm moving a page into its category folder."""

    def __init__(
        self,
        on_confirm: Callable[[], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy = _ENGLISH_COPY,
    ) -> None:
        """Build the category-move panel.

        Parameters
        ----------
        on_confirm : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Move the page.
        on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Keep the current location.
        """
        self.text = ft.Text("", selectable=True)
        self.confirm = ft.FilledButton(
            content=copy.PAGE_CATEGORY_MOVE_CONFIRM,
            on_click=on_confirm,
        )
        self.cancel = ft.TextButton(
            content=copy.PAGE_CANCEL,
            on_click=on_cancel,
        )
        self.panel = Panel(
            copy.PAGE_CATEGORY_MOVE_TITLE,
            self.text,
            [self.cancel, self.confirm],
        ).build()
        self.panel.visible = False


class DestructiveConfirmPanel:
    """Confirm one irreversible action with Cancel before the affirmative.

    Parameters
    ----------
    on_confirm : collections.abc.Callable[[], collections.abc.Awaitable[None]]
        Apply the destructive action.
    on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
        Dismiss the panel without writing.
    """

    def __init__(
        self,
        on_confirm: Callable[[], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy = _ENGLISH_COPY,
    ) -> None:
        """Build a reusable destructive confirmation panel.

        Parameters
        ----------
        on_confirm : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Apply the destructive action.
        on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Dismiss the panel without writing.
        """
        self.title = ft.Text("", style=afanes.ui.theme.TEXT_ROLES["title-4"])
        self.body = ft.Text("", selectable=True)
        self.confirm = ft.FilledButton(
            content="",
            on_click=on_confirm,
            style=afanes.ui.theme.DESTRUCTIVE_BUTTON_STYLE,
        )
        self.cancel = ft.TextButton(
            content=copy.PAGE_CANCEL,
            on_click=on_cancel,
        )
        self.actions = ft.Row(
            controls=[self.cancel, self.confirm],
            spacing=afanes.ui.theme.ITEM_GAP,
            wrap=True,
        )
        self.panel = ft.Container(
            bgcolor=afanes.ui.theme.CARD_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            visible=False,
            content=ft.Column(
                controls=[self.title, self.body, self.actions],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )


class RenamePanel:
    """Preview and confirm a page rename."""

    def __init__(
        self,
        on_change: Callable[[], Awaitable[None]],
        on_preview: Callable[[], Awaitable[None]],
        on_confirm: Callable[[], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy = _ENGLISH_COPY,
    ) -> None:
        """Build the rename panel.

        Parameters
        ----------
        on_change : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Update the rename availability as the text changes.
        on_preview : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Preview the rename.
        on_confirm : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Confirm the rename.
        on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Cancel the rename.
        """
        self.field = ft.TextField(
            label=copy.PAGE_RENAME_LABEL,
            width=afanes.ui.theme.PAGE_RENAME_WIDTH,
            on_change=on_change,
        )
        self.error = ft.Text(
            "",
            style=afanes.ui.theme.TEXT_ROLES["caption"],
            color=afanes.ui.theme.ERROR_TEXT_COLOR,
            visible=False,
            selectable=True,
        )
        self.preview_text = ft.Text("", selectable=True)
        self.preview = ft.OutlinedButton(
            content=copy.PAGE_RENAME_PREVIEW_ACTION,
            on_click=on_preview,
            disabled=True,
        )
        self.confirm = ft.FilledButton(
            content=copy.PAGE_RENAME_CONFIRM,
            on_click=on_confirm,
            disabled=True,
        )
        self.cancel = ft.TextButton(
            content=copy.PAGE_CANCEL,
            on_click=on_cancel,
        )
        self.panel = ft.Container(
            bgcolor=afanes.ui.theme.CARD_SURFACE_COLOR,
            border=ft.Border.all(afanes.ui.theme.BORDER_WIDTH, afanes.ui.theme.BORDER_COLOR),
            border_radius=afanes.ui.theme.SURFACE_RADIUS,
            padding=afanes.ui.theme.ITEM_GAP,
            visible=False,
            content=ft.Column(
                controls=[
                    ft.Text(copy.PAGE_RENAME_TITLE, style=afanes.ui.theme.TEXT_ROLES["title-4"]),
                    self.field,
                    self.error,
                    self.preview_text,
                    ft.Row(
                        controls=[self.cancel, self.preview, self.confirm],
                        spacing=afanes.ui.theme.ITEM_GAP,
                        wrap=True,
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
        )
