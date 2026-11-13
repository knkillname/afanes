"""Tests for the shared visual theme tokens."""

import re
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
        "border",
        "error",
        "on_error",
        "error_container",
        "on_error_container",
        "inverse_surface",
        "on_inverse_surface",
        "inverse_primary",
    }
)
SURFACES = ("page", "region", "card", "container")
TEXT_ROLES = ("text", "muted_text", "accent_text")
TEXT_CONTRAST = 4.5
NON_TEXT_CONTRAST = 3.0
SURFACE_RADIUS_VALUE = 12
CONTROL_RADIUS_VALUE = 8
ITEM_GAP_VALUE = 12
SECTION_GAP_VALUE = 18
PAGE_PADDING_VALUE = 24
SELECTION_TINT = 0.15
LOG_TINT = 0.18
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


class TestPalette:
    def test_every_required_role_exists_in_both_modes(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            assert set(palette) >= REQUIRED_PALETTE_ROLES

    def test_light_and_dark_tables_are_distinct(self) -> None:
        light = afanes.ui.theme.LIGHT_PALETTE
        dark = afanes.ui.theme.DARK_PALETTE

        for role in MODE_SPECIFIC_ROLES:
            assert light[role] != dark[role], role

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
        palette = afanes.ui.theme.LIGHT_PALETTE

        assert _contrast(palette["on_accent"], palette["accent_fill"]) >= NON_TEXT_CONTRAST
        assert _contrast(palette["on_accent"], palette["destructive"]) >= TEXT_CONTRAST

    def test_status_text_meets_text_contrast(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            assert _contrast(palette["error"], palette["card"]) >= TEXT_CONTRAST


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

    def test_surfaces_use_neutral_theme_surfaces(self) -> None:
        assert afanes.ui.theme.LIGHT_THEME.surfaces == ft.ThemeSurfaces.NEUTRAL
        assert afanes.ui.theme.DARK_THEME.surfaces == ft.ThemeSurfaces.NEUTRAL

    def test_surface_roles_differ_pairwise(self) -> None:
        for palette in (afanes.ui.theme.LIGHT_PALETTE, afanes.ui.theme.DARK_PALETTE):
            page, region, card = (palette[role] for role in ("page", "region", "card"))

            assert page != region
            assert region != card
            assert card != page

    def test_the_note_canvas_is_the_brightest_light_surface(self) -> None:
        palette = afanes.ui.theme.LIGHT_PALETTE

        assert _luminance(palette["card"]) > _luminance(palette["page"])
        assert _luminance(palette["page"]) > _luminance(palette["region"])

    def test_action_and_selection_colors_are_configured(self) -> None:
        for theme in (afanes.ui.theme.LIGHT_THEME, afanes.ui.theme.DARK_THEME):
            filled = theme.filled_button_theme
            tiles = theme.list_tile_theme

            assert filled is not None
            assert filled.style is not None
            assert filled.style.bgcolor == afanes.ui.theme.ACCENT_FILL
            assert tiles is not None
            assert tiles.selected_tile_color == afanes.ui.theme.SELECTED_ROW_COLOR

    def test_controls_take_the_standard_corner_radius(self) -> None:
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

    def test_spacing_uses_the_adwaita_rhythm(self) -> None:
        assert afanes.ui.theme.ITEM_GAP == ITEM_GAP_VALUE
        assert afanes.ui.theme.SECTION_GAP == SECTION_GAP_VALUE
        assert afanes.ui.theme.PAGE_PADDING == PAGE_PADDING_VALUE
        assert not hasattr(afanes.ui.theme, "CARD_RADIUS")

    def test_adoption_panel_spacing_matches_a_section_gap(self) -> None:
        assert afanes.ui.theme.ADOPTION_PANEL_GAP == afanes.ui.theme.SECTION_GAP
        assert afanes.ui.theme.ADOPTION_PANEL_GAP > 0

    def test_selection_is_a_fifteen_percent_accent_tint(self) -> None:
        assert ft.Colors.with_opacity(SELECTION_TINT, afanes.ui.theme.ACCENT_FILL) == (
            afanes.ui.theme.SELECTED_ROW_COLOR
        )
        assert afanes.ui.theme.SELECTED_ROW_COLOR.endswith(",0.15")

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


class TestTextTheme:
    def test_text_theme_defines_every_standard_role(self) -> None:
        roles = {
            "display_large",
            "display_medium",
            "display_small",
            "headline_large",
            "headline_medium",
            "headline_small",
            "title_large",
            "title_medium",
            "title_small",
            "body_large",
            "body_medium",
            "body_small",
            "label_large",
            "label_medium",
            "label_small",
        }

        theme = afanes.ui.theme.TEXT_THEME

        for role in roles:
            style = getattr(theme, role)
            assert style is not None, role
            assert style.size is not None, role

    def test_hierarchy_comes_from_the_named_roles(self) -> None:
        theme = afanes.ui.theme.TEXT_THEME

        assert theme.headline_medium is not None
        assert theme.headline_medium.size is not None
        assert theme.label_medium is not None
        assert theme.label_medium.size is not None
        assert theme.headline_medium.size > theme.label_medium.size
        assert theme.headline_medium.weight == ft.FontWeight.W_700

    def test_metadata_role_uses_the_muted_text_color(self) -> None:
        style = afanes.ui.theme.TEXT_THEME.body_small

        assert style is not None
        assert style.color == afanes.ui.theme.MUTED_TEXT_COLOR

    def test_both_themes_carry_the_text_theme(self) -> None:
        assert afanes.ui.theme.LIGHT_THEME.text_theme == afanes.ui.theme.TEXT_THEME
        assert afanes.ui.theme.DARK_THEME.text_theme == afanes.ui.theme.TEXT_THEME

    def test_every_role_used_by_a_view_resolves_through_the_theme(self) -> None:
        used: set[str] = set()
        for path in UI_ROOT.rglob("*.py"):
            used.update(re.findall(r"ft\.TextThemeStyle\.([A-Z_]+)", path.read_text(encoding="utf-8")))

        assert used
        theme = afanes.ui.theme.TEXT_THEME
        for role in used:
            assert getattr(theme, role.lower()) is not None, role
