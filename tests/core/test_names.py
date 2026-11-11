"""Tests for name normalization and cross-platform filename derivation."""

import hypothesis
import hypothesis.strategies

import afanes.core.names


class TestNormalizeName:
    def test_lowercases_and_trims(self) -> None:
        assert afanes.core.names.normalize_name("  Ada Lovelace  ") == "ada lovelace"

    def test_collapses_internal_whitespace(self) -> None:
        assert afanes.core.names.normalize_name("Ada \t  Lovelace\n") == "ada lovelace"

    def test_removes_one_markdown_extension(self) -> None:
        assert afanes.core.names.normalize_name("Ada Lovelace.md") == "ada lovelace"

    def test_removes_extensions_repeatedly_for_idempotence(self) -> None:
        assert afanes.core.names.normalize_name("Ada.md.md") == "ada"

    def test_ignores_extension_case(self) -> None:
        assert afanes.core.names.normalize_name("Report.MD") == "report"

    def test_folds_case_conservatively(self) -> None:
        assert afanes.core.names.normalize_name("Straße") == afanes.core.names.normalize_name("Strasse")

    def test_composed_and_decomposed_unicode_match(self) -> None:
        composed = "Jos\u00e9"
        decomposed = "Jose\u0301"
        assert afanes.core.names.normalize_name(composed) == afanes.core.names.normalize_name(decomposed)

    def test_empty_input_normalizes_to_empty(self) -> None:
        assert afanes.core.names.normalize_name("") == ""

    @hypothesis.given(hypothesis.strategies.text(max_size=50))
    def test_normalization_is_idempotent(self, text: str) -> None:
        once = afanes.core.names.normalize_name(text)
        assert afanes.core.names.normalize_name(once) == once


class TestSafeFilename:
    def test_replaces_forbidden_characters_with_spaces(self) -> None:
        assert afanes.core.names.safe_filename("Q1: Planning?") == "Q1 Planning"

    def test_collapses_repeated_forbidden_characters(self) -> None:
        assert afanes.core.names.safe_filename("a///b") == "a b"

    def test_removes_control_characters(self) -> None:
        assert afanes.core.names.safe_filename("Ada\x00Lovelace") == "AdaLovelace"

    def test_avoids_reserved_device_names(self) -> None:
        assert afanes.core.names.safe_filename("CON") == "CON-note"

    def test_avoids_reserved_device_name_with_extension(self) -> None:
        assert afanes.core.names.safe_filename("con.txt") == "con-note.txt"

    def test_removes_trailing_dot_and_space(self) -> None:
        assert afanes.core.names.safe_filename("Agenda. ") == "Agenda"

    def test_removes_leading_dots(self) -> None:
        assert afanes.core.names.safe_filename(".hidden") == "hidden"

    def test_removes_leading_dot_before_reserved_check(self) -> None:
        assert afanes.core.names.safe_filename(".CON") == "CON-note"

    def test_truncates_to_two_hundred_bytes(self) -> None:
        result = afanes.core.names.safe_filename("\u00e9" * 150)
        assert len(result.encode("utf-8")) <= afanes.core.names.MAX_NAME_BYTES

    def test_truncation_keeps_a_valid_character_boundary(self) -> None:
        result = afanes.core.names.safe_filename("a" + "\u00e9" * 150)
        assert result.encode("utf-8").decode("utf-8") == result

    def test_empty_result_falls_back_to_untitled(self) -> None:
        assert afanes.core.names.safe_filename(" . ") == "Untitled"

    def test_preserves_display_case(self) -> None:
        assert afanes.core.names.safe_filename("Turing Machine") == "Turing Machine"

    @hypothesis.given(hypothesis.strategies.text(max_size=100))
    def test_sanitized_names_are_idempotent(self, text: str) -> None:
        sanitized = afanes.core.names.safe_filename(text)
        assert afanes.core.names.safe_filename(sanitized) == sanitized

    @hypothesis.given(hypothesis.strategies.text(max_size=100))
    def test_sanitized_names_respect_every_cross_platform_rule(self, text: str) -> None:
        sanitized = afanes.core.names.safe_filename(text)
        assert sanitized
        assert len(sanitized.encode("utf-8")) <= afanes.core.names.MAX_NAME_BYTES
        assert not (set(sanitized) & afanes.core.names.FORBIDDEN_CHARACTERS)
        assert not sanitized.startswith(".")
        assert not sanitized.endswith((".", " "))
        assert sanitized.split(".", 1)[0].upper() not in afanes.core.names.RESERVED_DEVICE_NAMES


class TestUniqueName:
    def test_returns_name_when_available(self) -> None:
        assert afanes.core.names.unique_name("Ada", []) == "Ada"

    def test_appends_two_on_first_collision(self) -> None:
        assert afanes.core.names.unique_name("Ada", ["Ada"]) == "Ada 2"

    def test_reuses_a_gap_in_the_sequence(self) -> None:
        assert afanes.core.names.unique_name("Ada", ["Ada", "Ada 3"]) == "Ada 2"

    def test_collision_is_case_insensitive(self) -> None:
        assert afanes.core.names.unique_name("ada", ["Ada"]) == "ada 2"

    def test_collision_ignores_a_markdown_extension(self) -> None:
        assert afanes.core.names.unique_name("Ada", ["Ada.md"]) == "Ada 2"

    def test_suffixed_name_stays_within_the_byte_limit(self) -> None:
        long_name = "\u00e9" * 100
        result = afanes.core.names.unique_name(long_name, [long_name])
        assert len(result.encode("utf-8")) <= afanes.core.names.MAX_NAME_BYTES
        assert result.endswith(" 2")
