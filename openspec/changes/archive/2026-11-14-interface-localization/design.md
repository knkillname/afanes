# Design

## Context

See `proposal.md` for motivation. The current state that shapes the approach:

- Interface copy lives in `src/afanes/ui/strings.py`: 381 string constants, 6 mapping constants, and
  a `CopyFormatter`; 26 modules reference it 489 times. Command-line copy lives in
  `src/afanes/cli/strings.py` with 34 constants. No gettext catalogs exist yet; the standard library
  `gettext` module and the `.po`/`.mo` format are the selected pipeline.
- Domain failures carry free-form English strings. Roughly 250 sites raise or build a message across
  `core/errors.py`, `core/steps.py`, `core/frontmatter.py`, `core/vault/snapshot.py`,
  `core/template_cards.py`, and the vault services. The interface interpolates `str(exc)` into an
  English wrapper.
- Bundled templates already use `<template>/<locale>/` trees with an English base and fallback. The
  guide path is fixed at `reference/Getting started.md`. The eight template cards are a flat package
  folder, and the template labels and descriptions are English fields on `VaultTemplate`.
- Date display mixes `calendar.month_name`, `strftime("%B")`, a hardcoded `WEEKDAY_LABELS` tuple, and
  ISO strings. `LogTitle` produces English headings.
- `Settings` version `1` requires a vault path and is removed when the vault is closed, so it cannot
  own a preference that must survive the welcome state. `AppState` already has 10 annotated fields,
  which is its gate limit. Flet 1.1.2 exposes `DatePicker(locale=...)` and `flet.Locale`.
- Python does not apply the environment locale to `LC_TIME`; `locale.getlocale(LC_TIME)` reports `C`
  unless `setlocale` is called. `setlocale` mutates process-global state and is not thread-safe.

## Goals / Non-Goals

**Goals:**

- Deliver the whole localization row in one change: interface, command line, domain messages, dates,
  numbers, bundled content, locale resolution, preference storage, and the copy gate.
- Use the Python standard library `gettext` pipeline for translated strings: English source
  messages, reviewed `.po` catalogs, and compiled `.mo` catalogs.
- Keep every user-facing string in a reviewable catalog and keep `core` free of rendered copy.
- Keep the offline guarantee, the dependency set, the `AppState` gate, and Linux/macOS/Windows
  parity.
- Make the next feature, reminders, use the same bilingual catalog from its first commit.

**Non-Goals:**

- Live language switching. The preference applies on restart.
- A third locale, translated documentation, or translated user notes.
- Babel or another third-party translation package. The standard library `gettext` module loads
  the catalogs, and the two locales use bundled source data.
- Locale-aware collation or search normalization beyond the current Unicode case folding.
- A vault schema change, a persistent index, or a change to the settings file version.
- Localized filenames for user notes. Only the guide note gets a locale-specific path.
- OS-level reminder notifications, which remain outside `1.0.0`.

## Decisions

### D1. A locale value object and a non-mutating resolver

`core/localization.py` owns `LocaleTag`, `LocaleResolver`, and `LocaleFormat`.

`LocaleTag` is a frozen value object with the supported language (`en` or `es`) and the normalized
tag that produced it. Normalization lowercases the tag, replaces `_` with `-`, removes `.encoding`
and `@modifier`, and maps the language prefix. `es-*` maps to `es`, `en-*` maps to `en`, and every
other language maps to `en`. Windows locale names such as `Spanish_Spain` are normalized by their
language prefix; a small table maps `english` to `en` and `spanish` to `es`.

`LocaleResolver.resolve(override, environ, os_locale)` is deterministic and side-effect free. The
order is:

```text
saved override (en or es)
    -> LC_ALL
    -> LC_MESSAGES
    -> LANG
    -> the operating-system locale
    -> en
```

The resolver reads `locale.getlocale(LC_CTYPE)`, which Python sets from the environment at startup,
and never calls `locale.setlocale`. On Windows it accepts the Windows locale name form. The caller
supplies `environ` and `os_locale` in tests, so no test depends on the machine locale.

