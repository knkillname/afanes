# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Flet application shell and first-run routing."""

from pathlib import Path

import flet as ft

import afanes.ui.state
import afanes.ui.strings
import afanes.ui.theme
import afanes.ui.views.inbox
import afanes.ui.views.workspace


async def main(page: ft.Page) -> None:
    """Start the Afanes desktop application.

    Parameters
    ----------
    page : ft.Page
        Page created by :func:`flet.run`.

    Notes
    -----
    The shell chooses between the welcome state and the workspace from the
    shared application state, and rebuilds the page only when the vault
    changes. Browser sections, the page pane, and focused flows update inside
    the workspace without replacing it. The first development run may
    provision the Flet desktop client; application code performs no network
    I/O.
    """
    page.title = afanes.ui.strings.APP_TITLE
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = afanes.ui.theme.PAGE_PADDING
    page.window.width = 1100
    page.window.height = 760
    page.window.min_width = afanes.ui.theme.WINDOW_MIN_WIDTH
    page.window.min_height = afanes.ui.theme.WINDOW_MIN_HEIGHT
    picker = ft.FilePicker()
    page.services.append(picker)
    state = afanes.ui.state.app_state

    async def render() -> None:
        page.controls.clear()
        if state.vault_root is None:
            page.add(afanes.ui.views.inbox.build_welcome(choose_vault))
        else:
            page.add(afanes.ui.views.workspace.build_workspace(page.update, choose_vault))
        page.update()

    async def choose_vault() -> None:
        selected = await picker.get_directory_path(dialog_title=afanes.ui.strings.WELCOME_CHOOSE)
        if selected is None:
            return
        path = Path(selected)
        if state.vault_root is None:
            await state.choose_vault(path)
        else:
            await state.change_vault(path)
        await render()

    await state.start()
    await render()
