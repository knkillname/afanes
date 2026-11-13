# interface-theme Specification

## Purpose

Defines the visual identity of the Afanes interface: how it follows the operating system's light or
dark mode, the palette roles it exposes, how accent and surface depth communicate structure, and
the minimum legibility guarantees in each mode.

## Requirements


### Requirement: Appearance follows the operating system mode

Afanes SHALL present a light interface when the operating system requests a light appearance and a
dark interface when it requests a dark appearance, without a separate in-app switch.

#### Scenario: Light system appearance

- **WHEN** the interface starts while the operating system requests a light appearance
- **THEN** the interface renders with its light palette

#### Scenario: Dark system appearance

- **WHEN** the interface starts while the operating system requests a dark appearance
- **THEN** the interface renders with its dark palette

#### Scenario: Appearance changes while running

- **WHEN** the operating system appearance changes while the interface is open
- **THEN** the interface updates to the matching palette without restarting

### Requirement: Both modes define a complete, legible palette

Each mode SHALL define an independent palette from the Adwaita 1.8.0 reference: window, view,
sidebar, header bar, secondary container, body text, muted text, accent fill, accent text, status
colors, and the destructive color. The dark palette MUST be defined explicitly rather than derived
from the light palette by an automatic algorithm.

#### Scenario: Every role resolves in both modes

- **WHEN** the interface renders in either mode
- **THEN** every role it uses resolves to a defined value for that mode

#### Scenario: Reference surfaces resolve in both modes

- **WHEN** the interface renders in either mode
- **THEN** the window, sidebar, view, and secondary container resolve to the reference surface values for that mode

#### Scenario: Contrast holds in both modes

- **WHEN** body text, muted text, accent text, control labels, and focus indicators are rendered in either mode
- **THEN** body text and muted text meet a 4.5:1 contrast ratio against the window, sidebar, view, and container surfaces, accent text meets 4.5:1 against the view surface, and accent fills, icons, and control boundaries meet 3:1

#### Scenario: Text on a suggested fill inherits the reference threshold

- **WHEN** a label sits on the suggested accent fill
- **THEN** it meets 3:1 and is not treated as body text, matching the contrast of the reference implementation

#### Scenario: The dark palette is independent

- **WHEN** the interface renders in dark mode
- **THEN** its surfaces, text, accent, and status roles use the palette defined for dark mode rather than the light values

### Requirement: A restrained accent and action pair

The interface SHALL use one accent color for suggested actions, focus indicators, and links.
Selection SHALL use the neutral selected-row treatment, not the accent. The accent SHALL expose a
fill role and a text role, and the text role MUST meet a 4.5:1 contrast ratio against the view
surface. The interface MUST NOT introduce a second action hue, MUST NOT rely on hue alone to signal
state, and SHALL give destructive actions a distinct destructive style.

#### Scenario: Primary actions and selection use their assigned colors

- **WHEN** a primary action is shown and an entry is selected
- **THEN** the action uses the accent fill role and the selection uses the neutral selected-row token

#### Scenario: Suggested actions use the accent

- **WHEN** a suggested action is shown
- **THEN** its fill uses the accent fill role

#### Scenario: Accent text stays legible

- **WHEN** the accent text role is used for a link or small label on the note view
- **THEN** it meets a 4.5:1 contrast ratio against that surface in both modes

#### Scenario: Destructive actions are distinguished

- **WHEN** an action removes, moves, or discards a note
- **THEN** it uses the destructive style rather than the suggested style

#### Scenario: Focus is visible independently of hover

- **WHEN** a control receives keyboard focus
- **THEN** it shows a focus indicator using the accent color that does not depend on hover state

#### Scenario: State survives without hue

- **WHEN** the interface is viewed without color perception
- **THEN** selection, focus, and status remain distinguishable through shape, weight, icon, or text

### Requirement: Surfaces separate through boundaries

The window, navigation region, browser region, note view, and secondary containers SHALL resolve to four distinct surface values in each mode. Navigation SHALL use the sidebar surface and the browser SHALL use the window surface. Separation MAY combine a value step with a border. The note view SHALL be the brightest surface in light mode and darker than the window and navigation in dark mode. A selected entry SHALL use a neutral selected-row fill.

#### Scenario: The four roles differ

- **WHEN** the interface renders in either mode
- **THEN** the window, sidebar, note view, and secondary-container surfaces resolve to four different values

#### Scenario: Structural regions separate from the page

- **WHEN** the workspace renders with its navigation, browser, and detail regions
- **THEN** a value step or a visible boundary separates each region from the window background in both modes

#### Scenario: The browser shares the window surface

