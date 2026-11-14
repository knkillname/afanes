"""Tests for structured domain-message rendering."""

import string
from pathlib import Path

import pytest

import afanes.core.errors
import afanes.core.frontmatter
import afanes.core.localization
import afanes.i18n.catalog
import afanes.i18n.messages
import afanes.i18n.messages.en
import afanes.i18n.po

SPANISH = afanes.core.localization.LocaleTag.parse("es")
ENGLISH = afanes.core.localization.LocaleTag.parse("en")
MESSAGES_PO = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "afanes"
    / "i18n"
    / "locales"
    / "es"
    / "LC_MESSAGES"
    / "afanes-messages.po"
)


def placeholders(template: str) -> list[str]:
    return [name for _, name, _, _ in string.Formatter().parse(template) if name is not None]


class TestMessageTemplates:
    def test_every_message_code_has_an_english_template(self) -> None:
        assert set(afanes.i18n.messages.en.TEMPLATES) == set(afanes.core.errors.MessageCode)

    def test_every_message_code_has_a_spanish_entry(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.from_path(MESSAGES_PO)
        contexts = {entry.context for entry in catalog.messages}

        assert {code.value for code in afanes.core.errors.MessageCode} <= contexts

    def test_spanish_placeholders_match_english(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.from_path(MESSAGES_PO)
        spanish = {entry.context: entry.msgstr for entry in catalog.messages}
        mismatches = [
            code.value
            for code, english in afanes.i18n.messages.en.TEMPLATES.items()
            if sorted(placeholders(english)) != sorted(placeholders(spanish[code.value]))
        ]

        assert mismatches == []

    def test_every_spanish_entry_has_text(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.from_path(MESSAGES_PO)

        assert all(entry.msgstr.strip() for entry in catalog.messages)


class TestMessageCatalog:
    def test_english_renders_the_source_template(self) -> None:
        message = afanes.core.errors.DomainMessage.of(
            afanes.core.errors.MessageCode.SETTINGS_VERSION_UNSUPPORTED,
            source="settings.json",
        )

        assert (
            afanes.i18n.messages.MessageCatalog.english().render(message)
            == "Unsupported settings version in settings.json"
        )

    def test_spanish_renders_the_translated_template(self) -> None:
        message = afanes.core.errors.DomainMessage.of(
            afanes.core.errors.MessageCode.SETTINGS_VERSION_UNSUPPORTED,
            source="settings.json",
        )

        catalog = afanes.i18n.messages.MessageCatalog.for_locale(SPANISH)

        assert catalog.render(message) == "Versión de configuración no admitida en settings.json"

    def test_values_are_substituted_in_order(self) -> None:
        message = afanes.core.errors.DomainMessage.of(
            afanes.core.errors.MessageCode.PREFERENCES_LANGUAGE_INVALID,
            source="preferences.json",
        )

        catalog = afanes.i18n.messages.MessageCatalog.for_locale(SPANISH)

        assert "preferences.json" in catalog.render(message)

    def test_a_missing_template_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        message = afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.SETTINGS_READ_FAILED)
        monkeypatch.delitem(
            afanes.i18n.messages.en.TEMPLATES,
            afanes.core.errors.MessageCode.SETTINGS_READ_FAILED,
        )

        with pytest.raises(afanes.i18n.catalog.CatalogError, match="No English message template"):
            afanes.i18n.messages.MessageCatalog.english().render(message)

    def test_a_missing_value_fails(self) -> None:
        message = afanes.core.errors.DomainMessage(code=afanes.core.errors.MessageCode.SETTINGS_READ_FAILED)

        with pytest.raises(afanes.i18n.catalog.CatalogError, match="no value"):
            afanes.i18n.messages.MessageCatalog.english().render(message)

    def test_the_english_catalog_is_the_default(self) -> None:
        message = afanes.core.errors.DomainMessage.of(
            afanes.core.errors.MessageCode.PREFERENCES_READ_FAILED,
            source="preferences.json",
        )

        assert (
            afanes.i18n.messages.MessageCatalog.english().render(message)
            == "Could not read preferences: preferences.json"
        )


class TestRepresentativeDomainMessages:
    @pytest.mark.parametrize(
        ("message", "english", "spanish"),
        [
            (
                afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.FRONTMATTER_UNCLOSED),
                "Frontmatter opening fence is never closed",
                "El bloque de frontmatter no se cierra",
            ),
            (
                afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.NOTE_NO_TITLE),
                "Note has no level-1 heading",
                "La nota no tiene un encabezado de nivel 1",
            ),
            (
                afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.STEP_TEXT_REQUIRED),
                "A step needs text",
                "Un paso necesita texto",
            ),
            (
                afanes.core.errors.DomainMessage.of(
                    afanes.core.errors.MessageCode.NOTE_MISSING,
                    path="/v/note.md",
                ),
                "Note does not exist: /v/note.md",
                "La nota no existe: /v/note.md",
            ),
            (
                afanes.core.errors.DomainMessage.of(afanes.core.errors.MessageCode.TRASH_CONFIRMATION),
                "Trashing requires explicit confirmation",
                "Mover a la papelera requiere confirmación explícita",
            ),
            (
                afanes.core.errors.DomainMessage.of(
                    afanes.core.errors.MessageCode.PROCESSING_PROJECT_UNKNOWN,
                    name="'X'",
                ),
                "No project is named 'X'",
                "Ningún proyecto se llama 'X'",
            ),
            (
                afanes.core.errors.DomainMessage.of(
                    afanes.core.errors.MessageCode.UNKNOWN_TEMPLATE,
                    identifier="'x'",
                    valid="personal",
                ),
                "Unknown template 'x'; choose one of: personal",
                "Plantilla desconocida 'x'; elige una de: personal",
            ),
            (
                afanes.core.errors.DomainMessage.of(
                    afanes.core.errors.MessageCode.CARD_TYPE_REQUIRED,
                    path="vendor.md",
                ),
                "Bundled template card vendor.md must declare type: reference or log",
                "La tarjeta de plantilla incluida vendor.md debe declarar el tipo reference o log",
            ),
            (
                afanes.core.errors.DomainMessage.of(
                    afanes.core.errors.MessageCode.SETTINGS_READ_FAILED,
                    source="settings.json",
                ),
                "Could not read settings: settings.json",
                "No se pudo leer la configuración: settings.json",
            ),
            (
                afanes.core.errors.DomainMessage.of(
                    afanes.core.errors.MessageCode.PREFERENCES_READ_FAILED,
                    source="preferences.json",
                ),
                "Could not read preferences: preferences.json",
                "No se pudieron leer las preferencias: preferences.json",
            ),
            (
                afanes.core.errors.DomainMessage.of(
                    afanes.core.errors.MessageCode.DESTINATION_DIRECTORY_MISSING,
                    path="/v",
                ),
                "Destination directory does not exist: /v",
                "El directorio de destino no existe: /v",
            ),
        ],
    )
    def test_core_failures_render_in_both_locales(
        self,
        message: afanes.core.errors.DomainMessage,
        english: str,
        spanish: str,
    ) -> None:
        assert afanes.i18n.messages.MessageCatalog.english().render(message) == english
        assert afanes.i18n.messages.MessageCatalog.for_locale(SPANISH).render(message) == spanish

    def test_a_frontmatter_date_warning_survives_and_renders_in_both_locales(self) -> None:
        document = afanes.core.frontmatter.NoteDocument.from_text("---\ntype: note\ndate: 2026-11-13T10:00:00\n---\n")

        assert document.date_error is not None
        english = afanes.i18n.messages.MessageCatalog.english().render(document.date_error)
        spanish = afanes.i18n.messages.MessageCatalog.for_locale(SPANISH).render(document.date_error)
        assert english == "A note date is a calendar date, not a timestamp"
        assert spanish == "Una fecha de nota es una fecha de calendario, no una marca de tiempo"
