# Design

## Context

See `proposal.md` for motivation. The current state that shapes the approach:

- `PageView` is created once by `WorkspaceView` and its scrollable `content` column is reused
  across page changes. Flet does not guarantee an implicit scroll reset when children change.
- `_refresh_connections` always builds four subsections and the shared finished-projects toggle
  lives inside the Requested projects section.
- The Processing Wizard lists six outcomes; `ProcessingOutcome.LOG` already exists in core.
- Rename, type change, date change, and repair already return reports with updated, skipped, and
  failed paths; the UI discards the names and shows only a count.
- The parser treats a null `status` or `due_date` as absent before the note-type check.
- The architecture gate forbids new module-level functions and polices label writes.

Constraints: offline-only, no new dependency, `core` never imports Flet, views never perform
file I/O, one writer per vault, Pyrefly strict, 85% coverage.

## Goals / Non-Goals

**Goals:**

- Align behavior, specs, tests, and docs for the six audit findings.
- Keep the work inside the existing view/controller/core boundaries.
- Make each behavior testable at the UI boundary without a rendered window.
- Close the 15 missing-scenario gaps and the prioritized weak tests in the same change.

**Non-Goals:**

- Implement the matching-step display; the search spec is amended instead.
- Add a details dialog for rewrite reports.
- Fix all 48 weak tests or rewrite the audit report.
- Change parser behavior for null values.
- Edit the archived `add-project-roles` artifacts.

## Decisions

### 1. Connection sections are content-only; reveal controls live in the panel footer

`PageView._refresh_connections` builds a section only when it has at least one visible row. The
two checkboxes are passed to the existing `Panel` actions row, which is currently empty. A section
with only hidden completed items is omitted; the footer control remains visible because the
underlying connection set still has those items. Enabling the control re-renders the section.

This avoids duplicating the shared finished-projects toggle and avoids an empty heading whose only
content is a checkbox. The placeholder strings for empty sections become unused and are removed.
The `_show_completed_steps` and `_show_finished_projects` state stays on `PageView`.

Alternatives considered: keep toggles inside each section and duplicate the finished toggle in both
project sections (rejected: duplicate state and empty-looking sections); keep placeholders
(rejected: contradicts the specification and the docs).

### 2. The search requirement is narrowed, not the code

`ProjectsView` continues to render `next_step`; it will not render the matching step. The
`vault-browsing` delta changes the step-text scenario to require only that the project is listed.
This matches the existing documentation, which promises filtering but not match display.

Alternative considered: add a core helper that scans `note.steps` and render a `Match:` line
(rejected: extra core API and sidebar complexity for a behavior the maintainer chose not to keep).

### 3. Log entry is added to the wizard

Add `ProcessingOutcome.LOG` to `ProcessingView`'s ordered outcome list and add `"log": "Log entry"`
to `PROCESSING_OUTCOME_LABELS`. The existing `_refresh_dynamic` logic already hides status, due date,
roles, project, and template for non-project outcomes, and `_populate_plan` already uses the label
map. The change is the option, the label, and the tests.

Alternative considered: remove Log entry from the spec and docs (rejected: the archived log change
promised the outcome, core implements it, and the docs describe it).

### 4. Every page change explicitly scrolls to the top

Add `PageView.scroll_to_top()`, which awaits `self.content.scroll_to(offset=0, duration=0)`. Call it
after the page changes in:

- `WorkspaceView._select` after `_refresh_dynamic`;
- `PageView.open_connection` after `refresh`;
- `PageView.go_back` after `refresh`;
- `PageView.handle_link` after the linked page opens.

The `content` column is long-lived, so an implicit reset is not reliable. The explicit call covers
browser selection, links, connection entries, owned steps, and Back. Tests replace
`content.scroll_to` with an async recorder and assert `offset == 0`, because the real method requires
an attached Flet page.

Alternative considered: reset only for owned-step selection (rejected: the same defect affects every
page change, and the spec now states the general rule).

### 5. One rewrite report formatter for all four paths

Add a private method on `PageDialogState` that accepts `RenameReport | RewriteReport` and formats:

- `Updated: <relative paths>` for `updated`;
- `Not updated: <relative paths>` with the failure message for `failed` and the changed-on-disk
  reason for `skipped`.

The method uses `session.vault_root` to make paths relative and returns `None` when there are no
skipped or failed notes. Each of the four call sites keeps its total-failure string for exceptions
and uses a new partial-success string for the report. This avoids the current misleading “could not”
message when the operation succeeded.

Alternative considered: a report dialog or panel (deferred: partial failures are rare and the status
banner already exists). The formatter stays a private method because the architecture gate forbids
new module-level functions in `ui/state/dialogs.py`.

### 6. Null value keys are absent; parser behavior is unchanged

The `note-model` delta states that a null `status` or `due_date` is absent on every note type. The
parser keeps its early null return for those value keys. Category, requester, and owner remain strict
because they must name something. Tests add the log and reference null cases that the audit found.

Alternative considered: reject a forbidden key even when null (rejected: a blank hand-edited line
would make the note unreadable for a value that means nothing).

### 7. Test hardening is prioritized, not exhaustive

The change adds the fifteen missing-scenario tests, the report’s prioritized weak tests, and `owner`
in `LABEL_KEYS`. Tests use `tmp_path`, local fixtures, and `app_state.reset()`; they do not import
leading-underscore members. If a strengthened test exposes a behavior bug, implementation stops and
the change is amended rather than marking the task complete.

### 8. Prose cleanup stays narrow

Fix the frontmatter docstring (“six” recognized keys) and rename the stale `vault-browsing` and
`note-editing` requirement titles through a `RENAMED` delta. The `vault-browsing` Purpose remains for
a separate direct prose edit because OpenSpec deltas carry requirements, not Purpose.

### 9. One change, many small commits

The proposal and specs define one archive event, but implementation commits follow the tasks: one
commit per behavior fix with its regression tests, then separate commits for the gap tests, the weak
tests, the gate, and the documentation. This keeps the history reviewable and satisfies the
task-by-task workflow.

## Risks / Trade-offs

- **Large single change** → task-by-task commits, behavior fixes before test hardening, and a final
  layer-2 trace of the changed capabilities.
- **Flet scroll calls need an attached control** → call only from attached page-change paths and
  replace the method in tests.
- **Partial-failure banner can be long** → use vault-relative paths and reserve a details dialog for
  a follow-up if real reports become unwieldy.
- **Test hardening may reveal new gaps** → stop and amend the change; never mark a partial task
  complete.
- **Removing placeholder strings changes the visual layout** → update the strings module and the
  connection tests together.
- **Requirement renames and a MODIFIED block in the same delta** → OpenSpec applies `RENAMED` before
  `MODIFIED`; validate strictly after writing the delta.
- **Spec-only amendments can drift from code** → add the null and search tests in the same change.
- **Hidden-only sections depend on the footer control** → test a page with only a finished owned
  project and a page with only a completed owned step.

## Migration Plan

No data migration and no file-format change. Existing vaults remain valid; the null clarification is
retroactive. The UI changes are presentational and the scroll reset has no persistent state. Rollback
is a code and spec revert; no vault file is rewritten by this change.

The archive adds entries under `Unreleased`; no version bump unless a milestone completes.

## Open Questions

None blocking. The `vault-browsing` Purpose prose edit is deferred and does not affect the approach
or task breakdown.
