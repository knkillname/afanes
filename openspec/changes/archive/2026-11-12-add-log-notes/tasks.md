# Tasks

## 1. Date value object and frontmatter

- [x] 1.1 Add `DatePrecision` and a frozen slotted `NoteDate` value to `src/afanes/models/note.py`, with comparison and ISO-text helpers; verify `tests/models/test_note.py` covers year, month, day, ordering, and rejected values.
- [x] 1.2 Parse `date` in `NoteDocument.from_text` for `datetime.date`, integer year, and ISO strings, and record `date_error` for malformed values without raising; verify `tests/core/test_frontmatter.py` covers every accepted and rejected shape, including a Hypothesis round-trip.
- [x] 1.3 Serialize `date` in `NoteDocument.to_text` with day precision as a YAML date and year/month precision as strings; verify a parse-serialize-parse round-trip preserves precision in `tests/core/test_frontmatter.py`.
- [x] 1.4 Add `date` to `VaultNote` and populate it during the scan; verify `tests/core/vault/test_service.py` covers a dated note, an undated note, and a malformed date that stays in the snapshot.
- [x] 1.5 Add `date_text` and a `date_error` to `PageLabels`/`NormalDraft` and preserve the date through type changes and label edits; verify `tests/core/test_editing.py` covers blank, valid, malformed, and type-change cases.
- [x] 1.6 Stamp today's date when creating captures, references, projects, and link-created pages; verify `tests/core/vault/test_pages.py` and `tests/core/vault/test_service.py` assert the written frontmatter.
- [x] 1.7 Stamp the vault creation date into every bundled note during template rendering; verify `tests/core/test_templates.py` asserts the guide and starter notes carry the creation date and no placeholder.
- [x] 1.8 Update `docs/reference/frontmatter.md` and `docs/reference/vault-format.md` with the `date` key, ISO precision, lenient malformed handling, and the difference from `due_date`; verify `hatch run docs:build` passes.

## 2. Log type, identity, and references

- [x] 2.1 Add `NoteType.LOG` and `ReferenceScheme.LOG`, map `log` to the new scheme, and reject statuses on it; verify `tests/models/test_note.py` and `tests/core/test_links.py` cover the type and scheme.
- [x] 2.2 Enforce the log frontmatter rules in the parser: no `category`, `status`, `due_date`, or `asked_by`; verify `tests/core/test_frontmatter.py` covers each rejection.
- [x] 2.3 Extend reference parsing and resolution with `log:` and make it resolve only log notes; verify `tests/core/test_links.py` covers day, month, and year destinations, a title destination, and a `note:` destination aimed at a log.
- [x] 2.4 Add `Vault.log_directory(date)` for `log/<year>/` and `log/<year>/<month>/`, reusing case variants and never creating folders on scan; verify `tests/core/vault/test_service.py` covers year, month, day, case variants, and a read-only open.
- [x] 2.5 Add the shared one-per-date guard and use it for creation, processing, and date changes; verify `tests/core/vault/test_pages.py` and `tests/core/vault/test_processing.py` refuse an occupied date without writing.
- [x] 2.6 Plan a log date change as a rename-shaped preview that carries the new date, target path, affected references, and content hashes; verify `tests/core/vault/test_naming.py` covers day-to-day, day-to-month, month-to-year, and an occupied target.
- [x] 2.7 Apply a log date change: write the date, rename, move, rewrite resolving `log:` references, skip changed files, and report partial failures; verify `tests/core/vault/test_naming.py` covers success, a changed referrer, and a safe re-run.
- [x] 2.8 Handle type changes into and out of `log`: require a date when entering, rename to the date, rename to the display title when leaving, move to the target folder, and rewrite references; verify `tests/core/vault/test_naming.py` and `tests/core/test_editing.py` cover both directions and an undated note.
- [x] 2.9 Hide Rename for log pages and keep Trash available; verify `tests/ui/test_page_view.py` covers the log page controls.
- [x] 2.10 Document the `log:` scheme, date identity, and automatic date-change rewrite in `docs/reference/vault-format.md` and `docs/reference/frontmatter.md`; verify `hatch run docs:build` passes.

## 3. Creation, processing, and template cards

- [x] 3.1 Add `VaultPages.create_log_entry(date, title, scaffold)` that writes `type: log`, the date, and `# <title>` plus the card body, and opens in edit mode; verify `tests/core/vault/test_pages.py` covers day, month, year, Empty, a blank title, and an occupied date.
- [x] 3.2 Add the Log creation commands for **Today's entry**, an empty calendar day, and the plus on an empty month/year row, including the title-and-card dialog; verify `tests/ui/test_state.py` covers create, open-existing, blank title, and an occupied date.
- [x] 3.3 Add `ProcessingOutcome.LOG` to the plan, target mapping, and apply path; verify `tests/core/vault/test_processing.py` covers a dated capture, an undated capture using its last-modified date, and an occupied target.
- [x] 3.4 Make the Log outcome preserve the capture body and heading and write only `type` and `date`; verify `tests/core/vault/test_processing.py` asserts no category, status, due date, or requester.
- [x] 3.5 Generalize `TemplateCard` to carry `note_type` and an optional category, validate reference and log cards differently, and filter each picker by type; verify `tests/core/test_template_cards.py` covers a reference card, a log card, a log card with a category, and a non-reference/log type.
- [x] 3.6 Add `src/afanes/template_cards/daily.md` as the Daily entry log card and seed eight cards in a new vault; verify `tests/core/vault/test_service.py` asserts the eight files and the Daily entry frontmatter.
- [x] 3.7 Update the bundled guide to explain the log type, its date, and the Log section; verify `tests/core/test_templates.py` asserts the guide parses and contains the new section.
- [x] 3.8 Update `docs/reference/template-cards.md` and the template or processing docs for log cards and the Log outcome; verify `hatch run docs:build` passes.

