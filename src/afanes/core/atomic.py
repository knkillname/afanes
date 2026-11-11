# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Atomic UTF-8 text replacement shared by vault and settings writes."""

import contextlib
import os
import tempfile
from pathlib import Path

from afanes.core.errors import VaultError


def write_text_atomic(path: Path, text: str) -> None:
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
    before the replace, and the temporary file is removed when any step fails.
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
