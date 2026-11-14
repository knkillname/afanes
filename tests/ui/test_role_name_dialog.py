"""Tests for the read-mode project role name dialog."""

import asyncio

import flet as ft

import afanes.i18n.ui
import afanes.i18n.ui.en
import afanes.ui.components.role_name


class TestRoleNameDialog:
    def _dialog(
        self,
        saved: list[str],
        cancelled: list[bool],
        *,
        current: str | None = "Sam Rivera",
    ) -> afanes.ui.components.role_name.RoleNameDialog:
        async def save(name: str) -> None:
            saved.append(name)

        async def cancel() -> None:
            cancelled.append(True)

        return afanes.ui.components.role_name.RoleNameDialog(
            afanes.i18n.ui.en.ROLE_NAME_OWNER_TITLE,
            current,
            ["Ada Lovelace", "Sam Rivera", "Priya Nair"],
            save,
            cancel,
        )

    def test_offers_names_and_the_current_value(self) -> None:
        dialog = self._dialog([], [])

        keys = [option.key for option in dialog.name_field.options]

        assert keys == ["Ada Lovelace", "Priya Nair", "Sam Rivera"]
        assert dialog.name_field.value == "Sam Rivera"
        assert dialog.name_field.editable is True
        assert dialog.name_field.on_text_change == dialog.record_text
        assert dialog.name_field.on_select == dialog.record_selection

    def test_typed_text_wins_over_the_empty_selection(self) -> None:
        saved: list[str] = []
        dialog = self._dialog(saved, [], current=None)
        dialog.record_text(ft.Event(name="text_change", control=ft.Dropdown(text="Min")))

        asyncio.run(dialog.save())

        assert saved == ["Min"]

    def test_a_selection_replaces_earlier_typed_text(self) -> None:
        saved: list[str] = []
        dialog = self._dialog(saved, [], current=None)
        dialog.record_text(ft.Event(name="text_change", control=ft.Dropdown(text="Mi")))
        dialog.record_selection(ft.Event(name="select", control=ft.Dropdown(value="Min")))

        asyncio.run(dialog.save())

        assert saved == ["Min"]

    def test_save_writes_the_trimmed_name(self) -> None:
        saved: list[str] = []
        dialog = self._dialog(saved, [])
        dialog.name_field.value = "  Grace Hopper  "

        asyncio.run(dialog.save())

        assert saved == ["Grace Hopper"]

    def test_a_new_typed_name_is_accepted(self) -> None:
        saved: list[str] = []
        dialog = self._dialog(saved, [], current=None)
        dialog.name_field.value = "New Person"

        asyncio.run(dialog.save())

        assert saved == ["New Person"]

    def test_clear_reports_an_empty_name(self) -> None:
        saved: list[str] = []
        dialog = self._dialog(saved, [])

        asyncio.run(dialog.clear())

        assert saved == [""]

    def test_cancel_writes_nothing(self) -> None:
        saved: list[str] = []
        cancelled: list[bool] = []
        dialog = self._dialog(saved, cancelled)

        asyncio.run(dialog.cancel())

        assert saved == []
        assert cancelled == [True]
