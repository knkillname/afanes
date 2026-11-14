# Spec Delta

## Purpose

Defines the optional whole-note reminder Afanes stores in frontmatter and how schedules, due
occurrences, pauses, dismissal, and editing behave across the interface and vault formats.

## ADDED Requirements

### Requirement: A reminder is one optional whole-note schedule

A reference, project, or log entry MAY declare one `reminder` mapping. A capture MUST NOT have an
effective reminder. The mapping SHALL contain `zone` and exactly one of `recurrence` or `once`, and
MAY contain `handled`. A null `reminder` SHALL be treated as absent. Unknown keys inside the mapping
SHALL be preserved.

#### Scenario: A reference carries a reminder

- **WHEN** a reference declares a valid `reminder` mapping
- **THEN** the note parses and its reminder is available to Review

#### Scenario: A project carries a reminder

- **WHEN** a project declares a valid `reminder` mapping
- **THEN** the note parses and its reminder is available to Review

#### Scenario: A log entry carries a reminder

- **WHEN** a log entry declares a valid `reminder` mapping
- **THEN** the note parses and its reminder is available to Review

#### Scenario: A capture is not scheduled

- **WHEN** a note of type `note` declares a `reminder` mapping
- **THEN** the note stays readable, the reminder is ignored for scheduling, and a warning is shown

#### Scenario: An absent reminder is valid

- **WHEN** an eligible note declares no `reminder` key
- **THEN** the note parses with no reminder

#### Scenario: A null reminder is absent

- **WHEN** an eligible note declares `reminder: null`
- **THEN** the note parses with no reminder

#### Scenario: Unknown nested keys are preserved

- **WHEN** a `reminder` mapping contains an unrecognized nested key
- **THEN** the key remains in the file after the note is rewritten

### Requirement: A reminder stores one recurrence or one one-shot

A recurrence SHALL declare one `kind` and one or more `times`. The kind SHALL be `daily`,
`weekdays`, `month_day`, `nth_weekday`, `last_day`, or `last_weekday`. `weekdays` SHALL name one or
more days; `month_day` SHALL name a day from 1 to 31; `nth_weekday` SHALL name an ordinal from 1 to
5 and a weekday; `last_weekday` SHALL name a weekday. A one-shot SHALL declare one local date and
time. Times SHALL use `HH:MM` in the 24-hour clock.

#### Scenario: A daily schedule is valid

- **WHEN** a recurrence declares `kind: daily` and `times: ["09:00", "17:30"]`
- **THEN** the reminder parses with two daily times

#### Scenario: A selected-weekday schedule is valid

- **WHEN** a recurrence declares `kind: weekdays` and `weekdays: [mon, wed, fri]`
- **THEN** the reminder parses with those three weekdays

#### Scenario: A day-of-month schedule is valid

- **WHEN** a recurrence declares `kind: month_day` and `day: 15`
- **THEN** the reminder parses for the fifteenth day of each month

#### Scenario: An nth-weekday schedule is valid

- **WHEN** a recurrence declares `kind: nth_weekday`, `nth: 2`, and `weekday: fri`
- **THEN** the reminder parses for the second Friday of each month

#### Scenario: A last-day schedule is valid

- **WHEN** a recurrence declares `kind: last_day`
- **THEN** the reminder parses for the last calendar day of each month

#### Scenario: A last-weekday schedule is valid

- **WHEN** a recurrence declares `kind: last_weekday` and `weekday: fri`
- **THEN** the reminder parses for the last Friday of each month

#### Scenario: A one-shot is valid

- **WHEN** a reminder declares `once: 2026-11-20T09:00`
- **THEN** the reminder parses for that local date and time

#### Scenario: A recurrence requires a time

- **WHEN** a recurrence declares no `times` or an empty list
- **THEN** the reminder is malformed and does not schedule

#### Scenario: A time uses the 24-hour clock

- **WHEN** a recurrence declares a time such as `9:00`, `24:00`, or `noon`
- **THEN** the reminder is malformed and does not schedule

#### Scenario: A weekday list requires a day

- **WHEN** a `weekdays` recurrence declares no weekday or an unknown weekday
- **THEN** the reminder is malformed and does not schedule

#### Scenario: An nth weekday is bounded

- **WHEN** an `nth_weekday` recurrence declares `nth: 0` or `nth: 6`
- **THEN** the reminder is malformed and does not schedule

