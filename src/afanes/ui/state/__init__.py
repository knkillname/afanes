# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Application state singleton exposed to the presentation layer."""

from afanes.ui.state.controller import AppState as _AppState

app_state = _AppState()
