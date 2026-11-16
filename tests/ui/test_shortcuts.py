"""Tests for the grouped keyboard shortcut sheet."""

import typing

import flet as ft

import afanes.core.localization
import afanes.i18n.ui
import afanes.i18n.ui.en
import afanes.ui.components.shortcuts
from tests.ui.control_tree import visible_controls


def _texts(control: ft.Control) -> list[str]:
    return [item.value or "" for item in visible_controls(control) if isinstance(item, ft.Text)]


class TestShortcutSheet:
    def test_the_sheet_groups_every_shortcut_by_context(self) -> None:
        sheet = afanes.ui.components.shortcuts.ShortcutSheet()

        content = sheet.build().content
        assert isinstance(content, ft.Column)
        groups = content.controls

        assert [group.key for group in groups] == [
            "shortcuts-group-general",
            "shortcuts-group-calendar",
            "shortcuts-group-navigation",
        ]
        texts = [text for group in groups for text in _texts(group)]
        assert afanes.i18n.ui.en.SHORTCUT_GROUP_LABELS["general"] in texts
        assert afanes.i18n.ui.en.SHORTCUT_GROUP_LABELS["calendar"] in texts
        assert afanes.i18n.ui.en.SHORTCUT_GROUP_LABELS["navigation"] in texts
        for label in afanes.i18n.ui.en.SHORTCUT_LABELS.values():
            assert label in texts

    def test_close_has_initial_focus_and_reports_the_request(self) -> None:
        closed: list[bool] = []
        sheet = afanes.ui.components.shortcuts.ShortcutSheet(lambda: closed.append(True))

        assert sheet.close_button.autofocus is True
        assert sheet.close_button.content == afanes.i18n.ui.en.CLOSE_ACTION
        typing.cast("typing.Callable[[object], None]", sheet.close_button.on_click)(None)

        assert closed == [True]

    def test_the_sheet_renders_the_active_language(self) -> None:
        copy = afanes.i18n.ui.UiCopy.for_locale(afanes.core.localization.LocaleTag.parse("es"))
        sheet = afanes.ui.components.shortcuts.ShortcutSheet(copy=copy)

        texts = _texts(sheet.build())

        assert "Atajos de teclado" in texts
        assert "Calendario" in texts
