"""Tests for the collapsed Log date tree."""

import typing
from pathlib import Path

import flet as ft

import afanes.core.log
import afanes.core.vault.service
import afanes.ui.components.log_tree as log_tree_component


def _write_note(
    path: Path,
    *,
    date: str | None = None,
    body: str = "",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", "type: log"]
    if date is not None:
        lines.append(f"date: {date}")
    lines.extend(["---", "", body])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _timeline(root: Path) -> afanes.core.log.LogTimeline:
    return afanes.core.log.LogTimeline(afanes.core.vault.service.Vault(root).scan())


class TestLogTree:
    def test_builds_year_month_and_day_rows(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/2025.md", date="2025", body="# Year\n")
        _write_note(root / "log/2025/10/2025-10.md", date="2025-10", body="# Month\n")
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12", body="# Day\n")
        tree = log_tree_component.LogTree(lambda _path: None, lambda _y, _m: None, lambda _y: None)

        control = tree.build(_timeline(root))

        assert control.key == "log-tree"
        assert tree.year_tiles[2025].expanded is False
        assert (2025, 10) in tree.month_tiles
        assert (2025, 10, 12) in tree.day_tiles
        assert "month:2025-10" in tree.open_buttons
        assert "year:2025" in tree.open_buttons
        assert "log-undated" not in tree.open_buttons

    def test_undated_row_is_present(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/Undated.md", body="# No date\n")
        tree = log_tree_component.LogTree(lambda _path: None, lambda _y, _m: None, lambda _y: None)

        tree.build(_timeline(root))

        assert tree.undated_tile is not None
        assert tree.undated_tile.key == "log-undated"

    def test_empty_timeline_shows_the_empty_state(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        tree = log_tree_component.LogTree(lambda _path: None, lambda _y, _m: None, lambda _y: None)

        tree.build(_timeline(root))

        assert len(tree.root.controls) == 1
        first = tree.root.controls[0]
        assert isinstance(first, ft.Container)
        assert isinstance(first.content, ft.Text)
        assert first.content.value is not None

    def test_selected_day_expands_its_rows(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12", body="# Day\n")
        tree = log_tree_component.LogTree(
            lambda _path: None,
            lambda _y, _m: None,
            lambda _y: None,
            selected_day=(2025, 10, 12),
        )

        tree.build(_timeline(root))

        assert tree.year_tiles[2025].expanded is True
        assert tree.month_tiles[(2025, 10)].expanded is True
        assert tree.day_tiles[(2025, 10, 12)].expanded is True

    def test_month_plus_reports_the_month(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        _write_note(root / "log/2025/10/2025-10-12.md", date="2025-10-12", body="# Day\n")
        created: list[tuple[int, int]] = []
        tree = log_tree_component.LogTree(
            lambda _path: None,
            lambda year, month: created.append((year, month)),
            lambda _year: None,
        )
        tree.build(_timeline(root))
        handler = tree.plus_buttons["month:2025-10"].on_click
        assert handler is not None

        typing.cast("typing.Callable[[], None]", handler)()

        assert created == [(2025, 10)]

    def test_year_open_reports_the_entry(self, tmp_path: Path) -> None:
        root = tmp_path / "vault"
        note = _write_note(root / "log/2025/2025.md", date="2025", body="# Year\n")
        selected: list[Path] = []
        tree = log_tree_component.LogTree(
            selected.append,
            lambda _y, _m: None,
            lambda _y: None,
        )
        tree.build(_timeline(root))
        handler = tree.open_buttons["year:2025"].on_click
        assert handler is not None

        typing.cast("typing.Callable[[], None]", handler)()

        assert selected == [note]
