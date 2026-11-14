# Tasks

## 1. Core locale, formatting, and preference primitives

- [x] 1.1 Add `LocaleTag` and `LocaleResolver` in `src/afanes/core/localization.py`; verify tests cover `es-MX` to `es`, `en-GB` to `en`, an unsupported language to `en`, the `LC_ALL`/`LC_MESSAGES`/`LANG` precedence, Windows locale names, an unavailable OS locale, and that resolution never calls `locale.setlocale`; run `hatch test tests/core/test_localization.py`.
- [x] 1.2 Add `LocaleFormat` with English and Spanish month, weekday, title, short-date, time, and count data; verify both long log titles, short dates, month and weekday labels, time patterns, number grouping, and that display no longer depends on `strftime` or `calendar.month_name`; run `hatch test tests/core/test_localization.py`.
- [x] 1.3 Add `MessageCode` and the immutable `DomainMessage` value object in `src/afanes/core/errors.py` with the preference and settings codes used by this group; verify values are ordered and immutable, the technical `str()` is stable, and a missing code cannot be constructed; run `hatch test tests/core/test_errors.py`.
- [x] 1.4 Add `Preferences`, `PreferencesStore`, and the load result in `src/afanes/core/preferences.py`; verify a missing file means the system locale, `en` and `es` round-trip, a corrupt file is reported and preserved, the write is atomic, no vault is required, and clearing `settings.json` does not remove the preference; run `hatch test tests/core/test_preferences.py`.

## 2. Standard gettext package, compiler, and copy gate

- [x] 2.1 Add `TranslationLoader` and `LocalizedCatalog` in `src/afanes/i18n/catalog.py`, backed by the standard library `gettext.translation` with `fallback=True`; expose values through `__getattr__`, the six mappings through typed properties, and a corrupt or missing `.mo` fallback; verify an active value wins, a missing Spanish entry falls back to English, a missing English source fails, a corrupt `.mo` falls back, and mappings remain typed; run `hatch test tests/i18n/test_catalog.py`.
- [x] 2.2 Move the English interface copy into `src/afanes/i18n/ui/en.py` and create `src/afanes/i18n/locales/es/LC_MESSAGES/afanes-ui.po` for the shared, launch, welcome, and workspace sections, using the constant name as the gettext context; verify both locales load and the Spanish copy renders; run `hatch test tests/i18n/test_catalog.py`.
- [x] 2.3 Complete the Spanish `afanes-ui.po` for the page, processing, review, log, trash, and feedback sections; verify every English source key has a non-empty msgstr, the contexts match, and the longer copy renders; run `hatch test tests/i18n/test_copy.py tests/i18n/test_catalog.py`.
- [x] 2.4 Move the English command-line copy into `src/afanes/i18n/cli/en.py` and add `src/afanes/i18n/locales/es/LC_MESSAGES/afanes-cli.po`; keep command identifiers untranslated; verify help, reports, and failure copy load in both locales; run `hatch test tests/i18n/test_catalog.py`.
- [x] 2.5 Add the English domain message templates in `src/afanes/i18n/messages/en.py`, the `MessageCatalog` backed by the `afanes-messages` domain, and `src/afanes/i18n/locales/es/LC_MESSAGES/afanes-messages.po`; verify rendering with values, a missing template failure, a missing value failure, and placeholder parity; run `hatch test tests/i18n/test_messages.py`.
- [x] 2.6 Add `src/afanes/i18n/po.py` with the `PoCatalog` parser and standard `.mo` writer, `scripts/compile_catalogs.py`, and the `hatch run i18n-compile` command; verify a `.po` file round-trips through `gettext.GNUTranslations`, the header metadata is preserved, and no network or GNU gettext installation is required; run `hatch run i18n-compile` and `hatch test tests/i18n/test_po.py`.
- [x] 2.7 Replace the old copy gate with `tests/i18n/test_copy.py`; scan the English source, Spanish `.po` files, and compiled `.mo` files; enforce context/key parity, mapping parity, placeholder parity, ellipsis parity, per-language capitalization, banned pronouns, no extra or blank entries, no stale `.mo`, and no baseline; verify a missing entry, an extra entry, a context mismatch, a placeholder mismatch, a straight apostrophe, and an English header-case violation fail; run `hatch test tests/i18n/test_copy.py`.
- [x] 2.8 Update `AGENTS.md` and `tests/core/test_architecture.py` for the `i18n` package and its dependency edges; verify `core` cannot import `i18n`, `i18n` cannot import `ui`, `cli`, or Flet, and the DAG test passes; run `hatch test tests/core/test_architecture.py`.
- [x] 2.9 Document the gettext domains, the `.po`/`.mo` compiler, the per-entry fallback, the locale-aware gate, and the Monday-first calendar decision in `docs/develop/architecture.md` and `docs/develop/interface-standard.md`; run `hatch run docs:build` and `hatch test tests/docs/test_style.py`.
- [x] 2.10 Add a packaging test that builds the wheel and asserts every `src/afanes/i18n/locales/**/*.po` and `*.mo` file is present; verify the installed package can load all three domains without the source tree; run the packaging test and `hatch build`.

