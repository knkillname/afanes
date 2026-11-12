"""Tests for reference parsing, extraction, catalog building, and rewriting."""

import builtins
from pathlib import Path

import hypothesis
import hypothesis.strategies
import pytest

import afanes.core.links
from afanes.core.errors import InvalidReferenceError, ReferenceRewriteError
from afanes.core.links import (
    CatalogEntry,
    DestinationKind,
    MarkdownRewrite,
    NameCatalog,
    ReferenceKey,
    ResolutionOutcome,
)
from afanes.models.link import NoteReference, ReferenceScheme
from afanes.models.note import NoteType, ReferenceCategory

TWO_REWRITES = 2
LABEL_END_INDEX = 4


def _rewrite(
    markdown: str,
    old: NoteReference,
    new: NoteReference,
) -> afanes.core.links.MarkdownRewrite:
    return afanes.core.links.MarkdownBody(markdown).rewrite_references(old, new)


def _parse(destination: str) -> NoteReference:
    return afanes.core.links.ReferenceParser().parse(destination)


class TestReferenceKey:
    def test_normalizes_the_written_name(self) -> None:
        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="  Ada   Lovelace ")
        key = ReferenceKey.from_reference(reference)
        assert key == ReferenceKey(scheme=ReferenceScheme.PERSON, name="ada lovelace")

    def test_keeps_the_scheme(self) -> None:
        reference = NoteReference(scheme=ReferenceScheme.PROJECT, name="Release 1.0")
        key = ReferenceKey.from_reference(reference)
        assert key.scheme is ReferenceScheme.PROJECT


class TestParseReference:
    def test_parses_a_person_destination(self) -> None:
        reference = _parse("person:Ada")
        assert reference == NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")

    def test_strips_angle_brackets(self) -> None:
        reference = _parse("<person:Ada Lovelace>")
        assert reference.name == "Ada Lovelace"

    def test_matches_scheme_case_insensitively(self) -> None:
        reference = _parse("Person:Ada")
        assert reference.scheme is ReferenceScheme.PERSON

    def test_decodes_percent_escapes(self) -> None:
        reference = _parse("person:Ada%20Lovelace")
        assert reference.name == "Ada Lovelace"

    def test_trims_the_name(self) -> None:
        reference = _parse("<person: Ada >")
        assert reference.name == "Ada"

    def test_rejects_an_unknown_scheme(self) -> None:
        with pytest.raises(InvalidReferenceError):
            _parse("https://example.com")

    def test_rejects_a_destination_without_a_scheme(self) -> None:
        with pytest.raises(InvalidReferenceError):
            _parse("attachments/scan.png")

    def test_rejects_an_empty_name(self) -> None:
        with pytest.raises(InvalidReferenceError):
            _parse("note:")

    def test_rejects_a_whitespace_only_name(self) -> None:
        with pytest.raises(InvalidReferenceError):
            _parse("<note:   >")


class TestClassifyDestination:
    @pytest.mark.parametrize("destination", ["person:Ada", "project:Turing", "note:Call dentist"])
    def test_internal_schemes(self, destination: str) -> None:
        assert DestinationKind.classify(destination) is DestinationKind.INTERNAL

    @pytest.mark.parametrize("destination", ["https://example.com", "mailto:ada@example.com"])
    def test_external_schemes(self, destination: str) -> None:
        assert DestinationKind.classify(destination) is DestinationKind.EXTERNAL

    @pytest.mark.parametrize("scheme", sorted(afanes.core.links.UNSAFE_SCHEMES))
    def test_active_schemes_are_unsafe(self, scheme: str) -> None:
        destination = f"{scheme}:payload"
        assert DestinationKind.classify(destination) is DestinationKind.UNSAFE

    def test_relative_path_is_an_attachment(self) -> None:
        assert DestinationKind.classify("attachments/scan.png") is DestinationKind.ATTACHMENT

    def test_heading_fragment_is_an_anchor(self) -> None:
        assert DestinationKind.classify("#heading") is DestinationKind.ANCHOR

    def test_protocol_relative_url_is_external(self) -> None:
        assert DestinationKind.classify("//example.com") is DestinationKind.EXTERNAL


