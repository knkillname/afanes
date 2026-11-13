"""Tests for the shared atomic text writer."""

from pathlib import Path

import pytest

import afanes.core.atomic
from afanes.core.errors import VaultError

FAILING_FSYNC_CALL = 2


class TestAtomicWrite:
    def test_writes_utf8_text(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.atomic.AtomicWriter.write_text_atomic(path, "Ada\nLovelace\n")
        assert path.read_bytes() == b"Ada\nLovelace\n"

    def test_overwrites_an_existing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        path.write_text("old", encoding="utf-8")
        afanes.core.atomic.AtomicWriter.write_text_atomic(path, "new")
        assert path.read_text(encoding="utf-8") == "new"

    def test_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.atomic.AtomicWriter.write_text_atomic(path, "body")
        assert list(tmp_path.glob(".*.tmp")) == []

    def test_preserves_crlf_bytes(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        afanes.core.atomic.AtomicWriter.write_text_atomic(path, "one\r\ntwo\r\n")
        assert path.read_bytes() == b"one\r\ntwo\r\n"

    def test_rejects_a_missing_parent_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultError):
            afanes.core.atomic.AtomicWriter.write_text_atomic(tmp_path / "missing/note.md", "body")

    def test_cleans_up_after_replace_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "note.md"
        path.write_text("original", encoding="utf-8")

        def fail_replace(_source: object, _destination: object) -> None:
            message = "replace failed"
            raise OSError(message)

        monkeypatch.setattr(afanes.core.atomic.os, "replace", fail_replace)
        with pytest.raises(OSError, match="replace failed"):
            afanes.core.atomic.AtomicWriter.write_text_atomic(path, "replacement")
        assert path.read_text(encoding="utf-8") == "original"
        assert list(tmp_path.glob(".*.tmp")) == []


class TestExclusiveWrite:
    def test_writes_utf8_text(self, tmp_path: Path) -> None:
        path = tmp_path / "afanes.yaml"

        afanes.core.atomic.AtomicWriter.write_text_exclusive(path, "schema_version: 1\n")

        assert path.read_bytes() == b"schema_version: 1\n"

    def test_leaves_no_temporary_file(self, tmp_path: Path) -> None:
        path = tmp_path / "afanes.yaml"

        afanes.core.atomic.AtomicWriter.write_text_exclusive(path, "schema_version: 1\n")

        assert list(tmp_path.glob(".*.tmp")) == []

    def test_refuses_an_existing_file_and_keeps_it(self, tmp_path: Path) -> None:
        path = tmp_path / "afanes.yaml"
        path.write_text("original\n", encoding="utf-8")

        with pytest.raises(FileExistsError):
            afanes.core.atomic.AtomicWriter.write_text_exclusive(path, "replacement\n")

        assert path.read_text(encoding="utf-8") == "original\n"
        assert list(tmp_path.glob(".*.tmp")) == []

    def test_rejects_a_missing_parent_directory(self, tmp_path: Path) -> None:
        with pytest.raises(VaultError):
            afanes.core.atomic.AtomicWriter.write_text_exclusive(
                tmp_path / "missing/afanes.yaml", "schema_version: 1\n"
            )

    def test_cleans_up_after_a_failed_publish(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "afanes.yaml"
        original_fsync = afanes.core.atomic.os.fsync
        calls: list[int] = []

        def fail_second_fsync(descriptor: int) -> None:
            calls.append(descriptor)
            if len(calls) == FAILING_FSYNC_CALL:
                message = "publish failed"
                raise OSError(message)
            original_fsync(descriptor)

        def fail_link(_source: object, _destination: object) -> None:
            message = "links unavailable"
            raise OSError(message)

        monkeypatch.setattr(afanes.core.atomic.os, "fsync", fail_second_fsync)
        monkeypatch.setattr(afanes.core.atomic.os, "link", fail_link)
        with pytest.raises(OSError, match="publish failed"):
            afanes.core.atomic.AtomicWriter.write_text_exclusive(path, "schema_version: 1\n")

        assert not path.exists()
        assert list(tmp_path.glob(".*.tmp")) == []
