# Proposal

## Why

In the guided review, entering an Inbox item opens the Processing Wizard through
`ReviewState._enter_current_review_item()`, which does not load the vault template card catalog.
Choosing Reference or Later therefore shows an empty Template field until the user cancels and
reopens the capture from the Inbox. The wizard should offer the same choices regardless of where it
opens.

## What Changes

- Centralize opening a capture in `ProcessingState` so loading always reads the capture body and the
  vault's template card catalog together.
- Use that shared path from both Inbox processing and guided review entry and advance.
- Rebuild the Template dropdown options whenever the wizard refreshes, keeping a valid selection and
  falling back to Empty when a chosen card is no longer available.
- Add state and view tests for review entry, review advance, and option refresh.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `guided-review`: an Inbox item in a review session opens the Processing Wizard with the same
  template choices as processing from the Inbox.

## Impact

- `src/afanes/ui/state/processing.py`, `src/afanes/ui/state/review.py`,
  `src/afanes/ui/views/processing.py`
- `tests/ui/test_state.py`, `tests/ui/test_processing_view.py`
- No dependency, vault format, network, or user-facing documentation change. The documentation
  already states that the Template field lists every valid card plus Empty.
