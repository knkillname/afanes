"""Tests for reference template cards and their catalog."""

from pathlib import Path

import pytest

import afanes.core.template_cards
from afanes.core.errors import TemplateCardContentError
from afanes.models.note import NoteType

CARD_TEXT = """---
type: reference
category: person
title: Person
description: A contact.
---

## Contact

- Email:
"""


def _write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _catalog(root: Path) -> afanes.core.template_cards.TemplateCardCatalog:
    return afanes.core.template_cards.TemplateCardCatalog.from_root(root)


class TestCardParsing:
    def test_a_complete_card_parses(self, tmp_path: Path) -> None:
        _write(tmp_path, "person.md", CARD_TEXT)

        listing = _catalog(tmp_path).load()

        assert listing.issues == ()
        card = listing.cards[0]
        assert card.title == "Person"
        assert card.description == "A contact."
        assert card.note_type is NoteType.REFERENCE
        assert card.category is not None
        assert card.category.value == "person"
        assert card.body == "## Contact\n\n- Email:"
        assert card.text == CARD_TEXT

    def test_a_log_card_parses(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "daily.md",
            "---\ntype: log\ntitle: Daily entry\n---\n\n## What happened\n",
        )

        card = _catalog(tmp_path).load().cards[0]

        assert card.note_type is NoteType.LOG
        assert card.category is None
        assert card.title == "Daily entry"

    def test_a_log_card_with_a_category_is_refused(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "daily.md",
            "---\ntype: log\ncategory: personal\n---\n\n## What happened\n",
        )

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert len(listing.issues) == 1

    def test_the_title_falls_back_to_the_file_stem(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\n---\n\n## Details\n")

        card = _catalog(tmp_path).load().cards[0]

        assert card.title == "vendor"

    def test_the_description_is_optional(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\ntitle: Vendor\n---\n")

        card = _catalog(tmp_path).load().cards[0]

        assert card.description is None

    def test_a_blank_description_is_absent(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\ndescription: '  '\n---\n")

        card = _catalog(tmp_path).load().cards[0]

        assert card.description is None

    def test_an_empty_body_is_valid(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\n---\n")

        card = _catalog(tmp_path).load().cards[0]

        assert card.body == ""

    def test_a_level_one_heading_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\n---\n\n# Vendor\n")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert "level-1 heading" in listing.issues[0].message

    def test_a_missing_category_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\n---\n")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert "category" in listing.issues[0].message

    def test_a_non_reference_type_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: project\n---\n")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert "type: reference" in listing.issues[0].message

    def test_a_status_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\nstatus: later\n---\n")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert "status" in listing.issues[0].message

    def test_a_due_date_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\ndue_date: 2026-12-01\n---\n")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert "due_date" in listing.issues[0].message

    def test_malformed_frontmatter_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: [unclosed\n---\n")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert "frontmatter" in listing.issues[0].message

    def test_a_non_string_title_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\ntitle: 3\n---\n")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert "title must be a string" in listing.issues[0].message

    def test_a_non_string_description_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "vendor.md", "---\ntype: reference\ncategory: vendor\ndescription: [a]\n---\n")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert "description must be a string" in listing.issues[0].message

    def test_a_non_markdown_file_is_ignored(self, tmp_path: Path) -> None:
        _write(tmp_path, "notes.txt", "not a card")

        listing = _catalog(tmp_path).load()

        assert listing.cards == ()
        assert listing.issues == ()


class TestCardOrdering:
    def test_cards_are_ordered_by_title(self, tmp_path: Path) -> None:
        _write(tmp_path, "z.md", "---\ntype: reference\ncategory: place\ntitle: Place\n---\n")
        _write(tmp_path, "a.md", "---\ntype: reference\ncategory: person\ntitle: Person\n---\n")

        titles = [card.title for card in _catalog(tmp_path).load().cards]

        assert titles == ["Person", "Place"]

    def test_duplicate_titles_keep_both_paths(self, tmp_path: Path) -> None:
        _write(tmp_path, "zeta.md", "---\ntype: reference\ncategory: other\ntitle: Same\n---\n")
        _write(tmp_path, "alpha.md", "---\ntype: reference\ncategory: other\ntitle: Same\n---\n")

        paths = [card.relative_path.as_posix() for card in _catalog(tmp_path).load().cards]

        assert paths == ["alpha.md", "zeta.md"]

    def test_an_invalid_card_does_not_hide_the_valid_ones(self, tmp_path: Path) -> None:
        _write(tmp_path, "good.md", "---\ntype: reference\ncategory: person\ntitle: Person\n---\n")
        _write(tmp_path, "bad.md", "---\ntype: reference\n---\n")

        listing = _catalog(tmp_path).load()

        assert [card.title for card in listing.cards] == ["Person"]
        assert [issue.relative_path.as_posix() for issue in listing.issues] == ["bad.md"]

    def test_a_missing_folder_is_empty(self, tmp_path: Path) -> None:
        listing = _catalog(tmp_path / "missing").load()

        assert listing.cards == ()
        assert listing.issues == ()


class TestBundledCards:
    def test_bundled_catalog_holds_the_eight_defaults(self) -> None:
        cards = afanes.core.template_cards.TemplateCardCatalog.bundled().strict_cards()

        assert [card.title for card in cards] == [
            "Daily entry",
            "Organization",
            "Person",
            "Place",
            "Process",
            "Source",
            "Team",
            "Topic",
        ]
        assert [card.category.value if card.category is not None else None for card in cards] == [
            None,
            "organization",
            "person",
            "place",
            "process",
            "source",
            "team",
            "topic",
        ]

    def test_bundled_defaults_have_starter_bodies(self) -> None:
        cards = afanes.core.template_cards.TemplateCardCatalog.bundled().strict_cards()

        assert all(card.description for card in cards)
        assert all(card.body for card in cards)
        assert all(f"type: {card.note_type.value}" in card.text for card in cards)

    def test_a_broken_bundle_is_refused(self, tmp_path: Path) -> None:
        _write(tmp_path, "broken.md", "---\ntype: reference\n---\n")

        with pytest.raises(TemplateCardContentError) as info:
            _catalog(tmp_path).strict_cards()

        assert "broken.md" in str(info.value)

    def test_an_empty_bundle_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(TemplateCardContentError) as info:
            _catalog(tmp_path).strict_cards()

        assert "missing" in str(info.value)
