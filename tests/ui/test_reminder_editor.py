"""Tests for the inline reminder editor component."""

import asyncio
import datetime
import typing
from collections.abc import Callable, Coroutine

import flet as ft

import afanes.i18n.ui
import afanes.ui.components.reminder
from afanes.models.reminder import ClockTime, OneShot, Recurrence, Reminder, ReminderKind, Weekday

COPY = afanes.i18n.ui.UiCopy.english()
TWO_TIMES = 2
Handler = Callable[[], Coroutine[typing.Any, typing.Any, None]]


def _editor(
    saved: list[Reminder],
    removed: list[bool],
    cancelled: list[bool],
) -> afanes.ui.components.reminder.ReminderEditor:
    async def save(reminder: Reminder) -> bool:
        saved.append(reminder)
        return True

    async def remove() -> bool:
        removed.append(True)
        return True

    async def cancel() -> None:
        cancelled.append(True)

    return afanes.ui.components.reminder.ReminderEditor(save, remove, cancel, copy=COPY)


def _click(control: ft.Control) -> Callable[[], object]:
    return typing.cast("Callable[[], object]", control.__getattribute__("on_click"))


def _async_click(control: ft.Control) -> Handler:
    return typing.cast("Handler", control.__getattribute__("on_click"))


def _event(control: ft.Control) -> ft.Event[typing.Any]:
    return ft.Event(name="change", control=control)


class TestReminderEditor:
    def test_saves_a_daily_reminder(self) -> None:
        saved: list[Reminder] = []
        editor = _editor(saved, [], [])
        editor.load(None, None, allow_remove=False)

        asyncio.run(_async_click(editor.save_button)())

        assert len(saved) == 1
        assert isinstance(saved[0].schedule, Recurrence)
        assert saved[0].schedule.kind is ReminderKind.DAILY
        assert saved[0].schedule.times == (ClockTime(9, 0),)
        assert saved[0].zone is not None

    def test_saves_a_one_shot(self) -> None:
        saved: list[Reminder] = []
        editor = _editor(saved, [], [])
        editor.load(None, None, allow_remove=False)
        editor.mode_radio.value = "once"
        typing.cast("typing.Any", editor.mode_radio.on_change)(_event(editor.mode_radio))
        editor.once_field.value = "2026-11-20T09:00"

        asyncio.run(_async_click(editor.save_button)())

        assert len(saved) == 1
        assert isinstance(saved[0].schedule, OneShot)
        assert saved[0].schedule.text == "2026-11-20T09:00"

    def test_saves_selected_weekdays(self) -> None:
        saved: list[Reminder] = []
        editor = _editor(saved, [], [])
        editor.load(None, None, allow_remove=False)
        editor.kind_dropdown.value = ReminderKind.WEEKDAYS.value
        typing.cast("typing.Any", editor.kind_dropdown.on_select)(_event(editor.kind_dropdown))
        editor.weekday_checks[Weekday.MONDAY].value = True
        editor.weekday_checks[Weekday.FRIDAY].value = True

        asyncio.run(_async_click(editor.save_button)())

        assert isinstance(saved[0].schedule, Recurrence)
        assert saved[0].schedule.weekdays == (Weekday.MONDAY, Weekday.FRIDAY)

    def test_adds_and_removes_times(self) -> None:
        editor = _editor([], [], [])
        editor.load(None, None, allow_remove=False)
        editor.time_field.value = "17:30"

        _click(editor.add_time_button)()

        assert len(editor.times_column.controls) == TWO_TIMES
        row = typing.cast("ft.Row", editor.times_column.controls[-1])
        assert typing.cast("ft.Text", row.controls[0]).value == "17:30"

    def test_warns_about_a_short_month(self) -> None:
        editor = _editor([], [], [])
        editor.load(None, None, allow_remove=False)
        editor.kind_dropdown.value = ReminderKind.MONTH_DAY.value
        typing.cast("typing.Any", editor.kind_dropdown.on_select)(_event(editor.kind_dropdown))
        editor.day_dropdown.value = "31"
        typing.cast("typing.Any", editor.day_dropdown.on_select)(_event(editor.day_dropdown))

        assert editor.warning_text.visible is True
        assert editor.warning_text.value == COPY.REMINDER_SHORT_MONTH_WARNING

    def test_warns_about_a_fifth_weekday(self) -> None:
        editor = _editor([], [], [])
        editor.load(None, None, allow_remove=False)
        editor.kind_dropdown.value = ReminderKind.NTH_WEEKDAY.value
        typing.cast("typing.Any", editor.kind_dropdown.on_select)(_event(editor.kind_dropdown))
        editor.nth_dropdown.value = "5"
        typing.cast("typing.Any", editor.nth_dropdown.on_select)(_event(editor.nth_dropdown))

        assert editor.warning_text.visible is True
        assert "fifth" in (editor.warning_text.value or "")

    def test_a_one_shot_shortcut_uses_the_due_date(self) -> None:
        editor = _editor([], [], [])
        editor.load(None, datetime.date(2026, 11, 20), allow_remove=False)
        editor.mode_radio.value = "once"
        typing.cast("typing.Any", editor.mode_radio.on_change)(_event(editor.mode_radio))

        _click(editor.shortcut_day)()

        assert editor.once_field.value == "2026-11-19T09:00"

    def test_remove_is_offered_for_an_existing_reminder(self) -> None:
        removed: list[bool] = []
        editor = _editor([], removed, [])
        current = Reminder(
            schedule=Recurrence(kind=ReminderKind.DAILY, times=(ClockTime(9, 0),)),
            zone="America/Mexico_City",
        )
        editor.load(current, None, allow_remove=True)

        asyncio.run(_async_click(editor.remove_button)())

        assert removed == [True]
        assert editor.panel.visible is False

    def test_cancel_writes_nothing(self) -> None:
        cancelled: list[bool] = []
        editor = _editor([], [], cancelled)
        editor.load(None, None, allow_remove=False)
        editor.show()

        asyncio.run(_async_click(editor.cancel_button)())

        assert cancelled == [True]
        assert editor.panel.visible is False

    def test_invalid_time_keeps_the_editor_open(self) -> None:
        saved: list[Reminder] = []
        editor = _editor(saved, [], [])
        editor.load(None, None, allow_remove=False)
        editor.time_field.value = "9:00"

        _click(editor.add_time_button)()

        assert editor.error_text.visible is True
        assert saved == []
