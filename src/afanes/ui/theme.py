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
NO_GAP = 0
ITEM_GAP = 12
SIDEBAR_WIDTH = 260
NAVIGATION_WIDTH = 240
DRAWER_WIDTH = 280
NAVIGATION_PADDING = 8
BROWSER_MIN_WIDTH = 320
BROWSER_SHARE = 0.35
PAGE_MIN_WIDTH = 420
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
TOAST_DURATION_MS = 6000
TOAST_MARGIN = ITEM_GAP
TOAST_PADDING = ITEM_GAP
SURFACE_RADIUS = 12
CONTROL_RADIUS = 9
FOCUS_RING_WIDTH = 2
ROW_GAP = 4
FIELD_MIN_WIDTH = 200
PAGE_FORM_FIELD_HEIGHT = 56
PAGE_NAME_WIDTH = 420
REMINDER_TIME_FIELD_WIDTH = 160
PAGE_RENAME_WIDTH = 360
STEP_INDENT = 16
CONNECTIONS_GAP = 12
ICON_SIZE = 16
ICON_SIZE_LARGE = 32
CALENDAR_CELL_HEIGHT = 34
CALENDAR_GRID_SPACING = 0
CALENDAR_ROW_SPACING = 2
CALENDAR_HEADER_SPACING = 4
CALENDAR_CELL_SPACING = 1
CALENDAR_CELL_VERTICAL_PADDING = 6
CALENDAR_CELL_PADDING = ft.Padding.symmetric(vertical=CALENDAR_CELL_VERTICAL_PADDING)
CALENDAR_HEADER_DOT_SIZE = 6
CALENDAR_HEADER_DOT_RADIUS = 3
CALENDAR_DAY_DOT_SIZE = 4
CALENDAR_DAY_DOT_RADIUS = 2
DATE_PICKER_WIDTH = 360
DATE_PICKER_PERIOD_HEIGHT = 40
SHORTCUT_KEYS_MIN_WIDTH = 180
DATE_PICKER_MONTH_COLUMNS = 3
DATE_PICKER_YEAR_COLUMNS = 5

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

HIGH_CONTRAST_LIGHT_PALETTE = {
    "page": "#FFFFFF",
    "region": "#F2F2F2",
    "card": "#FFFFFF",
    "container": "#E9E9E9",
    "container_high": "#D9D9D9",
    "container_highest": "#C9C9C9",
    "page_dim": "#F2F2F2",
    "page_bright": "#FFFFFF",
    "text": "#000000",
    "muted_text": "#1F1F1F",
    "accent_fill": "#005A9C",
    "accent_text": "#004A80",
    "on_accent": "#FFFFFF",
    "accent_container": "#D6E8F8",
    "on_accent_container": "#001F35",
    "destructive": "#A40000",
    "border": "#5C5C5C",
    "control_border": "#333333",
    "notice": "#6B4E00",
    "error": "#A40000",
    "on_error": "#FFFFFF",
    "error_container": "#FBE0E1",
    "on_error_container": "#3A0000",
    "inverse_surface": "#000000",
    "on_inverse_surface": "#FFFFFF",
    "inverse_primary": "#9CCBFF",
}

HIGH_CONTRAST_DARK_PALETTE = {
    "page": "#000000",
    "region": "#141414",
    "card": "#0A0A0A",
    "container": "#1C1C1C",
    "container_high": "#282828",
    "container_highest": "#343434",
    "page_dim": "#0A0A0A",
    "page_bright": "#1C1C1C",
    "text": "#FFFFFF",
    "muted_text": "#E0E0E0",
    "accent_fill": "#8CC4FF",
    "accent_text": "#9CCBFF",
    "on_accent": "#000000",
    "accent_container": "#003A66",
    "on_accent_container": "#E0F0FF",
    "destructive": "#FF8A80",
    "border": "#9A9A9A",
    "control_border": "#C0C0C0",
    "notice": "#FFD166",
    "error": "#FF8A80",
    "on_error": "#000000",
    "error_container": "#4A0000",
    "on_error_container": "#FFE0DE",
    "inverse_surface": "#FFFFFF",
    "on_inverse_surface": "#000000",
    "inverse_primary": "#005A9C",
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
TRANSPARENT_COLOR = ft.Colors.TRANSPARENT

NOTICE_COLOR = LIGHT_PALETTE["notice"]
NOTICE_SURFACE_COLOR = ft.Colors.with_opacity(0.15, NOTICE_COLOR)
NOTICE_BORDER_COLOR = ft.Colors.with_opacity(0.55, NOTICE_COLOR)

SECTION_ICON_COLOR = ft.Colors.ON_SURFACE_VARIANT
LOG_ENTRY_TINT = ft.Colors.with_opacity(0.18, ft.Colors.PRIMARY)
LOG_ENTRY_DOT_COLOR = ft.Colors.PRIMARY
CALENDAR_SELECTED_COLOR = SELECTED_ROW_COLOR
CALENDAR_TODAY_COLOR = ACCENT_TEXT
CALENDAR_CELL_SHAPE = ft.RoundedRectangleBorder(radius=CONTROL_RADIUS)

ERROR_COLOR = ft.Colors.ERROR
ERROR_CONTAINER_COLOR = ft.Colors.ERROR_CONTAINER
ERROR_TEXT_COLOR = ft.Colors.ON_ERROR_CONTAINER
TOAST_SURFACE_COLOR = ft.Colors.INVERSE_SURFACE
TOAST_TEXT_COLOR = ft.Colors.ON_INVERSE_SURFACE
TOAST_ACTION_COLOR = ft.Colors.INVERSE_PRIMARY
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
DISABLED_FILL_COLOR = ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE)
DISABLED_TEXT_COLOR = ft.Colors.with_opacity(0.38, ft.Colors.ON_SURFACE)
FOCUS_RING_COLOR = ft.Colors.PRIMARY
CALENDAR_FOCUS_SIDE = ft.BorderSide(FOCUS_RING_WIDTH, FOCUS_RING_COLOR)
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

