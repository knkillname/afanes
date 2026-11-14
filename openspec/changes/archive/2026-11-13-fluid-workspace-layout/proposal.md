# Proposal

## Why

The workspace still uses fixed maximum widths and fixed field widths from the initial adaptive shell, so wide windows leave large unused gutters in the detail region and force related controls onto separate rows even when they fit. The Log destination shows **Today's Entry** on its own row above **Entries** and **Everything**, and a new log draft puts **Starter** below **Type** and **Date** instead of in the same flowing row. The result wastes space and makes the editor feel less responsive than the rest of the window.

## What Changes

- Remove the 720 px page-content cap so read and edit content fill the detail card at every window size.
- Remove the 360 px browser cap; the browser and detail share the remaining window width above their minimum widths, with the detail receiving the larger share.
- Replace fixed label-field widths in the page editor with one adaptive flow: visible fields share the available row, wrap only when the pane is too narrow, and grow to fill each row.
- Move the **Starter** dropdown for a new log draft into that same flow as **Type** and **Date**, while its description and warning remain directly below the fields.
- Put **Today's Entry**, **Entries**, and **Everything** in one Log control row that uses natural control widths and wraps only when the browser is too narrow.
- Keep fixed widths only for non-resizable surfaces and structural chrome: navigation, drawer, dialogs, headers, and the minimum window size.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interface-theme`: The workspace column requirement changes from bounded maximum widths to fluid columns that fill the window above their minimums; the page-content maximum width is removed.
- `note-editing`: The label form changes from fixed-width fields to one adaptive flow that includes the log **Starter** control; the body and form fill the detail region.
- `note-log`: The Log date controls gain a shared-row arrangement for **Today's Entry**, **Entries**, and **Everything**.

## Impact

- `src/afanes/ui/theme.py`: retire the browser and content maximum-width tokens; add the fluid layout and minimum field-width tokens.
- `src/afanes/ui/views/workspace.py`: size the browser and detail from available width and put the Log controls in one wrapping row.
- `src/afanes/ui/views/page.py`: fill the detail region, move the Starter dropdown into the label flow, and use an adaptive field layout.
- A shared `FieldFlow` component under `src/afanes/ui/components/` that owns the adaptive label rows.
- `tests/ui/test_theme.py`, `tests/ui/test_workspace_view.py`, `tests/ui/test_page_view.py`, `tests/ui/test_field_flow.py`, and `tests/ui/test_conformance.py`: update width expectations, add flow and Log-row coverage, and keep the conformance baseline shrinking.
- `docs/develop/interface-standard.md`, `docs/guide/workspace.md`, `docs/guide/log.md`, and `docs/guide/pages-and-editing.md`: document fluid columns, the page-width change, and the shared Log control row.