### Requirement: A reminder resolves its time zone

`zone` SHALL be a valid IANA time-zone name. A missing zone SHALL resolve to the system zone. An
unknown zone SHALL make the reminder malformed without hiding the note. The reminder's times SHALL
be interpreted as local wall-clock times in that zone. A daylight-saving gap SHALL skip that
occurrence, and a repeated hour SHALL produce at most one entry.

#### Scenario: A valid zone is stored

- **WHEN** a reminder declares `zone: America/Mexico_City`
- **THEN** its times are interpreted in that zone

#### Scenario: A missing zone uses the system zone

- **WHEN** a reminder declares no `zone`
- **THEN** the note parses and the reminder uses the system zone

#### Scenario: An unknown zone is malformed

- **WHEN** a reminder declares a zone that the time-zone database does not contain
- **THEN** the note stays readable, the reminder is ignored for scheduling, and a warning is shown

#### Scenario: A daylight-saving gap is skipped

- **WHEN** a reminder's local time does not exist because the clock moves forward
- **THEN** that occurrence is skipped for that day

#### Scenario: A repeated hour produces one entry

- **WHEN** a reminder's local time occurs twice because the clock moves back
- **THEN** the latest-occurrence rule produces at most one Review entry

### Requirement: A reminder has at most one due occurrence

The due occurrence SHALL be the latest occurrence at or before the current instant in the
reminder's zone. An occurrence SHALL be due only when it is after `handled` or `handled` is absent.
A schedule SHALL contribute at most one entry, showing the latest missed occurrence even when
several times or days were missed. A one-shot in the past SHALL be due once; a future one-shot
SHALL not be due.

#### Scenario: The latest missed occurrence is shown

- **WHEN** a daily schedule has missed several days
- **THEN** Review shows one entry for the most recent missed occurrence

#### Scenario: Multiple missed times collapse

- **WHEN** a schedule with times `09:00` and `17:30` is first checked at `18:00`
- **THEN** Review shows one entry for `17:30`, not two entries

#### Scenario: A handled occurrence is suppressed

- **WHEN** `handled` equals the latest occurrence
- **THEN** the reminder is not due

#### Scenario: A later time becomes due after dismissal

- **WHEN** the `09:00` occurrence is dismissed and the current time passes `17:30`
- **THEN** the `17:30` occurrence becomes due

#### Scenario: A past one-shot is due once

- **WHEN** a one-shot's local time is in the past and `handled` is absent
- **THEN** Review shows it once and a dismissal marks it handled

#### Scenario: A future one-shot is not due

- **WHEN** a one-shot's local time is in the future
- **THEN** the reminder is not due

#### Scenario: A missing monthly day is skipped

- **WHEN** a `month_day` schedule names the 31st and the month has no 31st
- **THEN** that month contributes no occurrence

#### Scenario: A missing nth weekday is skipped

- **WHEN** an `nth_weekday` schedule names the fifth Friday and the month has only four Fridays
- **THEN** that month contributes no occurrence

### Requirement: A due reminder leads the Review queue

The Review pending count SHALL include due reminders. A review session SHALL queue due reminders
before Inbox captures, ordered most overdue first. The launch digest SHALL include due reminders and
SHALL use neutral item wording. A reminder that becomes due during a session SHALL wait for the next
session.

#### Scenario: The pending count includes reminders

- **WHEN** one reminder is due and no other work is pending
- **THEN** Review shows one pending item

#### Scenario: A reminder precedes an Inbox capture

- **WHEN** a session contains a due reminder and an Inbox capture
- **THEN** the reminder card comes first

#### Scenario: The most overdue reminder comes first

- **WHEN** two reminders are due at different times
- **THEN** the reminder whose latest occurrence is older comes first

#### Scenario: The launch digest includes reminders

- **WHEN** a reminder is due at launch and no step is due
- **THEN** the digest reports one item and offers Start Review

#### Scenario: The digest uses neutral item wording

- **WHEN** the digest counts steps and reminders together
- **THEN** it reports “items” rather than “due steps”

#### Scenario: A new due reminder waits for the next session

- **WHEN** a reminder becomes due while a review session is active
- **THEN** it is not appended to the current queue and appears in the next session

### Requirement: A due reminder can be opened or dismissed

