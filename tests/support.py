"""Shared fixture helpers for the test suite."""

import datetime
import os
import typing
from pathlib import Path

import afanes.core.template_cards
import afanes.core.vault.processing
import afanes.core.vault.schema
import afanes.core.vault.snapshot
from afanes.core.processing import ProcessingOutcome
from afanes.models.note import Status


def constant[T](value: T) -> typing.Callable[..., T]:
    """Build an annotated callable that ignores its arguments and returns a value.

    Parameters
    ----------
    value : T
        Value returned by every call.

    Returns
    -------
    typing.Callable[..., T]
        Callable suitable for a constant-return ``monkeypatch`` replacement.
    """

    def supply(*_args: object, **_kwargs: object) -> T:
        return value

    return supply


def access_readable(_path: object, mode: int) -> bool:
    """Stand in for :func:`os.access` and report only readability.

    Parameters
    ----------
    _path : object
        Path passed by the caller and ignored.
    mode : int
        Requested access mode.

    Returns
    -------
    bool
        Whether the caller requested read access.
    """
    return mode == os.R_OK


def processing_request(
    source: Path,
    outcome: ProcessingOutcome,
    *,
    status: Status | None = None,
    due_date: datetime.date | None = None,
    owner: str | None = None,
    asked_by: str | None = None,
    project: str | None = None,
    card: afanes.core.template_cards.TemplateCard | None = None,
    today: datetime.date | None = None,
    snapshot: afanes.core.vault.snapshot.VaultSnapshot | None = None,
) -> afanes.core.vault.processing.ProcessingRequest:
    """Build a processing request for tests that start from a capture path.

    Parameters
    ----------
    source : pathlib.Path
        Capture path.
    outcome : afanes.core.processing.ProcessingOutcome
        Selected clarification outcome.
    status : afanes.models.note.Status | None
        Requested target status.
    due_date : datetime.date | None
        Optional due date.
    owner : str | None
        Optional project owner.
    asked_by : str | None
        Optional requester.
    project : str | None
        Optional append target.
    card : afanes.core.template_cards.TemplateCard | None
        Optional template card.
    today : datetime.date | None
        Optional completed date for Done now.
    snapshot : afanes.core.vault.snapshot.VaultSnapshot | None
        Optional pre-built scan.

    Returns
    -------
    afanes.core.vault.processing.ProcessingRequest
        Request carrying the capture path and options.
    """
    return afanes.core.vault.processing.ProcessingRequest(
        outcome=outcome,
        note_path=source,
        status=status,
        due_date=due_date,
        owner=owner,
        asked_by=asked_by,
        project=project,
        card=card,
        today=today,
        snapshot=snapshot,
    )


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
