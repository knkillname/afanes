"""Tests for the shared atomic text writer."""

from pathlib import Path

import pytest

import afanes.core.atomic
from afanes.core.errors import VaultError


class TestAtomicWrite:
    def test_writes_utf8_text(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.atomic.write_text_atomic(path, "Ada\nLovelace\n")
        assert path.read_bytes() == b"Ada\nLovelace\n"

    def test_overwrites_an_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        path.write_text("old", encoding="utf-8")
        afanes.core.atomic.write_text_atomic(path, "new")
        assert path.read_text(encoding="utf-8") == "new"

    def test_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.atomic.write_text_atomic(path, "body")
        assert list(tmp_path.glob(".*.tmp")) == []

    def test_preserves_crlf_bytes(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.atomic.write_text_atomic(path, "one\r\ntwo\r\n")
        assert path.read_bytes() == b"one\r\ntwo\r\n"

    def test_rejects_a_missing_parent_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultError):
            afanes.core.atomic.write_text_atomic(tmp_path / "missing/note.md", "body")

    def test_cleans_up_after_replace_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "note.md"
        path.write_text("original", encoding="utf-8")

        def fail_replace(_source: object, _destination: object) -> None:
            message = "replace failed"
            raise OSError(message)

        monkeypatch.setattr(afanes.core.atomic.os, "replace", fail_replace)
        with pytest.raises(OSError, match="replace failed"):
            afanes.core.atomic.write_text_atomic(path, "replacement")
        assert path.read_text(encoding="utf-8") == "original"
        assert list(tmp_path.glob(".*.tmp")) == []
