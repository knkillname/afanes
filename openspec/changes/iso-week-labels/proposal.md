# Proposal

## Why

Afanes plans in calendar dates, but people often plan in weeks. Every stored due date and step date already belongs to
an ISO week, yet the interface never shows it, so a reader has to calculate the week by hand. The full ISO week date
also makes the week-year visible at New Year, when a short week number is easy to misread.

## What Changes

- Show the full ISO week date beside every displayed calendar date: `2026-11-20 (2026-W47)`.
- Apply the same label to project due dates, step plan and actual dates, the projects list, review cards, and the
  processing preview.
- Use the ISO week-year and a Monday week start, so `2025-12-29` reads as `2025-12-29 (2026-W01)`.
- Keep the vault format, date inputs, and template placeholders unchanged. The label is presentation only and is
  never written to a note.
- Add no dependency, network call, or persistent index.

## Capabilities

### New Capabilities

- `date-display`: how the interface writes calendar dates and their ISO week context.

### Modified Capabilities

None.

## Impact

- `src/afanes/core/`: a small date-formatting value or helper that derives the ISO week label without touching the
  stored date.
- `src/afanes/ui/strings.py`: date-bearing copy becomes formattable with the week label.
- `src/afanes/ui/views/page.py`, `src/afanes/ui/views/project_body.py`, `src/afanes/ui/views/projects.py`,
  `src/afanes/ui/views/review.py`, and `src/afanes/ui/views/processing.py`: use the shared formatting.
- `docs/reference/frontmatter.md`, `docs/reference/step-metadata.md`, and `docs/guide/projects-and-steps.md`:
  explain the displayed week label and confirm the stored format is unchanged.
- Tests under `tests/core/` and `tests/ui/`.
- No dependency, vault format, storage, or network impact.
