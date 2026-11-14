"""Tests for transient notices, the toast presenter, and owned banners."""

import asyncio
import typing

import flet as ft
import pytest

import afanes.i18n.ui
import afanes.i18n.ui.en
import afanes.ui.components.toast
import afanes.ui.state
import afanes.ui.state.status
import afanes.ui.theme
import afanes.ui.views.workspace


class FakeToastPage:
    def __init__(self) -> None:
        self.dialogs: list[ft.DialogControl] = []
        self.updates = 0
        self.pops = 0

    def show_dialog(self, dialog: ft.DialogControl) -> None:
        self.dialogs.append(dialog)

    def pop_dialog(self) -> ft.DialogControl | None:
        self.pops += 1
        return self.dialogs.pop() if self.dialogs else None

    def update(self) -> None:
        self.updates += 1


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


class TestToastPresenter:
    def test_show_builds_a_floating_themed_snackbar(self) -> None:
        page = FakeToastPage()
        presenter = afanes.ui.components.toast.ToastPresenter(typing.cast("ft.Page", page))

        presenter.show(
            afanes.ui.state.status.Notice(
                message="Moved to Trash",
                action=afanes.ui.state.status.NoticeAction.UNDO_TRASH,
            )
        )

        snackbar = presenter.current
        assert isinstance(snackbar, ft.SnackBar)
        assert snackbar.behavior is ft.SnackBarBehavior.FLOATING
        assert snackbar.show_close_icon is True
        assert snackbar.duration == afanes.ui.theme.TOAST_DURATION_MS
        assert snackbar.bgcolor == afanes.ui.theme.TOAST_SURFACE_COLOR
        assert snackbar.margin == afanes.ui.theme.TOAST_MARGIN
        assert snackbar.padding == afanes.ui.theme.TOAST_PADDING
        assert isinstance(snackbar.content, ft.Text)
        assert snackbar.content.color == afanes.ui.theme.TOAST_TEXT_COLOR
        action = snackbar.action
        assert isinstance(action, ft.SnackBarAction)
        assert action.label == afanes.i18n.ui.en.UNDO_ACTION
        assert action.text_color == afanes.ui.theme.TOAST_ACTION_COLOR
        assert page.dialogs == [snackbar]
        assert page.pops == 0

    def test_a_message_without_an_action_has_no_snackbar_action(self) -> None:
        page = FakeToastPage()
        presenter = afanes.ui.components.toast.ToastPresenter(typing.cast("ft.Page", page))

        presenter.show(afanes.ui.state.status.Notice(message="Page restored"))

        snackbar = presenter.current
        assert snackbar is not None
        assert snackbar.action is None

    def test_a_new_toast_replaces_the_previous_one_without_popping(self) -> None:
        page = FakeToastPage()
        presenter = afanes.ui.components.toast.ToastPresenter(typing.cast("ft.Page", page))

        presenter.show(afanes.ui.state.status.Notice(message="First"))
        first = presenter.current
        presenter.show(afanes.ui.state.status.Notice(message="Second"))
        second = presenter.current

        assert first is not None
        assert second is not None
        assert first.open is False
        assert presenter.current is second
        assert page.dialogs == [first, second]
        assert page.pops == 0

    def test_the_action_runs_the_registered_command(self) -> None:
        page = FakeToastPage()
        received: list[afanes.ui.state.status.NoticeAction] = []

        async def on_action(action: afanes.ui.state.status.NoticeAction) -> None:
            received.append(action)

        presenter = afanes.ui.components.toast.ToastPresenter(
            typing.cast("ft.Page", page),
            on_action=on_action,
        )
        presenter.show(
            afanes.ui.state.status.Notice(
                message="Moved to Trash",
                action=afanes.ui.state.status.NoticeAction.UNDO_TRASH,
            )
        )
        snackbar = presenter.current
        assert snackbar is not None
        action = snackbar.action
        assert isinstance(action, ft.SnackBarAction)
        assert action.on_click is not None

        asyncio.run(typing.cast("typing.Any", action.on_click)(ft.Event(name="click", control=action)))

        assert received == [afanes.ui.state.status.NoticeAction.UNDO_TRASH]
        assert presenter.current is None
        assert snackbar.open is False
        assert page.pops == 0

    def test_dismissal_forgets_the_current_toast(self) -> None:
        page = FakeToastPage()
        presenter = afanes.ui.components.toast.ToastPresenter(typing.cast("ft.Page", page))
        presenter.show(afanes.ui.state.status.Notice(message="Moved to Trash"))
        snackbar = presenter.current
        assert snackbar is not None
        assert snackbar.on_dismiss is not None

        typing.cast("typing.Any", snackbar.on_dismiss)()

        assert presenter.current is None

    def test_close_never_pops_the_dialog_stack(self) -> None:
        page = FakeToastPage()
        presenter = afanes.ui.components.toast.ToastPresenter(typing.cast("ft.Page", page))
        presenter.show(afanes.ui.state.status.Notice(message="Moved to Trash"))
        snackbar = presenter.current
        assert snackbar is not None

        presenter.close()

        assert snackbar.open is False
        assert presenter.current is None
        assert page.pops == 0


