# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Vault settings file: schema version, validation, adoption, and creation.

The settings file is the explicit on-disk contract for a vault. It lives at
the vault root as ``afanes.yaml`` and records one schema version. This module
owns reading, validating, adopting, and writing that file; it performs no note
I/O and never creates a vault layout.
"""

import dataclasses
import os
import stat
from pathlib import Path

import yaml

import afanes.core.atomic
import afanes.core.vault.snapshot
from afanes.core.errors import (
    DomainMessage,
    MessageCode,
    VaultError,
    VaultMissingError,
    VaultNotDirectoryError,
    VaultSchemaError,
    VaultSchemaInvalidError,
    VaultSchemaMissingError,
    VaultSchemaNotAdoptableError,
    VaultSchemaUnsupportedError,
    VaultSchemaWriteError,
)

# Public canonical settings filename.
SCHEMA_FILENAME = "afanes.yaml"

# Public current on-disk schema version.
CURRENT_SCHEMA_VERSION = 1

# Public maximum size accepted for the settings file.
SCHEMA_MAX_BYTES = 4096

# Public folders that make an unversioned folder eligible for adoption.
DEFAULT_FOLDERS = (
    afanes.core.vault.snapshot.INBOX_DIRECTORY,
    afanes.core.vault.snapshot.TRASH_DIRECTORY,
    afanes.core.vault.snapshot.REFERENCE_DIRECTORY,
    afanes.core.vault.snapshot.PROJECTS_DIRECTORY,
    afanes.core.vault.snapshot.LOG_DIRECTORY,
)

INTEGER_TAG = "tag:yaml.org,2002:int"


@dataclasses.dataclass(frozen=True, slots=True, order=True)
class VaultSchema:
    """One validated on-disk vault schema.

    Attributes
    ----------
    version : int
        Positive schema version recorded by the settings file.
    """

    version: int

    def __post_init__(self) -> None:
        """Reject a value that cannot be a schema version.

        Raises
        ------
        ValueError
            If ``version`` is not a positive integer.
        """
        valid = isinstance(self.version, int) and not isinstance(self.version, bool) and self.version > 0
        if not valid:
            message = "Schema version must be a positive integer"
            raise ValueError(message)


@dataclasses.dataclass(frozen=True, slots=True)
class VaultSchemaAdoption:
    """Result of adopting or reusing a vault settings file.

    Attributes
    ----------
    root : pathlib.Path
        Resolved vault root that now contains a settings file.
    schema : VaultSchema
        Schema recorded by the settings file.
    created : bool
        Whether this operation wrote the settings file. ``False`` means a valid
        file was already present.
    """

    root: Path
    schema: VaultSchema
    created: bool


@dataclasses.dataclass(frozen=True, slots=True)
class VaultSchemaStore:
    """Read and write one vault's settings file.

    Parameters
    ----------
    root : pathlib.Path
        Candidate vault root. It must exist and be a directory.

    Raises
    ------
    VaultMissingError
        If the path does not exist.
    VaultNotDirectoryError
        If the path is not a directory.

    Notes
    -----
    The root is resolved at construction. Every settings path is derived from
    that root, so a caller cannot redirect the read or write elsewhere. The
    store never scans notes, creates folders, or writes anything except the
    settings file.
    """

    root: Path

    def __post_init__(self) -> None:
        """Resolve and validate the vault root.

        Raises
        ------
        VaultMissingError
            If the path does not exist.
        VaultNotDirectoryError
            If the path exists and is not a directory.
        """
        resolved = self.root.expanduser().resolve()
        if not resolved.exists():
            message = DomainMessage.of(MessageCode.VAULT_ROOT_MISSING, path=str(self.root))
            raise VaultMissingError(message)
        if not resolved.is_dir():
            message = DomainMessage.of(MessageCode.VAULT_ROOT_NOT_DIRECTORY, path=str(self.root))
            raise VaultNotDirectoryError(message)
        object.__setattr__(self, "root", resolved)

    @property
    def settings_path(self) -> Path:
        """Return the exact settings path inside this vault.

        Returns
        -------
        pathlib.Path
            Absolute ``afanes.yaml`` path at the vault root.
        """
        return self.root / SCHEMA_FILENAME

    def load(self) -> VaultSchema | None:
        """Read and validate the settings file without writing anything.

        Returns
        -------
        VaultSchema | None
            Validated schema, or ``None`` when the exact settings file is
            absent.

        Raises
        ------
        VaultSchemaInvalidError
            If the path is a symlink, is not a regular file, is too large, is
            not UTF-8 YAML, or does not match the current file shape.
        VaultSchemaUnsupportedError
            If the file declares a schema version other than the current one.

        Notes
        -----
        The file is parsed as a YAML node tree rather than constructed into
        arbitrary Python values. Only a mapping with exactly one
        ``schema_version`` integer entry is accepted, so duplicate keys and
        extra keys are refused. The file is never modified.
        """
        path = self.settings_path
        try:
            info = path.lstat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            message = DomainMessage.of(MessageCode.SCHEMA_INSPECT_FAILED, path=str(path))
            raise VaultSchemaInvalidError(message) from exc
        if stat.S_ISLNK(info.st_mode):
            message = DomainMessage.of(MessageCode.SCHEMA_SYMLINK, path=str(path))
            raise VaultSchemaInvalidError(message)
        if not stat.S_ISREG(info.st_mode):
            message = DomainMessage.of(MessageCode.SCHEMA_NOT_FILE, path=str(path))
            raise VaultSchemaInvalidError(message)
        if info.st_size > SCHEMA_MAX_BYTES:
            message = DomainMessage.of(MessageCode.SCHEMA_TOO_LARGE, path=str(path))
            raise VaultSchemaInvalidError(message)
        try:
            data = path.read_bytes()
        except OSError as exc:
            message = DomainMessage.of(MessageCode.SCHEMA_READ_FAILED, path=str(path))
            raise VaultSchemaInvalidError(message) from exc
        if len(data) > SCHEMA_MAX_BYTES:
            message = DomainMessage.of(MessageCode.SCHEMA_TOO_LARGE, path=str(path))
            raise VaultSchemaInvalidError(message)
        return self._parse(path, data)

    def require(self) -> VaultSchema:
        """Return a valid current schema or refuse the vault.

        Returns
        -------
        VaultSchema
            Validated current schema.

        Raises
        ------
        VaultSchemaMissingError
            If the vault has no exact settings file.
        VaultSchemaInvalidError
            If the settings file does not match the current shape.
        VaultSchemaUnsupportedError
            If the file declares another schema version.
        """
        schema = self.load()
        if schema is None:
            message = DomainMessage.of(MessageCode.SCHEMA_MISSING, path=str(self.root))
            raise VaultSchemaMissingError(message)
        return schema

    def is_adoptable(self) -> bool:
        """Report whether this folder can be adopted without writing.

        Returns
        -------
        bool
            ``True`` when the folder has no settings file, is writable, and
            contains every default folder (matched case-insensitively).
            ``False`` otherwise.
        """
        try:
            if self.load() is not None:
                return False
        except VaultSchemaError:
            return False
        if not os.access(self.root, os.W_OK | os.X_OK):
            return False
        try:
            names = {child.name.casefold() for child in self.root.iterdir() if child.is_dir()}
        except OSError:
            return False
        return all(folder.name.casefold() in names for folder in DEFAULT_FOLDERS)

    def adopt(self) -> VaultSchemaAdoption:
        """Write the current settings file into an adoptable folder.

        Returns
        -------
        VaultSchemaAdoption
            The resolved root, the recorded schema, and whether this call wrote
            the file. A valid file that already exists is reused unchanged and
            reports ``created=False``.

        Raises
        ------
        VaultSchemaNotAdoptableError
            If the folder has no valid settings file and is not writable or
            lacks a default folder.
        VaultSchemaInvalidError
            If a settings file exists and does not match the current shape.
        VaultSchemaUnsupportedError
            If a settings file exists and declares another schema version.
        VaultSchemaWriteError
            If the settings file cannot be written.

        Notes
        -----
        Only ``afanes.yaml`` is written. No note, folder, guide, or template
        card is created. The write is exclusive, so a concurrent file is never
        overwritten.
        """
        existing = self.load()
        if existing is not None:
            return VaultSchemaAdoption(root=self.root, schema=existing, created=False)
        if not self.is_adoptable():
            concurrent = self.load()
            if concurrent is not None:
                return VaultSchemaAdoption(root=self.root, schema=concurrent, created=False)
            raise VaultSchemaNotAdoptableError(self._not_adoptable_message())
        try:
            schema = self.create_current()
        except VaultSchemaWriteError:
            concurrent = self.load()
            if concurrent is None:
                raise
            return VaultSchemaAdoption(root=self.root, schema=concurrent, created=False)
        return VaultSchemaAdoption(root=self.root, schema=schema, created=True)

    def create_current(self) -> VaultSchema:
        """Write the current settings file without overwriting an existing one.

        Returns
        -------
        VaultSchema
            Schema written by this call.

        Raises
        ------
        VaultSchemaWriteError
            If the file already exists or cannot be written.
        """
        schema = VaultSchema(version=CURRENT_SCHEMA_VERSION)
        text = f"schema_version: {schema.version}\n"
        try:
            afanes.core.atomic.AtomicWriter.write_text_exclusive(self.settings_path, text)
        except (VaultError, OSError) as exc:
            message = DomainMessage.of(MessageCode.SCHEMA_WRITE_FAILED, path=str(self.root), detail=str(exc))
            raise VaultSchemaWriteError(message) from exc
        return schema

    def _parse(self, path: Path, data: bytes) -> VaultSchema:
        """Validate one settings file's bytes and return its schema.

        Parameters
        ----------
        path : pathlib.Path
            Exact settings path, used in diagnostics.
        data : bytes
            Complete file bytes already bounded by :data:`SCHEMA_MAX_BYTES`.

        Returns
        -------
        VaultSchema
            Validated current schema.

        Raises
        ------
        VaultSchemaInvalidError
            If the file is not UTF-8, is not YAML, or does not contain exactly
            one ``schema_version`` integer.
        VaultSchemaUnsupportedError
            If the declared version is not the current one.
        """
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            message = DomainMessage.of(MessageCode.SCHEMA_INVALID_UTF8, path=str(path))
            raise VaultSchemaInvalidError(message) from exc
        try:
            node = yaml.compose(text, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            message = DomainMessage.of(MessageCode.SCHEMA_INVALID_YAML, path=str(path))
            raise VaultSchemaInvalidError(message) from exc
        if not isinstance(node, yaml.MappingNode) or len(node.value) != 1:
            raise VaultSchemaInvalidError(self._shape_message(path))
        key_node, value_node = node.value[0]
        if not isinstance(key_node, yaml.ScalarNode) or key_node.value != "schema_version":
            raise VaultSchemaInvalidError(self._shape_message(path))
        if not isinstance(value_node, yaml.ScalarNode) or value_node.tag != INTEGER_TAG:
            raise VaultSchemaInvalidError(self._shape_message(path))
        try:
            version = int(value_node.value)
        except ValueError as exc:
            message = DomainMessage.of(MessageCode.SCHEMA_VERSION_NOT_INT, path=str(path))
            raise VaultSchemaInvalidError(message) from exc
        if version != CURRENT_SCHEMA_VERSION:
            raise VaultSchemaUnsupportedError(self._unsupported_message(path, version))
        return VaultSchema(version=version)

    def _shape_message(self, path: Path) -> DomainMessage:
        """Return the diagnostic for a file that does not match version 1."""
        return DomainMessage.of(MessageCode.SCHEMA_SHAPE, version=str(CURRENT_SCHEMA_VERSION), path=str(path))

    def _unsupported_message(self, path: Path, version: int) -> DomainMessage:
        """Return the diagnostic for an unsupported declared version."""
        if version > CURRENT_SCHEMA_VERSION:
            return DomainMessage.of(
                MessageCode.SCHEMA_NEWER,
                declared=str(version),
                supported=str(CURRENT_SCHEMA_VERSION),
                path=str(path),
            )
        return DomainMessage.of(
            MessageCode.SCHEMA_OLDER,
            declared=str(version),
            supported=str(CURRENT_SCHEMA_VERSION),
            path=str(path),
        )

    def _not_adoptable_message(self) -> DomainMessage:
        """Return the diagnostic for a folder that cannot be adopted."""
        if not os.access(self.root, os.W_OK | os.X_OK):
            return DomainMessage.of(MessageCode.SCHEMA_NOT_WRITABLE, path=str(self.root))
        try:
            names = {child.name.casefold() for child in self.root.iterdir() if child.is_dir()}
        except OSError:
            names = set()
        missing = [folder.name for folder in DEFAULT_FOLDERS if folder.name.casefold() not in names]
        folders = ", ".join(f"{name}/" for name in missing)
        return DomainMessage.of(MessageCode.SCHEMA_MISSING_FOLDERS, path=str(self.root), folders=folders)
