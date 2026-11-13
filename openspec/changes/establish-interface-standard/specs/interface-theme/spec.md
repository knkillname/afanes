# Spec Delta

## MODIFIED Requirements

### Requirement: Both modes define a complete, legible palette

Each mode SHALL define an independent palette: page and layered surface values, borders, body text,
muted text, accent fill, accent text, status colors, and the destructive color. The dark palette MUST
be defined explicitly rather than derived from the light palette by an automatic algorithm.

#### Scenario: Every role resolves in both modes

- **WHEN** the interface renders in either mode
- **THEN** every role it uses resolves to a defined value for that mode

#### Scenario: Contrast holds in both modes

- **WHEN** body text, muted text, control labels, and focus indicators are rendered in either mode
- **THEN** body text meets a 4.5:1 contrast ratio against its background, and large text, icons, and control boundaries meet 3:1

#### Scenario: The dark palette is independent

- **WHEN** the interface renders in dark mode
- **THEN** its surfaces, text, accent, and status roles use the palette defined for dark mode rather than the light values

### Requirement: A restrained accent and action pair

The interface SHALL use one accent color for selection, focus indicators, and suggested actions. The
accent SHALL expose a fill role and a text role, and the text role MUST meet a 4.5:1 contrast ratio
against the surface it sits on. The interface MUST NOT introduce a second action hue, MUST NOT rely on
hue alone to signal state, and SHALL give destructive actions a distinct destructive style.

#### Scenario: Primary actions and selection use their assigned colors

- **WHEN** a primary action is shown and an entry is selected
- **THEN** the action uses the accent fill role and the selection uses the accent tint

#### Scenario: Suggested actions use the accent

- **WHEN** a suggested action is shown
- **THEN** its fill uses the accent fill role

#### Scenario: Accent text stays legible

- **WHEN** the accent text role is used for a link or small label
- **THEN** it meets a 4.5:1 contrast ratio against its surface in both modes

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

The page, structural regions such as the sidebar, and content cards SHALL resolve to three distinct
surface values in each mode. Separation MAY combine a value step with a border. The note canvas SHALL
stay the brightest surface in light mode. A selected browser entry SHALL use an accent tint.

#### Scenario: The three roles differ

- **WHEN** the interface renders in either mode
- **THEN** the page, structural-region, and content-card surfaces resolve to three different values

#### Scenario: Structural regions separate from the page

- **WHEN** the workspace renders with its sidebar and content area
- **THEN** a value step or a visible boundary separates them from the page background in both modes

#### Scenario: Cards separate from their container

- **WHEN** a card or panel appears inside a structural region
- **THEN** its surface or boundary distinguishes it from the region behind it in both modes

#### Scenario: The note canvas stays white

- **WHEN** a note is open in light mode
- **THEN** the Markdown canvas is the brightest surface in the window

#### Scenario: Selection uses a neutral fill

- **WHEN** a browser entry is selected
- **THEN** its row keeps the neutral row surface, adds an accent tint over it, and remains distinguishable from an unselected row without relying on hue alone

### Requirement: Typographic hierarchy uses one family

Interface text SHALL use a single font family supplied by the platform. Hierarchy MUST come from the
named text-theme roles rather than from font sizes or weights set on individual controls, and the
application MUST NOT bundle a font file.

#### Scenario: Page title outranks body text

- **WHEN** a note page shows its title above rendered body text
- **THEN** the title is visibly larger or heavier than the body text in the same family

#### Scenario: Secondary metadata recedes

- **WHEN** a note shows identity, path, or other metadata beside its title
- **THEN** the metadata uses the muted text role rather than the body text role

#### Scenario: No additional font is required

- **WHEN** the application runs on a machine without additional installed fonts
- **THEN** the interface renders its full hierarchy with the platform font family

#### Scenario: No font asset ships

- **WHEN** the packaged application is inspected
- **THEN** it contains no bundled font file

#### Scenario: Hierarchy uses named text styles

- **WHEN** a control renders text with a distinct hierarchy
- **THEN** it selects a named text-theme role instead of setting its own font size or weight

## REMOVED Requirements

### Requirement: Browser sections have a redundant identity

**Reason**: Strict adherence to the reference design language replaces four per-section hues with one monochrome icon treatment and an accent-marked active section. The removed requirement mandated the hues, so it conflicts with the standard this change establishes.

