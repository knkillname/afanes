"""Tests for the shared visual theme tokens."""

from pathlib import Path

import flet as ft

import afanes.ui.theme

UI_ROOT = Path(__file__).resolve().parents[2] / "src" / "afanes" / "ui"

REQUIRED_PALETTE_ROLES = frozenset(
    {
        "page",
        "region",
        "card",
        "container",
        "container_high",
        "container_highest",
        "page_dim",
        "page_bright",
        "text",
        "muted_text",
        "accent_fill",
        "accent_text",
        "on_accent",
        "accent_container",
        "on_accent_container",
        "destructive",
        "border",
        "control_border",
        "notice",
        "error",
        "on_error",
        "error_container",
        "on_error_container",
        "inverse_surface",
        "on_inverse_surface",
        "inverse_primary",
    }
)
MODE_SPECIFIC_ROLES = frozenset(
    {
        "page",
        "region",
        "card",
        "container",
        "container_high",
        "container_highest",
        "page_dim",
        "page_bright",
        "text",
        "muted_text",
        "accent_text",
        "accent_container",
        "on_accent_container",
        "destructive",
        "border",
        "error",
        "error_container",
        "on_error_container",
        "inverse_surface",
        "on_inverse_surface",
        "inverse_primary",
    }
)
SURFACES = ("page", "region", "card", "container")
TEXT_CONTRAST = 4.5
NON_TEXT_CONTRAST = 3.0
SURFACE_RADIUS_VALUE = 12
CONTROL_RADIUS_VALUE = 9
ITEM_GAP_VALUE = 12
SECTION_GAP_VALUE = 18
PAGE_PADDING_VALUE = 24
ICON_SIZE_VALUE = 16
ICON_SIZE_LARGE_VALUE = 32
LIST_ROW_MIN_HEIGHT = 36
WINDOW_MIN_WIDTH_VALUE = 1024
WINDOW_MIN_HEIGHT_VALUE = 600
NAVIGATION_WIDTH_VALUE = 240
DRAWER_WIDTH_VALUE = 280
NAVIGATION_PADDING_VALUE = 8
BROWSER_MIN_WIDTH_VALUE = 320
BROWSER_MAX_WIDTH_VALUE = 360
PAGE_MIN_WIDTH_VALUE = 420
CONTENT_MAX_WIDTH_VALUE = 720
SHELL_WIDE_MIN_VALUE = 1100
SHELL_MEDIUM_MIN_VALUE = 1024
HEADER_HEIGHT_VALUE = 48
SELECTION_TINT = 0.10
LOG_TINT = 0.18
BASE_FONT_SIZE_VALUE = 15
SUGGESTED_LABEL_CONTRAST = 3.77
TITLE_1_RATIO = 1.81
TITLE_2_RATIO = 1.36
TITLE_3_RATIO = 1.36
TITLE_4_RATIO = 1.18
CAPTION_RATIO = 0.82
SRGB_LINEAR_THRESHOLD = 0.04045


def _channel(value: int) -> float:
    scaled = value / 255
    if scaled <= SRGB_LINEAR_THRESHOLD:
        return scaled / 12.92
    return ((scaled + 0.055) / 1.055) ** 2.4


def _luminance(color: str) -> float:
    digits = color.lstrip("#")
    red, green, blue = (int(digits[index : index + 2], 16) for index in (0, 2, 4))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _role_size(role: str) -> float:
    style = afanes.ui.theme.TEXT_ROLES[role]
    assert style.size is not None
    return style.size


