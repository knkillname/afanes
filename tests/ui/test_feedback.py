"""Tests for the transient notice and the owned persistent banners."""

import pytest

import afanes.ui.state
import afanes.ui.state.status
import afanes.ui.strings


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    afanes.ui.state.app_state.reset()


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


class TestOwnedBanners:
    def test_each_owner_keeps_its_own_banner(self) -> None:
        state = afanes.ui.state.app_state

        state.workspace.banner = afanes.ui.strings.VAULT_MISSING
        state.session.banner = afanes.ui.strings.REFRESH_FAILED.format(detail="disk full")
        state.pages.conflict = "changed"
        state.processing.banner = afanes.ui.strings.PROCESSING_REFRESH_FAILED.format(detail="disk full")

        assert state.workspace.banner == afanes.ui.strings.VAULT_MISSING
        assert state.session.banner == afanes.ui.strings.REFRESH_FAILED.format(detail="disk full")
        assert state.pages.banner == afanes.ui.strings.PAGE_CONFLICT_CHANGED
        assert state.processing.banner == afanes.ui.strings.PROCESSING_REFRESH_FAILED.format(detail="disk full")

    def test_clearing_one_owner_does_not_clear_another(self) -> None:
        state = afanes.ui.state.app_state
        state.workspace.banner = afanes.ui.strings.VAULT_MISSING
        state.session.banner = afanes.ui.strings.REFRESH_FAILED.format(detail="disk full")

        state.workspace.banner = None

        assert state.workspace.banner is None
        assert state.session.banner == afanes.ui.strings.REFRESH_FAILED.format(detail="disk full")

    def test_the_page_banner_prefers_its_conflict(self) -> None:
        state = afanes.ui.state.app_state
        state.pages.blocking_message = afanes.ui.strings.PAGE_PENDING_DIALOG
        state.pages.conflict = "missing"

        assert state.pages.banner == afanes.ui.strings.PAGE_CONFLICT_MISSING

        state.pages.conflict = None

        assert state.pages.banner == afanes.ui.strings.PAGE_PENDING_DIALOG
