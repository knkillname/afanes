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

import afanes.core.settings
import afanes.core.templates
import afanes.core.vault.schema
import afanes.core.vault.service
import afanes.i18n.cli
from afanes.core.errors import ConfigurationError, VaultError
from afanes.core.settings import Settings
from afanes.core.vault.service import VaultCreation

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
_ENGLISH_COPY = afanes.i18n.cli.CliCopy.english()


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
    def create(
        cls,
        path: Path,
        *,
        remember: bool,
        template: str | None = None,
        copy: afanes.i18n.cli.CliCopy = _ENGLISH_COPY,
    ) -> int:
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
            creation = afanes.core.vault.service.Vault.create_directory(
                path, template=template, locale=copy.locale.language
            )
        except VaultError as exc:
            CommandOutput.error(copy.CREATE_FAILED.format(detail=copy.render_error(exc)))
            return EXIT_FAILURE
        if remember:
            try:
                afanes.core.settings.SettingsStore.default().save(Settings(vault=creation.vault.root))
            except ConfigurationError as exc:
                cls._report(creation, remembered=False, copy=copy)
                CommandOutput.error(
                    copy.REMEMBER_FAILED.format(path=creation.vault.root, detail=copy.render_error(exc)),
                )
                return EXIT_FAILURE
        cls._report(creation, remembered=remember, copy=copy)
        return EXIT_SUCCESS

    @classmethod
    def adopt(
        cls,
        path: Path,
        *,
        remember: bool,
        copy: afanes.i18n.cli.CliCopy = _ENGLISH_COPY,
    ) -> int:
        """Add the vault settings file to an existing folder.

        Parameters
        ----------
        path : pathlib.Path
            Existing folder that contains the five default folders.
        remember : bool
            Whether the adopted vault becomes the one Afanes opens next launch.

        Returns
        -------
        int
            ``0`` when the folder was adopted or already versioned, ``1`` when
            adoption or the preferences write failed.

        Notes
        -----
        Adoption writes only ``afanes.yaml``. A valid settings file that
        already exists is reported and left unchanged, including preferences.
        The command performs blocking filesystem I/O and never opens the
        interface.
        """
        try:
            adoption = afanes.core.vault.schema.VaultSchemaStore(path).adopt()
        except VaultError as exc:
            CommandOutput.error(copy.ADOPT_FAILED.format(detail=copy.render_error(exc)))
            return EXIT_FAILURE
        if not adoption.created:
            CommandOutput.line(
                copy.ALREADY_VAULT.format(
                    path=adoption.root,
                    version=adoption.schema.version,
                ),
            )
            return EXIT_SUCCESS
        cls._report_adoption(adoption.root, adoption.schema.version, copy=copy)
        if remember:
            try:
                afanes.core.settings.SettingsStore.default().save(Settings(vault=adoption.root))
            except ConfigurationError as exc:
                CommandOutput.error(
                    copy.ADOPT_REMEMBER_FAILED.format(path=adoption.root, detail=copy.render_error(exc)),
                )
                return EXIT_FAILURE
        message = copy.REMEMBERED if remember else copy.NOT_REMEMBERED
        CommandOutput.line(message)
        return EXIT_SUCCESS

    @classmethod
    def templates(cls, *, copy: afanes.i18n.cli.CliCopy = _ENGLISH_COPY) -> int:
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
            summaries = afanes.core.templates.TemplateCatalog.bundled().summaries(copy.template_labels())
        except VaultError as exc:
            CommandOutput.error(copy.TEMPLATES_FAILED.format(detail=copy.render_error(exc)))
            return EXIT_FAILURE
        for summary in summaries:
            notes = (
                copy.TEMPLATE_NOTES_ONE
                if summary.note_count == 1
                else copy.TEMPLATE_NOTES_MANY.format(count=summary.note_count)
            )
            CommandOutput.line(
                copy.TEMPLATE_LINE.format(
                    identifier=summary.identifier,
                    label=summary.label,
                    description=summary.description,
                    notes=notes,
                ),
            )
        return EXIT_SUCCESS

    @classmethod
    def _report(
        cls,
        creation: VaultCreation,
        *,
        remembered: bool,
        copy: afanes.i18n.cli.CliCopy,
    ) -> None:
        """Write the structured creation summary."""
        root = creation.vault.root
        CommandOutput.line(copy.CREATED_VAULT.format(path=root))
        if creation.created_directories:
            parents = ", ".join(str(path) for path in creation.created_directories)
            CommandOutput.line(copy.CREATED_PARENTS.format(paths=parents))
        folders = ", ".join(f"{path.relative_to(root).as_posix()}/" for path in creation.seeded_directories)
        CommandOutput.line(copy.SEEDED_FOLDERS.format(folders=folders))
        cls._report_settings(creation.settings_file, root, copy=copy)
        template = creation.template or copy.TEMPLATE_NONE
        CommandOutput.line(copy.TEMPLATE_USED.format(template=template))
        notes = ", ".join(path.relative_to(root).as_posix() for path in creation.written_notes)
        CommandOutput.line(
            copy.WRITTEN_NOTES.format(notes=notes or copy.TEMPLATE_NONE),
        )
        message = copy.REMEMBERED if remembered else copy.NOT_REMEMBERED
        CommandOutput.line(message)

    @classmethod
    def _report_adoption(
        cls,
        root: Path,
        version: int,
        *,
        copy: afanes.i18n.cli.CliCopy,
    ) -> None:
        """Write the structured adoption summary."""
        CommandOutput.line(copy.ADOPTED_VAULT.format(path=root))
        CommandOutput.line(
            copy.SETTINGS_FILE.format(
                path=afanes.core.vault.schema.SCHEMA_FILENAME,
                version=version,
            ),
        )

    @staticmethod
    def _report_settings(
        settings_file: Path,
        root: Path,
        *,
        copy: afanes.i18n.cli.CliCopy,
    ) -> None:
        """Write the settings-file line for a created vault."""
        CommandOutput.line(
            copy.SETTINGS_FILE.format(
                path=settings_file.relative_to(root).as_posix(),
                version=afanes.core.vault.schema.CURRENT_SCHEMA_VERSION,
            ),
        )
