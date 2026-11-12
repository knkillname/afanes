# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The ``afanes vault`` command group.

The command is a thin adapter: it validates nothing itself, delegating vault
policy to :class:`afanes.core.vault.service.Vault` and preferences to
:class:`afanes.core.settings.SettingsStore`. Results go to standard output and
failures to standard error, so scripts can rely on the exit status and the
streams.
"""

import sys
from pathlib import Path

import afanes.cli.strings
import afanes.core.settings
import afanes.core.templates
import afanes.core.vault.service
from afanes.core.errors import ConfigurationError, VaultError
from afanes.core.settings import Settings
from afanes.core.vault.service import VaultCreation

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


class CommandOutput:
    """Write command results to the standard streams."""

    @staticmethod
    def line(text: str) -> None:
        """Write one line to standard output.

        Parameters
        ----------
        text : str
            Complete line, without a trailing newline.

        Notes
        -----
        This method is the only place where the command surface writes to
        standard output. It flushes so a piped caller sees the report before the
        process exits.
        """
        sys.stdout.write(f"{text}\n")
        sys.stdout.flush()

    @staticmethod
    def error(text: str) -> None:
        """Write one line to standard error.

        Parameters
        ----------
        text : str
            Complete message, without a trailing newline.

        Notes
        -----
        This method is the only place where the command surface writes to
        standard error. Expectations are reported as messages, never as
        tracebacks.
        """
        sys.stderr.write(f"{text}\n")
        sys.stderr.flush()


class VaultCommand:
    """Create vault directories and list starter content from the command line."""

    @classmethod
    def create(cls, path: Path, *, remember: bool, template: str | None = None) -> int:
        """Create and seed a vault directory.

        Parameters
        ----------
        path : pathlib.Path
            Directory to create or seed. It must be missing or empty.
        remember : bool
            Whether the new vault becomes the one Afanes opens next launch.
        template : str | None
            Bundled template identifier, or ``None`` to write only the guide
            note.

        Returns
        -------
        int
            ``0`` when the vault was created and, when requested, remembered;
            ``1`` when creation or the preferences write failed.

        Notes
        -----
        A created vault is reported even when the preferences write fails, so
        the user learns that the directory exists. The command performs
        blocking filesystem I/O and never opens the interface.
        """
        try:
            creation = afanes.core.vault.service.Vault.create_directory(path, template=template)
        except VaultError as exc:
            CommandOutput.error(afanes.cli.strings.CREATE_FAILED.format(detail=exc))
            return EXIT_FAILURE
        if remember:
            try:
                afanes.core.settings.SettingsStore.default().save(Settings(vault=creation.vault.root))
            except ConfigurationError as exc:
                cls._report(creation, remembered=False)
                CommandOutput.error(
                    afanes.cli.strings.REMEMBER_FAILED.format(path=creation.vault.root, detail=exc),
                )
                return EXIT_FAILURE
        cls._report(creation, remembered=remember)
        return EXIT_SUCCESS

    @classmethod
    def templates(cls) -> int:
        """Report every bundled template with its identifier and description.

        Returns
        -------
        int
            ``0`` when the catalog was read, ``1`` when it is unavailable.

        Notes
        -----
        The command reads package data only. It opens no vault, requires no
        display, and writes no file.
        """
        try:
            summaries = afanes.core.templates.TemplateCatalog.bundled().summaries()
        except VaultError as exc:
            CommandOutput.error(afanes.cli.strings.TEMPLATES_FAILED.format(detail=exc))
            return EXIT_FAILURE
        for summary in summaries:
            notes = (
                afanes.cli.strings.TEMPLATE_NOTES_ONE
                if summary.note_count == 1
                else afanes.cli.strings.TEMPLATE_NOTES_MANY.format(count=summary.note_count)
            )
            CommandOutput.line(
                afanes.cli.strings.TEMPLATE_LINE.format(
                    identifier=summary.identifier,
                    label=summary.label,
                    description=summary.description,
                    notes=notes,
                ),
            )
        return EXIT_SUCCESS

    @classmethod
    def _report(cls, creation: VaultCreation, *, remembered: bool) -> None:
        """Write the structured creation summary."""
        root = creation.vault.root
        CommandOutput.line(afanes.cli.strings.CREATED_VAULT.format(path=root))
        if creation.created_directories:
            parents = ", ".join(str(path) for path in creation.created_directories)
            CommandOutput.line(afanes.cli.strings.CREATED_PARENTS.format(paths=parents))
        folders = ", ".join(f"{path.relative_to(root).as_posix()}/" for path in creation.seeded_directories)
        CommandOutput.line(afanes.cli.strings.SEEDED_FOLDERS.format(folders=folders))
        template = creation.template or afanes.cli.strings.TEMPLATE_NONE
        CommandOutput.line(afanes.cli.strings.TEMPLATE_USED.format(template=template))
        notes = ", ".join(path.relative_to(root).as_posix() for path in creation.written_notes)
        CommandOutput.line(
            afanes.cli.strings.WRITTEN_NOTES.format(notes=notes or afanes.cli.strings.TEMPLATE_NONE),
        )
        message = afanes.cli.strings.REMEMBERED if remembered else afanes.cli.strings.NOT_REMEMBERED
        CommandOutput.line(message)