A reminder card SHALL show the note title and a relative time. **Open Page** SHALL be the suggested
action, **Dismiss** SHALL record the occurrence in `handled`, and **Skip** SHALL change nothing.
Dismiss MUST NOT change the note body, status, or schedule. A failed dismissal SHALL be reported and
SHALL leave the reminder due.

#### Scenario: The card shows the note and relative time

- **WHEN** a reminder is due
- **THEN** the card shows the note title and a relative time such as “2 hours ago”

#### Scenario: Open Page opens the note

- **WHEN** the user chooses Open Page
- **THEN** the reminder's note opens and the reminder stays due

#### Scenario: Dismiss records the occurrence

- **WHEN** the user chooses Dismiss
- **THEN** `handled` records the shown occurrence and the session advances

#### Scenario: Dismiss preserves the note

- **WHEN** the user dismisses a reminder
- **THEN** the note body, status, and schedule are unchanged

#### Scenario: Skip leaves the reminder due

- **WHEN** the user chooses Skip
- **THEN** no file is written and the reminder remains due for the next session

#### Scenario: A failed dismissal leaves the reminder due

- **WHEN** the `handled` write fails
- **THEN** the failure is reported and the reminder remains due

### Requirement: A reminder pauses and resumes

A reminder SHALL pause while its note is in Trash or its status is `done`, `cancelled`, `archived`,
or `later`. A paused reminder SHALL NOT appear in Review, the pending count, or the digest. When the
note returns, the reminder SHALL show one catch-up entry for the latest missed occurrence.
`waiting` and an absent status SHALL NOT pause. A log entry pauses only in Trash.

#### Scenario: Trash pauses a reminder

- **WHEN** a note with a due reminder is moved to Trash
- **THEN** the reminder does not appear in Review

#### Scenario: Restore catches up once

- **WHEN** a trashed note with a reminder is restored
- **THEN** Review shows one entry for the latest missed occurrence

#### Scenario: A done project pauses its reminder

- **WHEN** a project with a reminder is marked `done`
- **THEN** the reminder does not appear in Review

#### Scenario: A later project pauses its reminder

- **WHEN** a project with a reminder is deferred to `later`
- **THEN** the reminder does not appear in Review

#### Scenario: An archived reference pauses its reminder

- **WHEN** a reference with a reminder is archived
- **THEN** the reminder does not appear in Review

#### Scenario: A waiting project keeps its reminder active

- **WHEN** a project with a reminder has status `waiting`
- **THEN** the reminder remains eligible for Review

#### Scenario: A log pauses only in Trash

- **WHEN** a log entry with a reminder is active
- **THEN** the reminder remains eligible because a log has no status

### Requirement: The page shows the reminder schedule

Read mode SHALL show a reminder summary with the cadence, times, and stored zone. The summary SHALL
show a paused state when the note's status or Trash location suspends the reminder. A capture, a
raw-rescue page, and a trashed page SHALL NOT offer reminder editing.

#### Scenario: A reminder summary shows the schedule

- **WHEN** a page has a daily reminder at `09:00` in `America/Mexico_City`
- **THEN** read mode shows the cadence, time, and zone

#### Scenario: A paused reminder is labeled

- **WHEN** a page's reminder is paused by status or Trash
- **THEN** the summary reports that it is paused

#### Scenario: A capture has no reminder action

- **WHEN** a note of type `note` is open
- **THEN** no reminder summary or edit action is offered

#### Scenario: A trashed page has no reminder action

- **WHEN** a trashed note is open
- **THEN** its reminder summary is visible but editing is not offered

#### Scenario: A raw-rescue page has no reminder action

- **WHEN** an unparseable note is open in raw rescue mode
- **THEN** no reminder summary or edit action is offered

### Requirement: The reminder editor sets and changes a schedule

The reminder editor SHALL be a separate surface from the page's label form. It SHALL offer the six
recurrence kinds, one or more times, and a searchable IANA zone list defaulting to the system zone.
For a project with a due date, a one-shot SHALL offer same-day, one-day-before, and one-week-before
shortcuts. Choosing a monthly day that does not exist every month SHALL show an inline warning and
suggest the last-day or last-weekday choice. Cancelling SHALL write nothing.

#### Scenario: A daily reminder is set