**Migration**: Sections are identified by their label and icon. The active section is marked with the accent tint, the accent edge, and the accent icon color. The label and icon still carry the identity when color is not perceived.

## ADDED Requirements

### Requirement: Browser sections use one monochrome icon treatment

Each browser section SHALL show its label and its own icon using one neutral tint, and the active
section SHALL be marked with the accent in its icon, its edge, and its row tint. The interface MUST
NOT assign a distinct hue to each section.

#### Scenario: Label and icon identify the section

- **WHEN** the browser lists Inbox, Projects, References, Log, and Review
- **THEN** each entry shows its label and its own icon

#### Scenario: Active section uses the accent

- **WHEN** a section is active
- **THEN** its icon, edge, and row tint use the accent rather than a section-specific hue

#### Scenario: Non-active sections share one tint

- **WHEN** the browser renders its inactive sections
- **THEN** their icons use the same neutral tint

#### Scenario: Identity survives without color

- **WHEN** the active accent is not distinguishable
- **THEN** the label, icon, and active edge still identify the section

### Requirement: Interface icons are monochrome and tinted in code

The interface SHALL render icons as monochrome glyphs and SHALL apply color only through a named tint
role. It MUST NOT ship a custom interface icon set; a single application icon is outside this
requirement.

#### Scenario: Icons are monochrome

- **WHEN** any interface icon is rendered
- **THEN** its glyph is monochrome and its color comes from a tint role

#### Scenario: Tint follows meaning

- **WHEN** an icon carries a section, accent, muted, or destructive meaning
- **THEN** it uses the corresponding tint role rather than an arbitrary color

#### Scenario: No custom interface icon assets

- **WHEN** the packaged application is inspected
- **THEN** it contains no custom interface icon set

### Requirement: Differences from the reference language are bounded

Afanes SHALL differ from the reference design language only where the guidelines prefer a platform
choice or the toolkit cannot conform: the platform typeface (which the guidelines require), the
toolkit's monochrome interface icon set, the toolkit's widget rendering, the absent access-key
mnemonics, and the absent high-contrast style. Each difference MUST be recorded in the interface
standard, and removing one SHALL require its own change.

#### Scenario: A new difference requires a spec change

- **WHEN** a change proposes a visual behavior outside the reference language
- **THEN** it records the difference and updates this requirement rather than adding it silently

#### Scenario: The recorded list matches the implementation

- **WHEN** the interface standard lists differences
- **THEN** that list matches the typeface, icon, widget-rendering, access-key, and high-contrast behavior the application actually ships

### Requirement: Control values come from the interface tokens

Every color, corner radius, spacing, and dimension value SHALL come from the interface token module.
The build SHALL fail when a view or component introduces a value outside those tokens, except for
entries enumerated in a conformance baseline that may only shrink.

#### Scenario: A literal fails the build

- **WHEN** a view or component introduces a color, radius, spacing, or dimension literal that is not in the token module
- **THEN** the conformance gate fails and names the file and value

#### Scenario: The baseline may only shrink

- **WHEN** a change removes a baseline entry by migrating the offending code
- **THEN** the same change deletes that entry, and a baseline entry that no longer matches a violation also fails the gate

### Requirement: A view has at most one suggested action

A view SHALL contain at most one control using the suggested style, meaning the accent-filled action
style. Views enumerated in the conformance baseline are tracked exceptions until they are migrated,
and a new or modified view MUST conform.

#### Scenario: A new view conforms

- **WHEN** a view is added
- **THEN** it contains no more than one suggested-style control

#### Scenario: An existing exception is tracked

- **WHEN** an unmigrated view exceeds the limit
- **THEN** its file is listed in the conformance baseline and the gate passes

### Requirement: Buttons carry an icon or a label, not both

Outside a header bar, a button SHALL contain either an icon or a label. Views enumerated in the
conformance baseline are tracked exceptions until they are migrated, and a new or modified view MUST
conform.

#### Scenario: A new button chooses one

- **WHEN** a button outside a header bar is added
- **THEN** it shows either an icon or a label, not both

#### Scenario: An existing exception is tracked

- **WHEN** an unmigrated button shows both
- **THEN** its file is listed in the conformance baseline and the gate passes
