# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dialog that asks where to file a missing role reference.

The component owns only presentation. It reports the chosen category through an
async callback; the caller creates the note, refreshes the scan, and closes the
dialog.
"""

from collections.abc import Awaitable, Callable, Sequence

import flet as ft

import afanes.ui.strings
import afanes.ui.theme
from afanes.models.note import CategoryLabel


class RoleReferenceDialog:
    """Ask for the category of a reference created from a role name.

    Parameters
    ----------
    name : str
        Written owner, requester, or step owner name.
    categories : Sequence[CategoryLabel]
        Existing reference categories offered as suggestions. `person` is
        always added, and the list is sorted case-insensitively.
    on_confirm : Callable[[CategoryLabel | None], Awaitable[None]]
        Command that creates and opens the reference. ``None`` means no
        category.
    on_cancel : Callable[[], Awaitable[None]]
        Command that closes the dialog without writing.
    """

    def __init__(
        self,
        name: str,
        categories: Sequence[CategoryLabel],
        on_confirm: Callable[[CategoryLabel | None], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
    ) -> None:
        """Build the category controls and the dialog.

        Parameters
        ----------
        name : str
            Written role name shown in the dialog body.
        categories : Sequence[CategoryLabel]
            Existing reference categories offered as suggestions.
        on_confirm : Callable[[CategoryLabel | None], Awaitable[None]]
            Command that creates the reference with the chosen category.
        on_cancel : Callable[[], Awaitable[None]]
            Command that closes the dialog without writing.
        """
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self._typed_category: str | None = None
        self.name = name
        labels = sorted({"person", *(category.value for category in categories)}, key=str.casefold)
        self.category_field = ft.Dropdown(
            label=afanes.ui.strings.ROLE_REFERENCE_CATEGORY_LABEL,
            hint_text=afanes.ui.strings.ROLE_REFERENCE_CATEGORY_HINT,
            options=[
                ft.dropdown.Option(key="", text=afanes.ui.strings.ROLE_REFERENCE_NO_CATEGORY),
                *(ft.dropdown.Option(key=label, text=label) for label in labels),
            ],
            value="person",
            editable=True,
            enable_filter=True,
            autofocus=True,
            on_text_change=self.record_text,
            on_select=self.record_selection,
            key="role-reference-category",
        )
        self.error = ft.Text(
            "",
            color=afanes.ui.theme.ERROR_COLOR,
            visible=False,
            key="role-reference-error",
        )
        self.cancel_button = ft.TextButton(
            content=afanes.ui.strings.CANCEL_ACTION,
            on_click=self.cancel,
            key="role-reference-cancel",
        )
        self.confirm_button = ft.FilledButton(
            content=afanes.ui.strings.ROLE_REFERENCE_CREATE,
            on_click=self.submit,
            key="role-reference-create",
        )
        self.dialog = ft.AlertDialog(
            title=ft.Text(afanes.ui.strings.ROLE_REFERENCE_TITLE),
            content=ft.Column(
                controls=[
                    ft.Text(afanes.ui.strings.ROLE_REFERENCE_BODY.format(name=name)),
                    self.category_field,
                    self.error,
                ],
                tight=True,
            ),
            actions=[self.cancel_button, self.confirm_button],
            key="role-reference-dialog",
        )

    def record_text(self, event: ft.Event[ft.Dropdown]) -> None:
        """Keep typed free text available to the Create action.

        Parameters
        ----------
        event : flet.Event[flet.Dropdown]
            Text-change event carrying the current input text.

        Notes
        -----
        An editable dropdown stores a selected option in ``value`` and free
        text in ``text``. Confirming must prefer the typed text so a custom
        category is not mistaken for the default selection.
        """
        self._typed_category = event.control.text or ""

    def record_selection(self, event: ft.Event[ft.Dropdown]) -> None:
        """Replace typed text with the category chosen from the suggestions.

        Parameters
        ----------
        event : flet.Event[flet.Dropdown]
            Selection event carrying the chosen option key.
        """
        self._typed_category = event.control.value or ""

    async def submit(self) -> None:
        """Confirm the selected or typed category.

        Notes
        -----
        A blank field means no category. An invalid folder label is reported
        inline and the dialog stays open.
        """
        value = self._typed_category if self._typed_category is not None else self.category_field.value
        value = (value or "").strip()
        try:
            category = CategoryLabel(value) if value else None
        except ValueError:
            self.error.value = afanes.ui.strings.PAGE_CATEGORY_INVALID
            self.error.visible = True
            return
        self.error.visible = False
        await self._on_confirm(category)

    async def cancel(self) -> None:
        """Close the dialog without writing a note."""
        await self._on_cancel()
