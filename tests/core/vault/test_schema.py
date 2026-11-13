"""Tests for the vault settings file, its schema, and safe parsing."""

import os
from pathlib import Path

import pytest

import afanes.core.vault.schema
from afanes.core.errors import (
    VaultMissingError,
    VaultNotDirectoryError,
    VaultSchemaInvalidError,
    VaultSchemaMissingError,
    VaultSchemaNotAdoptableError,
    VaultSchemaUnsupportedError,
)
from tests.support import constant


def _write_settings(root: Path, text: str) -> Path:
    path = root / afanes.core.vault.schema.SCHEMA_FILENAME
    path.write_text(text, encoding="utf-8", newline="")
    return path


def _store(root: Path) -> afanes.core.vault.schema.VaultSchemaStore:
    return afanes.core.vault.schema.VaultSchemaStore(root)


class TestVaultSchemaFile:
    def test_accepts_the_current_schema(self, tmp_path: Path) -> None:
        _write_settings(tmp_path, "schema_version: 1\n")

        schema = _store(tmp_path).require()

        assert schema.version == afanes.core.vault.schema.CURRENT_SCHEMA_VERSION

    def test_accepts_a_comment_and_a_bom(self, tmp_path: Path) -> None:
        _write_settings(tmp_path, "\ufeff# Afanes vault\nschema_version: 1\n")

        assert _store(tmp_path).require().version == 1

    def test_a_case_variant_is_not_the_settings_file(self, tmp_path: Path) -> None:
        (tmp_path / "Afanes.yaml").write_text("schema_version: 1\n", encoding="utf-8")

        with pytest.raises(VaultSchemaMissingError):
            _store(tmp_path).require()

    def test_a_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert _store(tmp_path).load() is None

    def test_a_missing_file_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(VaultSchemaMissingError, match=r"afanes\.yaml"):
            _store(tmp_path).require()

    def test_the_settings_path_is_exact(self, tmp_path: Path) -> None:
        assert _store(tmp_path).settings_path == tmp_path / "afanes.yaml"


