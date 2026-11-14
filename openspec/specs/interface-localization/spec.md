# interface-localization Specification

## Purpose

Defines how Afanes selects, applies, and persists English and Spanish across the interface, command
line, validation messages, dates, numbers, and bundled starter content.

## Requirements

### Requirement: English and Spanish are the supported locales

Afanes SHALL support English (`en`) and Spanish (`es`). A regional tag SHALL resolve to its language
when that language is supported; any other tag SHALL resolve to English. Adding a locale MUST NOT
change existing copy keys or behavior.

#### Scenario: A regional Spanish tag resolves to Spanish

- **WHEN** the resolved tag is `es-MX`
- **THEN** the active locale is `es`

#### Scenario: A regional English tag resolves to English

- **WHEN** the resolved tag is `en-GB`
- **THEN** the active locale is `en`

#### Scenario: An unsupported language falls back to English

- **WHEN** the resolved tag is `fr-FR`
- **THEN** the active locale is `en`

### Requirement: The system locale is the default

When no saved override exists, Afanes SHALL resolve the locale from the operating-system locale.
When the system locale cannot be determined, the application SHALL use English. Resolution SHALL
perform no network request and MUST NOT require a translation package.

#### Scenario: A Spanish system locale selects Spanish

- **WHEN** the system locale is Spanish and no override is saved
- **THEN** the active locale is `es`

#### Scenario: An unknown system locale selects English

- **WHEN** the system locale is a language other than English or Spanish
- **THEN** the active locale is `en`

#### Scenario: An unavailable system locale selects English

- **WHEN** the operating system reports no usable locale
- **THEN** the active locale is `en`

### Requirement: An override applies on the next launch

The user SHALL be able to choose English, Spanish, or the system locale. The choice SHALL be stored
outside the vault and SHALL apply on the next launch; the running session MUST NOT switch copy.
Clearing the override SHALL restore system resolution.

#### Scenario: Choosing Spanish applies after a restart

- **WHEN** the user chooses Spanish and restarts the application
- **THEN** the interface starts in Spanish

#### Scenario: The running session does not switch

- **WHEN** the user chooses Spanish while the interface is running
- **THEN** the current session keeps its language until the next launch

#### Scenario: Clearing the override restores the system locale

- **WHEN** the user clears the override and restarts
- **THEN** the system locale is used again

#### Scenario: The preference survives a vault change

- **WHEN** the user changes or closes the vault
- **THEN** the saved language preference remains in effect

### Requirement: Copy falls back per key

Every user-facing string SHALL be read from the active locale catalog. A missing Spanish key SHALL
fall back to the English value for that key; a missing English key SHALL be a catalog defect that the
gate rejects. Fallback MUST NOT mix languages within a single string.

#### Scenario: A missing Spanish key falls back

- **WHEN** the Spanish catalog lacks one key
- **THEN** that key renders its English value and the rest of the interface stays Spanish

#### Scenario: A complete catalog needs no fallback

- **WHEN** both catalogs contain the same keys
- **THEN** every string renders in the active locale

#### Scenario: A string is never half translated

- **WHEN** a translated string contains interpolation values
- **THEN** the whole sentence renders in one language

### Requirement: The interface speaks the active locale

All interface copy—titles, labels, actions, hints, banners, notices, empty states, and tooltips—SHALL
use the active locale. No view SHALL contain inline user-facing copy. The layout SHALL remain usable
at the minimum window size with the longer locale.

#### Scenario: The Spanish interface renders Spanish copy

- **WHEN** the active locale is Spanish
- **THEN** every visible title, label, hint, notice, and tooltip is Spanish

#### Scenario: The English interface renders English copy

- **WHEN** the active locale is English
- **THEN** every visible title, label, hint, notice, and tooltip is English

#### Scenario: Spanish text fits the minimum window

- **WHEN** the Spanish interface renders at the minimum window size
- **THEN** no label, control, or message is clipped or overlaps another control

