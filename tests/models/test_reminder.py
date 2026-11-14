"""Tests for reminder value objects, parsing, and occurrence calculation."""

import datetime
import zoneinfo

import pytest
from hypothesis import given
from hypothesis import strategies as st

from afanes.models.reminder import (
    ClockTime,
    OneShot,
    Recurrence,
    RecurrenceFields,
    RecurrenceParse,
    Reminder,
    ReminderKind,
    ReminderParse,
    ReminderProblem,
    ScheduleParse,
    Weekday,
)

MEXICO = "America/Mexico_City"
NEW_YORK = "America/New_York"
UTC = datetime.UTC
NAIVE_ONCE = datetime.datetime.fromisoformat("2026-11-20T09:00")
EXAMPLE_DAY = 4


def instant(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime.datetime:
    return datetime.datetime(year, month, day, hour, minute, tzinfo=UTC)


def local_instant(year: int, month: int, day: int, hour: int, minute: int = 0, zone: str = MEXICO) -> datetime.datetime:
    return datetime.datetime(
        year,
        month,
        day,
        hour,
        minute,
        tzinfo=zoneinfo.ZoneInfo(zone),
    )


def daily(times: tuple[str, ...] = ("09:00",), zone: str = MEXICO) -> Reminder:
    return Reminder(
        schedule=Recurrence(
            kind=ReminderKind.DAILY,
            times=tuple(ClockTime.from_text(text) for text in times),
        ),
        zone=zone,
    )


class TestClockTime:
    def test_a_zero_padded_time_parses(self) -> None:
        assert ClockTime.from_text("09:05") == ClockTime(hour=9, minute=5)

    def test_the_canonical_text_is_zero_padded(self) -> None:
        assert ClockTime(hour=7, minute=30).text == "07:30"

    @pytest.mark.parametrize("text", ["9:00", "24:00", "23:60", "09:0", "noon", "09.00", "-1:00"])
    def test_invalid_text_is_rejected(self, text: str) -> None:
        with pytest.raises(ValueError, match="Invalid reminder time"):
            ClockTime.from_text(text)

    @pytest.mark.parametrize(("hour", "minute"), [(24, 0), (-1, 0), (0, 60), (True, 0)])
    def test_invalid_parts_are_rejected(self, hour: int, minute: int) -> None:
        with pytest.raises(ValueError, match="Invalid reminder"):
            ClockTime(hour=hour, minute=minute)


class TestWeekday:
    def test_members_are_monday_first(self) -> None:
        assert [day.value for day in Weekday] == ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    def test_from_text_is_case_insensitive(self) -> None:
        assert Weekday.from_text(" WED ") is Weekday.WEDNESDAY

    def test_from_date_maps_monday_to_zero(self) -> None:
        assert Weekday.from_date(datetime.date(2026, 11, 16)) is Weekday.MONDAY
        assert Weekday.from_date(datetime.date(2026, 11, 16)).position == 0

    def test_an_unknown_weekday_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown weekday"):
            Weekday.from_text("monday")


class TestRecurrenceParsing:
    @pytest.mark.parametrize(
        ("mapping", "expected"),
        [
            (
                {"kind": "daily", "times": ["09:00", "17:30"]},
                Recurrence(kind=ReminderKind.DAILY, times=(ClockTime(9, 0), ClockTime(17, 30))),
            ),
            (
                {"kind": "weekdays", "weekdays": ["fri", "mon", "wed"], "times": ["09:00"]},
                Recurrence(
                    kind=ReminderKind.WEEKDAYS,
                    times=(ClockTime(9, 0),),
                    weekdays=(Weekday.MONDAY, Weekday.WEDNESDAY, Weekday.FRIDAY),
                ),
            ),
            (
                {"kind": "month_day", "day": 15, "times": ["09:00"]},
                Recurrence(kind=ReminderKind.MONTH_DAY, times=(ClockTime(9, 0),), day=15),
            ),
            (
                {"kind": "nth_weekday", "nth": 2, "weekday": "fri", "times": ["09:00"]},
                Recurrence(
                    kind=ReminderKind.NTH_WEEKDAY,
                    times=(ClockTime(9, 0),),
                    nth=2,
                    weekday=Weekday.FRIDAY,
                ),
            ),
            (
                {"kind": "last_day", "times": ["09:00"]},
                Recurrence(kind=ReminderKind.LAST_DAY, times=(ClockTime(9, 0),)),
            ),
            (
                {"kind": "last_weekday", "weekday": "fri", "times": ["09:00"]},
                Recurrence(
                    kind=ReminderKind.LAST_WEEKDAY,
                    times=(ClockTime(9, 0),),
                    weekday=Weekday.FRIDAY,
                ),
            ),
        ],
    )
    def test_every_kind_parses(self, mapping: dict[str, object], expected: Recurrence) -> None:
        parsed = Recurrence.from_mapping(mapping)

        assert parsed.recurrence == expected

    def test_times_are_sorted_and_unique(self) -> None:
        parsed = Recurrence.from_mapping({"kind": "daily", "times": ["17:30", "09:00", "17:30"]})

        assert parsed.recurrence is not None
        assert parsed.recurrence.times == (ClockTime(9, 0), ClockTime(17, 30))

    def test_unknown_nested_keys_are_preserved(self) -> None:
        parsed = Recurrence.from_mapping({"kind": "daily", "times": ["09:00"], "label": "morning", "color": "blue"})

        assert parsed.recurrence is not None
        assert dict(parsed.recurrence.extra) == {"label": "morning", "color": "blue"}
        assert parsed.recurrence.to_mapping()["label"] == "morning"

    @pytest.mark.parametrize(
        ("mapping", "problem"),
        [
            ([], ReminderProblem.NOT_MAPPING),
            ({"times": ["09:00"]}, ReminderProblem.UNKNOWN_KIND),
            ({"kind": "hourly", "times": ["09:00"]}, ReminderProblem.UNKNOWN_KIND),
            ({"kind": "daily"}, ReminderProblem.TIMES),
            ({"kind": "daily", "times": []}, ReminderProblem.TIMES),
            ({"kind": "daily", "times": ["9:00"]}, ReminderProblem.TIMES),
            ({"kind": "daily", "times": [540]}, ReminderProblem.TIMES),
            ({"kind": "weekdays", "times": ["09:00"]}, ReminderProblem.WEEKDAYS),
            ({"kind": "weekdays", "weekdays": [], "times": ["09:00"]}, ReminderProblem.WEEKDAYS),
            ({"kind": "weekdays", "weekdays": ["monday"], "times": ["09:00"]}, ReminderProblem.WEEKDAYS),
            ({"kind": "month_day", "times": ["09:00"]}, ReminderProblem.DAY),
            ({"kind": "month_day", "day": 0, "times": ["09:00"]}, ReminderProblem.DAY),
            ({"kind": "month_day", "day": 32, "times": ["09:00"]}, ReminderProblem.DAY),
            ({"kind": "nth_weekday", "weekday": "fri", "times": ["09:00"]}, ReminderProblem.ORDINAL),
            ({"kind": "nth_weekday", "nth": 0, "weekday": "fri", "times": ["09:00"]}, ReminderProblem.ORDINAL),
            ({"kind": "nth_weekday", "nth": 6, "weekday": "fri", "times": ["09:00"]}, ReminderProblem.ORDINAL),
            ({"kind": "nth_weekday", "nth": 2, "times": ["09:00"]}, ReminderProblem.WEEKDAY),
            ({"kind": "last_weekday", "times": ["09:00"]}, ReminderProblem.WEEKDAY),
        ],
    )
    def test_malformed_mappings_report_the_first_problem(
        self,
        mapping: object,
        problem: ReminderProblem,
    ) -> None:
        assert Recurrence.from_mapping(mapping).problem is problem

    def test_parse_result_exposes_validity(self) -> None:
        assert RecurrenceParse(recurrence=Recurrence(ReminderKind.DAILY, (ClockTime(9, 0),))).is_valid
        assert not RecurrenceParse(problem=ReminderProblem.TIMES).is_valid

    def test_fields_carry_the_kind_specific_values(self) -> None:
        fields = RecurrenceFields(known=frozenset({"kind", "times"}), day=4)

        assert fields.day == EXAMPLE_DAY


class TestReminderParsing:
    def test_a_recurring_reminder_parses(self) -> None:
        parsed = Reminder.from_mapping(
            {
                "zone": MEXICO,
                "recurrence": {"kind": "daily", "times": ["09:00"]},
                "handled": "2026-11-14T15:00:00+00:00",
            }
        )

        assert parsed.reminder is not None
        assert parsed.reminder.zone == MEXICO
        assert parsed.reminder.handled == instant(2026, 11, 14, 15)

    def test_a_one_shot_reminder_parses(self) -> None:
        parsed = Reminder.from_mapping({"zone": MEXICO, "once": "2026-11-20T09:00"})

        assert parsed.reminder is not None
        assert parsed.reminder.schedule == OneShot(local=NAIVE_ONCE)

    def test_a_missing_zone_is_allowed(self) -> None:
        parsed = Reminder.from_mapping({"recurrence": {"kind": "daily", "times": ["09:00"]}})

        assert parsed.reminder is not None
        assert parsed.reminder.zone is None
        assert parsed.reminder.resolved_zone(MEXICO) == MEXICO

    def test_unknown_reminder_keys_are_preserved(self) -> None:
        parsed = Reminder.from_mapping(
            {
                "recurrence": {"kind": "daily", "times": ["09:00"]},
                "label": "morning",
            }
        )

        assert parsed.reminder is not None
        assert dict(parsed.reminder.extra) == {"label": "morning"}

    @pytest.mark.parametrize(
        ("mapping", "problem"),
        [
            ([], ReminderProblem.NOT_MAPPING),
            ({"zone": MEXICO}, ReminderProblem.SCHEDULE),
            (
                {"recurrence": {"kind": "daily", "times": ["09:00"]}, "once": "2026-11-20T09:00"},
                ReminderProblem.SCHEDULE,
            ),
            ({"recurrence": {"kind": "daily", "times": ["09:00"]}, "zone": "Mars/Olympus"}, ReminderProblem.ZONE),
            ({"recurrence": {"kind": "daily", "times": ["09:00"]}, "zone": 3}, ReminderProblem.ZONE),
            ({"recurrence": {"kind": "daily", "times": ["09:00"]}, "handled": "yesterday"}, ReminderProblem.HANDLED),
            (
                {"recurrence": {"kind": "daily", "times": ["09:00"]}, "handled": "2026-11-14T15:00:00"},
                ReminderProblem.HANDLED,
            ),
            ({"once": "tomorrow"}, ReminderProblem.ONCE),
            ({"once": "2026-11-20T09:00:00+00:00"}, ReminderProblem.ONCE),
        ],
    )
    def test_malformed_reminders_report_the_first_problem(
        self,
        mapping: object,
        problem: ReminderProblem,
    ) -> None:
        assert Reminder.from_mapping(mapping).problem is problem

    def test_parse_result_exposes_validity(self) -> None:
        assert ReminderParse(reminder=daily()).is_valid
        assert not ReminderParse(problem=ReminderProblem.SCHEDULE).is_valid

    def test_schedule_parse_result_exposes_validity(self) -> None:
        assert ScheduleParse(schedule=OneShot(NAIVE_ONCE)).is_valid
        assert not ScheduleParse(problem=ReminderProblem.ONCE).is_valid


class TestSerialization:
    @pytest.mark.parametrize(
        "mapping",
        [
            {"zone": MEXICO, "recurrence": {"kind": "daily", "times": ["09:00", "17:30"]}},
            {
                "zone": MEXICO,
                "recurrence": {"kind": "weekdays", "weekdays": ["mon", "wed", "fri"], "times": ["09:00"]},
            },
            {"zone": MEXICO, "recurrence": {"kind": "month_day", "day": 15, "times": ["09:00"]}},
            {
                "zone": MEXICO,
                "recurrence": {"kind": "nth_weekday", "nth": 2, "weekday": "fri", "times": ["09:00"]},
            },
            {"zone": MEXICO, "recurrence": {"kind": "last_day", "times": ["09:00"]}},
            {
                "zone": MEXICO,
                "recurrence": {"kind": "last_weekday", "weekday": "fri", "times": ["09:00"]},
            },
            {"zone": MEXICO, "once": "2026-11-20T09:00"},
        ],
    )
    def test_every_shape_round_trips(self, mapping: dict[str, object]) -> None:
        first = Reminder.from_mapping(mapping)
        assert first.reminder is not None

        second = Reminder.from_mapping(first.reminder.to_mapping())

        assert second.reminder == first.reminder

    def test_handled_serializes_with_an_offset(self) -> None:
        reminder = daily().with_handled(instant(2026, 11, 14, 15))

        assert reminder.to_mapping()["handled"] == "2026-11-14T15:00:00+00:00"

    def test_unknown_keys_survive_serialization(self) -> None:
        parsed = Reminder.from_mapping(
            {
                "recurrence": {"kind": "daily", "times": ["09:00"], "label": "morning"},
                "label": "routine",
            }
        )

        assert parsed.reminder is not None
        mapping = parsed.reminder.to_mapping()

        assert mapping["label"] == "routine"
        assert mapping["recurrence"]["label"] == "morning"  # type: ignore[index]

    def test_same_schedule_ignores_handled_and_extras(self) -> None:
        first = daily().with_handled(instant(2026, 11, 14, 15))
        second = Reminder(schedule=first.schedule, zone=first.zone, extra=(("label", "x"),))

        assert first.same_schedule(second)


class TestOccurrenceCalculation:
    def test_daily_latest_collapses_missed_times(self) -> None:
        reminder = daily(("09:00", "17:30"))
        reference = instant(2026, 11, 15, 0)

        assert reminder.latest_occurrence(reference, MEXICO) == local_instant(2026, 11, 14, 17, 30)

    def test_daily_next_occurrence_is_in_the_future(self) -> None:
        reminder = daily(("09:00", "17:30"))
        reference = instant(2026, 11, 15, 0)

        assert reminder.next_occurrence(reference, MEXICO) == local_instant(2026, 11, 15, 9, 0)

    def test_selected_weekdays_skip_the_weekend(self) -> None:
        reminder = Reminder(
            schedule=Recurrence(
                kind=ReminderKind.WEEKDAYS,
                times=(ClockTime(9, 0),),
                weekdays=(Weekday.MONDAY, Weekday.WEDNESDAY, Weekday.FRIDAY),
            ),
            zone=MEXICO,
        )

        latest = reminder.latest_occurrence(instant(2026, 11, 14, 18), MEXICO)

        assert latest == local_instant(2026, 11, 13, 9, 0)

    def test_month_day_crosses_to_the_previous_month(self) -> None:
        reminder = Reminder(
            schedule=Recurrence(kind=ReminderKind.MONTH_DAY, times=(ClockTime(9, 0),), day=15),
            zone=MEXICO,
        )

        assert reminder.latest_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 10, 15, 9)
        assert reminder.next_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 11, 15, 9)

    def test_nth_weekday_uses_the_requested_ordinal(self) -> None:
        reminder = Reminder(
            schedule=Recurrence(
                kind=ReminderKind.NTH_WEEKDAY,
                times=(ClockTime(9, 0),),
                nth=2,
                weekday=Weekday.FRIDAY,
            ),
            zone=MEXICO,
        )

        assert reminder.latest_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 11, 13, 9)
        assert reminder.next_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 12, 11, 9)

    def test_last_day_uses_the_calendar_month_end(self) -> None:
        reminder = Reminder(
            schedule=Recurrence(kind=ReminderKind.LAST_DAY, times=(ClockTime(9, 0),)),
            zone=MEXICO,
        )

        assert reminder.latest_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 10, 31, 9)
        assert reminder.next_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 11, 30, 9)

    def test_last_weekday_uses_the_last_matching_day(self) -> None:
        reminder = Reminder(
            schedule=Recurrence(
                kind=ReminderKind.LAST_WEEKDAY,
                times=(ClockTime(9, 0),),
                weekday=Weekday.FRIDAY,
            ),
            zone=MEXICO,
        )

        assert reminder.latest_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 10, 30, 9)
        assert reminder.next_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 11, 27, 9)

    def test_a_future_one_shot_is_not_due(self) -> None:
        reminder = Reminder(schedule=OneShot(NAIVE_ONCE), zone=MEXICO)

        assert reminder.due_occurrence(instant(2026, 11, 14, 18), MEXICO) is None
        assert reminder.next_occurrence(instant(2026, 11, 14, 18), MEXICO) == local_instant(2026, 11, 20, 9)

    def test_a_past_one_shot_is_due_once(self) -> None:
        reminder = Reminder(schedule=OneShot(NAIVE_ONCE), zone=MEXICO)
        reference = instant(2026, 11, 21, 18)

        due = reminder.due_occurrence(reference, MEXICO)

        assert due is not None
        assert due == local_instant(2026, 11, 20, 9)
        assert reminder.with_handled(due).due_occurrence(reference, MEXICO) is None

    def test_handled_suppresses_only_the_matching_occurrence(self) -> None:
        reminder = daily(("09:00", "17:30"))
        reference = instant(2026, 11, 15, 0)
        morning = local_instant(2026, 11, 14, 9)

        assert reminder.with_handled(morning).due_occurrence(reference, MEXICO) == local_instant(2026, 11, 14, 17, 30)
        assert reminder.with_handled(local_instant(2026, 11, 14, 17, 30)).due_occurrence(reference, MEXICO) is None

    def test_a_future_handled_value_is_treated_as_absent(self) -> None:
        reminder = daily().with_handled(instant(2030, 1, 1, 0))
        reference = instant(2026, 11, 14, 18)

        assert reminder.due_occurrence(reference, MEXICO) == local_instant(2026, 11, 14, 9)

    def test_occurrence_methods_require_an_aware_reference(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            daily().latest_occurrence(datetime.datetime.fromisoformat("2026-11-14T18:00"), MEXICO)

    def test_with_schedule_clears_handled_only_when_changed(self) -> None:
        reminder = daily().with_handled(instant(2026, 11, 14, 9))
        same = reminder.with_schedule(reminder.schedule, reminder.zone)

        changed = reminder.with_schedule(
            Recurrence(kind=ReminderKind.DAILY, times=(ClockTime(10, 0),)),
            MEXICO,
        )

        assert same.handled == instant(2026, 11, 14, 9)
        assert changed.handled is None


class TestDaylightSaving:
    def test_a_gap_time_is_skipped(self) -> None:
        reminder = daily(("02:30",), zone=NEW_YORK)
        reference = datetime.datetime(2026, 3, 8, 12, 0, tzinfo=zoneinfo.ZoneInfo(NEW_YORK))

        latest = reminder.latest_occurrence(reference, NEW_YORK)
        following = reminder.next_occurrence(reference, NEW_YORK)

        assert latest == datetime.datetime(2026, 3, 7, 2, 30, tzinfo=zoneinfo.ZoneInfo(NEW_YORK))
        assert following == datetime.datetime(2026, 3, 9, 2, 30, tzinfo=zoneinfo.ZoneInfo(NEW_YORK))

    def test_a_repeated_hour_produces_one_entry(self) -> None:
        reminder = daily(("01:30",), zone=NEW_YORK)
        reference = datetime.datetime(2026, 11, 1, 12, 0, tzinfo=zoneinfo.ZoneInfo(NEW_YORK))

        due = reminder.due_occurrence(reference, NEW_YORK)

        assert due is not None
        assert due.utcoffset() == datetime.timedelta(hours=-5)
        assert reminder.next_occurrence(reference, NEW_YORK) == datetime.datetime(
            2026, 11, 2, 1, 30, tzinfo=zoneinfo.ZoneInfo(NEW_YORK)
        )

    def test_a_missing_month_day_is_skipped(self) -> None:
        reminder = Reminder(
            schedule=Recurrence(kind=ReminderKind.MONTH_DAY, times=(ClockTime(9, 0),), day=31),
            zone=MEXICO,
        )

        assert reminder.latest_occurrence(instant(2026, 2, 15, 12), MEXICO) == local_instant(2026, 1, 31, 9)
        assert reminder.next_occurrence(instant(2026, 2, 15, 12), MEXICO) == local_instant(2026, 3, 31, 9)
        assert reminder.latest_occurrence(instant(2026, 4, 15, 12), MEXICO) == local_instant(2026, 3, 31, 9)

    def test_a_missing_fifth_weekday_is_skipped(self) -> None:
        reminder = Reminder(
            schedule=Recurrence(
                kind=ReminderKind.NTH_WEEKDAY,
                times=(ClockTime(9, 0),),
                nth=5,
                weekday=Weekday.FRIDAY,
            ),
            zone=MEXICO,
        )

        assert reminder.latest_occurrence(instant(2026, 2, 28, 12), MEXICO) == local_instant(2026, 1, 30, 9)
        assert reminder.next_occurrence(instant(2026, 2, 28, 12), MEXICO) == local_instant(2026, 5, 29, 9)


class TestOccurrenceProperties:
    @given(
        st.lists(
            st.integers(min_value=0, max_value=23),
            min_size=1,
            max_size=4,
            unique=True,
        ),
        st.integers(min_value=0, max_value=59),
        st.datetimes(
            min_value=datetime.datetime(2020, 1, 1, tzinfo=UTC),
            max_value=datetime.datetime(2030, 12, 31, tzinfo=UTC),
            timezones=st.just(UTC),
        ),
    )
    def test_latest_and_next_bracket_the_reference(
        self,
        hours: list[int],
        minute: int,
        reference: datetime.datetime,
    ) -> None:
        reminder = Reminder(
            schedule=Recurrence(
                kind=ReminderKind.DAILY,
                times=tuple(ClockTime(hour=hour, minute=minute) for hour in hours),
            ),
            zone=MEXICO,
        )

        latest = reminder.latest_occurrence(reference, MEXICO)
        following = reminder.next_occurrence(reference, MEXICO)

        assert latest is not None
        assert following is not None
        assert latest <= reference < following

    @given(
        st.lists(
            st.times(),
            min_size=1,
            max_size=4,
        )
    )
    def test_times_are_sorted_and_unique(self, times: list[datetime.time]) -> None:
        raw = [f"{time.hour:02d}:{time.minute:02d}" for time in times]

        parsed = Recurrence.from_mapping({"kind": "daily", "times": raw})

        assert parsed.recurrence is not None
        assert list(parsed.recurrence.times) == sorted(set(parsed.recurrence.times))

    @given(
        st.integers(min_value=1, max_value=31),
        st.integers(min_value=2020, max_value=2030),
        st.integers(min_value=1, max_value=12),
    )
    def test_month_day_never_crosses_into_an_invalid_date(self, day: int, year: int, month: int) -> None:
        reminder = Reminder(
            schedule=Recurrence(kind=ReminderKind.MONTH_DAY, times=(ClockTime(9, 0),), day=day),
            zone=MEXICO,
        )
        reference = instant(year, month, 28, 12)

        latest = reminder.latest_occurrence(reference, MEXICO)

        assert latest is not None
        assert latest.day == day
        assert latest.date() <= reference.date()

    @given(
        st.integers(min_value=1, max_value=5),
        st.sampled_from(list(Weekday)),
        st.integers(min_value=2020, max_value=2030),
        st.integers(min_value=1, max_value=12),
    )
    def test_nth_weekday_respects_its_bounds(
        self,
        nth: int,
        weekday: Weekday,
        year: int,
        month: int,
    ) -> None:
        reminder = Reminder(
            schedule=Recurrence(
                kind=ReminderKind.NTH_WEEKDAY,
                times=(ClockTime(9, 0),),
                nth=nth,
                weekday=weekday,
            ),
            zone=MEXICO,
        )
        reference = instant(year, month, 28, 12)

        latest = reminder.latest_occurrence(reference, MEXICO)

        assert latest is not None
        assert latest.weekday() == weekday.position
        assert (latest.day - 1) // 7 + 1 <= nth

    @given(
        st.lists(
            st.integers(min_value=0, max_value=23),
            min_size=1,
            max_size=4,
            unique=True,
        ),
        st.datetimes(
            min_value=datetime.datetime(2020, 1, 1, tzinfo=UTC),
            max_value=datetime.datetime(2030, 12, 31, tzinfo=UTC),
            timezones=st.just(UTC),
        ),
    )
    def test_latest_occurrence_is_the_maximum_missed_time(
        self,
        hours: list[int],
        reference: datetime.datetime,
    ) -> None:
        reminder = Reminder(
            schedule=Recurrence(
                kind=ReminderKind.DAILY,
                times=tuple(ClockTime(hour=hour, minute=0) for hour in hours),
            ),
            zone=MEXICO,
        )
        zone = zoneinfo.ZoneInfo(MEXICO)
        local_day = reference.astimezone(zone).date()
        previous_day = local_day - datetime.timedelta(days=1)
        candidates = [
            datetime.datetime(local_day.year, local_day.month, local_day.day, hour, 0, tzinfo=zone) for hour in hours
        ]
        candidates.extend(
            datetime.datetime(
                previous_day.year,
                previous_day.month,
                previous_day.day,
                hour,
                0,
                tzinfo=zone,
            )
            for hour in hours
        )
        missed = [candidate for candidate in candidates if candidate <= reference]

        latest = reminder.latest_occurrence(reference, MEXICO)

        assert latest == max(missed)