Alternatives considered:

- Babel: handles CLDR data, week starts, and plural rules, but adds a dependency and a data source
  for two known languages; rejected under the dependency policy and YAGNI.
- `locale.setlocale(LC_TIME, "")`: mutates process-global state, is not thread-safe, and can race
  with the interface; rejected.
- Using `strftime("%B")`: depends on the process C locale; rejected.

### D2. Standard gettext catalogs with English source strings

The runtime uses the Python standard library :mod:`gettext`. English is the source language and
remains the schema; Spanish is stored in gettext `.po` catalogs and loaded from compiled `.mo`
files. No custom translation format and no third-party translation package are introduced.

```text
src/afanes/i18n/
    __init__.py
    catalog.py                        # TranslationLoader, LocalizedCatalog
    po.py                             # PoCatalog parser and standard .mo writer
    ui/
        __init__.py                   # UiCopy
        en.py                         # English interface source constants
    cli/
        __init__.py                   # CliCopy
        en.py                         # English command-line source constants
    messages/
        __init__.py                   # MessageCatalog
        en.py                         # English message templates
    locales/
        es/LC_MESSAGES/
            afanes-ui.po / afanes-ui.mo
            afanes-cli.po / afanes-cli.mo
            afanes-messages.po / afanes-messages.mo
```

There are three gettext domains, one per surface. `LocalizedCatalog` loads the active domain with
`gettext.translation(domain, localedir, languages=[locale.language], fallback=True)`; English loads
`NullTranslations`, and a missing Spanish entry returns the English msgid. The catalog exposes
values through `__getattr__`, and the six mapping constants (`WORKSPACE_SECTION_LABELS`,
`REVIEW_KIND_LABELS`, `PROJECT_GROUP_LABELS`, `PROCESSING_OUTCOME_LABELS`,
`PROCESSING_STATUS_LABELS`, `PAGE_TYPE_LABELS`) get explicit typed properties so indexing stays
typed.

Every English constant is a source message. Attribute access looks up
`copy.WELCOME_TITLE` as `pgettext("WELCOME_TITLE", <English value>)`; the constant name is the
gettext context. That keeps identical English strings independently translatable — a capture noun
and a capture action are different contexts — while keeping the translator-facing msgid readable.
Mapping entries use `MAPPING.key` contexts. The `.po` files are the reviewable translation source.

`CopyFormatter` becomes a formatter bound to a catalog rather than a class that reads module
globals. It owns plural selection, date-tooltip phrasing, and count formatting. The catalog exposes
it as `copy.formatter`.

The domain message catalog is shared by the interface and the command line, so it uses the
`afanes-messages` domain rather than duplicating templates in both surfaces. English templates are
the msgids and the `.po` entries hold the Spanish templates.

The `.po` files are compiled to the standard binary `.mo` format by `afanes.i18n.po` and
`scripts/compile_catalogs.py`; `hatch run i18n-compile` refreshes them. The compiler is offline,
cross-platform, and tested by loading its output with `gettext.GNUTranslations`. This avoids a GNU
gettext installation and keeps the offline guarantee; it does not replace the standard runtime
loader with a custom format.

Only the `.po` sources are tracked in Git. Every `.mo` file is a generated build artifact, ignored
by Git, and produced before tests and packaging; D11 records the build wiring.

Alternatives considered:

- Custom Python catalogs: the earlier draft; rejected because the maintainer requires the standard
  library internationalization pipeline.
- Gettext with symbolic msgids: keeps stable keys but hides the English source from translators and
  departs from the standard `.po` workflow; rejected in favor of English msgids plus contexts.
- Babel: handles CLDR data and plural rules but adds a dependency for two known languages; rejected
  under the dependency policy and YAGNI.
- Duplicating the domain messages in the UI and CLI catalogs: violates DRY and risks drift.

### D3. The active catalog lives on `UiStatus`, not `AppState`

