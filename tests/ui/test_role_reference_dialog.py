"""Tests for the missing-role-name category dialog."""

import asyncio
from pathlib import Path

import flet as ft

import afanes.ui.components.role_reference
import afanes.ui.strings
from afanes.models.note import CategoryLabel
from tests.support import versioned


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


class TestRoleReferenceDialog:
    def _dialog(
        self,
        confirmed: list[CategoryLabel | None],
        cancelled: list[bool],
    ) -> afanes.ui.components.role_reference.RoleReferenceDialog:
        async def confirm(category: CategoryLabel | None) -> None:
            confirmed.append(category)

        async def cancel() -> None:
            cancelled.append(True)

        return afanes.ui.components.role_reference.RoleReferenceDialog(
            "Sam Rivera",
            [CategoryLabel("person"), CategoryLabel("place")],
            confirm,
            cancel,
        )

    def test_offers_existing_categories_and_no_category(self) -> None:
        dialog = self._dialog([], [])

        keys = [option.key for option in dialog.category_field.options]

        assert keys == ["", "person", "place"]
        assert dialog.category_field.value == "person"
        assert dialog.category_field.editable is True
        assert dialog.category_field.on_text_change == dialog.record_text
        assert dialog.category_field.on_select == dialog.record_selection
        assert afanes.ui.strings.PAGE_CATEGORY_INVALID not in dialog.error.value

    def test_person_is_the_default_even_when_not_supplied(self) -> None:
        async def confirm(_category: CategoryLabel | None) -> None:
            return None

        async def cancel() -> None:
            return None

        dialog = afanes.ui.components.role_reference.RoleReferenceDialog("Max Powers", [], confirm, cancel)

        assert dialog.category_field.value == "person"
        assert "person" in [option.key for option in dialog.category_field.options]

    def test_confirming_a_suggested_category_reports_it(self) -> None:
        confirmed: list[CategoryLabel | None] = []
        dialog = self._dialog(confirmed, [])
        dialog.category_field.value = "person"

        asyncio.run(dialog.submit())

        assert confirmed == [CategoryLabel("person")]

    def test_a_typed_category_is_accepted(self) -> None:
        confirmed: list[CategoryLabel | None] = []
        dialog = self._dialog(confirmed, [])
        dialog.category_field.value = "team"

        asyncio.run(dialog.submit())

        assert confirmed == [CategoryLabel("team")]

    def test_typed_text_wins_over_the_default_selection(self) -> None:
        confirmed: list[CategoryLabel | None] = []
        dialog = self._dialog(confirmed, [])
        dialog.record_text(ft.Event(name="text_change", control=ft.Dropdown(text="team")))

        asyncio.run(dialog.submit())

        assert confirmed == [CategoryLabel("team")]

    def test_a_selection_replaces_earlier_typed_text(self) -> None:
        confirmed: list[CategoryLabel | None] = []
        dialog = self._dialog(confirmed, [])
        dialog.record_text(ft.Event(name="text_change", control=ft.Dropdown(text="tea")))
        dialog.record_selection(ft.Event(name="select", control=ft.Dropdown(value="place")))

        asyncio.run(dialog.submit())

        assert confirmed == [CategoryLabel("place")]

    def test_a_blank_category_means_no_category(self) -> None:
        confirmed: list[CategoryLabel | None] = []
        dialog = self._dialog(confirmed, [])
        dialog.category_field.value = ""

        asyncio.run(dialog.submit())

        assert confirmed == [None]

    def test_an_invalid_category_stays_in_the_dialog(self) -> None:
        confirmed: list[CategoryLabel | None] = []
        dialog = self._dialog(confirmed, [])
        dialog.category_field.value = "../escape"

        asyncio.run(dialog.submit())

        assert confirmed == []
        assert dialog.error.visible is True
        assert dialog.error.value == afanes.ui.strings.PAGE_CATEGORY_INVALID

    def test_cancelling_writes_nothing(self) -> None:
        confirmed: list[CategoryLabel | None] = []
        cancelled: list[bool] = []
        dialog = self._dialog(confirmed, cancelled)

        asyncio.run(dialog.cancel())

        assert confirmed == []
        assert cancelled == [True]

    def test_cancelling_leaves_a_real_vault_unchanged(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        versioned(vault)
        before = _tree_state(vault)
        dialog = self._dialog([], [])

        asyncio.run(dialog.cancel())

        assert _tree_state(vault) == before

    def test_the_dialog_names_the_role(self) -> None:
        dialog = self._dialog([], [])

        body = dialog.dialog.content
        assert isinstance(body, ft.Column)
        assert afanes.ui.strings.ROLE_REFERENCE_BODY.format(name="Sam Rivera") in [
            control.value for control in body.controls if isinstance(control, ft.Text)
        ]