class TestReferenceReader:
    def test_reuses_one_reader_for_multiple_documents(self) -> None:
        reader = afanes.core.links.ReferenceReader()

        first = reader.extract("See [Ada](person:Ada).")
        second = reader.extract("Use `[Ada](person:Ada)` and see [Grace](person:Grace).")

        assert [reference.name for reference in first] == ["Ada"]
        assert [reference.name for reference in second] == ["Grace"]

    def test_extracts_a_plain_link(self) -> None:
        references = afanes.core.links.ReferenceReader().extract("See [Ada](person:Ada).")
        assert references == [NoteReference(scheme=ReferenceScheme.PERSON, name="Ada", label="Ada")]

    def test_extracts_an_angle_bracketed_destination(self) -> None:
        references = afanes.core.links.ReferenceReader().extract("[Ada](<person:Ada Lovelace>)")
        assert references[0].name == "Ada Lovelace"

    def test_keeps_a_custom_label(self) -> None:
        references = afanes.core.links.ReferenceReader().extract("[my colleague](person:Ada)")
        assert references[0].label == "my colleague"

    def test_extracts_reference_style_links(self) -> None:
        body = "[Ada][ada]\n\n[ada]: <person:Ada Lovelace>\n"
        references = afanes.core.links.ReferenceReader().extract(body)
        assert references == [NoteReference(scheme=ReferenceScheme.PERSON, name="Ada Lovelace", label="Ada")]

    def test_extracts_links_with_nested_label_brackets(self) -> None:
        references = afanes.core.links.ReferenceReader().extract("[see [the person]](person:Ada)")
        assert references[0].label == "see [the person]"

    def test_ignores_an_escaped_opening_bracket(self) -> None:
        assert afanes.core.links.ReferenceReader().extract(r"\[Ada](person:Ada)") == []

    def test_ignores_a_reference_inside_fenced_code(self) -> None:
        body = "```markdown\n[Ada](person:Ada)\n```\n"
        assert afanes.core.links.ReferenceReader().extract(body) == []

    def test_ignores_a_reference_inside_indented_code(self) -> None:
        body = "\n    [Ada](person:Ada)\n"
        assert afanes.core.links.ReferenceReader().extract(body) == []

    def test_ignores_a_reference_inside_inline_code(self) -> None:
        assert afanes.core.links.ReferenceReader().extract("Use `[Ada](person:Ada)` literally.") == []

    def test_ignores_a_reference_inside_an_html_comment(self) -> None:
        assert afanes.core.links.ReferenceReader().extract("<!-- [Ada](person:Ada) -->") == []

    def test_ignores_an_image_destination(self) -> None:
        assert afanes.core.links.ReferenceReader().extract("![diagram](person:Ada)") == []

    def test_ignores_bracket_link_syntax(self) -> None:
        assert afanes.core.links.ReferenceReader().extract("[[Ada Lovelace]]") == []

    def test_does_not_extract_external_links(self) -> None:
        assert afanes.core.links.ReferenceReader().extract("[docs](https://example.com)") == []

    def test_rejects_a_malformed_internal_destination(self) -> None:
        with pytest.raises(InvalidReferenceError):
            afanes.core.links.ReferenceReader().extract("[x](note:)")

    @hypothesis.given(
        hypothesis.strategies.text(
            alphabet=hypothesis.strategies.characters(blacklist_characters="~\n\r"),
            max_size=100,
        )
    )
    def test_a_fenced_code_block_hides_every_reference(self, text: str) -> None:
        body = f"~~~\n{text}\n~~~\n"
        assert afanes.core.links.ReferenceReader().extract(body) == []


class TestSchemeForNote:
    def test_person_category_maps_to_person(self) -> None:
        assert ReferenceScheme.for_note(NoteType.REFERENCE, ReferenceCategory.PERSON) is ReferenceScheme.PERSON

    def test_uncategorized_reference_maps_to_note(self) -> None:
        assert ReferenceScheme.for_note(NoteType.REFERENCE, None) is ReferenceScheme.NOTE

    def test_project_maps_to_project(self) -> None:
        assert ReferenceScheme.for_note(NoteType.PROJECT, None) is ReferenceScheme.PROJECT

    def test_action_maps_to_note(self) -> None:
        assert ReferenceScheme.for_note(NoteType.ACTION, None) is ReferenceScheme.NOTE

    def test_note_maps_to_note(self) -> None:
        assert ReferenceScheme.for_note(NoteType.NOTE, None) is ReferenceScheme.NOTE