### Requirement: The command line speaks the active locale

Help, success reports, usage errors, and operational failures SHALL use the same active locale as
the interface. The template listing SHALL report localized labels and descriptions. A headless
command MUST NOT import the interface or open a display.

#### Scenario: Spanish help is reported

- **WHEN** a headless command runs with `--help` under Spanish
- **THEN** its help text is Spanish

#### Scenario: A Spanish failure is reported

- **WHEN** a headless command fails under Spanish
- **THEN** its standard-error message is Spanish and the exit status is unchanged

#### Scenario: The template listing is localized

- **WHEN** the template catalog is listed under Spanish
- **THEN** labels and descriptions are Spanish and identifiers are unchanged

#### Scenario: Resolution needs no display

- **WHEN** a headless command resolves its locale
- **THEN** no interface module is imported and no display server is required

### Requirement: Domain messages are localized at the boundary

Validation failures, step warnings, scan failures, and template-card issues SHALL carry a stable
message identity and its values. The interface and command line SHALL render them in the active
locale; the same failure SHALL render in English when English is active. Core MUST NOT contain
locale-specific copy.

#### Scenario: A Spanish validation failure is rendered

- **WHEN** a validation failure reaches the Spanish interface
- **THEN** its message is Spanish and includes the failure's values

#### Scenario: A Spanish step warning is rendered

- **WHEN** a step warning reaches the Spanish interface
- **THEN** its message is Spanish and names the affected line

#### Scenario: A Spanish scan failure is rendered

- **WHEN** a note fails to parse under Spanish
- **THEN** the failure row shows a Spanish explanation and the note path

#### Scenario: English remains the default rendering

- **WHEN** a domain failure is rendered at the boundary before a locale is selected
- **THEN** the English catalog renders its message and no translation is required

#### Scenario: Core carries no localized copy

- **WHEN** the core package is inspected
- **THEN** it contains no Spanish interface strings

### Requirement: Dates, times, and numbers follow the locale

Human-readable dates, times, month names, and weekday names SHALL use the active locale's
conventions. Counts SHALL use the supported convention of comma grouping and a dot decimal separator
in both English and Spanish. ISO date input and log filenames SHALL remain unchanged. Date display
MUST NOT depend on the process-wide C locale.

#### Scenario: A Spanish day title uses Spanish

- **WHEN** a log draft opens for `2026-11-13` under Spanish
- **THEN** its heading is `13 de noviembre de 2026`

#### Scenario: An English day title uses English

- **WHEN** a log draft opens for `2026-11-13` under English
- **THEN** its heading is `November 13, 2026`

#### Scenario: Month and weekday names are localized

- **WHEN** the Log calendar renders a month under Spanish
- **THEN** the month and weekday labels are Spanish

#### Scenario: ISO input and filenames stay ISO

- **WHEN** a date is typed in a field or written as a log filename
- **THEN** the value remains `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`

#### Scenario: Counts use comma grouping

- **WHEN** a count of one thousand or more is displayed in either language
- **THEN** its digits are grouped with commas, as in `1,234`

#### Scenario: The C locale does not change display

- **WHEN** the process locale is `C` but the active locale is Spanish
- **THEN** dates and numbers still render in Spanish

### Requirement: Starter content is selected by locale with a fallback

The guide, starter templates, template cards, and template labels and descriptions SHALL be selected
for the active locale. A missing Spanish tree or card set SHALL fall back to English without failing
creation. The selected content SHALL still satisfy the bundled-tree validity rules.

#### Scenario: A Spanish vault receives Spanish content

- **WHEN** a vault is created under Spanish with a starter template
- **THEN** the guide, template notes, cards, labels, and descriptions are Spanish

#### Scenario: A missing Spanish tree falls back

- **WHEN** a template has no Spanish tree
- **THEN** its English tree is applied and creation succeeds

#### Scenario: Spanish template cards are seeded

- **WHEN** a vault is created under Spanish
- **THEN** the eight seeded cards have Spanish titles, descriptions, and starter bodies