`UiStatus` gains an immutable `copy: UiCopy` field, defaulting to the English catalog, and a
`set_copy` command. `AppState` keeps its 10 annotated fields and 10 public names. `UiStatus.reset`
restores the English default, so every existing UI test starts from English.

The shell resolves the locale before the first render and calls
`app_state.status.set_copy(UiCopy.for_locale(locale))`. State controllers read `self.status.copy`;
views read `self.state.status.copy` or receive the catalog from the shell. Components that take
callbacks and do not hold the state receive the catalog explicitly. No view keeps a cached catalogs
across a `reset`.

The interface path is:

```text
Launcher / AppShell.main
    -> PreferencesStore.load
    -> LocaleResolver.resolve
    -> UiCopy.for_locale(locale)
    -> app_state.status.set_copy
    -> first render
```

The command-line path resolves the same preference and system locale before building its parser and
passing `CliCopy` to the commands. The launcher resolves the locale before importing interface
modules so `--help` and missing-runtime messages are localized without loading Flet.

Alternatives considered:

- A new `AppState` field: breaks the 10-field gate.
- A module-level active catalog: hidden global and test-order coupling.
- Passing the catalog through every constructor: explicit but needless churn; `UiStatus` is already
  the shared interface context.

### D4. Domain messages become codes plus values

`core/errors.py` gains `MessageCode` and `DomainMessage`.

```text
MessageCode      a StrEnum with one stable member per domain message
DomainMessage    code: MessageCode, values: tuple[tuple[str, str], ...]
```

`AfanesError` requires a `DomainMessage`; its `str()` returns the code and values in a technical
form, not a translated sentence. `StepWarning`, `VaultFailure`, and `TemplateCardIssue` replace their
`message: str` field with `DomainMessage`. `NoteDocument.date_error` becomes
`DomainMessage | None`.

The interface and command line render a message with
`copy.messages.render(message)`. The English catalog is the default when no locale is selected.
Rendering substitutes the message values into the catalog template; a missing code or value is a
test failure and a boundary error, never a silent English fallback inside a Spanish sentence.

The English message module is the schema. A test asserts that every `MessageCode` member has an
English template and a Spanish `.po` entry, that both templates use the same placeholders, and that
no catalog entry is unknown. Pyrefly catches a call site that passes a string instead of a
`DomainMessage` because the exception constructor requires the value object.

Alternatives considered:

- Translating `str(exc)` by matching English text: lossy and fragile once values are interpolated.
- Keeping English details and translating only the wrapper: cheap but leaves mixed-language
  sentences and does not satisfy the gate.
- A core-owned English message table: puts rendered copy in core and duplicates the boundary
  catalog; rejected.

### D5. Dates, times, and numbers come from locale data

`core/localization.py` owns a frozen `LocaleFormat` with one data table per supported language:

| Value | English | Spanish |
| --- | --- | --- |
| Long day title | `November 13, 2026` | `13 de noviembre de 2026` |
| Long month title | `November 2026` | `noviembre de 2026` |
| Year title | `2026` | `2026` |
| Short date | `Nov 13, 2026` | `13 nov 2026` |
| Weekday labels | `Mo Tu We Th Fr Sa Su` | `Lu Ma Mi Ju Vi Sá Do` |
| Time | `2:30 PM` | `14:30` |
| Count grouping | `1,234` | `1,234` |

Spanish regional formats disagree about number grouping. The supported Spanish convention is the
Mexican one: comma grouping and the dot as the decimal separator. Decimal values are not part of this
change.

`LocaleFormat` exposes `log_title(date)`, `short_date(date)`, `month_name(month)`,
`weekday_labels()`, `time(value)`, and `count(value)`. It uses explicit tables, not `strftime` or
`calendar.month_name`, so the process C locale cannot change the display. The calendar stays
Monday-first for both languages; region-specific week starts are out of scope and recorded in the
interface standard. This is the recorded exception to the standard-library-first rule: the standard
`locale` module changes process-global state through `setlocale`, is not thread-safe, and is not
reliable for `LC_TIME` without that mutation.

