"""Tests for content growth when the interface text scale doubles."""

import datetime

import afanes.core.log
import afanes.i18n.ui
import afanes.models.note
import afanes.ui.components.calendar
import afanes.ui.components.date_entry
import afanes.ui.theme
import afanes.ui.views.page
import afanes.ui.views.workspace
from afanes.models.note import DatePrecision

HEADERS = ("navigation_header", "browser_search_bar", "browser_header", "detail_bar")
FORM_FIELDS = (
    "type_dropdown",
    "category_field",
    "status_dropdown",
    "due_field",
    "date_field",
    "asked_by_field",
    "owner_field",
)


def _noop() -> None:
    return None


async def _noop_async() -> None:
    return None


async def _ignore(_value: object) -> None:
    return None


def _month() -> afanes.core.log.CalendarMonth:
    return afanes.core.log.CalendarMonth(
        year=2025,
        month=10,
        first_weekday=2,
        days_in_month=31,
        days=tuple(afanes.core.log.CalendarDay(day=day, count=0) for day in range(1, 32)),
        month_count=0,
        year_count=0,
    )


def _actions() -> afanes.ui.views.workspace.WorkspaceActions:
    return afanes.ui.views.workspace.WorkspaceActions(
        _noop,
        _noop_async,
        _noop_async,
        _noop_async,
    )


class TestWorkspaceLargeText:
    def test_text_bearing_headers_grow_from_a_minimum(self) -> None:
        view = afanes.ui.views.workspace.WorkspaceView(_actions())

        for name in HEADERS:
            header = getattr(view, name)

            assert header.height is None
            assert header.min_height == afanes.ui.theme.HEADER_HEIGHT


class TestPageFormLargeText:
    def test_form_fields_grow_from_a_minimum(self) -> None:
        view = afanes.ui.views.page.PageView(afanes.ui.views.page.PageActions(update=_noop))

        for name in FORM_FIELDS:
            field = getattr(view, name)

            assert field.height is None
            assert field.min_height == afanes.ui.theme.PAGE_FORM_FIELD_HEIGHT


class TestCalendarLargeText:
    def test_day_cells_grow_from_a_minimum(self) -> None:
        grid = afanes.ui.components.calendar.CalendarGrid(lambda _day: None)

        grid.build(_month())

        for button in grid.day_buttons.values():
            assert button.height is None
            assert button.min_height == afanes.ui.theme.CALENDAR_CELL_HEIGHT


class TestDatePickerLargeText:
    def test_mode_and_period_cells_grow_from_a_minimum(self) -> None:
        dialog = afanes.ui.components.date_entry.DatePickerDialog(
            None,
            frozenset({DatePrecision.DAY, DatePrecision.MONTH, DatePrecision.YEAR}),
            _ignore,
            _noop_async,
            today=datetime.date(2026, 11, 15),
        )

        for button in dialog.mode_buttons.values():
            assert button.height is None
            assert button.min_height == afanes.ui.theme.DATE_PICKER_PERIOD_HEIGHT

        dialog.set_precision(DatePrecision.MONTH)

        for button in dialog.month_buttons.values():
            assert button.height is None
            assert button.min_height == afanes.ui.theme.DATE_PICKER_PERIOD_HEIGHT
