# Spec Delta

## ADDED Requirements

### Requirement: Keyboard shortcuts are discoverable

The interface SHALL expose one shortcut sheet listing every workspace shortcut, grouped as General,
Calendar, and Navigation. The sheet SHALL open from the primary menu and from `Ctrl+?`, and SHALL
close on Esc. The guide SHALL record that a browser may intercept desktop chords.

#### Scenario: The primary menu opens the sheet

- **WHEN** the user chooses Keyboard Shortcuts… from the primary menu
- **THEN** the shortcut sheet opens with every shortcut grouped by context

#### Scenario: Ctrl+? opens the sheet

- **WHEN** the user presses `Ctrl+?` while the workspace is open
- **THEN** the shortcut sheet opens without changing the active destination or page

#### Scenario: Every context is grouped

- **WHEN** the shortcut sheet renders
- **THEN** General, Calendar, and Navigation shortcuts each appear under their own heading

#### Scenario: Esc closes the sheet

- **WHEN** the shortcut sheet is open and the user presses Esc
- **THEN** the sheet closes without applying a command

#### Scenario: Browser interception is documented

- **WHEN** the user reads the workspace guide
- **THEN** it explains that a browser may intercept `Ctrl+F`, `Ctrl+N`, or `Ctrl+?` in web mode

### Requirement: Every interactive control has an accessible name

Every interactive control SHALL expose an accessible name drawn from its visible text, a tooltip, or
an explicit semantics label. A pointer-only container MUST NOT be the only way to operate a control.
The accessibility gate SHALL require zero unnamed interactive controls and MUST NOT carry a baseline.

#### Scenario: An icon-only action is named

- **WHEN** an icon-only action is rendered
- **THEN** its tooltip or semantics label supplies an accessible name

#### Scenario: A text action uses its label

- **WHEN** a button or menu item renders visible text
- **THEN** that text supplies its accessible name

#### Scenario: A clickable card is focusable and named

- **WHEN** a card is the target of a pointer action
- **THEN** it is reachable by keyboard and exposes the card title as its accessible name

#### Scenario: An unnamed interactive control fails the gate

- **WHEN** a new interactive control has no visible text, tooltip, or semantics label
- **THEN** the accessibility gate fails and names the control

#### Scenario: Decorative content is exempt

- **WHEN** an icon or container is not interactive and carries no meaning
- **THEN** the accessibility gate does not require a name for it

#### Scenario: The accessibility gate has no baseline

- **WHEN** the accessibility gate runs
- **THEN** it requires zero violations and offers no ledger of allowed exceptions

### Requirement: Messages are announced through live regions

The interface SHALL expose banners, toasts, and primary inline validation messages as live regions
where Flet supports them. The visible text SHALL remain the accessible name, and one message MUST NOT
be announced twice.

#### Scenario: A toast is announced

- **WHEN** a toast appears for a completed action
- **THEN** its message surface is a live region that carries the visible text

#### Scenario: A banner is announced

- **WHEN** a persistent banner appears
- **THEN** its message surface is a live region that carries the visible text

#### Scenario: Inline validation is announced

- **WHEN** an inline validation message appears beside a field or form
- **THEN** its message surface is a live region that carries the visible text

#### Scenario: A background refresh stays silent

- **WHEN** a background refresh changes data without showing a new message
- **THEN** no live region announces the refresh

### Requirement: Large text remains usable

At 200% text size, every primary view and dialog SHALL remain usable: text SHALL NOT clip, content
SHALL NOT scroll horizontally, controls SHALL remain reachable, and focus SHALL remain visible.
Text-bearing containers SHALL use minimum sizes and grow with their content.

#### Scenario: The workspace fits at 200% text

- **WHEN** the workspace renders at 1024x600 with 200% text
- **THEN** every region, toolbar, and browser control remains visible and usable without horizontal
  scrolling

#### Scenario: A dialog fits at 200% text

- **WHEN** a dialog renders with 200% text
- **THEN** its title, body, fields, and actions remain visible and reachable

#### Scenario: Focus remains visible at 200% text

- **WHEN** a control receives keyboard focus with 200% text
- **THEN** the focus indicator remains visible and is not clipped

#### Scenario: The real system setting is checked

- **WHEN** the operating system enables Large Text
- **THEN** every primary view remains usable at the minimum window and both breakpoints

### Requirement: The 200% layout is checked automatically

An automated rendered layout check SHALL run the desktop client at 200% text and compare keyed
control geometry in every primary view with a text layout snapshot. It SHALL fail on a missing view,
a collapsed region, a text-bearing control that does not grow, or geometry outside tolerance.

#### Scenario: A matching snapshot passes

- **WHEN** the rendered layout matches the committed snapshot
- **THEN** the layout check passes

#### Scenario: A non-growing text control fails

- **WHEN** a text-bearing control stays at its 100% height after text doubles and its text is not an
  intentional single-line ellipsis
- **THEN** the layout check fails and names the control

#### Scenario: A missing view fails

- **WHEN** a primary view does not render during the scripted tour
- **THEN** the layout check fails and names the missing view

#### Scenario: The check covers every primary view

- **WHEN** the layout check runs
- **THEN** it records the workspace destinations, the page states, the focused flows, and the
  shortcut and date dialogs at 200% text