`LogTitle` takes a `LocaleTag` and delegates to `LocaleFormat`. A date change compares the old
heading against the generated titles for the old date in every supported locale, then writes the
new title in the active locale. That rule is what `note-identity` requires; it avoids stale English
headings after a language change while preserving custom headings. The vault conversion takes the
active locale as an explicit parameter, defaulting to English for callers that do not supply one.

The Flet date picker receives `ft.Locale(language_code=locale.language)`. The returned date value is
unchanged; only the picker presentation is localized.

### D6. Language preference lives in its own preferences file

`core/preferences.py` adds `Preferences`, `PreferencesStore`, and `PreferencesStore.default()`.
`Preferences` holds `language: str | None`, where `None` means the system locale. The file is
`preferences.json` in the same platform configuration directory as `settings.json`, versioned, and
written through `AtomicWriter.write_text_atomic`. It contains no vault path and no note content.

A separate file is necessary because `settings.json` requires a vault and is removed when the vault
is closed. Keeping the language in `settings.json` would either lose it at the welcome state or
change the settings contract to allow a vaultless file. The preferences file survives changing and
closing the vault.

`PreferencesStore.load` returns a small load result carrying the preferences and, when the file is
corrupt, a `DomainMessage`. The caller reports the problem, uses system resolution, and leaves the
file untouched. The CLI writes that message to standard error and continues; the interface owns a
banner for it. Saving is explicit when the user chooses a language.

Alternatives considered:

- A language key in `settings.json`: simplest file count, but closing the vault deletes it.
- A vaultless `settings.json`: changes the settings contract and forces every settings consumer to
  handle a missing vault.
- A window-size/preferences store with more UI state: broader than this change; YAGNI.

### D7. Bundled content is locale-scoped end to end

- **Guide:** add `templates/_guide/es/` with `reference/Primeros pasos.md`. The guide path and its
  reserved stem are held in a small `GUIDE_PATHS`/`GUIDE_STEMS` table. A missing Spanish guide tree
  falls back to the English tree and the English path, and the existing guide validation runs
  against the path of the tree that supplied it. The Spanish template must keep the same guide
  shape rules: one reference note, no category, no status.
- **Templates:** add `templates/{personal,work,study}/es/` trees. The existing shape validator compares
  project count, reference count, and per-project step count, not filenames, so Spanish filenames
  and content are allowed. Every Spanish tree must pass the existing parse, reference, placement,
  and filename checks.
- **Template cards:** move the bundled cards to `template_cards/en/` and add
  `template_cards/es/` with the same eight filenames. `TemplateCardCatalog.bundled(locale)` resolves
  the locale folder with English fallback and keeps `relative_path` relative to the locale folder,
  so the seeded vault remains `templates/person.md`, not `templates/en/person.md`. A validation
  compares the Spanish set with the English set by filename, type, and category.
- **Template labels and descriptions:** remove the English `label`/`description` fields from
  `VaultTemplate`; the core catalog owns the fixed identifiers and order. The i18n message catalog
  owns the labels and descriptions, and the core `TemplateCatalog.summaries(labels)` builds the
  localized `TemplateSummary` objects from a small label catalog passed by the presentation. This
  keeps Spanish content out of core and gives the command line and interface the same fallback.
- **User content:** an existing vault keeps its notes. A language change never rewrites note text,
  frontmatter, filenames, or folders. Only a new draft or an explicit edit uses the active locale.

Alternatives considered:

- Translating only the UI and leaving starter content English: fails the localization row.
- Keeping the English guide filename in Spanish vaults: avoids a path change but produces an
  English identity in an otherwise Spanish vault; the change owns the spec delta instead.
- Putting Spanish template labels in core: puts rendered copy in core and conflicts with the
  boundary rule.

### D8. The copy gate validates gettext sources and compiled catalogs

The gate moves to `tests/i18n/test_copy.py` and scans the English source modules, the Spanish
`.po` catalogs, and the compiled `.mo` catalogs. It enforces:

