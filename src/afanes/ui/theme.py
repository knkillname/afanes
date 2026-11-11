# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized colors, spacing, typography, and dimensions for the interface.

Views import these tokens instead of hardcoding pixel values or colors. The
module is a UI leaf: it imports only Flet and never another Afanes UI module.
"""

import flet as ft

PAGE_PADDING = 24
SECTION_GAP = 16
ITEM_GAP = 8
LIST_WIDTH = 360
PREVIEW_MIN_WIDTH = 420
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 640
COMPOSER_MIN_LINES = 3
COMPOSER_MAX_LINES = 8
BANNER_PADDING = 12
CARD_RADIUS = 8

ERROR_CONTAINER_COLOR = ft.Colors.ERROR_CONTAINER
ERROR_TEXT_COLOR = ft.Colors.ON_ERROR_CONTAINER
SURFACE_CONTAINER_COLOR = ft.Colors.SURFACE_CONTAINER_LOW
BORDER_COLOR = ft.Colors.OUTLINE_VARIANT
MUTED_TEXT_COLOR = ft.Colors.ON_SURFACE_VARIANT
