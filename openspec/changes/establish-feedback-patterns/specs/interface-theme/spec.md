# Spec Delta

## ADDED Requirements

### Requirement: Feedback matches the lifetime of the event

The interface SHALL choose a feedback surface from the lifetime of the event: a transient toast for
a completed one-time action or undo, a banner for a condition that remains true, inline text for a
field or form problem, and an inline panel or dialog for a decision. A persistent condition MUST NOT
rely on a toast, and a one-time event MUST NOT leave a banner.

#### Scenario: A completed action uses a toast

- **WHEN** a user action completes and its result is not already visible in the interface
- **THEN** the result is reported in a transient toast

#### Scenario: A persistent condition uses a banner

- **WHEN** a condition remains true until the user resolves it
- **THEN** the condition is reported in a banner that does not dismiss on a timer

#### Scenario: A validation problem uses inline text

- **WHEN** a field or form value is invalid
- **THEN** the problem appears inline with that field or form rather than only in a banner or toast

#### Scenario: A decision uses a panel or dialog

- **WHEN** an action needs a choice or a consequence preview
- **THEN** the choice appears in an inline panel or a dialog

### Requirement: Toasts are transient and carry at most one action

A toast SHALL appear at the bottom center of the window, remain dismissible, and disappear on its
own. It SHALL carry a short title and at most one action. An action MUST be directly related to the
message and SHALL name the operation. A toast MUST NOT be the only report of a condition that
remains true, and its surface SHALL come from the interface tokens in both appearance modes.

#### Scenario: A toast appears at the bottom center

- **WHEN** a toast is shown
- **THEN** it appears at the bottom center of the window rather than over a particular region

#### Scenario: A toast dismisses itself

- **WHEN** a toast is shown without further interaction
- **THEN** it disappears after its transient interval

#### Scenario: A toast carries at most one action

- **WHEN** a toast offers an action
- **THEN** it offers exactly one action, and the action names the operation

#### Scenario: A toast without an action is allowed

- **WHEN** a one-time event needs only an explanation
- **THEN** the toast may carry no action

#### Scenario: A background refresh preserves the toast

- **WHEN** a background refresh completes while a toast is visible
- **THEN** the toast remains visible until its own interval ends or the user dismisses it

#### Scenario: A toast renders in both modes

- **WHEN** a toast is shown in either appearance mode
- **THEN** its surface and text use the themed overlay values and remain legible

### Requirement: Reversible destructive actions offer undo

When an action can be undone without data loss, the interface SHALL offer Undo in a toast instead of
a confirmation. An irreversible action SHALL use a confirmation that places Cancel first. The undo
opportunity SHALL be transient and SHALL end when the toast is dismissed or replaced.

#### Scenario: Trash offers Undo instead of a confirmation

- **WHEN** the user moves a note to trash
- **THEN** the move happens without a confirmation surface and a toast offers Undo

#### Scenario: Undo restores the action

- **WHEN** the user selects Undo on the toast for a reversible action
- **THEN** the action is reversed without data loss

#### Scenario: An irreversible action uses a confirmation

- **WHEN** an action cannot be undone
- **THEN** the interface asks for confirmation and places Cancel before the affirmative action

#### Scenario: A dismissed toast ends the undo opportunity

- **WHEN** the toast is dismissed or replaced before the user selects Undo
- **THEN** the reversible action is no longer offered for undo

### Requirement: Banners report persistent conditions only

A banner SHALL report a condition that remains true until it is resolved. It MUST NOT dismiss on a
timer. It SHALL be rendered from the state that owns the condition, and a background refresh MUST
NOT clear it.

#### Scenario: A page conflict stays visible across a refresh

- **WHEN** a page has an external change and a background refresh completes
- **THEN** the conflict banner remains visible

#### Scenario: A refresh failure stays until the next success

- **WHEN** a refresh fails and a later refresh succeeds
- **THEN** the failure banner remains until the successful refresh clears the condition

#### Scenario: A one-time failure does not use a banner

- **WHEN** a user action fails once and leaves no ongoing condition
- **THEN** the failure is reported in a toast rather than a banner

#### Scenario: A banner is owned by its condition

- **WHEN** a persistent condition is resolved
- **THEN** the banner is cleared by the state that owns the condition, not by an unrelated command

### Requirement: Inline feedback stays with its field or form

A validation problem SHALL appear inline with the field or form that caused it. It MUST NOT be
reported only in a banner or toast. The inline text SHALL identify the problem and SHALL clear when
the input becomes valid or the form closes.

#### Scenario: An invalid category shows inline

- **WHEN** a category value contains a path separator
- **THEN** the page reports the problem beside the category field

#### Scenario: A missing rename title shows inline

- **WHEN** a rename title is blank
- **THEN** the rename panel reports the problem beside its field

#### Scenario: A valid input clears the inline problem

- **WHEN** the user corrects an invalid field
- **THEN** the inline problem disappears without a separate command

#### Scenario: A form-level failure stays in the form

- **WHEN** a form command fails while the form is open
- **THEN** the failure appears in that form rather than in a page-wide banner

### Requirement: Dialogs follow the reference action rules

A dialog SHALL place initial focus on the first control the user should operate and SHALL close on
Esc. A destructive dialog MUST NOT assign its affirmative action as the default. The confirmation
order and labels remain those of the confirmation requirement.

#### Scenario: Initial focus reaches the first control

- **WHEN** a dialog opens
- **THEN** initial focus is on the control the user is expected to operate first

#### Scenario: Esc cancels the dialog

- **WHEN** the user presses Esc while a dialog is open
- **THEN** the dialog closes without applying the action

#### Scenario: A destructive dialog has no default action

- **WHEN** a dialog carries a destructive affirmative action
- **THEN** pressing Return does not trigger that action by default

#### Scenario: A dialog keeps the confirmation order

- **WHEN** a dialog asks for confirmation
- **THEN** Cancel appears before the affirmative action and the affirmative action names the operation

### Requirement: Menus and popovers stay small and close on Esc

A menu or popover SHALL stay small and low in complexity, SHALL close on Esc, and MUST NOT require
Close or Done buttons.

#### Scenario: A menu closes on Esc

- **WHEN** the user presses Esc while a menu or popover is open
- **THEN** it closes without applying a command

#### Scenario: A popover has no Close or Done button

- **WHEN** a popover is shown
- **THEN** it does not require a Close or Done button to dismiss it

#### Scenario: A popover stays small

- **WHEN** a popover is shown
- **THEN** it remains small and low in complexity rather than covering the work surface

### Requirement: Confirmation surfaces put Cancel first

A confirmation surface SHALL place Cancel before the affirmative action in reading order. The
affirmative action SHALL name the operation. Cancel MUST leave the note and the vault unchanged.

#### Scenario: A type change puts Cancel first

- **WHEN** the page offers changing a note's type
- **THEN** Cancel appears before the affirmative action

#### Scenario: A category move puts Cancel first

- **WHEN** the page offers moving a note to a category folder
- **THEN** Cancel appears before the affirmative action

#### Scenario: A rename puts Cancel first

- **WHEN** the page offers renaming a note
- **THEN** Cancel appears before the affirmative action

#### Scenario: Cancel changes nothing

- **WHEN** the user cancels any confirmation
- **THEN** no note is written, renamed, moved, or removed

## REMOVED Requirements

### Requirement: Confirmations put Cancel first

**Reason**: The trash confirmation is removed because trash is now immediate and undoable. The
remaining confirmation surfaces keep the same Cancel-first rule under the replacement requirement.

**Migration**: No user action is required. The type-change, category-move, rename, and other
confirmation surfaces keep Cancel before the affirmative action.
