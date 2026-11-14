"""Tests for the adaptive label-field flow."""

import typing

import flet as ft

import afanes.ui.components.field_flow
import afanes.ui.theme

ONE_ROW = 1
TWO_ROWS = 2
THREE_ROWS = 3
TWO_FIELDS = 2
THREE_FIELDS = 3
FIVE_FIELDS = 5
FIRST_ROW_COUNT = 3
SECOND_ROW_COUNT = 2


def _fields(count: int) -> list[ft.Text]:
    return [ft.Text(f"Field {index}") for index in range(count)]


def _rows(flow: afanes.ui.components.field_flow.FieldFlow) -> list[ft.Row]:
    return [typing.cast("ft.Row", control) for control in flow.column.controls]


class TestFieldFlow:
    def test_a_wide_pane_fills_one_row(self) -> None:
        fields = _fields(THREE_FIELDS)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(1200)

        rows = _rows(flow)
        assert len(rows) == ONE_ROW
        assert rows[0].controls == fields
        assert all(field.expand is True for field in fields)

    def test_an_odd_count_fills_every_run(self) -> None:
        fields = _fields(FIVE_FIELDS)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(700)

        rows = _rows(flow)
        assert len(rows) == TWO_ROWS
        assert len(rows[0].controls) == FIRST_ROW_COUNT
        assert len(rows[1].controls) == SECOND_ROW_COUNT
        assert all(field.expand is True for field in fields)

    def test_a_narrow_pane_stacks_the_fields(self) -> None:
        fields = _fields(THREE_FIELDS)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(300)

        rows = _rows(flow)
        assert len(rows) == THREE_ROWS
        assert all(len(row.controls) == ONE_ROW for row in rows)

    def test_hidden_controls_take_no_span(self) -> None:
        fields = _fields(THREE_FIELDS)
        fields[1].visible = False
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(1200)

        rows = _rows(flow)
        assert len(rows) == ONE_ROW
        assert rows[0].controls == [fields[0], fields[2]]
        assert fields[0].expand is True
        assert fields[2].expand is True

    def test_a_visibility_change_reflows_the_row(self) -> None:
        fields = _fields(THREE_FIELDS)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)
        flow.layout(1200)
        fields[1].visible = False
        flow.layout(1200)
        hidden_row = _rows(flow)[0]

        fields[1].visible = True
        flow.layout(1200)
        visible_row = _rows(flow)[0]

        assert hidden_row.controls == [fields[0], fields[2]]
        assert visible_row.controls == fields

    def test_no_visible_controls_empties_the_flow(self) -> None:
        fields = _fields(TWO_FIELDS)
        for field in fields:
            field.visible = False
        flow = afanes.ui.components.field_flow.FieldFlow(fields)

        flow.layout(1200)

        assert flow.column.controls == []

    def test_a_non_positive_width_keeps_the_current_rows(self) -> None:
        fields = _fields(THREE_FIELDS)
        flow = afanes.ui.components.field_flow.FieldFlow(fields)
        flow.layout(1200)
        rows = _rows(flow)

        flow.layout(0)

        assert _rows(flow) == rows

    def test_the_rows_use_the_theme_tokens(self) -> None:
        flow = afanes.ui.components.field_flow.FieldFlow(_fields(THREE_FIELDS))
        flow.layout(1200)

        rows = _rows(flow)
        assert flow.column.spacing == afanes.ui.theme.ITEM_GAP
        assert rows[0].spacing == afanes.ui.theme.ITEM_GAP
        assert rows[0].vertical_alignment == ft.CrossAxisAlignment.START
