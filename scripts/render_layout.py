# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Capture and check the rendered 100%/200% text layout snapshot.

The harness launches the real Flet desktop client with a temporary fixture
vault. It records keyed control geometry for every primary view, compares the
two text scales, and checks the result against the committed Linux snapshot.
Screenshots are not part of the gate.
"""

import argparse
import asyncio
import contextlib
import dataclasses
import datetime
import json
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import flet as ft

import afanes.core.localization
import afanes.core.vault.schema
import afanes.i18n.ui
import afanes.ui.app
import afanes.ui.components.date_entry
import afanes.ui.components.frozen
import afanes.ui.components.shortcuts
import afanes.ui.state
import afanes.ui.state.browser
import afanes.ui.state.session
import afanes.ui.theme
import afanes.ui.views.workspace
import tests.render.layout_snapshot
from afanes.models.note import DatePrecision

SNAPSHOT_PATH = ROOT / "tests" / "render" / "snapshots" / "linux.json"
REPORT_PATH = Path(tempfile.gettempdir()) / "afanes-render-layout.json"
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 600
SETTLE_ROUNDS = 4
SETTLE_SECONDS = 0.15
TEXT_SCALE = 2.0
SCHEMA_VERSION = 1
PLATFORM = "linux"
TEXT_CONTROLS = (
    ft.Text,
    ft.TextButton,
    ft.FilledButton,
    ft.OutlinedButton,
    ft.TextField,
    ft.ListTile,
    ft.Dropdown,
    ft.Checkbox,
)
_CHILD_ATTRIBUTES = (
    "controls",
    "content",
    "leading",
    "title",
    "subtitle",
    "trailing",
    "actions",
    "items",
    "suffix",
    "prefix",
)


class LayoutRenderer:
    """Drive the rendered tour and collect one report for both text scales."""

    def __init__(self, *, update: bool) -> None:
        self._update = update
        self._page: ft.Page | None = None
        self._shell: afanes.ui.app.AppShell | None = None
        self._workspace: afanes.ui.views.workspace.WorkspaceView | None = None
        self._copy = afanes.i18n.ui.UiCopy.for_locale(afanes.core.localization.LocaleTag.parse("en"))
        self._views: dict[str, dict[str, dict[str, object]]] = {"100": {}, "200": {}}
        self._current: dict[str, dict[str, float]] = {}
        self._text_keys: set[str] = set()
        self._token = 0
        self._probe_controls: list[ft.Control] = []
        self._vault = Path()
        self._failure = Path()
        self.report: dict[str, object] = {}
        self.issues: list[str] = []

    async def render(self, page: ft.Page) -> None:
        """Run the whole capture and close the window."""
        try:
            await self._render(page)
        except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            self.issues.append(f"rendered layout failed: {exc}")
            with contextlib.suppress(RuntimeError):
                await page.window.close()

    async def _render(self, page: ft.Page) -> None:
        """Build the fixture, run both tours, and write the report."""
        self._page = page
        page.window.width = WINDOW_WIDTH
        page.window.height = WINDOW_HEIGHT
        afanes.ui.state.app_state.status.set_copy(self._copy)
        afanes.ui.state.session.REFRESH_SECONDS = 3600.0
        with tempfile.TemporaryDirectory(prefix="afanes-render-") as temporary:
            self._vault = Path(temporary) / "vault"
            self._write_fixture(self._vault)
            self._shell = afanes.ui.app.AppShell(page, self._vault)
            await self._shell.start()
            self._workspace = self._shell.workspace
            if self._workspace is None:
                self.issues.append("the workspace did not render")
                await page.window.close()
                return
            page.update()
            self._workspace.resize(WINDOW_WIDTH)
            await self._tour("100")
            self._apply_text_scale(TEXT_SCALE)
            await self._tour("200")
            self._combine_views()
            self._evaluate()
            REPORT_PATH.write_text(
                json.dumps(self.report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            self._shell.release_session()
            await page.window.close()

    def _write_fixture(self, root: Path) -> None:
        """Write the temporary vault used by every captured view."""
        (root / "inbox").mkdir(parents=True)
        (root / "projects").mkdir()
        (root / "reference").mkdir()
        (root / "notes").mkdir()
        (root / "trash").mkdir()
        (root / "afanes.yaml").write_text(
            f"schema_version: {afanes.core.vault.schema.CURRENT_SCHEMA_VERSION}\n",
            encoding="utf-8",
        )
        (root / "inbox" / "Capture.md").write_text("---\ntype: note\n---\n\n# Capture\n", encoding="utf-8")
        (root / "projects" / "Launch.md").write_text(
            "---\ntype: project\nstatus: active\n---\n\n# Launch\n\n- [ ] Draft plan\n- [ ] Review plan\n",
            encoding="utf-8",
        )
        (root / "reference" / "Ada.md").write_text(
            "---\ntype: reference\ncategory: person\n---\n\n# Ada\n\nMathematician\n",
            encoding="utf-8",
        )
        (root / "notes" / "Misplaced.md").write_text("---\ntype: note\n---\n\n# Misplaced\n", encoding="utf-8")
        (root / "trash" / "Old.md").write_text(
            "---\ntype: note\ntrashed_from: notes/Old.md\ntrashed_on: 2026-11-10\n---\n\n# Old\n",
            encoding="utf-8",
        )
        self._failure = root / "reference" / "Broken.md"
        self._failure.write_text("---\ntype: refrence\n---\n\n# Broken\n", encoding="utf-8")
        log_path = root / "log" / "2026" / "11" / "2026-11-15.md"
        log_path.parent.mkdir(parents=True)
        log_path.write_text("---\ntype: log\ndate: 2026-11-15\n---\n\n# November 15, 2026\n", encoding="utf-8")

    async def _tour(self, scale: str) -> None:
        """Capture every primary view at one text scale."""
        await self._reset_flow()
        await self._plain_view(scale, "inbox", afanes.ui.state.browser.WorkspaceSection.INBOX)
        await self._plain_view(scale, "projects", afanes.ui.state.browser.WorkspaceSection.PROJECTS)
        await self._plain_view(scale, "references", afanes.ui.state.browser.WorkspaceSection.REFERENCES)
        await self._log_view(scale)
        await self._plain_view(
            scale,
            "needs-attention",
            afanes.ui.state.browser.WorkspaceSection.NEEDS_ATTENTION,
        )
        await self._plain_view(scale, "trash", afanes.ui.state.browser.WorkspaceSection.TRASH)
        await self._review_view(scale)
        await self._page_view(scale, "page-read", edit=False)
        await self._page_view(scale, "page-edit", edit=True)
        await self._raw_view(scale)
        await self._processing_view(scale)
        await self._shortcut_dialog(scale)
        await self._date_dialog(scale)

    async def _reset_flow(self) -> None:
        state = afanes.ui.state.app_state
        if state.review.review_session is not None:
            await state.review.finish()
        state.processing.clear()
        state.pages.clear()
        state.dialogs.clear()
        await state.browser.set_section(afanes.ui.state.browser.WorkspaceSection.INBOX)

    async def _plain_view(
        self,
        scale: str,
        name: str,
        section: afanes.ui.state.browser.WorkspaceSection,
    ) -> None:
        """Capture one destination without a focused flow."""
        await afanes.ui.state.app_state.browser.set_section(section)
        await self._record(scale, name, ["browser-list"])

    async def _log_view(self, scale: str) -> None:
        """Capture the Log calendar with a fixed month."""
        state = afanes.ui.state.app_state
        await state.browser.set_section(afanes.ui.state.browser.WorkspaceSection.LOG)
        state.browser.show_log_month(2026, 11)
        await self._record(scale, "log", ["log-calendar", "log-calendar-grid"])

    async def _review_view(self, scale: str) -> None:
        """Capture the review queue and its focused card."""
        state = afanes.ui.state.app_state
        await state.review.start()
        await state.browser.set_section(afanes.ui.state.browser.WorkspaceSection.REVIEW)
        await self._record(scale, "review", ["review-queue-0"])

    async def _page_view(self, scale: str, name: str, *, edit: bool) -> None:
        """Capture the read or edit state of one note page."""
        state = afanes.ui.state.app_state
        await self._reset_flow()
        await state.navigation.open_page(self._vault / "reference" / "Ada.md")
        if edit:
            state.pages.edit_page()
            await self._record(scale, name, ["page-toolbar", "page-edit-form"])
            return
        await self._record(scale, name, ["page-toolbar", "page-mode-host"])

    async def _raw_view(self, scale: str) -> None:
        """Capture the raw rescue state for an unreadable note."""
        state = afanes.ui.state.app_state
        await self._reset_flow()
        await state.navigation.open_failure(self._failure)
        await self._record(scale, "page-raw", ["page-toolbar", "page-raw-panel"])

    async def _processing_view(self, scale: str) -> None:
        """Capture the Processing Wizard for the inbox capture."""
        state = afanes.ui.state.app_state
        opened = await state.processing.begin(self._vault / "inbox" / "Capture.md")
        if not opened:
            message = "the Processing Wizard did not open"
            raise RuntimeError(message)
        await self._record(scale, "processing", ["processing-view"])

    async def _shortcut_dialog(self, scale: str) -> None:
        """Capture the shortcut sheet."""
        page = self._require_page()
        sheet = afanes.ui.components.shortcuts.ShortcutSheet(copy=self._copy)
        afanes.ui.components.frozen.FrozenControlRecovery.clear(sheet.dialog.content)
        token = self._next_token()
        self._attach(sheet.dialog.title, token)
        self._attach(sheet.dialog.content, token)
        self._attach(sheet.dialog.actions, token)
        page.show_dialog(sheet.dialog)
        page.update()
        await self._force_measure()
        await self._settle()
        self._store_dialog(scale, "shortcuts-dialog", ["shortcuts-close", "shortcuts-group-general"])
        page.pop_dialog()
        page.update()

    async def _date_dialog(self, scale: str) -> None:
        """Capture the day-only date picker."""
        page = self._require_page()

        async def confirm(_value: object) -> None:
            return None

        async def cancel() -> None:
            return None

        dialog = afanes.ui.components.date_entry.DatePickerDialog(
            None,
            frozenset({DatePrecision.DAY}),
            confirm,
            cancel,
            copy=self._copy,
            today=datetime.date(2026, 11, 15),
            update=page.update,
        )
        afanes.ui.components.frozen.FrozenControlRecovery.clear(dialog.dialog.content)
        token = self._next_token()
        self._attach(dialog.dialog.content, token)
        self._attach(dialog.dialog.actions, token)
        page.show_dialog(dialog.dialog)
        page.update()
        await self._force_measure()
        await self._settle()
        self._store_dialog(scale, "date-dialog", ["date-picker-body", "date-picker-grid-host"])
        page.pop_dialog()
        page.update()

    async def _record(self, scale: str, name: str, markers: list[str]) -> None:
        """Capture the current workspace tree."""
        workspace = self._fresh_workspace()
        self._workspace = workspace
        afanes.ui.components.frozen.FrozenControlRecovery.clear(workspace.root)
        token = self._next_token()
        self._attach(workspace.root, token)
        page = self._require_page()
        page.controls.clear()
        page.add(workspace.build())
        page.update()
        await self._force_measure()
        await self._settle()
        self._store(scale, name, markers, self._current, self._text_keys)

    def _store_dialog(self, scale: str, name: str, markers: list[str]) -> None:
        self._store(scale, name, markers, self._current, self._text_keys)

    def _store(
        self,
        scale: str,
        name: str,
        markers: list[str],
        controls: dict[str, dict[str, float]],
        text_keys: set[str],
    ) -> None:
        self._views[scale][name] = {
            "markers": markers,
            "controls": dict(controls),
            "text_keys": sorted(text_keys),
        }

    def _next_token(self) -> int:
        self._token += 1
        self._current = {}
        self._text_keys = set()
        self._probe_controls = []
        return self._token

    def _attach(self, control: ft.Control | Iterable[ft.Control] | None, token: int) -> None:
        """Attach a geometry recorder to every keyed control."""
        if control is None:
            return
        if isinstance(control, Iterable) and not isinstance(control, ft.Control):
            for item in control:
                self._attach(item, token)
            return
        if not isinstance(control, ft.Control):
            return
        key = control.key
        if key:
            self._probe_controls.append(control)
            self._attach_size(control, str(key), token)
        for attribute in _CHILD_ATTRIBUTES:
            child = getattr(control, attribute, None)
            if isinstance(child, ft.Control | list):
                self._attach(child, token)

    def _attach_size(self, control: ft.Control, key: str, token: int) -> None:
        if not isinstance(control, ft.LayoutControl):
            return
        if getattr(control, "on_size_change", None) is not None:
            return

        def handle(event: ft.LayoutSizeChangeEvent[ft.LayoutControl]) -> None:
            if token != self._token:
                return
            self._current[key] = {
                "width": tests.render.layout_snapshot.rounded(event.width),
                "height": tests.render.layout_snapshot.rounded(event.height),
            }
            if isinstance(control, TEXT_CONTROLS):
                self._text_keys.add(key)

        control.on_size_change = handle

    async def _force_measure(self) -> None:
        """Force one dimension change so the client reports the first geometry."""
        page = self._require_page()
        for probe in self._probe_controls:
            afanes.ui.components.frozen.FrozenControlRecovery.clear(probe)
        saved: list[tuple[ft.LayoutControl, object, object]] = [
            (control, control.width, control.height)
            for control in self._probe_controls
            if isinstance(control, ft.LayoutControl)
        ]
        for attribute in ("width", "height"):
            for control, _width, _height in saved:
                setattr(control, attribute, (getattr(control, attribute) or 0) + 1)
            page.update()
            await asyncio.sleep(SETTLE_SECONDS)
            for control, width, height in saved:
                afanes.ui.components.frozen.FrozenControlRecovery.clear(control)
                control.width = width
                control.height = height
            page.update()
            await asyncio.sleep(SETTLE_SECONDS)
        if self._workspace is not None:
            self._workspace.resize(WINDOW_WIDTH + 40)
            await asyncio.sleep(SETTLE_SECONDS)
            self._workspace.resize(WINDOW_WIDTH)
            await asyncio.sleep(SETTLE_SECONDS)

    async def _settle(self) -> None:
        """Give the client time to lay out, measure, and report each control."""
        page = self._require_page()
        for _ in range(SETTLE_ROUNDS):
            page.update()
            await asyncio.sleep(SETTLE_SECONDS)

    def _fresh_workspace(self) -> afanes.ui.views.workspace.WorkspaceView:
        shell = self._require_shell()
        actions = afanes.ui.views.workspace.WorkspaceActions(
            shell.page.update,
            shell.choose_vault,
            shell.create_vault,
            shell.close_vault,
            on_new_reference=shell.show_new_reference_dialog,
            pick_date=shell.pick_date,
            pick_note_date=shell.pick_note_date,
            on_log_entry=shell.open_log_date,
            on_missing_role=shell.show_role_reference_dialog,
            pick_role=shell.pick_role,
            on_about=shell.show_about_dialog,
            on_shortcuts=shell.show_shortcuts,
            on_notice=shell.toast.show,
        )
        workspace = afanes.ui.views.workspace.WorkspaceView(actions)
        workspace.resize(WINDOW_WIDTH)
        return workspace

    def _apply_text_scale(self, scale: float) -> None:
        """Patch the module text styles and page theme for the test scale."""
        page = self._require_page()
        roles = {name: self._scaled_style(style, scale) for name, style in afanes.ui.theme.TEXT_ROLES.items()}
        afanes.ui.theme.TEXT_ROLES = MappingProxyType(roles)
        afanes.ui.theme.CALENDAR_TODAY_TEXT = self._scaled_style(afanes.ui.theme.CALENDAR_TODAY_TEXT, scale)
        afanes.ui.theme.ROLE_LINK_TEXT_STYLE = self._scaled_style(afanes.ui.theme.ROLE_LINK_TEXT_STYLE, scale)
        afanes.ui.theme.ROLE_BROKEN_TEXT_STYLE = self._scaled_style(afanes.ui.theme.ROLE_BROKEN_TEXT_STYLE, scale)
        text_theme = ft.TextTheme(
            display_large=roles["title-1"],
            display_medium=roles["title-1"],
            display_small=roles["title-2"],
            headline_large=roles["title-1"],
            headline_medium=roles["title-1"],
            headline_small=roles["title-2"],
            title_large=roles["title-3"],
            title_medium=roles["title-4"],
            title_small=roles["heading"],
            body_large=roles["body"],
            body_medium=roles["body"],
            body_small=roles["caption"],
            label_large=roles["heading"],
            label_medium=roles["caption-heading"],
            label_small=roles["caption"],
        )
        page.theme = dataclasses.replace(afanes.ui.theme.LIGHT_THEME, text_theme=text_theme)
        page.dark_theme = dataclasses.replace(afanes.ui.theme.DARK_THEME, text_theme=text_theme)
        page.update()

    @staticmethod
    def _scaled_style(style: ft.TextStyle, scale: float) -> ft.TextStyle:
        if style.size is None:
            return style
        return dataclasses.replace(style, size=style.size * scale)

    def _require_page(self) -> ft.Page:
        if self._page is None:
            message = "the page is not ready"
            raise RuntimeError(message)
        return self._page

    def _require_shell(self) -> afanes.ui.app.AppShell:
        if self._shell is None:
            message = "the shell is not ready"
            raise RuntimeError(message)
        return self._shell

    def _require_workspace(self) -> afanes.ui.views.workspace.WorkspaceView:
        if self._workspace is None:
            message = "the workspace is not ready"
            raise RuntimeError(message)
        return self._workspace

    def _combine_views(self) -> None:
        views: dict[str, dict[str, object]] = {}
        for name, low in self._views["100"].items():
            high = self._views["200"].get(name)
            if high is None:
                self.issues.append(f"{name}: missing 200% capture")
                continue
            views[name] = {
                "markers": low["markers"],
                "low": low["controls"],
                "high": high["controls"],
                "text_keys": sorted(set(low["text_keys"]) | set(high["text_keys"])),
            }
        self.report = {
            "schema": SCHEMA_VERSION,
            "platform": PLATFORM,
            "window": {"width": WINDOW_WIDTH, "height": WINDOW_HEIGHT},
            "views": views,
        }

    def _evaluate(self) -> None:
        self.issues.extend(tests.render.layout_snapshot.capture_violations(self.report))
        self.issues.extend(tests.render.layout_snapshot.growth_violations(self.report))
        if self._update:
            if not self.issues:
                SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
                SNAPSHOT_PATH.write_text(
                    json.dumps(self.report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
            return
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        self.issues.extend(tests.render.layout_snapshot.snapshot_violations(self.report, snapshot))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Return the check or update mode."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="compare with the committed snapshot")
    group.add_argument("--update", action="store_true", help="rewrite the committed snapshot")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Launch the desktop client, capture the layout, and report the result."""
    arguments = parse_args(argv)
    renderer = LayoutRenderer(update=arguments.update)
    ft.run(renderer.render, assets_dir=None)
    if not renderer.report and not renderer.issues:
        renderer.issues.append("the rendered tour produced no report")
    if renderer.issues:
        for issue in renderer.issues:
            sys.stdout.write(f"{issue}\n")
        raise SystemExit(1)
    sys.stdout.write(f"layout report: {REPORT_PATH}\n")
    if arguments.update:
        sys.stdout.write(f"snapshot updated: {SNAPSHOT_PATH}\n")
    else:
        sys.stdout.write(f"snapshot matched: {SNAPSHOT_PATH}\n")


if __name__ == "__main__":
    main()
