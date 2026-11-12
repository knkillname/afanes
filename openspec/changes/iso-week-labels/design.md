# Design

## Context

See `proposal.md` for motivation. The current state that shapes the approach:

- Dates are stored as `datetime.date` values and rendered with `date.isoformat()` at each display site.
- Date-bearing copy is centralized in `ui/strings.py`; views pass a formatted date into a `{date}` placeholder.
- The processing preview currently builds its due-date detail with an inline f-string in `processing.py`.
- `ui/strings.py` is an import leaf and one of the modules allowed to define module-level functions.
- The vault, parser, and template renderer must keep writing `YYYY-MM-DD`.

## Goals / Non-Goals

**Goals:**

- One formatter that every date-bearing surface uses.
- Correct ISO week-year labels at year boundaries, on every supported platform.
- No change to stored data, accepted input formats, or template output.

**Non-Goals:**

- Accepting, storing, or editing week dates.
- Week-number columns in the date picker.
- Locale-specific or user-configurable week starts.
- Showing week numbers for file modification times or other non-vault metadata.

## Decisions

### Decision: format in `ui/strings.py`, not in `core`

Add `date_with_week(value: datetime.date) -> str` to `ui/strings.py`. It returns
`f"{value.isoformat()} ({iso_year}-W{iso_week:02d})"` using `value.isocalendar()`.

Rationale: the ISO week is user-facing copy, not stored domain data. The date model, the parser, and the template
renderer stay untouched. `ui/strings.py` already owns formatting helpers such as `reference_count` and is explicitly
allowed to define module-level functions.

Alternatives considered:

- **A `DateLabel` value object in `core/`.** More formal and core-testable, but it adds a domain concept for a purely
  presentational label and invites accidental use in stored output.
- **Change each `{date}` placeholder to `{date} ({week})`.** Spreads the formatting rule across every template and
  makes it easy to forget a surface.

### Decision: keep the existing `{date}` placeholders

Views pass `date_with_week(...)` into the existing `{date}` slots in `PROJECT_DUE`, `PAGE_STEP_PLAN`,
`PAGE_STEP_ACTUAL`, and `REVIEW_DUE`. No template text changes, so the copy stays stable and the diff stays small.

The processing preview's inline `f"Due: {plan.due_date.isoformat()}"` is replaced with the same formatter, which also
removes the last inline date copy outside `ui/strings.py`.

### Decision: compute the week with `isocalendar`, never `strftime`

Use `datetime.date.isocalendar()`, which returns the ISO week-year, week number, and weekday directly. Do not use
`strftime("%G-W%V")`: `%G` and `%V` support and behavior vary across platform C libraries, and the project targets
Windows, macOS, and Linux.

The label always uses the ISO week-year, even when it differs from `value.year`, and weeks start on Monday. No
`locale` or timezone setting participates. The week number is zero-padded to two digits, matching ISO 8601 (`W01`,
not `W1`).

### Decision: apply the formatter at display sites, not in the model

Each view that already has a `datetime.date` calls the formatter. The date inputs, their `YYYY-MM-DD` hints, the
frontmatter parser, the step metadata parser, and the template renderer are unchanged. A week date typed into a date
field remains a validation error.

This keeps the "presentation only" boundary testable: the same stored date renders the same label, and the file
content is identical with or without the feature.

## Risks / Trade-offs

- **[A surface is missed and shows a bare date]** → Add one view test per surface and a strings test for the
  formatter; the existing date copy is concentrated in a few call sites.
- **[Platform differences in week formatting]** → Use `isocalendar()` and avoid `strftime`; test the year-boundary
  dates `2025-12-29`, `2026-01-01`, `2021-01-01`, and `2020-12-31`.
- **[Dense rows become wider]** → Accept it; the spec chooses the full label for unambiguity. The label uses the
  existing metadata style rather than a new badge.
- **[A reader assumes the week is stored]** → The docs state that the vault keeps `YYYY-MM-DD` and that the label is
  display-only.
- **[Year-boundary confusion remains possible in the files]** → The files are unchanged by design; the label is the
  only place the week appears, and it always carries the week-year.

## Migration Plan

None. No stored data, input format, or template output changes. Rolling back removes the formatter call sites and the
label; every note remains valid throughout.