## 3. Interface catalog and language control

- [x] 3.1 Add `copy` and `set_copy` to `UiStatus`, keep the English catalog as the reset default, resolve the locale in `AppShell.main` from preferences and system, set the catalog before the first render, and pass `ft.Locale` to the date picker; verify English is the default, a Spanish preference renders Spanish, corrupt preferences show an owned banner and use the system locale, and the picker receives the locale; run `hatch test tests/ui/test_state.py tests/ui/test_app.py`.
- [x] 3.2 Migrate the state controllers in `src/afanes/ui/state/` from `afanes.ui.strings` to the active catalog, keeping the old module available for the unmigrated views; verify English state tests still pass and a Spanish controller notice renders Spanish; run `hatch test tests/ui/test_state.py tests/ui/test_feedback.py`.
- [x] 3.3 Migrate the views and components in `src/afanes/ui/views/`, `src/afanes/ui/components/`, and `src/afanes/ui/app.py` to the active catalog, delete `src/afanes/ui/strings.py`, and remove the old copy imports; verify no `afanes.ui.strings` reference remains and the English interface tests pass; run `hatch test tests/ui`.
- [x] 3.4 Add the language control to the welcome state and the primary menu with English, Español, and the system choice; save the preference outside the vault and show the restart notice; verify the control is reachable in both states, the preference is written, and the running session does not switch; run `hatch test tests/ui/test_state.py tests/ui/test_workspace_view.py`.
- [x] 3.5 Add English and Spanish rendering tests for the workspace, page, processing, review, projects, inbox, and log views; verify every visible view string comes from the active catalog and the Spanish copy is exercised; run `hatch test tests/ui`.
- [x] 3.6 Document the language control, the restart behavior, the system default, and the fallback in `docs/guide/workspace.md` and link the section from `docs/index.md`; run `hatch run docs:build` and `hatch test tests/docs/test_style.py`.

## 4. Command line and launcher

- [x] 4.1 Resolve the locale and preferences in `CommandLine.main` before building the parser, pass the command-line catalog through the command surface, and localize help, reports, usage errors, and operational failures; verify Spanish and English help, create output, errors, and unchanged exit codes; run `hatch test tests/cli/test_main.py`.
- [x] 4.2 Move the launch help and missing-runtime copy into the command-line catalog and resolve the locale before importing interface modules; verify `afanes --help` and a missing-runtime failure in both locales and that no Flet or interface module is imported; run `hatch test tests/ui/test_launch.py`.
- [x] 4.3 Localize `afanes vault templates` through the shared template label catalog; verify Spanish labels and descriptions, unchanged `personal`/`work`/`study` identifiers, and no vault requirement; run `hatch test tests/cli/test_main.py`.
- [x] 4.4 Document the command-line locale behavior in `docs/guide/command-line.md`; run `hatch run docs:build` and `hatch test tests/docs/test_style.py`.

## 5. Domain messages

