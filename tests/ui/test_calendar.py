"""Tests for the Log month calendar component."""

import typing

import flet as ft

import afanes.core.log
import afanes.ui.components.calendar as calendar_component
import afanes.ui.theme


def _month(
    *, day_counts: dict[int, int] | None = None, month_count: int = 0, year_count: int = 0
) -> afanes.core.log.CalendarMonth:
    counts = day_counts or {}
    return afanes.core.log.CalendarMonth(
        year=2025,
        month=10,
        first_weekday=2,
        days_in_month=31,
        days=tuple(afanes.core.log.CalendarDay(day=day, count=counts.get(day, 0)) for day in range(1, 32)),
        month_count=month_count,
        year_count=year_count,
    )


class TestLogCalendar:
    def test_builds_a_month_grid_with_accents(self) -> None:
        selected: list[int] = []
        calendar = calendar_component.LogCalendar(selected.append, lambda: None, lambda: None)

        control = calendar.build(_month(day_counts={12: 2}, month_count=1, year_count=1))

        assert control.key == "log-calendar"
        assert calendar.title.value == "October 2025"
        assert calendar.month_dot.visible is True
        assert calendar.year_dot.visible is True
        assert calendar.day_buttons[12].data == {"day": 12, "count": 2}
        style = calendar.day_buttons[12].style
        assert style is not None
        assert style.bgcolor == afanes.ui.theme.LOG_ENTRY_TINT
        plain_style = calendar.day_buttons[13].style
        assert plain_style is None or plain_style.bgcolor is None

    def test_day_dots_follow_the_filtered_counts(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)

        calendar.build(_month(day_counts={12: 0, 13: 1}))

        hidden = calendar.day_buttons[12].content
        shown = calendar.day_buttons[13].content
        assert isinstance(hidden, ft.Column)
        assert isinstance(shown, ft.Column)
        assert isinstance(hidden.controls[1], ft.Container)
        assert isinstance(shown.controls[1], ft.Container)
        assert hidden.controls[1].visible is False
        assert shown.controls[1].visible is True

    def test_empty_month_hides_header_dots(self) -> None:
        calendar = calendar_component.LogCalendar(lambda _day: None, lambda: None, lambda: None)

        calendar.build(_month())

        assert calendar.month_dot.visible is False
        assert calendar.year_dot.visible is False
        assert all(button.style is None or button.style.bgcolor is None for button in calendar.day_buttons.values())

    def test_day_click_reports_the_day(self) -> None:
        selected: list[int] = []
        calendar = calendar_component.LogCalendar(selected.append, lambda: None, lambda: None)
        calendar.build(_month())
        handler = calendar.day_buttons[12].on_click
        assert handler is not None

        typing.cast("typing.Callable[[], None]", handler)()

        assert selected == [12]

    def test_month_navigation_forwards(self) -> None:
        calls: list[str] = []
        calendar = calendar_component.LogCalendar(
            lambda _day: None,
            lambda: calls.append("previous"),
            lambda: calls.append("next"),
        )
        calendar.build(_month())
        previous = calendar.prev_button.on_click
        upcoming = calendar.next_button.on_click
        assert previous is not None
        assert upcoming is not None

        typing.cast("typing.Callable[[], None]", previous)()
        typing.cast("typing.Callable[[], None]", upcoming)()

        assert calls == ["previous", "next"]
