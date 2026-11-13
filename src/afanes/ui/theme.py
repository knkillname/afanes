# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized colors, spacing, typography, and dimensions for the interface.

Views import these tokens instead of hardcoding pixel values or colors. The
module is a UI leaf: it imports only Flet and never another Afanes UI module.

Two palette tables hold the light and dark values. Module tokens name the
toolkit role that resolves through a scheme field, so a view can ask for
``PAGE_SURFACE_COLOR`` without knowing which mode is active.
"""

import flet as ft

PAGE_PADDING = 24
SECTION_GAP = 18
ADOPTION_PANEL_GAP = SECTION_GAP
ITEM_GAP = 12
LIST_WIDTH = 360
SIDEBAR_WIDTH = 260
PAGE_MIN_WIDTH = 420
TEMPLATE_PICKER_WIDTH = 420
WORKSPACE_BODY_GAP = 16
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 640
COMPOSER_MIN_LINES = 3
COMPOSER_MAX_LINES = 8
BANNER_PADDING = 12
SURFACE_RADIUS = 12
CONTROL_RADIUS = 8
PAGE_FIELD_WIDTH = 200
PAGE_DUE_WIDTH = 240
PAGE_FORM_FIELD_HEIGHT = 56
PAGE_NAME_WIDTH = 420
PAGE_RENAME_WIDTH = 360
STEP_INDENT = 16
CONNECTIONS_GAP = 12

LIGHT_PALETTE = {
    "page": "#FAFAFA",
    "region": "#EBEBEB",
    "card": "#FFFFFF",
    "container": "#F6F5F4",
    "container_high": "#E4E3E1",
    "container_highest": "#DCDBD9",
    "page_dim": "#EBEBEB",
    "page_bright": "#FFFFFF",
    "text": "#2E3436",
    "muted_text": "#5E5C64",
    "accent_fill": "#3584E4",
    "accent_text": "#1C71D8",
    "on_accent": "#FFFFFF",
    "accent_container": "#D7E6FC",
    "on_accent_container": "#0B3B72",
    "destructive": "#C01C28",
    "border": "#D0CFCB",
    "control_border": "#7E7E7E",
    "notice": "#D4A72C",
    "error": "#C01C28",
    "on_error": "#FFFFFF",
    "error_container": "#F5D6D8",
    "on_error_container": "#4A0008",
    "inverse_surface": "#303030",
    "on_inverse_surface": "#FFFFFF",
    "inverse_primary": "#99C1F1",
}

DARK_PALETTE = {
    "page": "#242424",
    "region": "#303030",
    "card": "#1E1E1E",
    "container": "#303030",
    "container_high": "#363636",
    "container_highest": "#3C3C3C",
    "page_dim": "#1E1E1E",
    "page_bright": "#303030",
    "text": "#FFFFFF",
    "muted_text": "#C0BFBC",
    "accent_fill": "#3584E4",
    "accent_text": "#99C1F1",
    "on_accent": "#FFFFFF",
    "accent_container": "#1C4E86",
    "on_accent_container": "#D7E6FC",
    "destructive": "#C01C28",
    "border": "#4A4A4A",
    "control_border": "#7E7E7E",
    "notice": "#D4A72C",
    "error": "#FF7B63",
    "on_error": "#1A0A00",
    "error_container": "#4A1114",
    "on_error_container": "#FFD9D4",
    "inverse_surface": "#FAFAFA",
    "on_inverse_surface": "#2E3436",
    "inverse_primary": "#1C71D8",
}

ACCENT_FILL = LIGHT_PALETTE["accent_fill"]
ACCENT_TEXT = ft.Colors.TERTIARY
ON_ACCENT = LIGHT_PALETTE["on_accent"]
DESTRUCTIVE = LIGHT_PALETTE["destructive"]

PAGE_SURFACE_COLOR = ft.Colors.SURFACE
REGION_SURFACE_COLOR = ft.Colors.SURFACE_CONTAINER
CARD_SURFACE_COLOR = ft.Colors.SURFACE_CONTAINER_LOWEST
SURFACE_CONTAINER_COLOR = ft.Colors.SURFACE_CONTAINER_LOW
SELECTED_ROW_COLOR = ft.Colors.with_opacity(0.15, ACCENT_FILL)
BORDER_WIDTH = 1
SECTION_EDGE_WIDTH = 3

NOTICE_COLOR = LIGHT_PALETTE["notice"]
NOTICE_SURFACE_COLOR = ft.Colors.with_opacity(0.15, NOTICE_COLOR)
NOTICE_BORDER_COLOR = ft.Colors.with_opacity(0.55, NOTICE_COLOR)

SECTION_ICON_COLOR = ft.Colors.ON_SURFACE_VARIANT
LOG_ENTRY_TINT = ft.Colors.with_opacity(0.18, ACCENT_FILL)
LOG_ENTRY_DOT_COLOR = ACCENT_FILL

ERROR_COLOR = ft.Colors.ERROR
ERROR_CONTAINER_COLOR = ft.Colors.ERROR_CONTAINER
ERROR_TEXT_COLOR = ft.Colors.ON_ERROR_CONTAINER
BORDER_COLOR = ft.Colors.OUTLINE_VARIANT
CONTROL_BORDER_COLOR = ft.Colors.OUTLINE
TEXT_COLOR = ft.Colors.ON_SURFACE
MUTED_TEXT_COLOR = ft.Colors.ON_SURFACE_VARIANT
MUTED_ACTION_COLOR = ft.Colors.with_opacity(0.75, ft.Colors.ON_SURFACE_VARIANT)
STEP_SURFACE_COLOR = SURFACE_CONTAINER_COLOR
STEP_TEXT_COLOR = TEXT_COLOR
STEP_MUTED_ACTION_COLOR = MUTED_ACTION_COLOR

SPLASH_COLOR = ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY)
HIGHLIGHT_COLOR = ft.Colors.with_opacity(0.08, ft.Colors.PRIMARY)
HOVER_COLOR = ft.Colors.with_opacity(0.06, ft.Colors.PRIMARY)
FOCUS_COLOR = ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY)

# A Markdown style sheet takes a TextStyle, not a theme role. These two styles
# back the ``headline_small`` and ``body_small`` roles so the role definition
# still lives in one place.
STEP_MARKDOWN_TEXT_STYLE = ft.TextStyle(size=24, weight=ft.FontWeight.W_700, color=TEXT_COLOR)
METADATA_MARKDOWN_TEXT_STYLE = ft.TextStyle(size=12, weight=ft.FontWeight.W_400, color=MUTED_TEXT_COLOR)

TEXT_THEME = ft.TextTheme(
    display_large=ft.TextStyle(size=40, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
    display_medium=ft.TextStyle(size=36, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
    display_small=ft.TextStyle(size=32, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
    headline_large=ft.TextStyle(size=32, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
    headline_medium=ft.TextStyle(size=28, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
    headline_small=STEP_MARKDOWN_TEXT_STYLE,
    title_large=ft.TextStyle(size=22, weight=ft.FontWeight.W_600, color=TEXT_COLOR),
    title_medium=ft.TextStyle(size=16, weight=ft.FontWeight.W_600, color=TEXT_COLOR),
    title_small=ft.TextStyle(size=15, weight=ft.FontWeight.W_600, color=TEXT_COLOR),
    body_large=ft.TextStyle(size=16, weight=ft.FontWeight.W_400, color=TEXT_COLOR),
    body_medium=ft.TextStyle(size=14, weight=ft.FontWeight.W_400, color=TEXT_COLOR),
    body_small=METADATA_MARKDOWN_TEXT_STYLE,
    label_large=ft.TextStyle(size=14, weight=ft.FontWeight.W_600, color=TEXT_COLOR),
    label_medium=ft.TextStyle(size=12, weight=ft.FontWeight.W_700, color=MUTED_TEXT_COLOR),
    label_small=ft.TextStyle(size=11, weight=ft.FontWeight.W_500, color=MUTED_TEXT_COLOR),
)

BUTTON_SHAPE = ft.RoundedRectangleBorder(radius=CONTROL_RADIUS)

FILLED_BUTTON_THEME = ft.FilledButtonTheme(
    style=ft.ButtonStyle(bgcolor=ACCENT_FILL, color=ON_ACCENT, shape=BUTTON_SHAPE),
)
TEXT_BUTTON_THEME = ft.TextButtonTheme(style=ft.ButtonStyle(shape=BUTTON_SHAPE))
OUTLINED_BUTTON_THEME = ft.OutlinedButtonTheme(style=ft.ButtonStyle(shape=BUTTON_SHAPE))
DESTRUCTIVE_BUTTON_STYLE = ft.ButtonStyle(bgcolor=DESTRUCTIVE, color=ON_ACCENT, shape=BUTTON_SHAPE)

INPUT_DECORATION_THEME = ft.InputDecorationTheme(
    border=ft.OutlineInputBorder(
        border_radius=CONTROL_RADIUS,
        side=ft.BorderSide(BORDER_WIDTH, CONTROL_BORDER_COLOR),
    ),
)

LIST_TILE_THEME = ft.ListTileTheme(
    selected_tile_color=SELECTED_ROW_COLOR,
    selected_color=TEXT_COLOR,
)

LIGHT_THEME = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary=LIGHT_PALETTE["accent_fill"],
        on_primary=LIGHT_PALETTE["on_accent"],
        primary_container=LIGHT_PALETTE["accent_container"],
        on_primary_container=LIGHT_PALETTE["on_accent_container"],
        secondary=LIGHT_PALETTE["muted_text"],
        on_secondary=LIGHT_PALETTE["card"],
        secondary_container=LIGHT_PALETTE["region"],
        on_secondary_container=LIGHT_PALETTE["text"],
        tertiary=LIGHT_PALETTE["accent_text"],
        on_tertiary=LIGHT_PALETTE["on_accent"],
        error=LIGHT_PALETTE["error"],
        on_error=LIGHT_PALETTE["on_error"],
        error_container=LIGHT_PALETTE["error_container"],
        on_error_container=LIGHT_PALETTE["on_error_container"],
        surface=LIGHT_PALETTE["page"],
        on_surface=LIGHT_PALETTE["text"],
        on_surface_variant=LIGHT_PALETTE["muted_text"],
        outline=LIGHT_PALETTE["control_border"],
        outline_variant=LIGHT_PALETTE["border"],
        surface_container=LIGHT_PALETTE["region"],
        surface_container_low=LIGHT_PALETTE["container"],
        surface_container_lowest=LIGHT_PALETTE["card"],
        surface_container_high=LIGHT_PALETTE["container_high"],
        surface_container_highest=LIGHT_PALETTE["container_highest"],
        surface_dim=LIGHT_PALETTE["page_dim"],
        surface_bright=LIGHT_PALETTE["page_bright"],
        inverse_surface=LIGHT_PALETTE["inverse_surface"],
        on_inverse_surface=LIGHT_PALETTE["on_inverse_surface"],
        inverse_primary=LIGHT_PALETTE["inverse_primary"],
        shadow="#000000",
        scrim="#000000",
    ),
    surfaces=ft.ThemeSurfaces.NEUTRAL,
    text_theme=TEXT_THEME,
    filled_button_theme=FILLED_BUTTON_THEME,
    text_button_theme=TEXT_BUTTON_THEME,
    outlined_button_theme=OUTLINED_BUTTON_THEME,
    list_tile_theme=LIST_TILE_THEME,
    input_decoration_theme=INPUT_DECORATION_THEME,
    splash_color=SPLASH_COLOR,
    highlight_color=HIGHLIGHT_COLOR,
    hover_color=HOVER_COLOR,
    focus_color=FOCUS_COLOR,
    visual_density=ft.VisualDensity.STANDARD,
)

DARK_THEME = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary=DARK_PALETTE["accent_fill"],
        on_primary=DARK_PALETTE["on_accent"],
        primary_container=DARK_PALETTE["accent_container"],
        on_primary_container=DARK_PALETTE["on_accent_container"],
        secondary=DARK_PALETTE["muted_text"],
        on_secondary=DARK_PALETTE["card"],
        secondary_container=DARK_PALETTE["region"],
        on_secondary_container=DARK_PALETTE["text"],
        tertiary=DARK_PALETTE["accent_text"],
        on_tertiary=DARK_PALETTE["page"],
        error=DARK_PALETTE["error"],
        on_error=DARK_PALETTE["on_error"],
        error_container=DARK_PALETTE["error_container"],
        on_error_container=DARK_PALETTE["on_error_container"],
        surface=DARK_PALETTE["page"],
        on_surface=DARK_PALETTE["text"],
        on_surface_variant=DARK_PALETTE["muted_text"],
        outline=DARK_PALETTE["control_border"],
        outline_variant=DARK_PALETTE["border"],
        surface_container=DARK_PALETTE["region"],
        surface_container_low=DARK_PALETTE["container"],
        surface_container_lowest=DARK_PALETTE["card"],
        surface_container_high=DARK_PALETTE["container_high"],
        surface_container_highest=DARK_PALETTE["container_highest"],
        surface_dim=DARK_PALETTE["page_dim"],
        surface_bright=DARK_PALETTE["page_bright"],
        inverse_surface=DARK_PALETTE["inverse_surface"],
        on_inverse_surface=DARK_PALETTE["on_inverse_surface"],
        inverse_primary=DARK_PALETTE["inverse_primary"],
        shadow="#000000",
        scrim="#000000",
    ),
    surfaces=ft.ThemeSurfaces.NEUTRAL,
    text_theme=TEXT_THEME,
    filled_button_theme=FILLED_BUTTON_THEME,
    text_button_theme=TEXT_BUTTON_THEME,
    outlined_button_theme=OUTLINED_BUTTON_THEME,
    list_tile_theme=LIST_TILE_THEME,
    input_decoration_theme=INPUT_DECORATION_THEME,
    splash_color=SPLASH_COLOR,
    highlight_color=HIGHLIGHT_COLOR,
    hover_color=HOVER_COLOR,
    focus_color=FOCUS_COLOR,
    visual_density=ft.VisualDensity.STANDARD,
)

ROLE_LINK_TEXT_STYLE = ft.TextStyle(
    size=12,
    color=ACCENT_TEXT,
    decoration=ft.TextDecoration.UNDERLINE,
)
ROLE_BROKEN_TEXT_STYLE = ft.TextStyle(
    size=12,
    color=ERROR_COLOR,
    decoration=ft.TextDecoration.UNDERLINE,
)