class TestCatalog:
    def test_maps_each_type_to_its_scheme(self) -> None:
        catalog = NameCatalog.from_entries(
            [
                CatalogEntry(Path("people/Ada.md"), NoteType.REFERENCE, ReferenceCategory.PERSON),
                CatalogEntry(Path("work/Turing.md"), NoteType.PROJECT, None),
                CatalogEntry(Path("inbox/Call.md"), NoteType.ACTION, None),
            ]
        )
        assert catalog.candidates(ReferenceScheme.PERSON, "ada") == (Path("people/Ada.md"),)
        assert catalog.candidates(ReferenceScheme.PROJECT, "turing") == (Path("work/Turing.md"),)
        assert catalog.candidates(ReferenceScheme.NOTE, "call") == (Path("inbox/Call.md"),)

    def test_uncategorized_reference_stays_in_note_scheme(self) -> None:
        target = Path("reference/Ada.md")
        catalog = NameCatalog.from_entries([CatalogEntry(target, NoteType.REFERENCE, None)])

        assert catalog.candidates(ReferenceScheme.NOTE, "ada") == (target,)
        assert catalog.candidates(ReferenceScheme.PERSON, "ada") == ()

    def test_person_category_is_not_in_note_scheme(self) -> None:
        target = Path("reference/people/Ada.md")
        catalog = NameCatalog.from_entries([CatalogEntry(target, NoteType.REFERENCE, ReferenceCategory.PERSON)])

        assert catalog.candidates(ReferenceScheme.PERSON, "ada") == (target,)
        assert catalog.candidates(ReferenceScheme.NOTE, "ada") == ()

    def test_person_and_uncategorized_reference_can_share_a_name(self) -> None:
        person = Path("reference/people/Ada.md")
        reference = Path("reference/Ada.md")
        catalog = NameCatalog.from_entries(
            [
                CatalogEntry(person, NoteType.REFERENCE, ReferenceCategory.PERSON),
                CatalogEntry(reference, NoteType.REFERENCE, None),
            ]
        )

        assert catalog.candidates(ReferenceScheme.PERSON, "ada") == (person,)
        assert catalog.candidates(ReferenceScheme.NOTE, "ada") == (reference,)

    def test_allows_cross_scheme_name_reuse(self) -> None:
        catalog = NameCatalog.from_entries(
            [
                CatalogEntry(Path("people/Ada.md"), NoteType.REFERENCE, ReferenceCategory.PERSON),
                CatalogEntry(Path("work/Ada.md"), NoteType.PROJECT, None),
            ]
        )
        assert catalog.candidates(ReferenceScheme.PERSON, "ada") == (Path("people/Ada.md"),)
        assert catalog.candidates(ReferenceScheme.PROJECT, "ada") == (Path("work/Ada.md"),)

    def test_keeps_duplicate_names_as_multiple_candidates(self) -> None:
        first = Path("a/Ada.md")
        second = Path("b/Ada.md")
        catalog = NameCatalog.from_entries(
            [
                CatalogEntry(first, NoteType.REFERENCE, ReferenceCategory.PERSON),
                CatalogEntry(second, NoteType.REFERENCE, ReferenceCategory.PERSON),
            ]
        )
        assert catalog.candidates(ReferenceScheme.PERSON, "ada") == (first, second)

    def test_normalizes_case_and_unicode(self) -> None:
        catalog = NameCatalog.from_entries(
            [CatalogEntry(Path("people/Jose\u0301.md"), NoteType.REFERENCE, ReferenceCategory.PERSON)]
        )
        assert catalog.candidates(ReferenceScheme.PERSON, "jos\u00e9") == (Path("people/Jose\u0301.md"),)

    def test_candidates_are_sorted_deterministically(self) -> None:
        first = Path("z/Ada.md")
        second = Path("a/Ada.md")
        catalog = NameCatalog.from_entries(
            [
                CatalogEntry(first, NoteType.REFERENCE, ReferenceCategory.PERSON),
                CatalogEntry(second, NoteType.REFERENCE, ReferenceCategory.PERSON),
            ]
        )
        assert catalog.candidates(ReferenceScheme.PERSON, "ada") == (second, first)


