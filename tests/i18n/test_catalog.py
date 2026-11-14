"""Tests for the gettext catalog loader and the localized surfaces."""

import gettext
import types
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import pytest

import afanes.core.localization
import afanes.i18n.catalog
import afanes.i18n.cli
import afanes.i18n.po
import afanes.i18n.templates
import afanes.i18n.ui

SPANISH = afanes.core.localization.LocaleTag.parse("es")
ENGLISH = afanes.core.localization.LocaleTag.parse("en")


def source_module(**values: object) -> types.ModuleType:
    module = types.ModuleType("test_source")
    for name, value in values.items():
        setattr(module, name, value)
    return module


def write_catalog(localedir: Path, domain: str, language: str, text: str) -> None:
    path = localedir / language / "LC_MESSAGES" / f"{domain}.po"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    afanes.i18n.po.PoCatalog.parse(text).write_mo(path.with_suffix(".mo"))


def catalog_text(entries: tuple[tuple[str, str, str], ...]) -> str:
    lines = [
        'msgid ""',
        'msgstr ""',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Language: es\\n"',
        "",
    ]
    for context, msgid, msgstr in entries:
        lines.extend(
            [
                f'msgctxt "{context}"',
                f'msgid "{msgid}"',
                f'msgstr "{msgstr}"',
                "",
            ]
        )
    return "\n".join(lines)


class TestTranslationLoader:
    def test_a_missing_domain_loads_a_null_catalog(self, tmp_path: Path) -> None:
        loader = afanes.i18n.catalog.TranslationLoader(tmp_path)

        translations = loader.load("missing", SPANISH)

        assert isinstance(translations, gettext.NullTranslations)

    def test_a_valid_catalog_loads(self, tmp_path: Path) -> None:
        write_catalog(tmp_path, "test", "es", catalog_text((("GREETING", "Hello", "Hola"),)))
        loader = afanes.i18n.catalog.TranslationLoader(tmp_path)

        translations = loader.load("test", SPANISH)

        assert translations.pgettext("GREETING", "Hello") == "Hola"

    def test_a_corrupt_catalog_falls_back(self, tmp_path: Path) -> None:
        path = tmp_path / "es" / "LC_MESSAGES" / "test.mo"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not a catalog")
        loader = afanes.i18n.catalog.TranslationLoader(tmp_path)

        translations = loader.load("test", SPANISH)

        assert translations.pgettext("GREETING", "Hello") == "Hello"


