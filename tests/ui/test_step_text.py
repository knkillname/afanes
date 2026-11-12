"""Tests for the shared read-only step text renderer."""

import asyncio
import typing

import flet as ft

import afanes.ui.components.step_text
import afanes.ui.theme


def _style() -> ft.TextStyle:
    return ft.TextStyle(size=13, color=afanes.ui.theme.TEXT_COLOR)


class TestStepTextRendering:
    def test_renders_github_flavored_markdown(self) -> None:
        control = afanes.ui.components.step_text.StepText("**Bold** [Ada](<note:Ada>)", _style()).build()

        assert isinstance(control, ft.Markdown)
        assert control.value == "**Bold** [Ada](<note:Ada>)"
        assert control.extension_set is ft.MarkdownExtensionSet.GITHUB_FLAVORED
        assert control.auto_follow_links is False

    def test_uses_compact_paragraph_spacing(self) -> None:
        control = afanes.ui.components.step_text.StepText("Call", _style()).build()

        style_sheet = control.md_style_sheet
        assert style_sheet is not None
        assert style_sheet.p_padding == 0
        assert style_sheet.block_spacing == 0

    def test_applies_the_surface_text_style(self) -> None:
        style = _style()
        control = afanes.ui.components.step_text.StepText("Call", style).build()

        style_sheet = control.md_style_sheet
        assert style_sheet is not None
        assert style_sheet.p_text_style == style
        assert style_sheet.a_text_style is not None
        assert style_sheet.a_text_style.color == style.color
        assert style_sheet.a_text_style.decoration is ft.TextDecoration.UNDERLINE

    def test_selection_is_opt_in(self) -> None:
        plain = afanes.ui.components.step_text.StepText("Call", _style()).build()
        selectable = afanes.ui.components.step_text.StepText("Call", _style(), selectable=True).build()

        assert plain.selectable is False
        assert selectable.selectable is True

    def test_expansion_is_configurable(self) -> None:
        plain = afanes.ui.components.step_text.StepText("Call", _style()).build()
        expanded = afanes.ui.components.step_text.StepText("Call", _style(), expand=True).build()

        assert plain.expand is False
        assert expanded.expand is True

    def test_key_is_forwarded(self) -> None:
        control = afanes.ui.components.step_text.StepText("Call", _style(), key="step-text").build()

        assert control.key == "step-text"


class TestStepTextLinks:
    def test_links_are_display_only_by_default(self) -> None:
        control = afanes.ui.components.step_text.StepText("[Ada](<note:Ada>)", _style()).build()

        assert control.on_tap_link is None

    def test_link_handler_receives_the_destination(self) -> None:
        followed: list[str] = []

        async def follow(event: ft.Event[ft.Markdown]) -> None:
            followed.append(str(event.data))

        control = afanes.ui.components.step_text.StepText(
            "[Ada](<note:Ada>)",
            _style(),
            on_tap_link=follow,
        ).build()
        assert control.on_tap_link is not None
        handler = typing.cast("typing.Any", control.on_tap_link)
        result = handler(ft.Event(name="tap", control=control, data="note:Ada"))

        asyncio.run(typing.cast("typing.Coroutine[typing.Any, typing.Any, None]", result))

        assert followed == ["note:Ada"]