class TestNoticeLifecycle:
    def test_a_second_notice_replaces_the_first(self) -> None:
        status = afanes.ui.state.status.UiStatus()

        status.show_notice("First")
        status.show_notice("Second", action=afanes.ui.state.status.NoticeAction.UNDO_TRASH)

        assert status.notice == afanes.ui.state.status.Notice(
            message="Second",
            action=afanes.ui.state.status.NoticeAction.UNDO_TRASH,
        )

    def test_a_notice_is_consumed_once(self) -> None:
        status = afanes.ui.state.status.UiStatus()
        status.show_notice("Moved to Trash")

        notice = status.take_notice()

        assert notice is not None
        assert notice.message == "Moved to Trash"
        assert status.take_notice() is None

    def test_reset_discards_the_notice(self) -> None:
        status = afanes.ui.state.status.UiStatus()
        status.show_notice("Moved to Trash")

        status.reset()

        assert status.notice is None


class TestWorkspaceNotice:
    def test_the_workspace_consumes_one_notice_and_forwards_it(self) -> None:
        state = afanes.ui.state.app_state
        received: list[afanes.ui.state.status.Notice] = []

        async def noop() -> None:
            return None

        view = afanes.ui.views.workspace.WorkspaceView(
            afanes.ui.views.workspace.WorkspaceActions(
                update=lambda: None,
                on_change_vault=noop,
                on_create_vault=noop,
                on_close_vault=noop,
                on_notice=received.append,
            )
        )
        state.status.show_notice(
            "Moved to Trash",
            action=afanes.ui.state.status.NoticeAction.UNDO_TRASH,
        )

        view.refresh()

        assert received == [
            afanes.ui.state.status.Notice(
                message="Moved to Trash",
                action=afanes.ui.state.status.NoticeAction.UNDO_TRASH,
            )
        ]
        assert state.status.take_notice() is None


class TestOwnedBanners:
    def test_each_owner_keeps_its_own_banner(self) -> None:
        state = afanes.ui.state.app_state

        state.workspace.banner = afanes.i18n.ui.en.VAULT_MISSING
        state.session.banner = afanes.i18n.ui.en.REFRESH_FAILED.format(detail="disk full")
        state.pages.conflict = "changed"
        state.processing.banner = afanes.i18n.ui.en.PROCESSING_REFRESH_FAILED.format(detail="disk full")

        assert state.workspace.banner == afanes.i18n.ui.en.VAULT_MISSING
        assert state.session.banner == afanes.i18n.ui.en.REFRESH_FAILED.format(detail="disk full")
        assert state.pages.banner == afanes.i18n.ui.en.PAGE_CONFLICT_CHANGED
        assert state.processing.banner == afanes.i18n.ui.en.PROCESSING_REFRESH_FAILED.format(detail="disk full")

    def test_clearing_one_owner_does_not_clear_another(self) -> None:
        state = afanes.ui.state.app_state
        state.workspace.banner = afanes.i18n.ui.en.VAULT_MISSING
        state.session.banner = afanes.i18n.ui.en.REFRESH_FAILED.format(detail="disk full")

        state.workspace.banner = None

        assert state.workspace.banner is None
        assert state.session.banner == afanes.i18n.ui.en.REFRESH_FAILED.format(detail="disk full")

    def test_the_page_banner_prefers_its_conflict(self) -> None:
        state = afanes.ui.state.app_state
        state.pages.blocking_message = afanes.i18n.ui.en.PAGE_PENDING_DIALOG
        state.pages.conflict = "missing"

        assert state.pages.banner == afanes.i18n.ui.en.PAGE_CONFLICT_MISSING

        state.pages.conflict = None

        assert state.pages.banner == afanes.i18n.ui.en.PAGE_PENDING_DIALOG
