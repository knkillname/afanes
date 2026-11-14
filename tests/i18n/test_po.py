"""Tests for the offline gettext source parser and compiler."""

import gettext
import io
from pathlib import Path

import pytest

import afanes.i18n.po

HEADER = 'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n"Language: es\\n"\n\n'
EXPECTED_MESSAGES = 2


def catalog_text() -> str:
    return (
        HEADER
        + 'msgctxt "GREETING"\n'
        + 'msgid "Hello"\n'
        + 'msgstr "Hola"\n'
        + "\n"
        + 'msgctxt "FAREWELL"\n'
        + 'msgid "Goodbye"\n'
        + 'msgstr "Adiós"\n'
    )


class TestPoCatalogParse:
    def test_context_and_translation_are_parsed(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.parse(catalog_text())

        assert [entry.context for entry in catalog.messages] == ["GREETING", "FAREWELL"]
        assert [entry.msgstr for entry in catalog.messages] == ["Hola", "Adiós"]

    def test_the_header_is_separate_from_messages(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.parse(catalog_text())

        assert catalog.header is not None
        assert catalog.header.msgid == ""
        assert "Content-Type" in catalog.header.msgstr

    def test_a_multiline_value_is_joined(self) -> None:
        text = HEADER + 'msgctxt "LONG"\nmsgid "A long"\n" message"\nmsgstr "Un mensaje"\n" largo"\n'

        catalog = afanes.i18n.po.PoCatalog.parse(text)

        assert catalog.messages[0].msgid == "A long message"
        assert catalog.messages[0].msgstr == "Un mensaje largo"

    def test_comments_and_obsolete_entries_are_ignored(self) -> None:
        text = (
            HEADER
            + "# translator note\n"
            + "#. extracted comment\n"
            + 'msgctxt "GREETING"\n'
            + 'msgid "Hello"\n'
            + 'msgstr "Hola"\n'
            + "\n"
            + '#~ msgctxt "OLD"\n'
            + '#~ msgid "Old"\n'
            + '#~ msgstr "Viejo"\n'
        )

        catalog = afanes.i18n.po.PoCatalog.parse(text)

        assert [entry.context for entry in catalog.messages] == ["GREETING"]

    def test_a_missing_msgstr_is_rejected(self) -> None:
        text = HEADER + 'msgctxt "GREETING"\nmsgid "Hello"\n'

        with pytest.raises(afanes.i18n.po.PoError, match="no msgstr"):
            afanes.i18n.po.PoCatalog.parse(text)

    def test_a_duplicate_key_is_rejected(self) -> None:
        text = (
            HEADER
            + 'msgctxt "GREETING"\nmsgid "Hello"\nmsgstr "Hola"\n\n'
            + 'msgctxt "GREETING"\nmsgid "Hello"\nmsgstr "Hola"\n'
        )

        with pytest.raises(afanes.i18n.po.PoError, match="Duplicate catalog key"):
            afanes.i18n.po.PoCatalog.parse(text)

    def test_plural_forms_are_rejected(self) -> None:
        text = HEADER + 'msgid "note"\nmsgid_plural "notes"\nmsgstr[0] "nota"\n'

        with pytest.raises(afanes.i18n.po.PoError, match="plural forms"):
            afanes.i18n.po.PoCatalog.parse(text)

    def test_an_unrecognized_directive_is_rejected(self) -> None:
        with pytest.raises(afanes.i18n.po.PoError, match="unrecognized directive"):
            afanes.i18n.po.PoCatalog.parse(HEADER + "something unexpected\n")

    def test_an_invalid_string_literal_is_rejected(self) -> None:
        with pytest.raises(afanes.i18n.po.PoError, match="invalid string literal"):
            afanes.i18n.po.PoCatalog.parse(HEADER + 'msgid "Hello\nmsgstr "Hola"\n')

    def test_from_path_reads_the_source(self, tmp_path: Path) -> None:
        path = tmp_path / "catalog.po"
        path.write_text(catalog_text(), encoding="utf-8")

        catalog = afanes.i18n.po.PoCatalog.from_path(path)

        assert len(catalog.messages) == EXPECTED_MESSAGES


class TestMoWriter:
    def test_the_output_loads_with_the_standard_library(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.parse(catalog_text())
        translations = gettext.GNUTranslations(io.BytesIO(catalog.to_mo()))

        assert translations.pgettext("GREETING", "Hello") == "Hola"
        assert translations.pgettext("FAREWELL", "Goodbye") == "Adiós"

    def test_the_header_metadata_is_preserved(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.parse(catalog_text())
        translations = gettext.GNUTranslations(io.BytesIO(catalog.to_mo()))

        assert translations.info()["content-type"] == "text/plain; charset=UTF-8"
        assert translations.info()["language"] == "es"

    def test_identical_msgids_with_different_contexts_stay_independent(self) -> None:
        text = (
            HEADER
            + 'msgctxt "CAPTURE_NOUN"\nmsgid "Capture"\nmsgstr "Captura"\n\n'
            + 'msgctxt "CAPTURE_ACTION"\nmsgid "Capture"\nmsgstr "Capturar"\n'
        )
        catalog = afanes.i18n.po.PoCatalog.parse(text)
        translations = gettext.GNUTranslations(io.BytesIO(catalog.to_mo()))

        assert translations.pgettext("CAPTURE_NOUN", "Capture") == "Captura"
        assert translations.pgettext("CAPTURE_ACTION", "Capture") == "Capturar"

    def test_the_output_is_deterministic(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.parse(catalog_text())

        assert catalog.to_mo() == catalog.to_mo()

    def test_write_mo_creates_the_file(self, tmp_path: Path) -> None:
        catalog = afanes.i18n.po.PoCatalog.parse(catalog_text())
        path = tmp_path / "catalog.mo"

        catalog.write_mo(path)

        assert path.is_file()

    def test_a_catalog_without_a_header_still_loads(self) -> None:
        catalog = afanes.i18n.po.PoCatalog.parse('msgctxt "GREETING"\nmsgid "Hello"\nmsgstr "Hola"\n')
        translations = gettext.GNUTranslations(io.BytesIO(catalog.to_mo()))

        assert translations.pgettext("GREETING", "Hello") == "Hola"


class TestCatalogCompiler:
    def test_every_po_file_is_compiled(self, tmp_path: Path) -> None:
        source = tmp_path / "es" / "LC_MESSAGES" / "sample.po"
        source.parent.mkdir(parents=True)
        source.write_text(catalog_text(), encoding="utf-8")

        compiled = afanes.i18n.po.CatalogCompiler(tmp_path).compile()

        assert compiled == (source.with_suffix(".mo"),)
        assert source.with_suffix(".mo").is_file()

    def test_the_compiled_catalog_loads(self, tmp_path: Path) -> None:
        source = tmp_path / "es" / "LC_MESSAGES" / "sample.po"
        source.parent.mkdir(parents=True)
        source.write_text(catalog_text(), encoding="utf-8")
        afanes.i18n.po.CatalogCompiler(tmp_path).compile()

        with source.with_suffix(".mo").open("rb") as stream:
            translations = gettext.GNUTranslations(stream)

        assert translations.pgettext("GREETING", "Hello") == "Hola"

    def test_no_po_files_compiles_nothing(self, tmp_path: Path) -> None:
        assert afanes.i18n.po.CatalogCompiler(tmp_path).compile() == ()
