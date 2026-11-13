# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Atomic UTF-8 text replacement shared by vault and settings writes.

``AtomicWriter`` owns the two write contracts; both are stateless classmethods.
"""

import contextlib
import os
import tempfile
from pathlib import Path

from afanes.core.errors import VaultError


class AtomicWriter:
    """Publish complete UTF-8 files without partial writes.

    Notes
    -----
    The writer has no per-path state. Call the classmethods directly.
    """

    @classmethod
    def write_text_exclusive(cls, path: Path, text: str) -> None:
        """Write UTF-8 text without replacing an existing file.

        Parameters
        ----------
        path : Path
            Destination file. Its parent directory must already exist.
        text : str
            Complete file contents. Newline style is the caller's responsibility.

        Raises
        ------
        VaultError
            If the parent directory does not exist.
        FileExistsError
            If the destination already exists.
        OSError
            If the file cannot be written.

        Notes
        -----
        The temporary file lives in the destination directory and is published
        with ``os.link``, which refuses to replace an existing target. When the
        filesystem cannot create hard links, the writer falls back to an
        exclusive open. The temporary file is removed when any step fails, and a
        partial fallback file is removed too.
        """
        parent = path.parent
        if not parent.is_dir():
            message = f"Destination directory does not exist: {parent}"
            raise VaultError(message)

        data = text.encode("utf-8")
        descriptor, temporary_name = tempfile.mkstemp(dir=parent, prefix=f".{path.name}.", suffix=".tmp")
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary_path, path)
            except FileExistsError:
                raise
            except OSError:
                exclusive_descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
                try:
                    with os.fdopen(exclusive_descriptor, "wb") as stream:
                        stream.write(data)
                        stream.flush()
                        os.fsync(stream.fileno())
                except BaseException:
                    with contextlib.suppress(OSError):
                        os.close(exclusive_descriptor)
                    with contextlib.suppress(OSError):
                        path.unlink()
                    raise
        finally:
            with contextlib.suppress(OSError):
                temporary_path.unlink()

    @classmethod
    def write_text_atomic(cls, path: Path, text: str) -> None:
        """Write UTF-8 text through a temporary file and an atomic replace.

        Parameters
        ----------
        path : Path
            Destination file. Its parent directory must already exist.
        text : str
            Complete file contents. Newline style is the caller's responsibility.

        Raises
        ------
        VaultError
            If the parent directory does not exist.

        Notes
        -----
        The temporary file lives in the destination directory so the final
        ``os.replace`` stays on one filesystem. The file is flushed and fsynced
        before the replace, and the temporary file is removed when any step
        fails.
        """
        parent = path.parent
        if not parent.is_dir():
            message = f"Destination directory does not exist: {parent}"
            raise VaultError(message)

        data = text.encode("utf-8")
        descriptor, temporary_name = tempfile.mkstemp(dir=parent, prefix=f".{path.name}.", suffix=".tmp")
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        except BaseException:
            with contextlib.suppress(OSError):
                temporary_path.unlink()
            raise
