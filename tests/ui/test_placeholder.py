"""Tests for the shared symbolic placeholder page."""

import flet as ft

import afanes.ui.components.placeholder
import afanes.ui.theme

ICON_AND_TITLE = 2


def _column(control: ft.Control) -> ft.Column:
    assert isinstance(control, ft.Container)
    content = control.content
    assert isinstance(content, ft.Column)
    return content


def _icon(control: ft.Control) -> ft.Icon:
    assert isinstance(control, ft.Semantics)
    assert control.exclude_semantics is True
    content = control.content
    assert isinstance(content, ft.Icon)
    return content


class TestPlaceholderPage:
    def test_builds_icon_heading_guidance_and_one_action(self) -> None:
        action = ft.OutlinedButton(content="Create")

        page = afanes.ui.components.placeholder.PlaceholderPage(
            ft.Icons.INBOX_OUTLINED,
            "Inbox Is Empty",
            body="Captures appear here",
            action=action,
        )
        column = _column(page.build())

        icon = _icon(column.controls[0])
        assert icon.icon == ft.Icons.INBOX_OUTLINED
        assert icon.size == afanes.ui.theme.ICON_SIZE_LARGE
        assert icon.color == afanes.ui.theme.MUTED_TEXT_COLOR
        title = column.controls[1]
        assert isinstance(title, ft.Text)
        assert title.value == "Inbox Is Empty"
        assert title.style == afanes.ui.theme.TEXT_ROLES["title-4"]
        body = column.controls[2]
        assert isinstance(body, ft.Text)
        assert body.value == "Captures appear here"
        assert body.selectable is True
        assert column.controls[3] is action

    def test_guidance_and_action_are_optional(self) -> None:
        page = afanes.ui.components.placeholder.PlaceholderPage(
            ft.Icons.DESCRIPTION_OUTLINED,
            "No Page Open",
        )
        column = _column(page.build())

        assert len(column.controls) == ICON_AND_TITLE
        assert isinstance(column.controls[1], ft.Text)
        assert column.controls[1].value == "No Page Open"

    def test_the_icon_is_decorative_and_the_text_is_accessible(self) -> None:
        page = afanes.ui.components.placeholder.PlaceholderPage(
            ft.Icons.SEARCH_OFF_OUTLINED,
            "No Notes Match “absent”",
            body="Try a different word",
        )
        column = _column(page.build())

        _icon(column.controls[0])
        assert isinstance(column.controls[1], ft.Text)
        assert column.controls[1].value == "No Notes Match “absent”"
        assert isinstance(column.controls[2], ft.Text)
        assert column.controls[2].value == "Try a different word"

    def test_the_page_centers_its_content(self) -> None:
        page = afanes.ui.components.placeholder.PlaceholderPage(
            ft.Icons.DELETE_OUTLINE,
            "Trash Is Empty",
        )
        root = page.build()

        assert isinstance(root, ft.Container)
        assert root.alignment == ft.Alignment.CENTER
        assert root.key == "placeholder-page"