class TestResolution:
    def test_resolves_a_unique_match(self) -> None:
        target = Path("people/Ada.md")
        catalog = NameCatalog.from_entries([CatalogEntry(target, NoteType.REFERENCE, ReferenceCategory.PERSON)])
        result = catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="ada"))
        assert result.outcome is ResolutionOutcome.RESOLVED
        assert result.targets == (target,)

    def test_reports_an_unresolved_reference(self) -> None:
        catalog = NameCatalog.from_entries([])
        result = catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.UNRESOLVED
        assert result.targets == ()

    def test_reports_all_candidates_for_an_ambiguous_name(self) -> None:
        first = Path("a/Ada.md")
        second = Path("b/Ada.md")
        catalog = NameCatalog.from_entries(
            [
                CatalogEntry(first, NoteType.REFERENCE, ReferenceCategory.PERSON),
                CatalogEntry(second, NoteType.REFERENCE, ReferenceCategory.PERSON),
            ]
        )
        result = catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.AMBIGUOUS
        assert result.targets == (first, second)

    def test_namespaces_never_resolve_across_schemes(self) -> None:
        catalog = NameCatalog.from_entries([CatalogEntry(Path("work/Ada.md"), NoteType.PROJECT, None)])
        result = catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.UNRESOLVED

    def test_heals_when_a_matching_note_is_added(self) -> None:
        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")
        before = NameCatalog.from_entries([]).resolve(reference)
        after = NameCatalog.from_entries(
            [CatalogEntry(Path("people/Ada.md"), NoteType.REFERENCE, ReferenceCategory.PERSON)]
        ).resolve(reference)
        assert before.outcome is ResolutionOutcome.UNRESOLVED
        assert after.outcome is ResolutionOutcome.RESOLVED

    def test_dangles_when_a_matching_note_is_removed(self) -> None:
        reference = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")
        catalog = NameCatalog.from_entries(
            [CatalogEntry(Path("people/Ada.md"), NoteType.REFERENCE, ReferenceCategory.PERSON)]
        )
        before = catalog.resolve(reference)
        after = NameCatalog.from_entries([]).resolve(reference)
        assert before.outcome is ResolutionOutcome.RESOLVED
        assert after.outcome is ResolutionOutcome.UNRESOLVED

    @pytest.mark.parametrize("name", ["../Ada", "people/Ada", "people\\Ada", "..", "..md"])
    def test_traversal_looking_names_match_nothing(self, name: str) -> None:
        catalog = NameCatalog.from_entries(
            [CatalogEntry(Path("people/Ada.md"), NoteType.REFERENCE, ReferenceCategory.PERSON)]
        )
        result = catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name=name))
        assert result.outcome is ResolutionOutcome.UNRESOLVED

    def test_resolution_performs_no_file_io(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fail(*_args: object, **_kwargs: object) -> None:
            message = "resolution must not open a file"
            raise AssertionError(message)

        monkeypatch.setattr(builtins, "open", fail)
        catalog = NameCatalog.from_entries(
            [CatalogEntry(Path("people/Ada.md"), NoteType.REFERENCE, ReferenceCategory.PERSON)]
        )
        result = catalog.resolve(NoteReference(scheme=ReferenceScheme.PERSON, name="Ada"))
        assert result.outcome is ResolutionOutcome.RESOLVED


class TestRewriteBodyReferences:
    old = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada Lovelace")
    new = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King")

    def test_updates_an_angle_bracketed_destination_and_label(self) -> None:
        result = _rewrite("[Ada Lovelace](<person:Ada Lovelace>)", self.old, self.new)
        assert result.text == "[Ada King](<person:Ada King>)"
        assert result.count == 1

    def test_preserves_a_custom_label(self) -> None:
        result = _rewrite("[my colleague](<person:Ada Lovelace>)", self.old, self.new)
        assert result.text == "[my colleague](<person:Ada King>)"

    def test_updates_a_case_variant_destination(self) -> None:
        result = _rewrite("[x](<Person:ada lovelace>)", self.old, self.new)
        assert result.text == "[x](<person:Ada King>)"

    def test_percent_encodes_a_bare_destination(self) -> None:
        old = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada")
        new = NoteReference(scheme=ReferenceScheme.PERSON, name="Ada King")
        result = _rewrite("[Ada](person:Ada)", old, new)
        assert result.text == "[Ada King](person:Ada%20King)"

    def test_rewrites_every_occurrence(self) -> None:
        body = "[Ada Lovelace](<person:Ada Lovelace>) and [again](<person:Ada Lovelace>)"
        result = _rewrite(body, self.old, self.new)
        assert result.count == TWO_REWRITES
        assert "Ada Lovelace>" not in result.text

    def test_ignores_an_image_destination(self) -> None:
        body = "![Ada Lovelace](<person:Ada Lovelace>)"
        assert _rewrite(body, self.old, self.new) == MarkdownRewrite(body, 0)

    def test_ignores_a_reference_inside_a_code_span(self) -> None:
        body = "`[Ada Lovelace](<person:Ada Lovelace>)`"
        assert _rewrite(body, self.old, self.new) == MarkdownRewrite(body, 0)

    def test_ignores_a_reference_inside_a_fenced_block(self) -> None:
        body = "~~~\n[Ada Lovelace](<person:Ada Lovelace>)\n~~~"
        assert _rewrite(body, self.old, self.new) == MarkdownRewrite(body, 0)

    def test_ignores_a_reference_inside_an_html_comment(self) -> None:
        body = "<!-- [Ada Lovelace](<person:Ada Lovelace>) -->"
        assert _rewrite(body, self.old, self.new) == MarkdownRewrite(body, 0)

    def test_ignores_an_escaped_link(self) -> None:
        body = r"\[Ada Lovelace](<person:Ada Lovelace>)"
        assert _rewrite(body, self.old, self.new) == MarkdownRewrite(body, 0)

    def test_rewrites_a_link_after_an_escaped_bang(self) -> None:
        body = r"\![Ada Lovelace](<person:Ada Lovelace>)"
        result = _rewrite(body, self.old, self.new)
        assert result.text == r"\![Ada King](<person:Ada King>)"
        assert result.count == 1

    def test_rewrites_a_reference_style_definition(self) -> None:
        body = "[Ada][ada]\n\n[ada]: <person:Ada Lovelace>\n"
        result = _rewrite(body, self.old, self.new)
        assert result.count == 1
        assert "[ada]: <person:Ada King>" in result.text

    def test_returns_unchanged_text_when_nothing_matches(self) -> None:
        body = "[Grace](person:Grace)"
        assert _rewrite(body, self.old, self.new) == MarkdownRewrite(body, 0)

    def test_raises_when_verification_cannot_parse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def broken(_reader: afanes.core.links.ReferenceReader, _markdown: str) -> list[NoteReference]:
            message = "broken"
            raise InvalidReferenceError(message)

        monkeypatch.setattr(afanes.core.links.ReferenceReader, "extract", broken)
        with pytest.raises(ReferenceRewriteError):
            _rewrite("[Ada Lovelace](<person:Ada Lovelace>)", self.old, self.new)

    def test_raises_when_the_old_reference_survives(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def stale(_reader: afanes.core.links.ReferenceReader, _markdown: str) -> list[NoteReference]:
            return [self.old]

        monkeypatch.setattr(afanes.core.links.ReferenceReader, "extract", stale)
        with pytest.raises(ReferenceRewriteError):
            _rewrite("[Ada Lovelace](<person:Ada Lovelace>)", self.old, self.new)


class TestMarkdownValues:
    def test_edit_batch_extends_edits_and_counts(self) -> None:
        first = afanes.core.links.EditBatch(
            edits=(afanes.core.links.MarkdownEdit(0, 1, "a"),),
            count=1,
        )
        second = afanes.core.links.EditBatch(
            edits=(afanes.core.links.MarkdownEdit(2, 3, "b"),),
            count=1,
        )

        combined = first.extend(second)

        assert combined.edits == (*first.edits, *second.edits)
        assert combined.count == TWO_REWRITES

    def test_link_label_keeps_text_and_next_index(self) -> None:
        label = afanes.core.links.LinkLabel(text="Ada", next_index=4)

        assert label.text == "Ada"
        assert label.next_index == LABEL_END_INDEX

    def test_markdown_rewrite_keeps_text_and_count(self) -> None:
        rewrite = afanes.core.links.MarkdownRewrite(text="body", count=2)

        assert rewrite.text == "body"
        assert rewrite.count == TWO_REWRITES
