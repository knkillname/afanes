"""Tests for the shared visual theme tokens."""

import flet as ft

import afanes.ui.theme

TEXT_STYLE_LEVELS = 3


class TestTheme:
    def test_no_font_family_is_bundled(self) -> None:
        assert afanes.ui.theme.THEME.font_family is None

    def test_text_styles_differ_in_hierarchy(self) -> None:
        styles = {
            (style.size, style.weight, style.color)
            for style in (
                afanes.ui.theme.PAGE_TITLE_TEXT_STYLE,
                afanes.ui.theme.SECTION_LABEL_TEXT_STYLE,
                afanes.ui.theme.METADATA_TEXT_STYLE,
            )
        }

        assert len(styles) == TEXT_STYLE_LEVELS
        assert afanes.ui.theme.PAGE_TITLE_TEXT_STYLE.size is not None
        assert afanes.ui.theme.PAGE_TITLE_TEXT_STYLE.weight == ft.FontWeight.W_600

    def test_action_and_selection_colors_are_configured(self) -> None:
        filled = afanes.ui.theme.THEME.filled_button_theme
        tiles = afanes.ui.theme.THEME.list_tile_theme

        assert filled is not None
        assert filled.style is not None
        assert filled.style.bgcolor == afanes.ui.theme.ACTION_COLOR
        assert tiles is not None
        assert tiles.selected_tile_color == afanes.ui.theme.SELECTED_ROW_COLOR