## 4. Log query service and workspace

- [x] 4.1 Add `src/afanes/core/log.py` with a read-only `LogTimeline` over a snapshot, producing year/month/day buckets, Undated, calendar marks, and Entries/Everything filtering; verify `tests/core/test_log.py` covers each precision, nested entries, Undated, and an empty snapshot.
- [x] 4.2 Extend settings with a per-vault `log_modes` mapping, defaulting to `entries` for a missing or unknown value; verify `tests/core/test_settings.py` covers load, save, an absent mapping, and an unknown value.
- [x] 4.3 Add Log mode, viewed month, and selection state to `BrowserState`; verify `tests/ui/test_state.py` covers reset, mode changes, and mode restoration from settings.
- [x] 4.4 Add `WorkspaceSection.LOG` and its sidebar tile with the current-mode count; verify `tests/ui/test_workspace_view.py` covers the tile, selection, and the Log lower panel.
- [x] 4.5 Build a calendar component with month navigation, day cells, day tint and dot, month and year header dots, and keyboard focus; verify `tests/ui/test_calendar.py` covers the grid, accents, previous/next month, and empty months.
- [x] 4.6 Build the collapsed year/month/day tree with entries at their date level, an Undated row, expand/collapse, and plus/dot controls; verify `tests/ui/test_log_tree.py` covers the three levels, the plus control, the open control, and Undated.
- [x] 4.7 Wire the calendar and tree clicks: one entry opens it, several expand the tree, an empty day creates, and a plus creates a month/year entry; verify `tests/ui/test_workspace_view.py` covers each click path.
- [x] 4.8 Add the Entries/Everything switch and make search filter both the tree and the calendar; verify `tests/ui/test_workspace_view.py` covers the switch, persistence, matching entries, and removed accents.
- [x] 4.9 Keep the page pane as the reading area when a log entry is selected, and refresh the tree after a date change or trash; verify `tests/ui/test_workspace_view.py` covers selection, refresh, and Back.
- [x] 4.10 Add `docs/guide/log.md` and update `docs/guide/workspace.md` and `README.md` for the Log section, calendar, tree, modes, and creation actions; verify `hatch run docs:build` passes.

## 5. Page editor and log pages

- [x] 5.1 Show the note date in the read meta row for every page and add the Date field to the edit form; verify `tests/ui/test_page_view.py` covers a dated note, an undated note, and both dates on a project.
- [x] 5.2 Hide category, status, due date, and requester for log pages, and show the malformed-date warning; verify `tests/ui/test_page_view.py` covers the log form and a bad date.
- [x] 5.3 Add the page date-change command that calls the date-change plan/apply and reports partial rewrite failures; verify `tests/ui/test_state.py` covers a successful change, an occupied date, and a skipped referrer.
- [x] 5.4 Route type changes into and out of `log` through the date/rename path instead of the stranded-reference preview; verify `tests/ui/test_state.py` covers both directions and an undated note.
- [x] 5.5 Update the editing and page documentation for the Date field, the two project dates, and the hidden log labels; verify `hatch run docs:build` passes.

## 6. Integration and gates

- [x] 6.1 Apply the `date-display` formatter to the Date field and log dates when that capability exists, and keep ISO text otherwise; verify the date-related tests pass with and without the formatter.
- [x] 6.2 Run `hatch check` and verify lint, format, and Pyrefly strict pass.
- [x] 6.3 Run `hatch test --cover` and verify the suite passes with coverage at or above 85%.
- [x] 6.4 Run `hatch run docs:build` and verify the documentation builds with warnings as errors.
- [x] 6.5 Run `openspec validate --all --strict` and `openspec doctor` and verify both pass.
- [x] 6.6 Run the vocabulary compliance greps from `AGENTS.md` section 6.1 and verify both exit 1 with no output.
- [x] 6.7 Smoke-test a vault: create, open, edit, date-change, process a capture into a log entry, switch modes, search, and trash a log entry; verify every action matches the specs and no scan writes a file.
- [x] 6.8 Verify opening a vault with undated notes and no `log/` folder leaves every file and folder unchanged.

## Workflow follow-up

- Archive the change after review and green gates.
- Run the post-archive release workflow in `AGENTS.md` section 5.3; bump the version only if the archive completes a coherent milestone.