class TestLocalizedCatalog:
    def test_the_active_language_wins(self, tmp_path: Path) -> None:
        write_catalog(
            tmp_path,
            "test",
            "es",
            catalog_text((("GREETING", "Hello", "Hola"), ("FAREWELL", "Goodbye", "Adiós"))),
        )
        source = source_module(GREETING="Hello", FAREWELL="Goodbye")

        catalog = afanes.i18n.catalog.LocalizedCatalog.load(
            source, "test", SPANISH, afanes.i18n.catalog.TranslationLoader(tmp_path)
        )

        assert catalog.GREETING == "Hola"
        assert catalog.FAREWELL == "Adiós"

    def test_a_missing_spanish_entry_falls_back_to_english(self, tmp_path: Path) -> None:
        write_catalog(tmp_path, "test", "es", catalog_text((("GREETING", "Hello", "Hola"),)))
        source = source_module(GREETING="Hello", OTHER="Other")

        catalog = afanes.i18n.catalog.LocalizedCatalog.load(
            source, "test", SPANISH, afanes.i18n.catalog.TranslationLoader(tmp_path)
        )

        assert catalog.GREETING == "Hola"
        assert catalog.OTHER == "Other"

    def test_a_missing_english_source_fails(self, tmp_path: Path) -> None:
        write_catalog(tmp_path, "test", "es", catalog_text((("GREETING", "Hello", "Hola"),)))
        source = source_module(GREETING="Hello")

        catalog = afanes.i18n.catalog.LocalizedCatalog.load(
            source, "test", SPANISH, afanes.i18n.catalog.TranslationLoader(tmp_path)
        )

        with pytest.raises(AttributeError, match="MISSING"):
            catalog.MISSING  # noqa: B018

    def test_a_corrupt_catalog_falls_back_to_english(self, tmp_path: Path) -> None:
        path = tmp_path / "es" / "LC_MESSAGES" / "test.mo"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not a catalog")
        source = source_module(GREETING="Hello")

        catalog = afanes.i18n.catalog.LocalizedCatalog.load(
            source, "test", SPANISH, afanes.i18n.catalog.TranslationLoader(tmp_path)
        )

        assert catalog.GREETING == "Hello"

    def test_mappings_are_localized_and_read_only(self, tmp_path: Path) -> None:
        write_catalog(
            tmp_path,
            "test",
            "es",
            catalog_text((("LABELS.alpha", "Alpha", "Alfa"), ("LABELS.beta", "Beta", "Beta"))),
        )
        source = source_module(LABELS=MappingProxyType({"alpha": "Alpha", "beta": "Beta"}))

        catalog = afanes.i18n.catalog.LocalizedCatalog.load(
            source, "test", SPANISH, afanes.i18n.catalog.TranslationLoader(tmp_path)
        )

        assert isinstance(catalog.mapping("LABELS"), Mapping)
        assert catalog.mapping("LABELS") == {"alpha": "Alfa", "beta": "Beta"}
        with pytest.raises(TypeError):
            catalog.mapping("LABELS")["gamma"] = "Gamma"  # type: ignore[index]

    def test_a_mapping_with_a_non_text_value_fails(self) -> None:
        source = source_module(LABELS=MappingProxyType({"alpha": 1}))

        catalog = afanes.i18n.catalog.LocalizedCatalog.load(source, "test", ENGLISH)

        with pytest.raises(TypeError, match="strings to strings"):
            catalog.mapping("LABELS")


class TestUiCopy:
    def test_english_is_the_default(self) -> None:
        assert afanes.i18n.ui.UiCopy.english().WELCOME_TITLE == "Welcome to Afanes"

    def test_the_spanish_interface_renders_spanish(self) -> None:
        copy = afanes.i18n.ui.UiCopy.for_locale(SPANISH)

        assert copy.WELCOME_TITLE == "Bienvenido a Afanes"
        assert copy.BROWSER_SEARCH_HINT == "Buscar en todas las notas"
        assert copy.PAGE_BODY_LABEL == "Cuerpo (Markdown)"
        assert copy.PROCESSING_TITLE == "Procesar captura"
        assert copy.REVIEW_TITLE == "Revisión"
        assert copy.LOG_EMPTY == "Aún no hay entradas"
        assert copy.TRASH_TITLE == "Papelera"
        assert copy.CAPTURE_FAILED == "No se pudo capturar la idea: {detail}"

    def test_the_english_interface_renders_english(self) -> None:
        copy = afanes.i18n.ui.UiCopy.english()

        assert copy.WELCOME_TITLE == "Welcome to Afanes"
        assert copy.WORKSPACE_SECTION_LABELS["inbox"] == "Inbox"

    def test_the_six_mappings_are_localized(self) -> None:
        copy = afanes.i18n.ui.UiCopy.for_locale(SPANISH)

        assert copy.WORKSPACE_SECTION_LABELS["inbox"] == "Bandeja de entrada"
        assert copy.WORKSPACE_SECTION_LABELS["needs_attention"] == "Requiere atención"
        assert copy.REVIEW_KIND_LABELS["due_step"] == "Paso vencido"
        assert copy.PROJECT_GROUP_LABELS["closed"] == "Cerrados"
        assert copy.PROCESSING_OUTCOME_LABELS["append_step"] == "Añadir paso"
        assert copy.PROCESSING_STATUS_LABELS["archived"] == "Archivado"
        assert copy.PAGE_TYPE_LABELS["log"] == "Registro"

    def test_the_spanish_catalog_exposes_locale_formatting(self) -> None:
        copy = afanes.i18n.ui.UiCopy.for_locale(SPANISH)

        assert copy.locale_format.language == "es"

    def test_the_formatter_uses_the_active_catalog(self) -> None:
        english = afanes.i18n.ui.UiCopy.english().formatter
        spanish = afanes.i18n.ui.UiCopy.for_locale(SPANISH).formatter

        assert english.note_count(1) == "1 note"
        assert english.note_count(1234) == "1,234 notes"
        assert spanish.note_count(1) == "1 nota"
        assert spanish.note_count(1234) == "1,234 notas"
        assert english.open_step_count(2) == "2 open steps"
        assert spanish.open_step_count(2) == "2 pasos abiertos"
        assert english.review_pending(0) == "0 Pending"
        assert spanish.review_pending(0) == "0 pendientes"
        assert english.trash_entry_count(3) == "3 trashed notes"
        assert spanish.trash_entry_count(3) == "3 notas en la papelera"
        assert english.reference_count(2, 1) == "2 references in 1 note"
        assert spanish.reference_count(2, 1) == "2 referencias en 1 nota"
        assert english.log_day_tooltip(13, 0) == "13: no entries"
        assert spanish.log_day_tooltip(13, 0) == "13: sin entradas"
        assert english.log_day_tooltip(13, 1) == "13: 1 entry"
        assert spanish.log_day_tooltip(13, 1) == "13: 1 entrada"
        assert english.log_day_tooltip(13, 2) == "13: 2 entries"
        assert spanish.log_day_tooltip(13, 2) == "13: 2 entradas"
        assert english.log_entry_count(1234) == "(1,234)"
        assert spanish.log_entry_count(1234) == "(1,234)"