- every English interface and CLI constant has a `.po` entry whose context is the constant name and
  whose msgid is the English value;
- every mapping entry has a `.po` entry whose context is `MAPPING.key`;
- every `MessageCode` member has an English template and a `afanes-messages.po` entry;
- no extra `.po` entry and no untranslated or blank msgstr;
- identical interpolation placeholders between each English msgid and its Spanish msgstr;
- a compiled `.mo` that matches its `.po` source; a stale `.mo` fails the gate;
- no string ending with a period; typographic apostrophes and one-character ellipses;
- ellipsis contexts marked as further-input actions in every locale;
- banned first- and second-person pronouns for the string's language;
- English header/sentence capitalization from the existing classification sets;
- Spanish capitalization as sentence-style, with no English title-case pattern;
- no baseline.

The English interface and CLI modules remain the schema. The Spanish `.po` entries and the compiled
`.mo` files are checked against them. Tests that need a real sentence use the English source, so
existing English copy tests stay stable.

Alternatives considered:

- A per-locale fork of the gate: duplicates the mechanical rules.
- A baseline for Spanish: contradicts the no-baseline standard.
- Trusting `gettext` fallback instead of requiring parity: hides missing translations until runtime.

### D9. Architecture and test gates move with the package

The dependency graph becomes:

```text
models  <-  core  <-  i18n  <-  ui
                  <-  i18n  <-  cli
core    <-  ui
core    <-  cli
```

`core` never imports `i18n`, Flet, `ui`, or `cli`. `i18n` imports the standard library (`gettext`
included), `models`, and `core` only. `ui` and `cli` never import each other. `i18n` must not import
Flet. The architecture test gains these edges and forbids the reverse ones.

The package data under `src/afanes/i18n/locales/` contains the tracked `.po` sources and the `.mo`
catalogs generated from them at build time. A packaging test builds the wheel and asserts that every
`.po` source and its compiled `.mo` counterpart is present.

`AGENTS.md` changes in the same task as the package: the standard-library-first rule, the layout,
the dependency DAG, the gettext catalog location, the domain-message rule, the copy-gate path, and
the `UiStatus` active-catalog exception. `tests/core/test_architecture.py` remains the hard gate; no
gate is weakened.

The interface conformance baseline may only shrink. The language control is a normal menu or button;
it does not add a suggested or destructive action, and it must not add an entry to the baseline.

### D10. Migration order

The work lands in one change but is committed in reviewable slices:

```text
1. core primitives      LocaleTag, resolver, LocaleFormat, MessageCode,
                        DomainMessage, Preferences
2. gettext catalogs     English source modules, Spanish .po/.mo domains,
                        offline compiler, catalog loader, copy gate
3. interface            active catalog on UiStatus, migrate call sites,
                        language control, date picker
4. command line         resolve locale, localized parser and output,
                        launcher help
5. domain messages      migrate exception, warning, scan, card message sites
6. dates and log        localized metadata dates, log titles, cross-locale
                        date-change comparison
7. bundled content      Spanish guide, templates, cards, labels
8. gates and release    architecture, conformance, docs, changelog, RELEASE
```

Each slice is green before the next. The Spanish copy is drafted in the same change and reviewed by
the maintainer; the copy gate catches mechanical regressions, not tone.

### D11. Compiled catalogs are generated build artifacts

The repository tracks only the reviewed `.po` sources. Every `.mo` file is ignored by Git and
produced by the offline compiler before it is needed: a session-scoped test fixture compiles the
catalogs before locale tests, a Hatchling build hook compiles them into the wheel and source
distribution, and the Hatch `package` script compiles them before a packaged desktop build. The
packaging test derives the expected `.mo` paths from the `.po` sources, so a missing compiled
catalog fails the build. Documentation screenshots remain the only committed binary artifacts.

Alternatives considered:

- Commit the `.mo` files: rejected because they are binary build outputs derived from the reviewed
  `.po` sources; the project omits generated binaries from version control.
- Compile on import or first run: rejected because it writes into the installed package and can
  fail on a read-only installation.