- **WHEN** the user chooses Daily, `09:00`, and a zone, then saves
- **THEN** the page's `reminder` mapping contains that recurrence and zone

#### Scenario: A one-shot is set

- **WHEN** the user chooses a one-shot date and time, then saves
- **THEN** the page's `reminder` mapping contains that `once` value

#### Scenario: A selected-weekday reminder is set

- **WHEN** the user chooses Monday, Wednesday, and Friday, then saves
- **THEN** the `weekdays` list contains those days

#### Scenario: The zone picker defaults to the system zone

- **WHEN** the editor opens
- **THEN** the selected zone is the computer's current IANA zone

#### Scenario: The zone picker is searchable

- **WHEN** the user types part of a zone name
- **THEN** the list filters to matching IANA zones

#### Scenario: A deadline shortcut fills a one-shot

- **WHEN** a project has a due date and the user chooses “One day before”
- **THEN** the one-shot date is the day before that due date at the chosen time

#### Scenario: A short-month warning is shown

- **WHEN** the user chooses the 31st for a monthly reminder
- **THEN** an inline warning explains that some months have no 31st and suggests the last-day choice

#### Scenario: A fifth-weekday warning is shown

- **WHEN** the user chooses the fifth Friday for a monthly reminder
- **THEN** an inline warning explains that some months have only four Fridays and suggests the last-Friday choice

#### Scenario: Cancelling writes nothing

- **WHEN** the user cancels the reminder editor
- **THEN** no file is created, changed, or removed

### Requirement: A reminder can be removed with Undo

Removing a reminder SHALL take effect immediately and SHALL offer Undo in a toast. Undo SHALL
restore the exact previous schedule, zone, and handled occurrence. The opportunity SHALL end when
the toast is dismissed or replaced, or when the application exits.

#### Scenario: Remove clears the reminder

- **WHEN** the user chooses Remove Reminder
- **THEN** the `reminder` key is removed and a toast offers Undo

#### Scenario: Undo restores the reminder

- **WHEN** the user chooses Undo before the toast ends
- **THEN** the exact previous reminder is written back

#### Scenario: The opportunity is transient

- **WHEN** the reminder toast is dismissed or replaced
- **THEN** Undo is no longer offered

### Requirement: Editing a schedule resets the handled occurrence

Saving a changed recurrence, one-shot, or zone SHALL clear `handled` so the edited schedule starts
from its latest occurrence. Saving an unchanged reminder SHALL preserve `handled`. A body-only edit
SHALL preserve the reminder and its `handled` value.

#### Scenario: A changed time clears handled

- **WHEN** the user changes a reminder's time and saves
- **THEN** `handled` is removed and the new schedule's latest occurrence is due

#### Scenario: A changed zone clears handled

- **WHEN** the user changes a reminder's zone and saves
- **THEN** `handled` is removed

#### Scenario: An unchanged save preserves handled

- **WHEN** the user opens the editor and saves without changing the schedule
- **THEN** `handled` is preserved

#### Scenario: A body edit preserves handled

- **WHEN** the user edits only the note body and saves
- **THEN** the reminder and its `handled` value are preserved

### Requirement: Reminder data is validated without hiding the page

A malformed reminder SHALL leave the note readable, SHALL be ignored for scheduling, SHALL show a
warning, and SHALL be preserved until the user replaces or removes it. A reminder on a capture SHALL
be ignored with a warning. Correcting the value SHALL restore scheduling without rewriting the note
on a scan.

#### Scenario: A malformed mapping is reported

- **WHEN** `reminder` is a list or a scalar instead of a mapping
- **THEN** the page stays readable and a warning is shown

#### Scenario: An unknown recurrence kind is reported

- **WHEN** a recurrence declares an unsupported `kind`
- **THEN** the reminder is ignored and a warning is shown

#### Scenario: An invalid time is reported

- **WHEN** a recurrence declares an invalid time
- **THEN** the reminder is ignored and a warning is shown

#### Scenario: A misplaced reminder is reported

- **WHEN** a capture declares a reminder
- **THEN** the page stays readable and the reminder is ignored with a warning

#### Scenario: A missing zone still works

- **WHEN** a valid reminder declares no zone
- **THEN** the reminder schedules in the system zone

#### Scenario: A body save preserves a malformed reminder

- **WHEN** the note has a malformed reminder and the user saves only the body
- **THEN** the malformed raw value remains unchanged