CALENDAR_TODAY_TEXT = ft.TextStyle(
    size=CAPTION_SIZE,
    weight=ft.FontWeight.W_700,
    color=ACCENT_TEXT,
    height=TEXT_ROLES["caption"].height,
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
    style=ft.ButtonStyle(
        bgcolor={
            ft.ControlState.DEFAULT: ACCENT_FILL,
            ft.ControlState.DISABLED: DISABLED_FILL_COLOR,
        },
        color={
            ft.ControlState.DEFAULT: ON_ACCENT,
            ft.ControlState.DISABLED: DISABLED_TEXT_COLOR,
        },
        shape=BUTTON_SHAPE,
    ),
)
TEXT_BUTTON_THEME = ft.TextButtonTheme(style=ft.ButtonStyle(shape=BUTTON_SHAPE))
OUTLINED_BUTTON_THEME = ft.OutlinedButtonTheme(style=ft.ButtonStyle(shape=BUTTON_SHAPE))
DESTRUCTIVE_BUTTON_STYLE = ft.ButtonStyle(
    bgcolor={
        ft.ControlState.DEFAULT: DESTRUCTIVE,
        ft.ControlState.DISABLED: DISABLED_FILL_COLOR,
    },
    color={
        ft.ControlState.DEFAULT: ft.Colors.ON_ERROR,
        ft.ControlState.DISABLED: DISABLED_TEXT_COLOR,
    },
    shape=BUTTON_SHAPE,
)

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


class ThemeBuilder:
    """Build one Flet theme from a complete palette table.

    Notes
    -----
    The builder keeps the standard and high-contrast themes on one source of
    truth. Views keep using the toolkit roles, so a palette swap never needs a
    per-view branch.
    """

    @classmethod
    def build(cls, palette: typing.Mapping[str, str], *, dark: bool) -> ft.Theme:
        """Build a Flet theme for one palette.

        Parameters
        ----------
        palette : typing.Mapping[str, str]
            Complete role-to-color table.
        dark : bool
            Whether the theme is the dark variant.

        Returns
        -------
        flet.Theme
            Theme with the palette color scheme and the shared control themes.
        """
        return ft.Theme(
            color_scheme=cls._color_scheme(palette, dark=dark),
            surfaces=ft.ThemeSurfaces.NEUTRAL,
            text_theme=TEXT_THEME,
            icon_theme=ICON_THEME,
            filled_button_theme=cls._filled_button_theme(palette),
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

    @classmethod
    def _color_scheme(cls, palette: typing.Mapping[str, str], *, dark: bool) -> ft.ColorScheme:
        """Build the Material color scheme for one palette."""
        return ft.ColorScheme(
            primary=palette["accent_fill"],
            on_primary=palette["on_accent"],
            primary_container=palette["accent_container"],
            on_primary_container=palette["on_accent_container"],
            secondary=palette["muted_text"],
            on_secondary=palette["card"],
            secondary_container=palette["region"],
            on_secondary_container=palette["text"],
            tertiary=palette["accent_text"],
            on_tertiary=palette["page"] if dark else palette["on_accent"],
            error=palette["error"],
            on_error=palette["on_error"],
            error_container=palette["error_container"],
            on_error_container=palette["on_error_container"],
            surface=palette["page"],
            on_surface=palette["text"],
            on_surface_variant=palette["muted_text"],
            outline=palette["control_border"],
            outline_variant=palette["border"],
            surface_container=palette["region"],
            surface_container_low=palette["container"],
            surface_container_lowest=palette["card"],
            surface_container_high=palette["container_high"],
            surface_container_highest=palette["container_highest"],
            surface_dim=palette["page_dim"],
            surface_bright=palette["page_bright"],
            inverse_surface=palette["inverse_surface"],
            on_inverse_surface=palette["on_inverse_surface"],
            inverse_primary=palette["inverse_primary"],
            shadow="#000000",
            scrim="#000000",
        )

    @classmethod
    def _filled_button_theme(cls, palette: typing.Mapping[str, str]) -> ft.FilledButtonTheme:
        """Build the suggested-action button theme for one palette."""
        return ft.FilledButtonTheme(
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: palette["accent_fill"],
                    ft.ControlState.DISABLED: DISABLED_FILL_COLOR,
                },
                color={
                    ft.ControlState.DEFAULT: palette["on_accent"],
                    ft.ControlState.DISABLED: DISABLED_TEXT_COLOR,
                },
                shape=BUTTON_SHAPE,
            )
        )


LIGHT_THEME = ThemeBuilder.build(LIGHT_PALETTE, dark=False)
DARK_THEME = ThemeBuilder.build(DARK_PALETTE, dark=True)
HIGH_CONTRAST_LIGHT_THEME = ThemeBuilder.build(HIGH_CONTRAST_LIGHT_PALETTE, dark=False)
HIGH_CONTRAST_DARK_THEME = ThemeBuilder.build(HIGH_CONTRAST_DARK_PALETTE, dark=True)

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