- Load `.po` files at runtime: rejected because it replaces the standard library gettext loader
  with a custom runtime format.

## Risks / Trade-offs

- **A 489-reference copy migration can miss a site.** → Replace module access surface by surface,
  keep the English module as the schema, and let the copy gate and Spanish UI tests fail on any
  leftover English constant. Commit per surface.
- **A 250-site domain-message migration can miss a raise.** → Make `AfanesError` require a
  `DomainMessage` so Pyrefly rejects string raises, and add a test that every enum member has an
  English template and a Spanish `.po` entry. Migrate by module, not by grep.
- **Spanish copy can be tonally wrong even when mechanically valid.** → Maintainer review, sample
  screenshots, and a short style note for Spanish in the interface standard.
- **Longer Spanish text can overflow the 1024x600 minimum.** → Render each view in Spanish in tests
  and in the manual desktop review; wrap labels and keep the content width.
- **Locale detection differs on Windows.** → Normalize Windows locale names, keep the English
  fallback, and cover the matrix in unit tests. The browser presentation uses the process locale.
- **The new package can violate the dependency DAG.** → Update the architecture gate in the same
  slice as the package and run it before migrating any call site.
- **A fresh checkout has no compiled catalogs.** → The test-session preflight compiles them before
  locale tests, the Hatchling hook compiles them into the wheel and source distribution, and the
  Hatch `package` script compiles them before desktop packaging; the packaging test fails when a
  source lacks its compiled counterpart.
- **A `.po` change can be tested against an old local `.mo`.** → The test-session preflight
  recompiles every source before locale tests, and packaging recompiles before shipping.
- **The `.mo` compiler is custom code.** → It writes the standard binary format and is exercised by
  loading its output through `gettext.GNUTranslations`; no custom runtime format is introduced.
- **English msgids change during review.** → The copy gate compares every English value with its
  `.po` msgid, so a changed source fails until the catalog is updated.
- **Identical English strings need different translations.** → Every constant has its own gettext
  context, so a capture noun and a capture action can translate differently.
- **The language preference can be lost on close.** → Keep it in a separate preferences file and
  add a close-and-restart test.
- **The Spanish template trees can drift in shape.** → The existing shape validator runs before any
  write; add both locales to the template tests.
- **The guide path change can surprise existing English users.** → The English path is unchanged;
  only Spanish vaults use `reference/Primeros pasos.md`, and the guide is a new note in that vault.
- **The cross-locale heading rule can rewrite a heading that looks generated.** → It only matches
  the exact long generated title, not ISO dates or arbitrary date-shaped text; a custom heading in
  another language is preserved.
- **A separate preferences file adds a second configuration contract.** → Version it, keep it
  optional, never overwrite a corrupt file, and keep it free of vault data.

## Migration Plan

1. Land the core primitives with unit tests. No interface behavior changes yet.
2. Create the `i18n` package, move the English source modules, add the tracked `.po` catalogs, the
   offline `.mo` compiler with its test and build wiring, and the copy gate. The interface still
   renders English until the call sites migrate.
3. Inject the active catalog through `UiStatus`, migrate the interface surface, and add the language
   control and restart notice.
4. Resolve and apply the locale in the command line and launcher.
5. Migrate domain failures, warnings, scan failures, and card issues to `DomainMessage`.
6. Format dates and numbers by locale and make log titles and date changes locale-aware.
7. Add the Spanish guide, templates, cards, and labels.
8. Run the full gates, update the documentation and `RELEASE.md`, and record the `Unreleased` entry.
   The archive step decides the version; the change is one coherent group and is likely a MINOR
   release.

Rollback is a source revert. The `.po`/`.mo` catalogs and the preferences file are ignored by older
versions, no vault schema is migrated, and no note content is rewritten by localization. The Spanish
bundled content can remain unused if the catalogs are reverted.

## Open Questions

None that change the specs, the approach, or the task breakdown. The final Spanish phrasing is a
content review during implementation, and the short-date pattern is fixed by this design.