- [x] 5.1 Migrate `core/frontmatter.py` parse failures and date warnings to `MessageCode` and `DomainMessage`; add their English templates and Spanish `.po` entries; verify the warning and error text render in both locales and the values survive; run `hatch test tests/core/test_frontmatter.py tests/i18n/test_messages.py`.
- [x] 5.2 Migrate `core/steps.py` step errors and warnings to `MessageCode` and `DomainMessage`; add their templates and `.po` entries; verify a step warning names the line and renders in both locales; run `hatch test tests/core/test_steps.py tests/i18n/test_messages.py`.
- [x] 5.3 Migrate the vault failures in `core/vault/snapshot.py`, `core/vault/service.py`, `core/vault/pages.py`, `core/vault/naming.py`, `core/vault/trash.py`, `core/vault/trash_metadata.py`, and `core/vault/processing.py` to `MessageCode` and `DomainMessage`; add their templates and `.po` entries; verify a scan failure, a naming collision, a trash failure, and a processing failure render in both locales; run the vault tests and `tests/i18n/test_messages.py`.
- [x] 5.4 Migrate `core/templates.py`, `core/template_cards.py`, `core/settings.py`, `core/preferences.py`, `core/processing.py`, and `core/atomic.py` to `MessageCode` and `DomainMessage`; add their templates and `.po` entries; verify template, card, settings, preference, processing, and atomic failures render in both locales; run the affected tests and `tests/i18n/test_messages.py`.
- [x] 5.5 Require `DomainMessage` in `AfanesError`, remove every string-message path in core, and verify every `MessageCode` member has an English template and a Spanish `.po` entry with matching placeholders; verify Pyrefly rejects a string message and no unknown catalog entry remains; run `hatch check` and `hatch test tests/core tests/i18n`.
- [x] 5.6 Render domain messages at the interface and command-line boundary, replacing `str(exc)` in banners, notices, inline errors, failure rows, warnings, and card issues with `copy.messages.render`; verify mixed-language sentences are gone in both locales; run `hatch test tests/ui tests/cli`.
- [x] 5.7 Document the domain-message rule in `AGENTS.md` section 4.3 and `docs/develop/architecture.md`; run `hatch test tests/core/test_architecture.py` and `hatch run docs:build`.

## 6. Dates, numbers, and log titles

- [x] 6.1 Replace `calendar.month_name`, `strftime("%B")`, and the hardcoded `WEEKDAY_LABELS` in the calendar and log tree with `LocaleFormat`; verify Spanish and English month and weekday labels and the calendar grid; run `hatch test tests/ui/test_calendar.py tests/ui/test_log_tree.py`.
- [x] 6.2 Format human-readable metadata dates for due, plan, done, and trash rows with `LocaleFormat.short_date`, while keeping ISO values in editable fields, links, and filenames; verify both locales and unchanged ISO inputs; run the affected UI tests.
- [x] 6.3 Make `LogTitle` locale-aware and thread the active locale through `NormalDraft.for_log`, `VaultPages.create_log_page`, and the log draft path; verify English and Spanish day, month, and year titles and the ISO filename; run `hatch test tests/core/test_log.py tests/core/test_editing.py tests/core/vault/test_pages.py`.
- [x] 6.4 Make a log date change compare the old heading against generated titles in every supported locale and write the new title in the active locale; verify the four cross-locale scenarios in `note-identity`, including a custom heading that is preserved; run `hatch test tests/core/vault/test_naming.py`.
- [x] 6.5 Document localized titles, metadata dates, the date picker, and the cross-locale heading rule in `docs/guide/log.md`; run `hatch run docs:build` and `hatch test tests/docs/test_style.py`.

## 7. Bundled content

- [x] 7.1 Add `src/afanes/templates/_guide/es/reference/Primeros pasos.md`; add the guide path and reserved-stem tables, validate the guide against the path of the tree that supplied it, and reserve every supported guide stem; verify the Spanish path and content, the English fallback, and the reserved-name refusal; run `hatch test tests/core/test_templates.py`.
- [x] 7.2 Add the Spanish trees for `personal`, `work`, and `study` under `src/afanes/templates/`; preserve project, reference, and per-project step counts; verify both locales pass the bundled-tree validation and the Spanish notes parse; run `hatch test tests/core/test_templates.py`.
- [x] 7.3 Move the bundled cards into `src/afanes/template_cards/en/`, add `src/afanes/template_cards/es/` with the same eight filenames, types, and categories, and update `TemplateCardCatalog.bundled(locale)` to keep the seeded path flat; verify Spanish seeding, English fallback, stable vault paths, and refusal of an invalid localized card; run `hatch test tests/core/test_template_cards.py`.
- [x] 7.4 Move the template labels and descriptions out of `VaultTemplate` into the shared template label catalog, and build localized `TemplateSummary` values in the interface and command line; verify Spanish and English labels and descriptions, English fallback, and the unchanged catalog order; run `hatch test tests/core/test_templates.py tests/cli/test_main.py`.
- [x] 7.5 Document the Spanish starter content, the guide path, and the localized bundled cards in `docs/reference/templates.md`, `docs/reference/template-cards.md`, and `docs/reference/vault-format.md`; run `hatch run docs:build` and `hatch test tests/docs/test_style.py`.

## 8. Integration checks and release artifacts

