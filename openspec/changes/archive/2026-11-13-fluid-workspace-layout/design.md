# Design

## Context

See `proposal.md` for the motivation. The current shell gives the browser a 360 px width token and leaves the detail at the remaining width, while `PageView` centers a 720 px column inside the detail card. The page label row wraps fixed-width controls, and the new-log Starter control sits outside that row. The Log date controls are split across two rows before the calendar.

The workspace already has the breakpoint state and resize entry point needed for a fluid layout. `PageView` already renders the edit form in an expanding host and the body field already expands vertically.

## Goals / Non-Goals

**Goals:**

- Fill every resizable workspace region with the width the window gives it, above the existing minimums.
- Make the page editor use the full detail card width and keep all visible label controls in one adaptive flow.
- Put the Log date controls in one natural-width row.
- Keep the conformance gate and existing architecture rules: tokens for every layout value, views presentational, shared components under `ui/components/`.

**Non-Goals:**

- Making the navigation resizable, or changing its fixed width.
- Changing fixed widths on non-resizable dialogs or the in-window control heights used to align fields.
- Adding a new draggable splitter or user-resizable pane.
- Changing the Processing Wizard form in this change; it has fixed control widths, but no maximum-width cap, and it is outside the reported Log and page-editor paths.

## Decisions

### 1. Fluid browser and detail columns

Replace `BROWSER_MAX_WIDTH` with a share token, `BROWSER_SHARE = 0.35`. In the wide and medium arrangements, the shell computes the browser width from the available width after the navigation and gaps:

```text
browser = clamp(available * BROWSER_SHARE, BROWSER_MIN_WIDTH, available - PAGE_MIN_WIDTH)
detail  = remaining width
```

The browser no longer has a maximum; the upper clamp only protects the detail minimum. The detail keeps `expand=True` and receives every remaining pixel. At narrow widths the browser alone fills the region as today.

Alternative considered: give both regions `expand` factors. Equal flex splits the browser too wide, and a 1:2 flex drops the browser below its 320 px minimum at the 1100 px wide breakpoint. An explicit share with a floor is predictable across the three breakpoints.

The navigation stays fixed because it is a control surface, not a resizable content pane. Dialogs keep their widths because they are not resizable.

### 2. Page content fills the card

Remove `CONTENT_MAX_WIDTH`, the fixed `page_column` width, and the `fit_width` resize plumbing. The page column becomes an expanding child of the card row; the card padding remains the only lateral inset. Read mode and edit mode both use the full width, matching the owner decision to drop the reading cap.

Alternative considered: keep the 720 px cap in read mode and widen only edit mode. Rejected because the owner asked for fully adaptive content and the extra mode-dependent column would add state without a user-visible benefit.

### 3. Adaptive label flow with flex rows

Add a `FieldFlow` component under `src/afanes/ui/components/`. It owns one `ft.Column` of `ft.Row` runs and lays out its visible children from the measured pane width:

1. Compute the row capacity from the field minimum width token and the gap: `capacity = max(1, floor((width + gap) / (FIELD_MIN_WIDTH + gap)))`.
2. Split the visible controls into chunks of that capacity, capped by the number of controls.
3. Set `expand=True` on every visible control and append one `ft.Row` per chunk. Each row divides its width equally between its children.
4. Re-run the layout when the pane width changes or when visibility changes; hidden controls are left out of the rows.

`FieldFlow` exposes the configured `controls` order and the rendered `column`. Rebuilding the rows moves the same controls between runs; Flet serializes the new tree, so no control is duplicated. This differs from the original grid plan: `ResponsiveRow` allocated a twelve-column cell, but a Dropdown kept its intrinsic width inside that cell, which produced the visible gap between Type and Date. Flex rows force every child to fill its share. Alternative considered: fixed-width controls with `Row(wrap=True)`. It cannot stretch children, so it keeps the reported dead space.

`PageView` passes its label controls to the component in this order: Type, Category, Status, Date, Starter, Due date, Owner, Asked by. The page card keeps its `on_size_change` event and forwards the rendered width to `FieldFlow.layout(width)`; type changes and starter visibility call the same method after the existing refresh logic. The body field stays below the flow and keeps `expand=True`.

### 4. Starter joins the label flow

The `TemplateCardPicker` dropdown becomes a child of the `FieldFlow` in the page editor. The existing `log_starter_panel` keeps the description and warning and remains the visibility flag used by tests and refresh logic. The dropdown is hidden when the starter is unavailable; the description and warning hide with the panel.

The panel sits after the flow and before the body field, so the selected card description and invalid-card warning stay directly below the controls rather than inside a narrow field cell.

### 5. Log controls share one row

Replace the two separate rows in `_log_controls` with one `ft.Row(wrap=True)` containing **Today's Entry**, **Entries**, and **Everything** in that order. The buttons keep their intrinsic widths; `wrap` handles the narrow browser case. The calendar, divider, and date tree follow unchanged.

### 6. Sticky behavior

No new sticky positioning is added. The existing fixed headers and detail toolbar already sit outside the scrolling browser list and page content, so they stay visible while their content scrolls. The fluid change only affects width allocation and field wrapping.

## Risks / Trade-offs

- [Very wide read-mode lines] → The owner accepted uncapped content; the detail still receives about 65% of the workspace after the navigation, and the change can add a reading preference later if needed.
- [The browser minimum collides with the detail minimum near 1100 px] → The browser width is clamped to `available - PAGE_MIN_WIDTH`; the breakpoint already collapses the navigation at 1024 px, and the layout is tested at 1024, 1100, and very wide sizes.
- [Dropdowns keep their intrinsic width inside a grid cell] → Use flex rows where every visible control sets `expand=True`; keep a regression test and the three-width visual check.
- [Rebuilding rows on each resize moves controls between parents] → The new tree is serialized whole and tests plus the visual check cover repeated width changes.
- [Visibility changes do not reflow the flow] → Every type change, starter change, and refresh calls the flow layout method; tests cover the log and project label sets.
- [Removing `fit_width` breaks callers] → Replace it and its width-tracking handler with the `FieldFlow` reflow handler, and update the width tests together.
- [Conformance baseline changes] → Use named tokens for the share, minimum field width, and gaps; run the conformance gate and only shrink baseline entries that no longer occur.

## Migration Plan

No data migration. The change is presentational and reversible by restoring the removed width tokens and the two Log rows. Existing vault files, drafts, and log entries are untouched.

## Verification

The desktop app was run against a temporary vault with a new log draft open in the Log section, at 1024x700, 1100x760, and 1800x900.

- At 1024, the Log controls share one row, Type and Date share the first label row, Starter wraps below them because three fields no longer fit, the body fills the card, and no region clips.
- At 1100, the browser and detail fill the window, the two-row label flow remains, and no region clips.
- At 1800, Today's Entry, Entries, and Everything stay in one row; Type, Date, and Starter share one label row with equal widths, the body fills the remaining width and height, and no region clips.