class TestCliCopy:
    def test_english_cli_copy_loads(self) -> None:
        copy = afanes.i18n.cli.CliCopy.english()

        assert copy.DESCRIPTION == "Work with Afanes vaults without opening the interface"
        assert copy.VAULT_COMMAND == "vault"

    def test_spanish_cli_copy_loads(self) -> None:
        copy = afanes.i18n.cli.CliCopy.for_locale(SPANISH)

        assert copy.DESCRIPTION == "Trabaja con bóvedas de Afanes sin abrir la interfaz"
        assert copy.CREATED_VAULT == "Bóveda creada en {path}"
        assert copy.TEMPLATES_FAILED == "No se pudo leer el contenido inicial incluido: {detail}"

    def test_command_identifiers_stay_untranslated(self) -> None:
        copy = afanes.i18n.cli.CliCopy.for_locale(SPANISH)

        assert copy.VAULT_COMMAND == "vault"
        assert copy.CREATE_COMMAND == "create"
        assert copy.ADOPT_COMMAND == "adopt"
        assert copy.TEMPLATES_COMMAND == "templates"


class TestTemplateLabels:
    def test_spanish_labels_and_descriptions_load(self) -> None:
        labels = afanes.i18n.ui.UiCopy.for_locale(SPANISH).template_labels()

        assert [label.identifier for label in labels] == ["personal", "work", "study"]
        assert [label.label for label in labels] == ["Personal", "Trabajo", "Estudio"]
        assert (
            labels[1].description
            == "Resultados compartidos, los grupos que los poseen y los procesos que los sostienen"
        )

    def test_english_labels_keep_the_catalog_order(self) -> None:
        labels = afanes.i18n.ui.UiCopy.english().template_labels()

        assert [label.label for label in labels] == ["Personal", "Work", "Study"]

    def test_missing_spanish_labels_fall_back_to_english(self, tmp_path: Path) -> None:
        labels = afanes.i18n.templates.TemplateLabelCatalog.for_locale(
            SPANISH,
            afanes.i18n.catalog.TranslationLoader(tmp_path),
        ).labels()

        assert [label.label for label in labels] == ["Personal", "Work", "Study"]