- [x] 8.1 Add end-to-end locale tests covering a saved Spanish preference, a system fallback, corrupt preferences, UI startup, CLI startup, and the restart-only rule; verify the interface and command line agree on the locale; run the new integration tests.
- [x] 8.2 Run the conformance, copy, and architecture gates; verify the conformance baseline did not grow, the copy gate has no baseline, the `.mo` catalogs are current, and the dependency edges hold; run `hatch test tests/ui/test_conformance.py tests/i18n/test_copy.py tests/core/test_architecture.py`.
- [x] 8.3 Run the full gates: `hatch run i18n-compile`, `hatch check`, `hatch test --cover`, `hatch run docs:build`, `openspec validate --all --strict`, `openspec doctor`, both vocabulary greps, and `git diff --check`.
- [x] 8.4 Update `CHANGELOG.md` with the localization entry under `Unreleased`, correct `RELEASE.md`'s current version from `0.8.0` to `0.9.0` before the archive bump, update it again if the release workflow bumps the version, and update `README.md` if the feature list needs it; verify the changelog format and the documentation build.
- [x] 8.5 Perform the manual desktop review in English and Spanish: the welcome language control, the restart notice, every destination, the Log calendar and tree, the date picker, a created vault with Spanish starter content, and the 1024x600 minimum; record the results with the version, date, and machine.
- [x] 8.6 Stop tracking compiled `.mo` catalogs: remove the `.gitignore` exception, add a Hatchling build hook and a Hatch `package` script that compile the `.po` sources into the wheel, sdist, and packaged desktop build, compile at test-session startup, and update the packaging test to derive each expected `.mo` from its tracked `.po` source; update `AGENTS.md` and the architecture docs; verify a checkout without `.mo` files passes `hatch test`, the wheel contains all three compiled catalogs, and `git status` lists no `.mo`; run `hatch check`, the packaging test, and `hatch run docs:build`.

## Verification

Manual desktop review on Linux (2026-11-14), Afanes `0.9.0`, Flet `1.1.2`, Ubuntu 26.10,
kernel `7.3.0-10-generic` x86_64, GNOME on Wayland, machine `tlacoyo`. The review used an isolated
`settings.json` and `preferences.json` under `/tmp/opencode/localization-review/` and temporary
vaults, so no user settings or notes were touched.

- **Welcome state.** English and Spanish rendered the title, body, Choose/Open action, New Vault
  action, vault note, and the Language control in the active language.
- **Every destination.** Review, Inbox, Projects, References, Log, Needs Attention, and Trash
  rendered in both languages with localized titles, actions, empty states, counts, and rows. The
  review found and fixed two presentation defects before this record: the sidebar review badge
  forced `Revisión` to wrap mid-word, so the sidebar now shows the compact numeric count; and the
  uncategorized reference heading came from the core English title, so the view now uses the
  localized References label.
- **Log.** Spanish showed `noviembre de 2026`, `Lu Ma Mi Ju Vi Sá Do`, `13 nov 2026`, and a Spanish
  entry heading; English showed `November 2026`, `Mo Tu We Th Fr Sa Su`, `Nov 13, 2026`, and an
  English heading. The entry kept its ISO filename and links.
- **Date picker.** The Spanish and English pickers showed the active language's month names, weekday
  names, and Cancel/OK controls. Flet's fixed header pane clips the longer Spanish title to
  `Seleccionar fe…`; the localizable month, weekday, and action strings are correct.
- **Language command and restart notice.** Choosing a language saved `preferences.json` and showed
  `The language change applies after a restart` in English and
  `El cambio de idioma se aplica después de reiniciar` in Spanish, while the running session kept its
  catalog.
- **Spanish starter content.** A vault created under Spanish contained
  `reference/Primeros pasos.md`, Spanish project and reference notes, and localized cards at the flat
  `templates/` paths.
- **Minimum size.** At 1024x600 the navigation moved behind the drawer toggle, the browser and detail
  stayed usable, and no horizontal overflow or clipped destination title appeared.
- **Screenshots.** `/tmp/opencode/localization-review/en/` and
  `/tmp/opencode/localization-review/es/`.

## Workflow follow-up

- Archive the change after the maintainer approves the completed tasks and every gate passes.
- Run the post-archive release workflow; the change is one coherent group and is likely a MINOR release.
- Record the delivered localization and any resolved runtime dependency versions in the changelog.
- Tag, push, or publish only when the maintainer asks.