class TestVaultSchemaValidation:
    @pytest.mark.parametrize(
        "text",
        [
            "schema_version: 1\nother: true\n",
            "other: 1\n",
            "schema_version:\n",
            "schema_version: one\n",
            "schema_version: true\n",
            "schema_version: 1.0\n",
            "schema_version: '1'\n",
            "schema_version: 1\nschema_version: 1\n",
            "schema_version: 1\nschema_version: 2\n",
        ],
    )
    def test_rejects_a_file_that_does_not_match_the_shape(self, tmp_path: Path, text: str) -> None:
        _write_settings(tmp_path, text)

        with pytest.raises(VaultSchemaInvalidError):
            _store(tmp_path).load()

    @pytest.mark.parametrize(
        "text",
        [
            "schema_version: [unclosed\n",
            "- 1\n",
            "schema_version: 1\n---\nschema_version: 1\n",
            "",
        ],
    )
    def test_rejects_malformed_yaml_or_a_non_mapping(self, tmp_path: Path, text: str) -> None:
        _write_settings(tmp_path, text)

        with pytest.raises(VaultSchemaInvalidError):
            _store(tmp_path).load()

    def test_rejects_invalid_utf8(self, tmp_path: Path) -> None:
        (tmp_path / "afanes.yaml").write_bytes(b"\xff\xfe")

        with pytest.raises(VaultSchemaInvalidError, match="UTF-8"):
            _store(tmp_path).load()

    def test_rejects_an_oversized_file(self, tmp_path: Path) -> None:
        text = "schema_version: 1\n" + "#" * afanes.core.vault.schema.SCHEMA_MAX_BYTES
        _write_settings(tmp_path, text)

        with pytest.raises(VaultSchemaInvalidError, match="too large"):
            _store(tmp_path).load()

    def test_a_newer_schema_is_unsupported(self, tmp_path: Path) -> None:
        _write_settings(tmp_path, "schema_version: 2\n")

        with pytest.raises(VaultSchemaUnsupportedError, match="update Afanes"):
            _store(tmp_path).load()

    def test_an_older_schema_is_unsupported_before_one_point_zero(self, tmp_path: Path) -> None:
        _write_settings(tmp_path, "schema_version: 0\n")

        with pytest.raises(VaultSchemaUnsupportedError, match="does not migrate"):
            _store(tmp_path).load()

    def test_rejects_a_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "elsewhere.yaml"
        target.write_text("schema_version: 1\n", encoding="utf-8")
        link = tmp_path / "afanes.yaml"
        try:
            link.symlink_to(target)
        except OSError:
            pytest.skip("symlinks are unavailable on this platform")

        with pytest.raises(VaultSchemaInvalidError, match="symbolic link"):
            _store(tmp_path).load()

    def test_rejects_a_directory(self, tmp_path: Path) -> None:
        (tmp_path / "afanes.yaml").mkdir()

        with pytest.raises(VaultSchemaInvalidError, match="not a regular file"):
            _store(tmp_path).load()

    def test_rejects_an_unreadable_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_settings(tmp_path, "schema_version: 1\n")

        def fail_read(_path: Path) -> bytes:
            message = "permission denied"
            raise PermissionError(message)

        monkeypatch.setattr(Path, "read_bytes", fail_read)
        with pytest.raises(VaultSchemaInvalidError, match="Could not read"):
            _store(tmp_path).load()

    @pytest.mark.parametrize(
        "text",
        [
            "schema_version: 2\n",
            "schema_version: 1\nextra: true\n",
            "schema_version: one\n",
            "schema_version: [unclosed\n",
            "schema_version: 1\nschema_version: 1\n",
        ],
    )
    def test_invalid_files_are_preserved_byte_for_byte(self, tmp_path: Path, text: str) -> None:
        path = _write_settings(tmp_path, text)
        before = path.read_bytes()

        with pytest.raises((VaultSchemaInvalidError, VaultSchemaUnsupportedError)):
            _store(tmp_path).load()

        assert path.read_bytes() == before

    def test_reading_does_not_create_a_file(self, tmp_path: Path) -> None:
        with pytest.raises(VaultSchemaMissingError):
            _store(tmp_path).require()

        assert list(tmp_path.iterdir()) == []

    def test_the_root_must_exist(self, tmp_path: Path) -> None:
        with pytest.raises(VaultMissingError):
            _store(tmp_path / "missing")

    def test_the_root_must_be_a_directory(self, tmp_path: Path) -> None:
        file_path = tmp_path / "vault"
        file_path.write_text("body", encoding="utf-8")

        with pytest.raises(VaultNotDirectoryError):
            _store(file_path)

    def test_the_stored_root_is_absolute(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = tmp_path / "vault"
        root.mkdir()
        monkeypatch.chdir(tmp_path)

        assert _store(Path("vault")).root == root.resolve()

    def test_an_os_error_while_inspecting_is_invalid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        def fail_lstat(_path: Path) -> os.stat_result:
            message = "permission denied"
            raise PermissionError(message)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
        with pytest.raises(VaultSchemaInvalidError, match="Could not inspect"):
            _store(tmp_path).load()


def _make_adoptable(root: Path, *, templates: bool = False) -> None:
    for folder in afanes.core.vault.schema.DEFAULT_FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    if templates:
        (root / "templates").mkdir()


def _tree_state(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


class TestAdoptionEligibility:
    def test_all_default_folders_enable_adoption(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)

        assert _store(tmp_path).is_adoptable() is True

    def test_a_missing_default_folder_prevents_adoption(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        (tmp_path / "log").rmdir()

        assert _store(tmp_path).is_adoptable() is False

    def test_the_templates_folder_is_optional(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path, templates=False)

        assert _store(tmp_path).is_adoptable() is True

    def test_folder_names_are_matched_case_insensitively(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        (tmp_path / "inbox").rename(tmp_path / "Inbox")

        assert _store(tmp_path).is_adoptable() is True

    def test_extra_folders_are_allowed(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        (tmp_path / "work").mkdir()

        assert _store(tmp_path).is_adoptable() is True

    def test_a_versioned_folder_is_not_adoptable(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        _write_settings(tmp_path, "schema_version: 1\n")

        assert _store(tmp_path).is_adoptable() is False

    def test_an_invalid_settings_file_is_not_adoptable(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        _write_settings(tmp_path, "schema_version: 2\n")

        assert _store(tmp_path).is_adoptable() is False

    def test_an_unwritable_folder_is_not_adoptable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _make_adoptable(tmp_path)
        monkeypatch.setattr(afanes.core.vault.schema.os, "access", constant(False))

        assert _store(tmp_path).is_adoptable() is False

    def test_an_unwritable_folder_cannot_be_adopted(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _make_adoptable(tmp_path)
        monkeypatch.setattr(afanes.core.vault.schema.os, "access", constant(False))

        with pytest.raises(VaultSchemaNotAdoptableError, match="not writable"):
            _store(tmp_path).adopt()

        assert not (tmp_path / "afanes.yaml").exists()


class TestAdoptionWrite:
    def test_adoption_writes_only_the_settings_file(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        before = _tree_state(tmp_path)
        before_entries = sorted(path.name for path in tmp_path.iterdir())

        adoption = _store(tmp_path).adopt()

        assert adoption.created is True
        assert adoption.root == tmp_path.resolve()
        assert adoption.schema.version == 1
        assert (tmp_path / "afanes.yaml").read_text(encoding="utf-8") == "schema_version: 1\n"
        assert _tree_state(tmp_path) == {**before, "afanes.yaml": b"schema_version: 1\n"}
        assert sorted(path.name for path in tmp_path.iterdir()) == sorted([*before_entries, "afanes.yaml"])

    def test_an_adopted_folder_has_a_valid_schema(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)

        _store(tmp_path).adopt()

        assert _store(tmp_path).require().version == 1

    def test_an_already_versioned_folder_is_reused_unchanged(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        path = _write_settings(tmp_path, "schema_version: 1\n")
        before = path.read_bytes()

        adoption = _store(tmp_path).adopt()

        assert adoption.created is False
        assert adoption.schema.version == 1
        assert path.read_bytes() == before

    def test_an_already_versioned_folder_with_a_different_case_is_not_adopted_again(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        (tmp_path / "Afanes.yaml").write_text("schema_version: 1\n", encoding="utf-8")

        adoption = _store(tmp_path).adopt()

        assert adoption.created is True
        assert (tmp_path / "Afanes.yaml").read_text(encoding="utf-8") == "schema_version: 1\n"

    def test_an_invalid_file_is_refused_and_preserved(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        path = _write_settings(tmp_path, "schema_version: 2\n")
        before = path.read_bytes()

        with pytest.raises(VaultSchemaUnsupportedError):
            _store(tmp_path).adopt()

        assert path.read_bytes() == before

    def test_missing_folders_are_refused_without_a_write(self, tmp_path: Path) -> None:
        _make_adoptable(tmp_path)
        (tmp_path / "projects").rmdir()

        with pytest.raises(VaultSchemaNotAdoptableError, match="projects/"):
            _store(tmp_path).adopt()

        assert not (tmp_path / "afanes.yaml").exists()