- **WHEN** the workspace renders its browser region
- **THEN** the browser uses the window surface and does not add a fifth surface role

#### Scenario: Cards separate from their container

- **WHEN** a view or panel appears inside a structural region
- **THEN** its surface or boundary distinguishes it from the region behind it in both modes

#### Scenario: The note canvas stays white

- **WHEN** a note is open in light mode
- **THEN** the Markdown view is the brightest surface in the window

#### Scenario: The note canvas is darker than the chrome in dark mode

- **WHEN** a note is open in dark mode
- **THEN** the Markdown view is darker than the window and navigation region

#### Scenario: Selection uses a neutral fill

- **WHEN** a navigation or browser entry is selected
- **THEN** its row uses the neutral selected-row token with no accent tint or accent edge, and remains distinguishable from an unselected row without relying on hue alone

### Requirement: Typographic hierarchy uses one family

Interface text SHALL use a single font family supplied by the platform. Hierarchy MUST come from the
GNOME standard styles — `title-1` through `title-4`, `heading`, `body`, `caption`, and
`caption-heading` — expressed as relative percentages of a base size rather than per-control sizes
or weights. The application MUST NOT bundle a font file.

#### Scenario: Page title outranks body text

- **WHEN** a note page shows its title above rendered body text
- **THEN** the title uses a higher standard role than the body text in the same family

#### Scenario: Secondary metadata recedes

- **WHEN** a note shows identity, path, or other metadata beside its title
- **THEN** the metadata uses the caption role rather than the body role

#### Scenario: No additional font is required

- **WHEN** the application runs on a machine without additional installed fonts
- **THEN** the interface renders its full hierarchy with the platform font family

#### Scenario: No font asset ships

- **WHEN** the packaged application is inspected
- **THEN** it contains no bundled font file

#### Scenario: Hierarchy uses named standard roles

- **WHEN** a control renders text with a distinct hierarchy
- **THEN** it selects a named standard role instead of setting its own size, weight, or Material theme-role name

#### Scenario: The scale is relative

- **WHEN** the base text size changes
- **THEN** every standard role scales proportionally

### Requirement: Browser sections use one monochrome icon treatment

Each browser section SHALL show its label and its own icon using one neutral tint. The active section
SHALL use the neutral selected-row treatment. The interface MUST NOT assign a distinct hue to each
section and MUST NOT use the accent to distinguish one section from another.

#### Scenario: Label and icon identify the section

- **WHEN** the browser lists Inbox, Projects, References, Log, and Review
- **THEN** each entry shows its label and its own icon

#### Scenario: Active section uses the neutral selected row

- **WHEN** a section is active
- **THEN** its row uses the neutral selected-row token rather than a section-specific hue or the accent

#### Scenario: Non-active sections share one tint

- **WHEN** the browser renders its inactive sections
- **THEN** their icons use the same neutral tint

#### Scenario: Identity survives without color

- **WHEN** the active fill is not distinguishable
- **THEN** the label and icon still identify the section

#### Scenario: Accent is not a section identity

- **WHEN** two sections are compared
- **THEN** the accent does not distinguish one section from another

### Requirement: Interface icons are monochrome and tinted in code

The interface SHALL render icons as monochrome symbolic or outlined glyphs at the standard sizes
defined by the tokens, and SHALL apply color only through a named tint role. It MUST NOT ship a
custom interface icon set; a single application icon is outside this requirement.

#### Scenario: Icons are monochrome

- **WHEN** any interface icon is rendered
- **THEN** its glyph is monochrome and its color comes from a tint role

#### Scenario: Tint follows meaning

- **WHEN** an icon carries a section, accent, muted, or destructive meaning
- **THEN** it uses the corresponding tint role rather than an arbitrary color

#### Scenario: Icons use token sizes

- **WHEN** an interface icon is rendered
- **THEN** its size comes from an icon-size token rather than an arbitrary literal

#### Scenario: Icons use the symbolic style

- **WHEN** an icon has an outlined or symbolic variant
- **THEN** the interface uses that variant instead of a filled pictorial glyph

#### Scenario: No custom interface icon assets

- **WHEN** the packaged application is inspected
- **THEN** it contains no custom interface icon set

### Requirement: Differences from the reference language are bounded

Afanes SHALL conform to the reference language except where the Flet toolkit cannot express a
guideline mechanism: the Material interface icon set (asset-free), the toolkit's widget rendering,
the absent access-key mnemonics, the absent high-contrast input, and the native title bar that cannot
host application controls. The platform typeface is guideline-required, not a difference. Each
difference MUST be recorded in the interface standard, and removing one SHALL require its own change.

#### Scenario: A new difference requires a spec change

