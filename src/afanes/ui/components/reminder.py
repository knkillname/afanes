# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inline reminder editor used by the page view.

The component owns the recurrence form, the time list, the IANA zone picker,
and the one-shot shortcuts. It reports a complete :class:`Reminder` to its
caller and never reads or writes the vault.
"""

import datetime
import zoneinfo
from collections.abc import Awaitable, Callable

import flet as ft
import tzlocal

import afanes.i18n.ui
import afanes.models.note
import afanes.ui.theme
from afanes.models.reminder import ClockTime, OneShot, Recurrence, Reminder, ReminderKind, Weekday
from afanes.ui.components.date_entry import DatePickerActions, DatePickerButton, PickDate
from afanes.ui.components.panel import Panel

_ENGLISH_COPY = afanes.i18n.ui.UiCopy.english()
_DAYS_IN_MONTH = 31
_DAYS_IN_WEEK = 7
_SHORT_MONTH_START = 29


class ReminderEditor:
    """Edit one reminder without leaving the page.

    Parameters
    ----------
    on_save : Callable[[Reminder], Awaitable[bool]]
        Command that writes the chosen reminder. A true result closes the
        editor.
    on_remove : Callable[[], Awaitable[bool]]
        Command that removes the reminder. A true result closes the editor.
    on_cancel : Callable[[], Awaitable[None]]
        Command that closes the editor without writing.
    copy : afanes.i18n.ui.UiCopy
        Active interface catalog.
    pick_date : afanes.ui.components.date_entry.PickDate | None
        Command that opens the day-only date picker, or ``None`` when the host
        does not provide one.

    Notes
    -----
    The panel starts hidden. Call :meth:`load` with the current reminder and
    the project due date before showing it. Saving reports one complete
    reminder; the page view owns the write and its conflict guard.
    """

    def __init__(
        self,
        on_save: Callable[[Reminder], Awaitable[bool]],
        on_remove: Callable[[], Awaitable[bool]],
        on_cancel: Callable[[], Awaitable[None]],
        *,
        copy: afanes.i18n.ui.UiCopy = _ENGLISH_COPY,
        pick_date: PickDate | None = None,
    ) -> None:
        """Build the reminder controls.

        Parameters
        ----------
        on_save : collections.abc.Callable[[Reminder], collections.abc.Awaitable[bool]]
            Write the chosen reminder.
        on_remove : collections.abc.Callable[[], collections.abc.Awaitable[bool]]
            Remove the reminder.
        on_cancel : collections.abc.Callable[[], collections.abc.Awaitable[None]]
            Close without writing.
        copy : afanes.i18n.ui.UiCopy
            Active interface catalog.
        pick_date : afanes.ui.components.date_entry.PickDate | None
            Command that opens the day-only date picker, or ``None`` when the
            host does not provide one.
        """
        self._copy = copy
        self._pick_date = pick_date
        self._on_save = on_save
        self._on_remove = on_remove
        self._on_cancel = on_cancel
        self._zone_names = tuple(sorted(zoneinfo.available_timezones()))
        self._system_zone = tzlocal.get_localzone_name()
        self._times: list[ClockTime] = [ClockTime(hour=9, minute=0)]
        self._mode = "recurrence"
        self._due_date: datetime.date | None = None
        self._allow_remove = False
        self._build_controls()
        self.panel = Panel(
            self._copy.REVIEW_REMINDER_TITLE,
            ft.Column(
                controls=[
                    self.mode_row,
                    self.recurrence_fields,
                    self.once_group,
                    self.zone_field,
                    self.warning_text,
                    self.error_text,
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
                scroll=ft.ScrollMode.AUTO,
            ),
            [self.cancel_button, self.remove_button, self.save_button],
        ).build()
        self.panel.visible = False

    def load(
        self,
        reminder: Reminder | None,
        due_date: datetime.date | None,
        *,
        allow_remove: bool,
    ) -> None:
        """Populate the editor for one page.

        Parameters
        ----------
        reminder : Reminder | None
            Current valid reminder, or ``None`` for a page without one.
        due_date : datetime.date | None
            Project due date used by the one-shot shortcuts.
        allow_remove : bool
            Whether the page has a raw reminder that can be removed, including
            a malformed one.
        """
        self._due_date = due_date
        self._allow_remove = allow_remove
        self.remove_button.visible = allow_remove
        self.error_text.visible = False
        self.warning_text.visible = False
        if reminder is None:
            self._mode = "recurrence"
            self._times = [ClockTime(hour=9, minute=0)]
            self.kind_dropdown.value = ReminderKind.DAILY.value
            self.zone_field.value = self._system_zone
            self.once_field.value = ""
        else:
            self._mode = "recurrence" if isinstance(reminder.schedule, Recurrence) else "once"
            self.zone_field.value = reminder.resolved_zone(self._system_zone)
            if isinstance(reminder.schedule, Recurrence):
                self._times = list(reminder.schedule.times)
                self.kind_dropdown.value = reminder.schedule.kind.value
                self._load_recurrence(reminder.schedule)
                self.once_field.value = ""
            else:
                self._times = [ClockTime(hour=reminder.schedule.local.hour, minute=reminder.schedule.local.minute)]
                self.once_field.value = reminder.schedule.text
        self.mode_radio.value = self._mode
        self._render_times()
        self._sync_visibility()

    def show(self) -> None:
        """Make the editor panel visible."""
        self.panel.visible = True

    def hide(self) -> None:
        """Hide the editor panel."""
        self.panel.visible = False

    def _build_controls(self) -> None:
        """Create the form controls and their groups."""
        self.mode_radio = ft.RadioGroup(
            content=ft.Row(
                controls=[
                    ft.Radio(value="recurrence", label=self._copy.REMINDER_MODE_RECURRING),
                    ft.Radio(value="once", label=self._copy.REMINDER_MODE_ONCE),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            ),
            value="recurrence",
            on_change=self._mode_changed,
        )
        self.mode_row = ft.Row(
            controls=[self.mode_radio],
            spacing=afanes.ui.theme.ITEM_GAP,
            wrap=True,
        )
        self.kind_dropdown = ft.Dropdown(
            label=self._copy.REVIEW_REMINDER_TITLE,
            options=[ft.dropdown.Option(key=key, text=value) for key, value in self._copy.REMINDER_KIND_LABELS.items()],
            value=ReminderKind.DAILY.value,
            on_select=self._kind_changed,
            key="reminder-kind",
        )
        self.weekday_checks = {
            weekday: ft.Checkbox(label=name)
            for weekday, name in zip(Weekday, self._copy.locale_format.weekday_names(), strict=True)
        }
        self.weekday_group = ft.Row(
            controls=list(self.weekday_checks.values()),
            spacing=afanes.ui.theme.ITEM_GAP,
            wrap=True,
        )
        self.day_dropdown = ft.Dropdown(
            label=self._copy.REMINDER_DAY_LABEL,
            options=[ft.dropdown.Option(key=str(day), text=str(day)) for day in range(1, _DAYS_IN_MONTH + 1)],
            value="1",
            on_select=self._validate_warning,
            key="reminder-day",
        )
        self.day_group = ft.Row(controls=[self.day_dropdown], spacing=afanes.ui.theme.ITEM_GAP)
        self.nth_dropdown = ft.Dropdown(
            label=self._copy.REMINDER_ORDINAL_LABEL,
            options=[
                ft.dropdown.Option(key=str(number), text=self._copy.REMINDER_ORDINAL_LABELS[str(number)])
                for number in range(1, _DAYS_IN_WEEK - 2)
            ],
            value="1",
            on_select=self._validate_warning,
            key="reminder-nth",
        )
        self.weekday_dropdown = ft.Dropdown(
            label=self._copy.REMINDER_WEEKDAY_LABEL,
            options=[
                ft.dropdown.Option(key=weekday.value, text=name)
                for weekday, name in zip(
                    Weekday,
                    self._copy.locale_format.weekday_names(),
                    strict=True,
                )
            ],
            value=Weekday.MONDAY.value,
            key="reminder-weekday",
        )
        self.nth_group = ft.Row(
            controls=[self.nth_dropdown, self.weekday_dropdown],
            spacing=afanes.ui.theme.ITEM_GAP,
            wrap=True,
        )
        self.last_weekday_dropdown = ft.Dropdown(
            label=self._copy.REMINDER_WEEKDAY_LABEL,
            options=[
                ft.dropdown.Option(key=weekday.value, text=name)
                for weekday, name in zip(
                    Weekday,
                    self._copy.locale_format.weekday_names(),
                    strict=True,
                )
            ],
            value=Weekday.MONDAY.value,
            key="reminder-last-weekday",
        )
        self.last_weekday_group = ft.Row(
            controls=[self.last_weekday_dropdown],
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        self.times_label = ft.Text(self._copy.REMINDER_TIMES_LABEL, style=afanes.ui.theme.TEXT_ROLES["caption"])
        self.times_column = ft.Column(controls=[], spacing=afanes.ui.theme.NO_GAP)
        self.time_field = ft.TextField(
            label=self._copy.REMINDER_TIMES_LABEL,
            hint_text=self._copy.REMINDER_TIME_HINT,
            width=afanes.ui.theme.REMINDER_TIME_FIELD_WIDTH,
            key="reminder-time",
        )
        self.add_time_button = ft.TextButton(
            content=self._copy.REMINDER_ADD_TIME,
            on_click=self._add_time,
            key="reminder-add-time",
        )
        self.recurrence_fields = ft.Column(
            controls=[
                self.kind_dropdown,
                self.weekday_group,
                self.day_group,
                self.nth_group,
                self.last_weekday_group,
                self.times_label,
                self.times_column,
                ft.Row(
                    controls=[self.time_field, self.add_time_button],
                    spacing=afanes.ui.theme.ITEM_GAP,
                    wrap=True,
                ),
            ],
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        self.once_field = ft.TextField(
            label=self._copy.REMINDER_ONCE_LABEL,
            hint_text=self._copy.REMINDER_ONCE_HINT,
            key="reminder-once",
        )
        if self._pick_date is not None:
            DatePickerButton(
                DatePickerActions(self._pick_once_date, self._apply_once_date),
                copy=self._copy,
            ).attach(self.once_field)
        self.shortcut_due = ft.TextButton(
            content=self._copy.REMINDER_SHORTCUT_DUE,
            on_click=self._due_shortcut,
            key="reminder-shortcut-due",
        )
        self.shortcut_day = ft.TextButton(
            content=self._copy.REMINDER_SHORTCUT_DAY_BEFORE,
            on_click=self._day_before_shortcut,
            key="reminder-shortcut-day",
        )
        self.shortcut_week = ft.TextButton(
            content=self._copy.REMINDER_SHORTCUT_WEEK_BEFORE,
            on_click=self._week_before_shortcut,
            key="reminder-shortcut-week",
        )
        self.shortcut_row = ft.Row(
            controls=[self.shortcut_due, self.shortcut_day, self.shortcut_week],
            spacing=afanes.ui.theme.ITEM_GAP,
            wrap=True,
        )
        self.once_group = ft.Column(
            controls=[self.once_field, self.shortcut_row],
            spacing=afanes.ui.theme.ITEM_GAP,
        )
        self.zone_field = ft.Dropdown(
            label=self._copy.REMINDER_ZONE_LABEL,
            hint_text=self._copy.REMINDER_ZONE_HINT,
            options=[ft.dropdown.Option(key=name, text=name) for name in self._zone_names],
            value=self._system_zone,
            editable=True,
            enable_filter=True,
            key="reminder-zone",
        )
        self.warning_text = ft.Text("", color=afanes.ui.theme.MUTED_TEXT_COLOR, selectable=True)
        self.warning_text.visible = False
        self.error_text = ft.Text("", color=afanes.ui.theme.MUTED_TEXT_COLOR, selectable=True)
        self.error_text.visible = False
        self.cancel_button = ft.TextButton(
            content=self._copy.CANCEL_ACTION,
            on_click=self._cancel,
            key="reminder-cancel",
        )
        self.remove_button = ft.TextButton(
            content=self._copy.REMINDER_REMOVE,
            on_click=self._remove,
            key="reminder-remove",
        )
        self.save_button = ft.OutlinedButton(
            content=self._copy.REMINDER_SAVE,
            on_click=self._save,
            key="reminder-save",
        )

    def _load_recurrence(self, recurrence: Recurrence) -> None:
        """Fill the kind-specific controls from a parsed recurrence."""
        for weekday, checkbox in self.weekday_checks.items():
            checkbox.value = weekday in recurrence.weekdays
        self.day_dropdown.value = str(recurrence.day or 1)
        self.nth_dropdown.value = str(recurrence.nth or 1)
        if recurrence.weekday is not None:
            self.weekday_dropdown.value = recurrence.weekday.value
            self.last_weekday_dropdown.value = recurrence.weekday.value

    def _mode_changed(self, event: ft.Event[ft.RadioGroup]) -> None:
        """Switch between recurrence and one-shot fields."""
        self._mode = event.control.value or "recurrence"
        self._sync_visibility()

    def _kind_changed(self, _event: ft.Event[ft.Dropdown]) -> None:
        """Switch the recurrence-kind fields."""
        self._sync_visibility()

    def _validate_warning(self, _event: object = None) -> None:
        """Show a warning for a monthly day or fifth weekday that can skip."""
        self._sync_visibility()

    def _sync_visibility(self) -> None:
        """Show only the fields that belong to the chosen mode and kind."""
        recurring = self._mode == "recurrence"
        kind_value = self.kind_dropdown.value or ReminderKind.DAILY.value
        try:
            kind = ReminderKind(kind_value)
        except ValueError:
            kind = ReminderKind.DAILY
        self.recurrence_fields.visible = recurring
        self.once_group.visible = not recurring
        self.weekday_group.visible = recurring and kind is ReminderKind.WEEKDAYS
        self.day_group.visible = recurring and kind is ReminderKind.MONTH_DAY
        self.nth_group.visible = recurring and kind is ReminderKind.NTH_WEEKDAY
        self.last_weekday_group.visible = recurring and kind is ReminderKind.LAST_WEEKDAY
        self.shortcut_row.visible = not recurring and self._due_date is not None
        warning = ""
        if recurring and kind is ReminderKind.MONTH_DAY and self._day_value() >= _SHORT_MONTH_START:
            warning = self._copy.REMINDER_SHORT_MONTH_WARNING
        if recurring and kind is ReminderKind.NTH_WEEKDAY and self.nth_dropdown.value == "5":
            weekday = self._weekday_name(self.weekday_dropdown.value)
            warning = self._copy.REMINDER_FIFTH_WEEKDAY_WARNING.format(weekday=weekday)
        self.warning_text.value = warning
        self.warning_text.visible = bool(warning)

    def _day_value(self) -> int:
        """Return the selected day of month as an integer."""
        try:
            return int(self.day_dropdown.value or "1")
        except ValueError:
            return 1

    def _weekday_name(self, value: str | None) -> str:
        """Return the localized full name for a weekday value."""
        try:
            weekday = Weekday(value or Weekday.MONDAY.value)
        except ValueError:
            weekday = Weekday.MONDAY
        return self._copy.locale_format.weekday_names()[weekday.position]

    def _add_time(self, _event: object = None) -> None:
        """Add the typed time to the list."""
        try:
            time = ClockTime.from_text((self.time_field.value or "").strip())
        except ValueError:
            self._show_error()
            return
        if time not in self._times:
            self._times.append(time)
            self._times.sort()
        self.time_field.value = ""
        self.error_text.visible = False
        self._render_times()

    def _remove_time(self, time: ClockTime) -> None:
        """Remove one time from the list."""
        self._times = [value for value in self._times if value != time]
        self._render_times()

    def _remove_time_handler(self, time: ClockTime) -> Callable[[], None]:
        """Bind a remove button to one time."""

        def remove() -> None:
            self._remove_time(time)

        return remove

    def _render_times(self) -> None:
        """Rebuild the time rows from the current list."""
        self.times_column.controls = [
            ft.Row(
                controls=[
                    ft.Text(time.text, style=afanes.ui.theme.TEXT_ROLES["caption"]),
                    ft.TextButton(
                        content=self._copy.REMINDER_REMOVE_TIME,
                        on_click=self._remove_time_handler(time),
                    ),
                ],
                spacing=afanes.ui.theme.ITEM_GAP,
            )
            for time in self._times
        ]

    def _due_shortcut(self, _event: object = None) -> None:
        """Fill the one-shot with the project due date."""
        self._fill_shortcut(0)

    def _day_before_shortcut(self, _event: object = None) -> None:
        """Fill the one-shot with one day before the project due date."""
        self._fill_shortcut(1)

    def _week_before_shortcut(self, _event: object = None) -> None:
        """Fill the one-shot with one week before the project due date."""
        self._fill_shortcut(7)

    async def _pick_once_date(self) -> afanes.models.note.NoteDate | None:
        """Open the day-only picker for the one-shot date portion."""
        if self._pick_date is None:
            return None
        text = (self.once_field.value or "").strip()
        date_text = text[:10]
        try:
            current = datetime.date.fromisoformat(date_text)
        except ValueError:
            current = None
        chosen = await self._pick_date(current)
        return None if chosen is None else afanes.models.note.NoteDate.from_date(chosen)

    async def _apply_once_date(self, value: afanes.models.note.NoteDate) -> None:
        """Write a picked one-shot date and keep the typed time."""
        self.once_field.value = f"{value.text}T{self._once_time().text}"
        self.error_text.visible = False

    def _once_time(self) -> ClockTime:
        """Return the typed one-shot time, or the first chosen time."""
        text = (self.once_field.value or "").strip()
        _date, _separator, time_text = text.partition("T")
        try:
            return ClockTime.from_text(time_text.strip())
        except ValueError:
            return self._times[0] if self._times else ClockTime(hour=9, minute=0)

    def _fill_shortcut(self, days_before: int) -> None:
        """Write one shortcut date at the first chosen time."""
        if self._due_date is None:
            return
        time = self._times[0] if self._times else ClockTime(hour=9, minute=0)
        target = self._due_date - datetime.timedelta(days=days_before)
        self.once_field.value = f"{target.isoformat()}T{time.text}"
        self.error_text.visible = False

    async def _save(self, _event: object = None) -> None:
        """Build a reminder and report it to the page."""
        reminder = self._collect()
        if reminder is None:
            self._show_error()
            return
        if await self._on_save(reminder):
            self.hide()

    async def _remove(self, _event: object = None) -> None:
        """Report a removal to the page."""
        if await self._on_remove():
            self.hide()

    async def _cancel(self, _event: object = None) -> None:
        """Close without writing."""
        self.hide()
        await self._on_cancel()

    def _collect(self) -> Reminder | None:
        """Build one reminder from the form, or ``None`` when invalid."""
        zone = (self.zone_field.value or self.zone_field.text or "").strip()
        if not zone:
            return None
        if self._mode == "once":
            return self._collect_once(zone)
        return self._collect_recurrence(zone)

    def _collect_once(self, zone: str) -> Reminder | None:
        """Build a one-shot reminder from the form."""
        try:
            schedule = OneShot.from_value(self.once_field.value or "")
            return Reminder(schedule=schedule, zone=zone)
        except ValueError:
            return None

    def _collect_recurrence(self, zone: str) -> Reminder | None:
        """Build a recurrence reminder from the form."""
        if not self._times:
            return None
        try:
            kind = ReminderKind(self.kind_dropdown.value or ReminderKind.DAILY.value)
        except ValueError:
            return None
        weekdays = tuple(weekday for weekday, box in self.weekday_checks.items() if box.value)
        try:
            schedule = Recurrence(
                kind=kind,
                times=tuple(self._times),
                weekdays=weekdays,
                day=int(self.day_dropdown.value or "1") if kind is ReminderKind.MONTH_DAY else None,
                nth=int(self.nth_dropdown.value or "1") if kind is ReminderKind.NTH_WEEKDAY else None,
                weekday=self._selected_weekday(kind),
            )
            return Reminder(schedule=schedule, zone=zone)
        except (TypeError, ValueError):
            return None

    def _selected_weekday(self, kind: ReminderKind) -> Weekday | None:
        """Return the weekday selected for a kind that needs one."""
        if kind is ReminderKind.NTH_WEEKDAY:
            value = self.weekday_dropdown.value
        elif kind is ReminderKind.LAST_WEEKDAY:
            value = self.last_weekday_dropdown.value
        else:
            return None
        try:
            return Weekday(value or Weekday.MONDAY.value)
        except ValueError:
            return None

    def _show_error(self) -> None:
        """Show the inline form error."""
        self.error_text.value = self._copy.REMINDER_FORM_INVALID
        self.error_text.visible = True