#### Scenario: A correction restores scheduling

- **WHEN** the user replaces a malformed reminder with a valid one
- **THEN** the warning clears and the reminder is eligible for Review

#### Scenario: Scanning writes nothing

- **WHEN** a vault containing a malformed reminder is opened or scanned
- **THEN** no note is rewritten

### Requirement: Reminders are localized and stay offline

Reminder copy, relative times, weekday names, and zone labels SHALL follow the active locale.
Reminder calculation SHALL work offline on Linux, macOS, and Windows. The feature MUST NOT create an
operating-system notification, account, telemetry, or network request.

#### Scenario: English reminder copy is shown

- **WHEN** the active locale is English
- **THEN** the page summary, editor, card, and toast copy are English

#### Scenario: Spanish reminder copy is shown

- **WHEN** the active locale is Spanish
- **THEN** the page summary, editor, card, and toast copy are Spanish

#### Scenario: Relative times are localized

- **WHEN** a reminder was due two hours ago
- **THEN** the card reports “2 hours ago” in English or “hace 2 horas” in Spanish

#### Scenario: Weekday names are localized

- **WHEN** the editor shows weekday choices
- **THEN** the names follow the active locale and stay Monday-first

#### Scenario: Reminder calculation is offline

- **WHEN** a reminder is created, edited, or evaluated
- **THEN** no network request is made

#### Scenario: Zones resolve on every supported platform

- **WHEN** a reminder uses an IANA zone on Linux, macOS, or Windows
- **THEN** the same zone rules apply on each platform

#### Scenario: No operating-system notification is created

- **WHEN** a reminder becomes due
- **THEN** the application updates Review and does not request an operating-system notification

### Requirement: The Review count refreshes while the application is open

While a vault is open, the Review pending count SHALL update within 15 seconds of a reminder
becoming due. The refresh SHALL read the existing snapshot, SHALL NOT write to the vault, SHALL NOT
change an active session's queue, and SHALL stop when the vault closes or the application exits.

#### Scenario: The badge updates after a reminder becomes due

- **WHEN** a reminder becomes due while the application is open
- **THEN** the Review count updates within 15 seconds

#### Scenario: The session queue is unchanged

- **WHEN** a reminder becomes due during an active review session
- **THEN** the session keeps its snapshot queue

#### Scenario: Closing the vault stops the refresh

- **WHEN** the vault is closed
- **THEN** the periodic refresh stops

#### Scenario: The refresh writes nothing

- **WHEN** the periodic refresh runs
- **THEN** no note or settings file is created, changed, or removed

#### Scenario: The refresh runs in a browser session

- **WHEN** the application runs in a browser session with a vault open
- **THEN** the Review count refreshes the same way

### Requirement: Reminders require the current vault format

Reminders SHALL be available only in a schema `2` vault. A writable schema `1` vault SHALL be
upgraded by rewriting only `afanes.yaml` and SHALL show a one-time notice. A read-only schema `1`
vault SHALL open for browsing with reminders off and a persistent banner. Schema `3` and newer SHALL
be refused. A scan or read-only open MUST NOT write a reminder.

#### Scenario: Schema 2 enables reminders

- **WHEN** a schema `2` vault opens
- **THEN** reminders are read, shown, and editable

#### Scenario: A writable schema 1 vault is upgraded

- **WHEN** a writable schema `1` vault opens
- **THEN** `afanes.yaml` becomes schema `2` and a one-time notice reports the upgrade

#### Scenario: The upgrade writes only the settings file

- **WHEN** a writable schema `1` vault is upgraded
- **THEN** no note is created, changed, or removed

#### Scenario: A read-only schema 1 vault opens with reminders off

- **WHEN** a read-only schema `1` vault opens
- **THEN** browsing works and reminders are not shown or offered

#### Scenario: The read-only old vault shows a banner

- **WHEN** a read-only schema `1` vault is open
- **THEN** a persistent banner explains that the vault must be writable to upgrade and enable reminders

#### Scenario: A read-only old vault is not written

- **WHEN** a read-only schema `1` vault is open or scanned
- **THEN** no vault file is created or modified

#### Scenario: A newer schema is refused

- **WHEN** a vault declares schema `3` or newer
- **THEN** the application refuses to open it and reports that Afanes must be updated
