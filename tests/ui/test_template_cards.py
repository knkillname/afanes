"""Tests for the shared template card picker component."""

import typing
from pathlib import Path

import afanes.ui.strings
from afanes.core.template_cards import TemplateCard, TemplateCardCatalog, TemplateCardIssue
from afanes.models.note import NoteType
from afanes.ui.components.template_cards import TemplateCardContext, TemplateCardPicker

EMPTY_KEY = "empty"


def _card(
    relative: str,
    *,
    title: str,
    description: str | None = None,
    note_type: NoteType = NoteType.REFERENCE,
) -> TemplateCard:
    lines = ["---", f"type: {note_type.value}"]
    if note_type is NoteType.REFERENCE:
        lines.append("category: general")
    lines.append(f"title: {title}")
    if description is not None:
        lines.append(f"description: {description}")
    lines.extend(["---", "", "## Starter"])
    return TemplateCardCatalog.parse(Path(relative), "\n".join(lines))


def _picker(
    context: TemplateCardContext = TemplateCardContext.REFERENCE,
    *,
    on_change: typing.Callable[[], None] | None = None,
) -> TemplateCardPicker:
    return TemplateCardPicker(context, "test", on_change)


class TestTemplateCardPickerOptions:
    def test_orders_cards_by_title_and_puts_empty_last(self) -> None:
        picker = _picker()
        picker.refresh(
            [
                _card("zeta.md", title="Zeta"),
                _card("alpha.md", title="Alpha"),
                _card("beta.md", title="Beta"),
            ]
        )

        keys = [option.key for option in picker.dropdown.options]
        assert keys == ["card:alpha.md", "card:beta.md", "card:zeta.md", EMPTY_KEY]

    def test_disambiguates_duplicate_titles_with_the_relative_path(self) -> None:
        picker = _picker()
        picker.refresh(
            [
                _card("person/a.md", title="Person", description="A contact."),
                _card("vendor/person.md", title="Person"),
            ]
        )

        texts = [option.text for option in picker.dropdown.options]
        assert texts == [
            afanes.ui.strings.BROWSER_TEMPLATE_OPTION_DUPLICATE.format(
                title="Person", description="A contact.", path="person/a.md"
            ),
            afanes.ui.strings.BROWSER_TEMPLATE_OPTION_DUPLICATE_PLAIN.format(title="Person", path="vendor/person.md"),
            afanes.ui.strings.BROWSER_TEMPLATE_EMPTY,
        ]

    def test_derives_control_keys_from_the_prefix(self) -> None:
        picker = TemplateCardPicker(TemplateCardContext.REFERENCE, "new-reference")

        assert picker.dropdown.key == "new-reference-template"
        assert picker.description.key == "new-reference-template-description"
        assert picker.warning.key == "new-reference-template-warning"

    def test_keeps_a_selection_that_survives_a_refresh(self) -> None:
        keep = _card("keep.md", title="Keep")
        replace = _card("replace.md", title="Replace")
        picker = _picker()
        picker.refresh([keep, replace])
        picker.dropdown.value = "card:keep.md"

        picker.refresh([keep, _card("other.md", title="Other")])

        assert picker.dropdown.value == "card:keep.md"
        assert picker.selected_card == keep

    def test_falls_back_to_empty_when_the_card_disappears(self) -> None:
        picker = _picker()
        picker.refresh([_card("gone.md", title="Gone")])
        picker.dropdown.value = "card:gone.md"

        picker.refresh([_card("other.md", title="Other")])

        assert picker.dropdown.value == EMPTY_KEY
        assert picker.selected_card is None


class TestTemplateCardPickerCopy:
    def test_shows_the_selected_card_description(self) -> None:
        card = _card("person.md", title="Person", description="A contact.")
        picker = _picker()
        picker.refresh([card])

        picker.dropdown.value = "card:person.md"
        typing.cast("typing.Any", picker.dropdown.on_select)()

        assert picker.description.value == "A contact."

    def test_shows_the_empty_description_for_empty(self) -> None:
        picker = _picker()
        picker.refresh([_card("person.md", title="Person", description="A contact.")])

        assert picker.description.value == afanes.ui.strings.BROWSER_TEMPLATE_DESCRIPTION_EMPTY

    def test_shows_the_no_description_text_for_a_plain_card(self) -> None:
        picker = _picker()
        picker.refresh([_card("plain.md", title="Plain")])

        picker.dropdown.value = "card:plain.md"
        typing.cast("typing.Any", picker.dropdown.on_select)()

        assert picker.description.value == afanes.ui.strings.BROWSER_TEMPLATE_NO_DESCRIPTION

    def test_log_context_describes_a_log_entry_without_a_category(self) -> None:
        picker = _picker(TemplateCardContext.LOG)
        picker.refresh([])

        empty = picker.dropdown.options[-1]

        assert empty.text == afanes.ui.strings.LOG_CARD_EMPTY
        assert "category" not in empty.text.casefold()
        assert picker.description.value == afanes.ui.strings.LOG_CARD_DESCRIPTION_EMPTY
        assert "category" not in picker.description.value.casefold()

    def test_calls_the_change_callback_after_a_selection(self) -> None:
        calls: list[int] = []
        picker = _picker(on_change=lambda: calls.append(1))
        picker.refresh([_card("person.md", title="Person")])
        picker.dropdown.value = "card:person.md"

        typing.cast("typing.Any", picker.dropdown.on_select)()

        assert calls == [1]


class TestTemplateCardPickerWarnings:
    def test_reports_invalid_cards(self) -> None:
        picker = _picker()
        issue = TemplateCardIssue(relative_path=Path("broken.md"), message="cannot be read")

        picker.refresh([], [issue])

        assert picker.warning.visible
        assert picker.warning.value == afanes.ui.strings.BROWSER_TEMPLATE_INVALID.format(paths="broken.md")

    def test_hides_the_warning_when_the_listing_is_clean(self) -> None:
        picker = _picker()
        picker.refresh([], [TemplateCardIssue(relative_path=Path("broken.md"), message="cannot be read")])

        picker.refresh([])

        assert not picker.warning.visible
        assert picker.warning.value == ""

    def test_log_context_uses_the_shared_warning_text(self) -> None:
        picker = _picker(TemplateCardContext.LOG)

        picker.refresh([], [TemplateCardIssue(relative_path=Path("broken.md"), message="cannot be read")])

        assert picker.warning.visible
        assert picker.warning.value == afanes.ui.strings.BROWSER_TEMPLATE_INVALID.format(paths="broken.md")
