"""Shared fixture helpers for the test suite."""

from pathlib import Path

import afanes.core.vault.schema


def versioned(root: Path) -> Path:
    """Create a directory with the current vault settings file.

    Parameters
    ----------
    root : pathlib.Path
        Directory to create or reuse as a vault root.

    Returns
    -------
    pathlib.Path
        The same root, now containing ``afanes.yaml``.
    """
    root.mkdir(parents=True, exist_ok=True)
    path = root / afanes.core.vault.schema.SCHEMA_FILENAME
    path.write_text(
        f"schema_version: {afanes.core.vault.schema.CURRENT_SCHEMA_VERSION}\n",
        encoding="utf-8",
        newline="",
    )
    return root


def ensure_vault(path: Path) -> None:
    """Add the current settings file to a note's nearest ``vault`` ancestor.

    Parameters
    ----------
    path : pathlib.Path
        Note path about to be written by a test helper.

    Notes
    -----
    Test vaults are conventionally named ``vault`` under ``tmp_path``. When a
    helper is about to create the tree for the first time, this writes the
    settings file so the UI's open gate accepts it. An existing settings file,
    valid or not, is left untouched.
    """
    root = next((parent for parent in path.parents if parent.name == "vault"), None)
    if root is None:
        return
    if not (root / afanes.core.vault.schema.SCHEMA_FILENAME).exists():
        versioned(root)
