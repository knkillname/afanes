# Proposal

## Why

Afanes ships an English-only interface, command line, validation surface, date display, and starter
content. The `1.0.0` gate requires English and Spanish, and the roadmap places localization before
reminders so the reminder interface is born bilingual. The bundled template trees already have a
locale layout with an English fallback, but the interface copy, the command-line catalog, the domain
messages, date and number formatting, and the eight template cards are still single-language.

## What Changes

- Add a supported-locale model for English (`en`) and Spanish (`es`), resolved from the system
  locale by default, with `es-*` collapsing to `es` and unknown locales falling back to English.
- Store an optional in-app language override outside the vault. The override applies on the next
  launch; the running interface is not re-rendered.
- Replace the single interface and command-line copy catalogs with standard gettext domains for the
  interface, command line, and domain messages. English stays the source language; Spanish lives in
  reviewed `.po` catalogs compiled to `.mo` with the project's offline compiler. Missing entries fall
  back to English per key.
- Treat compiled `.mo` catalogs as generated build artifacts: track only the reviewed `.po` sources,
  compile them at test startup and during packaging, and keep every binary catalog out of version
  control.
- Extend the copy gate to validate the English source constants against every `.po` and `.mo` entry,
  require key and placeholder parity across locales, and apply language-appropriate capitalization
  while keeping the no-final-period, typographic, ellipsis, and neutral-tone rules.
- Give domain failures, step warnings, scan failures, and template-card issues stable codes and
  parameters, and render them through the active catalog at the interface and command-line boundary.
  The English default rendering remains available for logs and tests.
- Add locale-aware date, time, and number formatting. New log drafts use the locale's long date
  title, while filenames remain ISO dates.
- Localize the bundled guide, the three starter templates, the eight template cards, and the
  template catalog labels and descriptions. Each content category falls back to English when a
  locale tree is missing.
- Localize the native date picker by passing the resolved locale.
- Keep documentation in English.
- **BREAKING**: the interface and command-line copy constants become gettext message sources; domain
  errors, warnings, scan failures, and card issues gain structured message payloads; `LogTitle`,
  `TemplateCatalog`, `TemplateCardCatalog`, and the date formatter gain locale-aware construction;
  app-owned preferences and the `PreferencesStore` are added; the guide note path becomes
  locale-specific.

## Capabilities

### New Capabilities

- `interface-localization`: supported locales, system and override resolution, per-key fallback,
  localized interface and command-line copy, localized domain messages, locale-aware date, time, and
  number formatting, localized bundled content selection, and the restart-only override contract.

### Modified Capabilities

- `interface-theme`: the writing-style gate becomes locale-aware; Spanish copy follows Spanish
  capitalization while the mechanical rules stay shared.
- `app-runtime`: the active locale is resolved before interface copy loads; the web presentation
  uses the process locale; startup remains offline.
- `vault-selection`: app-owned preferences carry the optional language override and preserve it
  across vault changes and closing the vault, while corrupt preferences still fail safely.
- `command-line`: help, reports, and failures follow the same locale as the interface, including the
  headless template listing.
- `vault-templates`: the guide note path and the template catalog labels and descriptions become
  locale-scoped with an English fallback.
- `template-cards`: the eight bundled cards become locale-scoped with an English fallback; the
  seeded cards use the active locale.
- `note-log`: the default date title for a new log draft uses the active locale's long date.
- `note-identity`: a log date change recognizes a generated heading in any supported locale and
  writes the new title in the active locale.

## Impact

- Interface: 26 modules and roughly 490 copy references across views, components, and state
  controllers; the shared UI context gains the active catalog.
- Core: `errors.py`, `steps.py`, `frontmatter.py`, `vault/snapshot.py`, `template_cards.py`,
  `templates.py`, `log.py`, and `settings.py`.
- Command line: `cli/main.py` and `cli/strings.py`.
- Data: no vault schema change and no persistent index. App-owned preferences gain an optional
  language entry that survives vault changes and closing the vault. Vault note content is never
  rewritten by a locale change.
- Bundled content: `templates/_guide`, `templates/personal`, `templates/work`, `templates/study`,
  and `template_cards` gain Spanish trees; the English trees remain the fallback.
- Localization data: three gettext domains (`afanes-ui`, `afanes-cli`, `afanes-messages`) under
  `src/afanes/i18n/locales/es/LC_MESSAGES/`, with reviewed `.po` sources. The `.mo` catalogs are
  generated by the small offline compiler at test startup and during packaging and are never
  committed, so no GNU gettext installation or third-party package is required.
- Tests: copy-gate parity tests, locale resolution, formatting, error rendering, command-line output,
  template selection, and interface rendering in both locales.
- Dependencies: none added; formatting data is bundled source. The application remains offline and
  cross-platform.
- Documentation: `docs/` stays English; the language setting, localized dates, and localized starter
  content are documented. `RELEASE.md`'s stale current-version statement is corrected.