#### Scenario: Localized trees keep the required shape

- **WHEN** a Spanish tree differs from the English tree in project, reference, or step count
- **THEN** creation is refused before any note is written

#### Scenario: The guide path matches the locale

- **WHEN** a vault is created under Spanish
- **THEN** the guide note is written at the Spanish guide path

### Requirement: A locale change never rewrites vault content

Changing the interface language, opening a vault under another locale, or scanning SHALL NOT modify
note text, frontmatter, filenames, or folders. Only a new draft or an explicit edit SHALL write
content in the active locale.

#### Scenario: Opening a vault in Spanish performs no write

- **WHEN** an existing English-created vault is opened under Spanish
- **THEN** no note text, frontmatter, filename, or folder changes

#### Scenario: Switching the override performs no write

- **WHEN** the user changes the language preference
- **THEN** the vault is untouched

#### Scenario: A new draft uses the active locale

- **WHEN** the user opens a new log draft under Spanish
- **THEN** its generated heading is Spanish

#### Scenario: An existing custom heading is untouched

- **WHEN** an entry with a custom heading is opened under another locale
- **THEN** its heading remains unchanged

### Requirement: Localization stays offline and cross-platform

Locale data and bundled translations SHALL ship with the application. Resolution and rendering MUST
NOT contact the network, download locale data, or depend on a system translation package. English and
Spanish SHALL behave the same on Linux, macOS, and Windows.

#### Scenario: Offline startup works in both locales

- **WHEN** the application starts with no network access
- **THEN** both English and Spanish interfaces render fully

#### Scenario: No locale data is downloaded

- **WHEN** a locale is resolved or applied
- **THEN** no remote request is made

#### Scenario: Platform parity holds

- **WHEN** the same vault is opened on Linux, macOS, and Windows under one locale
- **THEN** the interface language and date formats match

#### Scenario: No optional translation package is required

- **WHEN** the application is installed without extra packages
- **THEN** both supported locales work

### Requirement: The copy gate enforces locale parity

An automated gate SHALL validate the English source modules, the Spanish `.po` catalogs, and the
compiled `.mo` catalogs. It SHALL require every English message to have a context-matching `.po`
entry with the same interpolation placeholders, apply language-appropriate capitalization, and
enforce the shared typographic and tone rules with no baseline. A `.mo` file that does not match its
`.po` source SHALL fail the gate.

#### Scenario: A missing key fails the gate

- **WHEN** one locale lacks a key present in its counterpart
- **THEN** the gate fails and names the key

#### Scenario: An extra key fails the gate

- **WHEN** one locale declares a key its counterpart lacks
- **THEN** the gate fails and names the key

#### Scenario: A placeholder mismatch fails the gate

- **WHEN** the same key uses different interpolation placeholders across locales
- **THEN** the gate fails and names the key

#### Scenario: Spanish capitalization is accepted

- **WHEN** a Spanish heading uses Spanish sentence-style capitalization
- **THEN** the gate accepts it

#### Scenario: English header capitalization is still enforced

- **WHEN** an English heading uses sentence capitalization instead of header capitalization
- **THEN** the gate fails and names the constant

#### Scenario: Typographic rules apply in both locales

- **WHEN** either catalog contains a straight apostrophe, three periods, or a final period
- **THEN** the gate fails and names the string

#### Scenario: The gate has no baseline

- **WHEN** the copy gate runs
- **THEN** it requires zero violations and offers no ledger of allowed exceptions

#### Scenario: A context mismatch fails the gate

- **WHEN** a Spanish entry uses a different message context than its English source
- **THEN** the gate fails and names the context

#### Scenario: A stale compiled catalog fails the gate

- **WHEN** a `.po` source changes without recompiling its `.mo` file
- **THEN** the gate fails and names the stale catalog

#### Scenario: The compiled catalogs are scanned

- **WHEN** the copy gate runs
- **THEN** it checks every Spanish `.po` file and its compiled `.mo` counterpart

