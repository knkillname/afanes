# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Dialog that sets one project role name from read mode.

The component owns only presentation. It reports the chosen name through an
async callback; the caller writes the label and closes the dialog.
"""

from collections.abc import Awaitable, Callable, Sequence

import flet as ft

import afanes.ui.strings
import afanes.ui.theme


class RoleNameDialog:
    """Ask for an owner or requester name with vault-name suggestions.

    Parameters
    ----------
    title : str
        Dialog title, already localized.
    current : str | None
        Current written name, or ``None`` when the role is empty.
    names : Sequence[str]
        Note names offered as suggestions. A typed name that matches no note is
        still accepted.
    on_save : Callable[[str], Awaitable[None]]
        Command that writes the selected name. An empty string clears the role.
    on_cancel : Callable[[], Awaitable[None]]
        Command that closes the dialog without writing.
    """

    def __init__(
        self,
        title: str,
        current: str | None,
        names: Sequence[str],
        on_save: Callable[[str], Awaitable[None]],
        on_cancel: Callable[[], Awaitable[None]],
    ) -> None:
        """Build the name field, suggestions, and dialog actions.

        Parameters
        ----------
        title : str
            Dialog title, already localized.
        current : str | None
            Current written name, or ``None`` when the role is empty.
        names : Sequence[str]
            Note names offered as suggestions.
        on_save : Callable[[str], Awaitable[None]]
            Command that writes the selected name or clears it with ``""``.
        on_cancel : Callable[[], Awaitable[None]]
            Command that closes the dialog without writing.
        """
        self._on_save = on_save
        self._on_cancel = on_cancel
        self._typed_name: str | None = None
        self.title = title
        values = {name for name in names if name}
        if current:
            values.add(current)
        self.name_field = ft.Dropdown(
            label=afanes.ui.strings.ROLE_NAME_LABEL,
            hint_text=afanes.ui.strings.ROLE_NAME_HINT,
            options=[ft.dropdown.Option(key=name, text=name) for name in sorted(values, key=str.casefold)],
            value=current or "",
            editable=True,
            enable_filter=True,
            autofocus=True,
            on_text_change=self.record_text,
            on_select=self.record_selection,
            key="role-name-field",
        )
        self.cancel_button = ft.TextButton(
            content=afanes.ui.strings.CANCEL_ACTION,
            on_click=self.cancel,
            key="role-name-cancel",
        )
        self.clear_button = ft.TextButton(
            content=afanes.ui.strings.ROLE_NAME_CLEAR,
            on_click=self.clear,
            key="role-name-clear",
        )
        self.save_button = ft.FilledButton(
            content=afanes.ui.strings.ROLE_NAME_SAVE,
            on_click=self.save,
            key="role-name-save",
        )
        self.dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Column(
                controls=[
                    ft.Text(afanes.ui.strings.ROLE_NAME_BODY),
                    self.name_field,
                ],
                tight=True,
            ),
            actions=[self.cancel_button, self.clear_button, self.save_button],
            key="role-name-dialog",
        )

    def record_text(self, event: ft.Event[ft.Dropdown]) -> None:
        """Keep typed free text available to the Save action.

        Parameters
        ----------
        event : flet.Event[flet.Dropdown]
            Text-change event carrying the current input text.

        Notes
        -----
        An editable dropdown stores a selected option in ``value`` and free
        text in ``text``. Saving must prefer the typed text so a new name is
        not mistaken for an empty selection.
        """
        self._typed_name = event.control.text or ""

    def record_selection(self, event: ft.Event[ft.Dropdown]) -> None:
        """Replace typed text with the name chosen from the suggestions.

        Parameters
        ----------
        event : flet.Event[flet.Dropdown]
            Selection event carrying the chosen option key.
        """
        self._typed_name = event.control.value or ""

    async def save(self) -> None:
        """Write the typed or selected name, or clear the role when blank."""
        value = self._typed_name if self._typed_name is not None else self.name_field.value
        await self._on_save((value or "").strip())

    async def clear(self) -> None:
        """Clear the role."""
        await self._on_save("")

    async def cancel(self) -> None:
        """Close the dialog without writing."""
        await self._on_cancel()