- **WHEN** a change proposes a visual behavior outside the reference language
- **THEN** it records the difference and updates this requirement rather than adding it silently

#### Scenario: The recorded list matches the implementation

- **WHEN** the interface standard lists differences
- **THEN** that list matches the icon, widget-rendering, access-key, high-contrast, and native-title-bar behavior the application actually ships

#### Scenario: The platform typeface is not a difference

- **WHEN** the differences are listed
- **THEN** the platform typeface is described as the guideline-required choice rather than as a deviation

#### Scenario: The limiting toolkit is named

- **WHEN** a toolkit limitation is documented
- **THEN** it names the Flet API that is missing rather than a broader framework

#### Scenario: The title bar stays native

- **WHEN** the application runs on a desktop platform
- **THEN** the operating-system title bar is used as provided and the workspace toolbar is the in-window equivalent of the reference header bar

### Requirement: Control values come from the interface tokens

Every color, corner radius, spacing, dimension, icon size, column width, maximum content width, and minimum window value SHALL come from the interface token module. The minimum window SHALL be 1024x600. The build SHALL fail when a view or component introduces a value outside those tokens, except for entries enumerated in a conformance baseline that may only shrink.

#### Scenario: A literal fails the build

- **WHEN** a view or component introduces a color, radius, spacing, dimension, icon size, column width, content width, or minimum-window literal that is not in the token module
- **THEN** the conformance gate fails and names the file and value

#### Scenario: The baseline may only shrink

- **WHEN** a change removes a baseline entry by migrating the offending code
- **THEN** the same change deletes that entry, and a baseline entry that no longer matches a violation also fails the gate

#### Scenario: The smallest window fits the reference desktop size

- **WHEN** the application opens at its minimum window size
- **THEN** the window is 1024x600 and no control clips

#### Scenario: Column widths come from tokens

- **WHEN** the workspace lays out its navigation, browser, and detail regions
- **THEN** every width and breakpoint comes from a named token rather than a literal in a view

#### Scenario: Strict visual rules are gated

- **WHEN** a view introduces a Material text-role name, an arbitrary icon size, or an accent selection
- **THEN** the conformance gate fails

### Requirement: Workspace columns use bounded widths

The navigation, browser, and detail regions SHALL have widths that support adaptive scaling. Navigation SHALL keep a fixed width. The browser SHALL have a minimum and maximum width. The detail SHALL keep at least its minimum content width and SHALL constrain long-form text and forms to a maximum content width on large windows.

#### Scenario: The browser has a minimum width

- **WHEN** the browser region is shown
- **THEN** its width is at least the browser minimum token

#### Scenario: The browser has a maximum width

- **WHEN** the window is wider than the sum of the three regions
- **THEN** the browser does not grow past its maximum token

#### Scenario: The note text is bounded on a large window

- **WHEN** a note is open in a very wide window
- **THEN** its prose and form controls stay within the maximum content width rather than spanning the whole window

#### Scenario: The detail keeps its minimum

- **WHEN** the browser is at its maximum width
- **THEN** the detail region is not narrower than its minimum content width

#### Scenario: No control clips at the minimum window

- **WHEN** the workspace renders at 1024x600 in either mode
- **THEN** no navigation, browser, toolbar, or detail control clips horizontally or vertically

### Requirement: A view has at most one suggested or destructive action

A view SHALL contain at most one control using either the suggested style (accent-filled) or the
destructive style. Views enumerated in the conformance baseline are tracked exceptions until they
are migrated, and a new or modified view MUST conform.

#### Scenario: A new view conforms

- **WHEN** a view is added
- **THEN** it contains no more than one suggested-or-destructive-style control

#### Scenario: A view does not combine both styles

- **WHEN** a view shows a suggested action
- **THEN** it does not also show a destructive action in the same view

#### Scenario: An existing exception is tracked

- **WHEN** an unmigrated view exceeds the limit
- **THEN** its file is listed in the conformance baseline and the gate passes

### Requirement: Buttons carry an icon or a label, not both

Outside a header bar, a sidebar, or a view switcher, a button SHALL contain either an icon or a
label. Views enumerated in the conformance baseline are tracked exceptions until they are migrated,
and a new or modified view MUST conform.

#### Scenario: A new button chooses one

- **WHEN** a button outside a header bar, sidebar, or view switcher is added
- **THEN** it shows either an icon or a label, not both

#### Scenario: The sidebar exception is allowed

- **WHEN** a sidebar row shows an icon and a label
- **THEN** the combination is allowed

#### Scenario: An existing exception is tracked

- **WHEN** an unmigrated button shows both
- **THEN** its file is listed in the conformance baseline and the gate passes