### Requirement: The native date picker follows the locale

The date picker SHALL open in the active locale. Choosing a date SHALL return the same date value
regardless of locale; only its presentation changes.

#### Scenario: The Spanish picker renders in Spanish

- **WHEN** the date picker opens under Spanish
- **THEN** its month names, weekday names, and controls are Spanish

#### Scenario: The English picker renders in English

- **WHEN** the date picker opens under English
- **THEN** its month names, weekday names, and controls are English

#### Scenario: The chosen date is locale independent

- **WHEN** the user chooses a date under either locale
- **THEN** the same calendar date is returned

### Requirement: The language control is discoverable and reversible

The language control SHALL be available from the welcome state and the workspace, SHALL name each
language in that language, and SHALL explain that the change applies on restart.

#### Scenario: The welcome state offers the language control

- **WHEN** the application starts without a vault
- **THEN** the language control is reachable before a vault is opened

#### Scenario: The workspace offers the language control

- **WHEN** a vault is open
- **THEN** the language control is reachable from the primary menu

#### Scenario: Language names are autonyms

- **WHEN** the language control lists the choices
- **THEN** it shows English and Español, plus the system-locale choice in the active copy

#### Scenario: The restart requirement is explained

- **WHEN** the user chooses a language
- **THEN** the interface states that the change applies after a restart

### Requirement: Catalogs use the standard gettext format

Afanes SHALL store Spanish translations in gettext `.po` catalogs and load compiled `.mo`
catalogs with the Python standard library `gettext` module. English SHALL be the source language.
Each translatable string SHALL carry a stable message context so identical English strings can
translate independently. A missing Spanish entry SHALL fall back to the English source. The
compiled `.mo` catalog SHALL be generated from its `.po` source by the project's offline compiler.

#### Scenario: Spanish translations live in a gettext catalog

- **WHEN** the Spanish locale is selected
- **THEN** the interface, command line, and domain messages load from compiled `.mo` catalogs in the standard `localedir` layout

#### Scenario: Runtime uses the standard library

- **WHEN** a catalog is loaded
- **THEN** the standard library `gettext` module reads it and no third-party translation package is imported

#### Scenario: Identical English strings translate independently

- **WHEN** the same English word has different contexts, such as a capture noun and a capture action
- **THEN** each context resolves its own Spanish entry

#### Scenario: A missing Spanish entry falls back

- **WHEN** the Spanish catalog has no entry for a context
- **THEN** the English source renders for that entry

#### Scenario: The compiled catalog is current

- **WHEN** a `.po` source changes without recompiling
- **THEN** the copy gate fails and names the stale `.mo` file

#### Scenario: The compiler stays offline

- **WHEN** the `.po` catalogs are compiled
- **THEN** the compiler writes the standard `.mo` format without a network request or a GNU gettext installation

### Requirement: Compiled catalogs are build artifacts

The repository SHALL track only gettext `.po` sources. Every compiled `.mo` catalog SHALL be
generated by the project's offline compiler as a build artifact, never committed, and produced
before tests load catalogs and before any package is built. Test runs, wheels, source distributions,
and packaged desktop builds SHALL contain the compiled catalogs for every tracked source.

#### Scenario: Compiled catalogs are not tracked

- **WHEN** the repository is inspected
- **THEN** it contains no `.mo` file and `.gitignore` excludes every `.mo` file

#### Scenario: A fresh checkout compiles before tests

- **WHEN** the test suite starts without `.mo` files
- **THEN** it compiles every `.po` source before locale tests load them

#### Scenario: Packaging compiles the catalogs

- **WHEN** a wheel or source distribution is built
- **THEN** every tracked `.po` source has its compiled `.mo` counterpart in the artifact

#### Scenario: Desktop packaging compiles the catalogs

- **WHEN** a packaged desktop build is produced
- **THEN** its bundled package contains the compiled catalogs for every tracked `.po` source