class TestPalette:
    def test_every_required_role_exists_in_both_modes(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            assert set(palette) >= REQUIRED_PALETTE_ROLES

    def test_light_and_dark_tables_are_distinct(self) -> None:
        light = afanes.ui.theme.LIGHT_PALETTE
        dark = afanes.ui.theme.DARK_PALETTE

        for role in MODE_SPECIFIC_ROLES:
            assert light[role] != dark[role], role

    def test_reference_surfaces_are_pinned(self) -> None:
        light = afanes.ui.theme.LIGHT_PALETTE
        dark = afanes.ui.theme.DARK_PALETTE

        assert light["page"] == "#FAFAFB"
        assert light["region"] == "#EBEBED"
        assert light["card"] == "#FFFFFF"
        assert light["container"] == "#F3F3F5"
        assert dark["page"] == "#222226"
        assert dark["region"] == "#2E2E32"
        assert dark["card"] == "#1D1D20"
        assert dark["container"] == "#28282C"

    def test_body_text_meets_text_contrast_on_every_surface(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            for surface in SURFACES:
                assert _contrast(palette["text"], palette[surface]) >= TEXT_CONTRAST

    def test_muted_text_meets_text_contrast_on_every_surface(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            for surface in SURFACES:
                assert _contrast(palette["muted_text"], palette[surface]) >= TEXT_CONTRAST

    def test_accent_text_meets_text_contrast_on_the_note_canvas(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            assert _contrast(palette["accent_text"], palette["card"]) >= TEXT_CONTRAST

    def test_accent_fill_meets_non_text_contrast_on_every_surface(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            for surface in SURFACES:
                assert _contrast(palette["accent_fill"], palette[surface]) >= NON_TEXT_CONTRAST

    def test_control_boundaries_meet_non_text_contrast(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            for surface in SURFACES:
                assert _contrast(palette["control_border"], palette[surface]) >= NON_TEXT_CONTRAST

    def test_text_on_the_accent_fill_and_destructive_fill_is_legible(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            assert _contrast(palette["on_accent"], palette["accent_fill"]) >= NON_TEXT_CONTRAST
            assert _contrast(palette["on_error"], palette["destructive"]) >= TEXT_CONTRAST

    def test_suggested_fill_label_contrast_is_the_inherited_reference(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            assert round(_contrast(palette["on_accent"], palette["accent_fill"]), 2) == SUGGESTED_LABEL_CONTRAST

    def test_status_text_meets_text_contrast(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            assert _contrast(palette["on_error_container"], palette["card"]) >= TEXT_CONTRAST
            assert _contrast(palette["on_error_container"], palette["error_container"]) >= TEXT_CONTRAST


class TestTheme:
    def test_no_font_family_is_bundled(self) -> None:
        assert afanes.ui.theme.LIGHT_THEME.font_family is None
        assert afanes.ui.theme.DARK_THEME.font_family is None

    def test_light_and_dark_themes_are_distinct_objects(self) -> None:
        assert afanes.ui.theme.LIGHT_THEME is not afanes.ui.theme.DARK_THEME
        assert not hasattr(afanes.ui.theme, "THEME")

    def test_both_themes_expose_an_explicit_color_scheme(self) -> None:
        light = afanes.ui.theme.LIGHT_THEME.color_scheme
        dark = afanes.ui.theme.DARK_THEME.color_scheme

        assert light is not None
        assert dark is not None
        assert light.surface == afanes.ui.theme.LIGHT_PALETTE["page"]
        assert dark.surface == afanes.ui.theme.DARK_PALETTE["page"]
        assert light.tertiary == afanes.ui.theme.LIGHT_PALETTE["accent_text"]
        assert dark.tertiary == afanes.ui.theme.DARK_PALETTE["accent_text"]
        assert light.error == afanes.ui.theme.LIGHT_PALETTE["error"]
        assert dark.error == afanes.ui.theme.DARK_PALETTE["error"]

    def test_surfaces_use_neutral_theme_surfaces(self) -> None:
        assert afanes.ui.theme.LIGHT_THEME.surfaces == ft.ThemeSurfaces.NEUTRAL
        assert afanes.ui.theme.DARK_THEME.surfaces == ft.ThemeSurfaces.NEUTRAL

    def test_four_surface_roles_differ_pairwise(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            values = {palette[role] for role in SURFACES}

            assert len(values) == len(SURFACES)

    def test_light_depth_raises_the_note_canvas(self) -> None:
        palette = afanes.ui.theme.LIGHT_PALETTE

        assert _luminance(palette["card"]) > _luminance(palette["page"])
        assert _luminance(palette["page"]) > _luminance(palette["region"])

    def test_dark_depth_recesses_the_note_canvas(self) -> None:
        palette = afanes.ui.theme.DARK_PALETTE

        assert _luminance(palette["card"]) < _luminance(palette["page"])
        assert _luminance(palette["page"]) < _luminance(palette["region"])

    def test_action_and_selection_colors_are_configured(self) -> None:
        for theme in (afanes.ui.theme.LIGHT_THEME, afanes.ui.theme.DARK_THEME):
            filled = theme.filled_button_theme
            tiles = theme.list_tile_theme

            assert filled is not None
            assert filled.style is not None
            bgcolor = filled.style.bgcolor
            assert isinstance(bgcolor, dict)
            assert bgcolor[ft.ControlState.DEFAULT] == afanes.ui.theme.ACCENT_FILL
            assert tiles is not None
            assert tiles.selected_tile_color == afanes.ui.theme.SELECTED_ROW_COLOR

    def test_destructive_style_uses_the_error_fill(self) -> None:
        assert afanes.ui.theme.DESTRUCTIVE == ft.Colors.ERROR
        style = afanes.ui.theme.DESTRUCTIVE_BUTTON_STYLE
        bgcolor = style.bgcolor
        assert isinstance(bgcolor, dict)
        assert bgcolor[ft.ControlState.DEFAULT] == ft.Colors.ERROR

    def test_disabled_actions_look_insensitive(self) -> None:
        filled = afanes.ui.theme.FILLED_BUTTON_THEME.style
        destructive = afanes.ui.theme.DESTRUCTIVE_BUTTON_STYLE
        assert filled is not None
        filled_bgcolor = filled.bgcolor
        filled_color = filled.color
        destructive_bgcolor = destructive.bgcolor
        assert isinstance(filled_bgcolor, dict)
        assert isinstance(filled_color, dict)
        assert isinstance(destructive_bgcolor, dict)
        assert filled_bgcolor[ft.ControlState.DISABLED] == afanes.ui.theme.DISABLED_FILL_COLOR
        assert filled_color[ft.ControlState.DISABLED] == afanes.ui.theme.DISABLED_TEXT_COLOR
        assert filled_bgcolor[ft.ControlState.DISABLED] != filled_bgcolor[ft.ControlState.DEFAULT]
        assert destructive_bgcolor[ft.ControlState.DISABLED] == afanes.ui.theme.DISABLED_FILL_COLOR

    def test_controls_take_the_reference_corner_radius(self) -> None:
        filled = afanes.ui.theme.FILLED_BUTTON_THEME.style
        text = afanes.ui.theme.TEXT_BUTTON_THEME.style
        border = afanes.ui.theme.INPUT_DECORATION_THEME.border

        assert filled is not None
        assert isinstance(filled.shape, ft.RoundedRectangleBorder)
        assert filled.shape.radius == afanes.ui.theme.CONTROL_RADIUS
        assert text is not None
        assert isinstance(text.shape, ft.RoundedRectangleBorder)
        assert text.shape.radius == afanes.ui.theme.CONTROL_RADIUS
        assert isinstance(border, ft.OutlineInputBorder)
        assert border.border_radius == afanes.ui.theme.CONTROL_RADIUS
        assert afanes.ui.theme.SURFACE_RADIUS == SURFACE_RADIUS_VALUE
        assert afanes.ui.theme.CONTROL_RADIUS == CONTROL_RADIUS_VALUE

    def test_feedback_colors_come_from_the_tokens(self) -> None:
        theme = afanes.ui.theme.LIGHT_THEME

        assert theme.splash_color == afanes.ui.theme.SPLASH_COLOR
        assert theme.highlight_color == afanes.ui.theme.HIGHLIGHT_COLOR
        assert theme.hover_color == afanes.ui.theme.HOVER_COLOR
        assert theme.focus_color == afanes.ui.theme.FOCUS_COLOR
        assert theme.visual_density == ft.VisualDensity.STANDARD

    def test_hover_and_highlight_are_neutral_while_focus_is_accent(self) -> None:
        assert ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE) == afanes.ui.theme.HOVER_COLOR
        assert ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE) == afanes.ui.theme.HIGHLIGHT_COLOR
        assert ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE) == afanes.ui.theme.SPLASH_COLOR
        assert ft.Colors.with_opacity(0.15, ft.Colors.PRIMARY) == afanes.ui.theme.FOCUS_COLOR

    def test_toast_tokens_use_the_overlay_roles(self) -> None:
        assert afanes.ui.theme.TOAST_SURFACE_COLOR == ft.Colors.INVERSE_SURFACE
        assert afanes.ui.theme.TOAST_TEXT_COLOR == ft.Colors.ON_INVERSE_SURFACE
        assert afanes.ui.theme.TOAST_ACTION_COLOR == ft.Colors.INVERSE_PRIMARY
        assert afanes.ui.theme.TOAST_DURATION_MS > 0
        assert afanes.ui.theme.TOAST_MARGIN == afanes.ui.theme.ITEM_GAP
        assert afanes.ui.theme.TOAST_PADDING == afanes.ui.theme.ITEM_GAP

    def test_toast_roles_are_defined_in_both_palettes(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            assert palette["inverse_surface"]
            assert palette["on_inverse_surface"]

    def test_icons_use_the_reference_size_tokens(self) -> None:
        assert afanes.ui.theme.ICON_SIZE == ICON_SIZE_VALUE
        assert afanes.ui.theme.ICON_SIZE_LARGE == ICON_SIZE_LARGE_VALUE
        for theme in (afanes.ui.theme.LIGHT_THEME, afanes.ui.theme.DARK_THEME):
            icon_theme = theme.icon_theme

            assert icon_theme is not None
            assert icon_theme.size == afanes.ui.theme.ICON_SIZE

    def test_list_rows_use_the_reference_minimum_height(self) -> None:
        tiles = afanes.ui.theme.LIST_TILE_THEME

        assert tiles.min_height == LIST_ROW_MIN_HEIGHT

    def test_minimum_window_fits_the_reference_desktop_size(self) -> None:
        assert afanes.ui.theme.WINDOW_MIN_WIDTH == WINDOW_MIN_WIDTH_VALUE
        assert afanes.ui.theme.WINDOW_MIN_HEIGHT == WINDOW_MIN_HEIGHT_VALUE

    def test_shell_tokens_match_the_designed_widths(self) -> None:
        assert afanes.ui.theme.NAVIGATION_WIDTH == NAVIGATION_WIDTH_VALUE
        assert afanes.ui.theme.DRAWER_WIDTH == DRAWER_WIDTH_VALUE
        assert afanes.ui.theme.NAVIGATION_PADDING == NAVIGATION_PADDING_VALUE
        assert afanes.ui.theme.BROWSER_MIN_WIDTH == BROWSER_MIN_WIDTH_VALUE
        assert afanes.ui.theme.BROWSER_MAX_WIDTH == BROWSER_MAX_WIDTH_VALUE
        assert afanes.ui.theme.PAGE_MIN_WIDTH == PAGE_MIN_WIDTH_VALUE
        assert afanes.ui.theme.CONTENT_MAX_WIDTH == CONTENT_MAX_WIDTH_VALUE
        assert afanes.ui.theme.SHELL_WIDE_MIN == SHELL_WIDE_MIN_VALUE
        assert afanes.ui.theme.SHELL_MEDIUM_MIN == SHELL_MEDIUM_MIN_VALUE
        assert afanes.ui.theme.HEADER_HEIGHT == HEADER_HEIGHT_VALUE
        assert not hasattr(afanes.ui.theme, "LIST_WIDTH")

    def test_shell_width_relationships_hold(self) -> None:
        theme = afanes.ui.theme

        assert theme.BROWSER_MIN_WIDTH < theme.BROWSER_MAX_WIDTH
        assert theme.PAGE_MIN_WIDTH < theme.CONTENT_MAX_WIDTH
        assert theme.SHELL_MEDIUM_MIN < theme.SHELL_WIDE_MIN
        assert theme.HEADER_HEIGHT > 0
        assert theme.NAVIGATION_WIDTH > 0
        assert theme.NAVIGATION_WIDTH < theme.DRAWER_WIDTH

    def test_the_shell_fits_its_breakpoints(self) -> None:
        theme = afanes.ui.theme

        assert theme.NAVIGATION_WIDTH + theme.BROWSER_MAX_WIDTH + theme.PAGE_MIN_WIDTH <= theme.SHELL_WIDE_MIN
        assert theme.BROWSER_MAX_WIDTH + theme.PAGE_MIN_WIDTH <= theme.SHELL_MEDIUM_MIN

    def test_spacing_uses_the_adwaita_rhythm(self) -> None:
        assert afanes.ui.theme.ITEM_GAP == ITEM_GAP_VALUE
        assert afanes.ui.theme.SECTION_GAP == SECTION_GAP_VALUE
        assert afanes.ui.theme.PAGE_PADDING == PAGE_PADDING_VALUE
        assert not hasattr(afanes.ui.theme, "CARD_RADIUS")
        assert not hasattr(afanes.ui.theme, "SECTION_EDGE_WIDTH")

    def test_adoption_panel_spacing_matches_a_section_gap(self) -> None:
        assert afanes.ui.theme.ADOPTION_PANEL_GAP == afanes.ui.theme.SECTION_GAP
        assert afanes.ui.theme.ADOPTION_PANEL_GAP > 0

    def test_selection_is_a_neutral_ten_percent_shade(self) -> None:
        assert ft.Colors.with_opacity(SELECTION_TINT, ft.Colors.ON_SURFACE) == (afanes.ui.theme.SELECTED_ROW_COLOR)
        assert ft.Colors.with_opacity(0.15, afanes.ui.theme.ACCENT_FILL) != afanes.ui.theme.SELECTED_ROW_COLOR

    def test_no_per_section_hue_remains(self) -> None:
        for name in (
            "INBOX_SECTION_COLOR",
            "PROJECTS_SECTION_COLOR",
            "REFERENCES_SECTION_COLOR",
            "LOG_SECTION_COLOR",
            "REVIEW_SECTION_COLOR",
        ):
            assert not hasattr(afanes.ui.theme, name)

        assert afanes.ui.theme.SECTION_ICON_COLOR == afanes.ui.theme.MUTED_TEXT_COLOR
        assert afanes.ui.theme.LOG_ENTRY_DOT_COLOR == afanes.ui.theme.ACCENT_FILL
        assert ft.Colors.with_opacity(LOG_TINT, afanes.ui.theme.ACCENT_FILL) == afanes.ui.theme.LOG_ENTRY_TINT


class TestTextRoles:
    def test_standard_roles_are_defined(self) -> None:
        expected = {
            "title-1",
            "title-2",
            "title-3",
            "title-4",
            "heading",
            "body",
            "caption",
            "caption-heading",
        }

        assert set(afanes.ui.theme.TEXT_ROLES) == expected
        for role, style in afanes.ui.theme.TEXT_ROLES.items():
            assert style.size is not None, role
            assert style.weight is not None, role

    def test_scale_is_relative_to_the_base_size(self) -> None:
        roles = afanes.ui.theme.TEXT_ROLES
        base = afanes.ui.theme.BASE_FONT_SIZE

        assert base == BASE_FONT_SIZE_VALUE
        assert roles["title-1"].size == round(base * TITLE_1_RATIO)
        assert roles["title-2"].size == round(base * TITLE_2_RATIO)
        assert roles["title-3"].size == round(base * TITLE_3_RATIO)
        assert roles["title-4"].size == round(base * TITLE_4_RATIO)
        assert roles["heading"].size == base
        assert roles["body"].size == base
        assert roles["caption"].size == round(base * CAPTION_RATIO)
        assert roles["caption-heading"].size == round(base * CAPTION_RATIO)

    def test_hierarchy_and_weights_follow_the_reference(self) -> None:
        roles = afanes.ui.theme.TEXT_ROLES

        assert _role_size("title-1") > _role_size("title-2")
        assert _role_size("title-2") >= _role_size("title-3")
        assert _role_size("title-3") > _role_size("title-4")
        assert _role_size("title-4") > _role_size("heading")
        assert _role_size("heading") > _role_size("caption")
        assert roles["title-1"].weight == ft.FontWeight.W_800
        assert roles["title-2"].weight == ft.FontWeight.W_800
        assert roles["title-3"].weight == ft.FontWeight.W_700
        assert roles["title-4"].weight == ft.FontWeight.W_700
        assert roles["heading"].weight == ft.FontWeight.W_700
        assert roles["body"].weight == ft.FontWeight.W_400
        assert roles["caption"].weight == ft.FontWeight.W_400

    def test_caption_roles_use_the_muted_text_color(self) -> None:
        roles = afanes.ui.theme.TEXT_ROLES

        assert roles["caption"].color == afanes.ui.theme.MUTED_TEXT_COLOR
        assert roles["caption-heading"].color == afanes.ui.theme.MUTED_TEXT_COLOR
        assert roles["body"].color == afanes.ui.theme.TEXT_COLOR

    def test_both_themes_carry_the_text_theme(self) -> None:
        assert afanes.ui.theme.LIGHT_THEME.text_theme == afanes.ui.theme.TEXT_THEME
        assert afanes.ui.theme.DARK_THEME.text_theme == afanes.ui.theme.TEXT_THEME

    def test_views_use_standard_roles_and_no_material_theme_styles(self) -> None:
        sources = list(UI_ROOT.rglob("*.py"))
        text_roles = "\n".join(path.read_text(encoding="utf-8") for path in sources)

        assert 'TEXT_ROLES["' in text_roles
        assert "theme_style=ft.TextThemeStyle" not in text_roles
        assert "ft.TextStyle(size=" not in text_roles.replace((UI_ROOT / "theme.py").read_text(encoding="utf-8"), "")
