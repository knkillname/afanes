# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Centralized colors, spacing, typography, and dimensions for the interface.

Views import these tokens instead of hardcoding pixel values or colors. The
module is a UI leaf: it imports only Flet and never another Afanes UI module.

Two palette tables hold the light and dark values from the Adwaita 1.8.0
reference. Module tokens name the toolkit role that resolves through a scheme
field, so a view can ask for ``PAGE_SURFACE_COLOR`` without knowing which mode
is active. Text roles are the GNOME standard styles, expressed relative to
``BASE_FONT_SIZE`` rather than as per-control sizes.
"""

import types
import typing

import flet as ft

PAGE_PADDING = 24
SECTION_GAP = 18
ADOPTION_PANEL_GAP = SECTION_GAP
ITEM_GAP = 12
SIDEBAR_WIDTH = 260
NAVIGATION_WIDTH = 220
DRAWER_WIDTH = 280
BROWSER_MIN_WIDTH = 320
BROWSER_MAX_WIDTH = 360
PAGE_MIN_WIDTH = 420
CONTENT_MAX_WIDTH = 720
SHELL_WIDE_MIN = 1100
SHELL_MEDIUM_MIN = 1024
HEADER_HEIGHT = 48
TEMPLATE_PICKER_WIDTH = 420
WORKSPACE_BODY_GAP = 16
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 600
COMPOSER_MIN_LINES = 3
COMPOSER_MAX_LINES = 8
BANNER_PADDING = 12
SURFACE_RADIUS = 12
CONTROL_RADIUS = 9
PAGE_FIELD_WIDTH = 200
PAGE_DUE_WIDTH = 240
PAGE_FORM_FIELD_HEIGHT = 56
PAGE_NAME_WIDTH = 420
PAGE_RENAME_WIDTH = 360
STEP_INDENT = 16
CONNECTIONS_GAP = 12
ICON_SIZE = 16
ICON_SIZE_LARGE = 32

LIGHT_PALETTE = {
    "page": "#FAFAFB",
    "region": "#EBEBED",
    "card": "#FFFFFF",
    "container": "#F3F3F5",
    "container_high": "#E4E3E1",
    "container_highest": "#DCDBD9",
    "page_dim": "#F3F3F5",
    "page_bright": "#FFFFFF",
    "text": "#333334",
    "muted_text": "#5E5C64",
    "accent_fill": "#3584E4",
    "accent_text": "#1C71D8",
    "on_accent": "#FFFFFF",
    "accent_container": "#D7E6FC",
    "on_accent_container": "#0B3B72",
    "destructive": "#E01B24",
    "border": "#D0CFCB",
    "control_border": "#7E7E7E",
    "notice": "#D4A72C",
    "error": "#E01B24",
    "on_error": "#FFFFFF",
    "error_container": "#F5D6D8",
    "on_error_container": "#4A0008",
    "inverse_surface": "#2E2E32",
    "on_inverse_surface": "#FFFFFF",
    "inverse_primary": "#99C1F1",
}

DARK_PALETTE = {
    "page": "#222226",
    "region": "#2E2E32",
    "card": "#1D1D20",
    "container": "#28282C",
    "container_high": "#36363A",
    "container_highest": "#3C3C40",
    "page_dim": "#1D1D20",
    "page_bright": "#2E2E32",
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
    "error": "#C01C28",
    "on_error": "#FFFFFF",
    "error_container": "#4A1114",
    "on_error_container": "#FFD9D4",
    "inverse_surface": "#FAFAFB",
    "on_inverse_surface": "#222226",
    "inverse_primary": "#1C71D8",
}

ACCENT_FILL = LIGHT_PALETTE["accent_fill"]
ACCENT_TEXT = ft.Colors.TERTIARY
ON_ACCENT = LIGHT_PALETTE["on_accent"]
DESTRUCTIVE = ft.Colors.ERROR

PAGE_SURFACE_COLOR = ft.Colors.SURFACE
REGION_SURFACE_COLOR = ft.Colors.SURFACE_CONTAINER
CARD_SURFACE_COLOR = ft.Colors.SURFACE_CONTAINER_LOWEST
SURFACE_CONTAINER_COLOR = ft.Colors.SURFACE_CONTAINER_LOW
SELECTED_ROW_COLOR = ft.Colors.with_opacity(0.10, ft.Colors.ON_SURFACE)
BORDER_WIDTH = 1

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

SPLASH_COLOR = ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE)
HIGHLIGHT_COLOR = ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE)
HOVER_COLOR = ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE)
FOCUS_COLOR = ft.Colors.with_opacity(0.15, ft.Colors.PRIMARY)
DRAWER_SCRIM_COLOR = ft.Colors.with_opacity(0.14, "#000000")
DRAWER_SHADOW = ft.BoxShadow(
    blur_radius=28,
    color=ft.Colors.with_opacity(0.34, "#000000"),
    offset=ft.Offset(2, 0),
)

BASE_FONT_SIZE = 15
CAPTION_SIZE = round(BASE_FONT_SIZE * 0.82)
TITLE_4_SIZE = round(BASE_FONT_SIZE * 1.18)
TITLE_3_SIZE = round(BASE_FONT_SIZE * 1.36)
TITLE_2_SIZE = round(BASE_FONT_SIZE * 1.36)
TITLE_1_SIZE = round(BASE_FONT_SIZE * 1.81)

TEXT_ROLES: typing.Mapping[str, ft.TextStyle] = types.MappingProxyType(
    {
        "title-1": ft.TextStyle(
            size=TITLE_1_SIZE,
            weight=ft.FontWeight.W_800,
            color=TEXT_COLOR,
        ),
        "title-2": ft.TextStyle(
            size=TITLE_2_SIZE,
            weight=ft.FontWeight.W_800,
            color=TEXT_COLOR,
        ),
        "title-3": ft.TextStyle(
            size=TITLE_3_SIZE,
            weight=ft.FontWeight.W_700,
            color=TEXT_COLOR,
        ),
        "title-4": ft.TextStyle(
            size=TITLE_4_SIZE,
            weight=ft.FontWeight.W_700,
            color=TEXT_COLOR,
        ),
        "heading": ft.TextStyle(
            size=BASE_FONT_SIZE,
            weight=ft.FontWeight.W_700,
            color=TEXT_COLOR,
        ),
        "body": ft.TextStyle(
            size=BASE_FONT_SIZE,
            weight=ft.FontWeight.W_400,
            color=TEXT_COLOR,
            height=1.4,
        ),
        "caption": ft.TextStyle(
            size=CAPTION_SIZE,
            weight=ft.FontWeight.W_400,
            color=MUTED_TEXT_COLOR,
            height=1.4,
        ),
        "caption-heading": ft.TextStyle(
            size=CAPTION_SIZE,
            weight=ft.FontWeight.W_700,
            color=MUTED_TEXT_COLOR,
        ),
    }
)

TEXT_THEME = ft.TextTheme(
    display_large=TEXT_ROLES["title-1"],
    display_medium=TEXT_ROLES["title-1"],
    display_small=TEXT_ROLES["title-2"],
    headline_large=TEXT_ROLES["title-1"],
    headline_medium=TEXT_ROLES["title-1"],
    headline_small=TEXT_ROLES["title-2"],
    title_large=TEXT_ROLES["title-3"],
    title_medium=TEXT_ROLES["title-4"],
    title_small=TEXT_ROLES["heading"],
    body_large=TEXT_ROLES["body"],
    body_medium=TEXT_ROLES["body"],
    body_small=TEXT_ROLES["caption"],
    label_large=TEXT_ROLES["heading"],
    label_medium=TEXT_ROLES["caption-heading"],
    label_small=TEXT_ROLES["caption"],
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
    min_height=36,
)

ICON_THEME = ft.IconTheme(size=ICON_SIZE)

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
    icon_theme=ICON_THEME,
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
    icon_theme=ICON_THEME,
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
    size=CAPTION_SIZE,
    color=ACCENT_TEXT,
    decoration=ft.TextDecoration.UNDERLINE,
)
ROLE_BROKEN_TEXT_STYLE = ft.TextStyle(
    size=CAPTION_SIZE,
    color=ERROR_TEXT_COLOR,
    decoration=ft.TextDecoration.UNDERLINE,
)
