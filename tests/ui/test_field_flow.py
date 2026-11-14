"""Tests for the adaptive label-field flow."""

import flet as ft

import afanes.ui.components.field_flow
import afanes.ui.theme

FULL_ROW = 12
HALF_ROW = 6
QUARTER_ROW = 4


def _fields(count: int) -> list[ft.Text]:
    return [ft.Text(f"Field {index}") for index in range(count)]


class TestFieldFlow:
    def test_a_wide_pane_fills_one_row(self) -> None:
        fields = _fields(3)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(1200)

        assert [field.col for field in fields] == [QUARTER_ROW, QUARTER_ROW, QUARTER_ROW]

    def test_an_odd_count_fills_every_run(self) -> None:
        fields = _fields(5)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(700)

        assert [field.col for field in fields] == [QUARTER_ROW, QUARTER_ROW, QUARTER_ROW, HALF_ROW, HALF_ROW]

    def test_a_narrow_pane_stacks_the_fields(self) -> None:
        fields = _fields(3)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(300)

        assert [field.col for field in fields] == [FULL_ROW, FULL_ROW, FULL_ROW]

    def test_hidden_controls_take_no_span(self) -> None:
        fields = _fields(3)
        fields[1].visible = False
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(1200)

        assert fields[0].col == HALF_ROW
        assert fields[1].col == FULL_ROW
        assert fields[2].col == HALF_ROW

    def test_a_visibility_change_reflows_the_row(self) -> None:
        fields = _fields(3)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)
        flow.layout(300)

        fields[1].visible = False
        flow.layout(1200)
        hidden_spans = [field.col for field in (fields[0], fields[2])]
        fields[1].visible = True
        flow.layout(1200)

        assert hidden_spans == [HALF_ROW, HALF_ROW]
        assert [field.col for field in fields] == [QUARTER_ROW, QUARTER_ROW, QUARTER_ROW]

    def test_a_non_positive_width_keeps_the_current_spans(self) -> None:
        fields = _fields(3)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)
        flow.layout(1200)

        flow.layout(0)

        assert [field.col for field in fields] == [QUARTER_ROW, QUARTER_ROW, QUARTER_ROW]

    def test_the_row_uses_the_theme_tokens(self) -> None:
        flow = afanes.ui.components.field_flow.FieldFlow(_fields(3))

        assert flow.row.columns == afanes.ui.theme.FIELD_FLOW_COLUMNS
        assert flow.row.spacing == afanes.ui.theme.ITEM_GAP
        assert flow.row.run_spacing == afanes.ui.theme.ITEM_GAP
