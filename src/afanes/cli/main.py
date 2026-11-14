# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Parser and entry point for the headless command surface.

The installed ``afanes`` command forwards a recognized subcommand here before
the graphical runtime is checked. Parsing uses the standard-library
``argparse`` module and every failure becomes an exit status: ``0`` success,
``1`` expected failure, ``2`` usage error.
"""

import argparse
import dataclasses
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

import afanes.cli.vault
import afanes.core.errors
import afanes.core.localization
import afanes.core.preferences
import afanes.i18n.cli

USAGE_EXIT_CODE = 2

_ENGLISH_COPY = afanes.i18n.cli.CliCopy.english()


@dataclasses.dataclass(slots=True)
class UsageError:
    """Report an argparse failure in the active locale.

    Attributes
    ----------
    parser : argparse.ArgumentParser
        Parser whose usage line is printed before the error.
    copy : afanes.i18n.cli.CliCopy
        Active command-line catalog.
    """

    parser: argparse.ArgumentParser
    copy: afanes.i18n.cli.CliCopy

    def __call__(self, _message: str) -> NoReturn:
        """Print the usage line and exit with the usage status.

        Parameters
        ----------
        _message : str
            English detail supplied by argparse. It is replaced by the
            localized generic error so no mixed-language line is shown.

        Raises
        ------
        SystemExit
            Always, with :data:`USAGE_EXIT_CODE`.
        """
        self.parser.print_usage(sys.stderr)
        self.parser.exit(USAGE_EXIT_CODE, f"{self.copy.USAGE_ERROR}\n")


class CommandLine:
    """Parse and run one headless command."""

    @classmethod
    def resolve_copy(cls) -> tuple[afanes.i18n.cli.CliCopy, afanes.core.errors.DomainMessage | None]:
        """Resolve the command-line catalog from preferences and the system.

        Returns
        -------
        tuple[afanes.i18n.cli.CliCopy, afanes.core.errors.DomainMessage | None]
            Active catalog and an optional corrupt-preferences report.

        Notes
        -----
        Resolution reads the preferences file and the process environment. It
        imports no interface module, opens no display, and makes no network
        request.
        """
        load = afanes.core.preferences.PreferencesStore.default().load()
        locale = afanes.core.localization.LocaleResolver.resolve(
            load.preferences.language,
            os.environ,
            afanes.core.localization.LocaleResolver.system_locale(),
        )
        return afanes.i18n.cli.CliCopy.for_locale(locale), load.problem

    @classmethod
    def _prepare(cls, parser: argparse.ArgumentParser, copy: afanes.i18n.cli.CliCopy) -> None:
        """Attach the localized help action and usage error to one parser.

        Parameters
        ----------
        parser : argparse.ArgumentParser
            Parser to prepare.
        copy : afanes.i18n.cli.CliCopy
            Active command-line catalog.
        """
        parser.add_argument(
            "-h",
            "--help",
            action="help",
            help=copy.HELP_OPTION,
        )
        setattr(parser, "error", UsageError(parser, copy))  # noqa: B010

    @classmethod
    def build_parser(cls, copy: afanes.i18n.cli.CliCopy = _ENGLISH_COPY) -> argparse.ArgumentParser:
        """Build the command-line parser.

        Parameters
        ----------
        copy : afanes.i18n.cli.CliCopy
            Active command-line catalog.

        Returns
        -------
        argparse.ArgumentParser
            Parser with the ``vault`` command group and its actions.

        Notes
        -----
        Parsing is pure: it touches no filesystem path and imports no interface
        module, so tests can exercise it without a display.
        """
        parser = argparse.ArgumentParser(
            prog=copy.PROGRAM,
            description=copy.DESCRIPTION,
            add_help=False,
        )
        cls._prepare(parser, copy)
        commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
        vault = commands.add_parser(
            copy.VAULT_COMMAND,
            help=copy.VAULT_HELP,
            description=copy.VAULT_HELP,
            add_help=False,
        )
        cls._prepare(vault, copy)
        actions = vault.add_subparsers(dest="action", required=True, metavar="ACTION")
        create = actions.add_parser(
            copy.CREATE_COMMAND,
            help=copy.CREATE_HELP,
            description=copy.CREATE_HELP,
            add_help=False,
        )
        cls._prepare(create, copy)
        create.add_argument(
            "directory",
            metavar="DIR",
            type=Path,
            help=copy.CREATE_DIRECTORY_HELP,
        )
        create.add_argument(
            "--no-remember",
            action="store_true",
            dest="no_remember",
            help=copy.NO_REMEMBER_HELP,
        )
        create.add_argument(
            "--template",
            metavar="ID",
            dest="template",
            default=None,
            help=copy.TEMPLATE_OPTION_HELP,
        )
        adopt = actions.add_parser(
            copy.ADOPT_COMMAND,
            help=copy.ADOPT_HELP,
            description=copy.ADOPT_HELP,
            add_help=False,
        )
        cls._prepare(adopt, copy)
        adopt.add_argument(
            "directory",
            metavar="DIR",
            type=Path,
            help=copy.ADOPT_DIRECTORY_HELP,
        )
        adopt.add_argument(
            "--no-remember",
            action="store_true",
            dest="no_remember",
            help=copy.ADOPT_NO_REMEMBER_HELP,
        )
        templates = actions.add_parser(
            copy.TEMPLATES_COMMAND,
            help=copy.TEMPLATES_HELP,
            description=copy.TEMPLATES_HELP,
            add_help=False,
        )
        cls._prepare(templates, copy)
        return parser

    @classmethod
    def run(
        cls,
        argv: Sequence[str],
        copy: afanes.i18n.cli.CliCopy = _ENGLISH_COPY,
    ) -> int:
        """Parse arguments and run the requested command.

        Parameters
        ----------
        argv : collections.abc.Sequence[str]
            Arguments after the program name. The sequence is parsed, never
            modified.
        copy : afanes.i18n.cli.CliCopy
            Active command-line catalog.

        Returns
        -------
        int
            Exit status: ``0`` on success, ``1`` on an expected failure, ``2``
            for a usage error.

        Notes
        -----
        ``argparse`` reports usage errors by raising :class:`SystemExit`. The
        status is returned instead so the graphical entry point can decide how
        to exit.
        """
        parser = cls.build_parser(copy)
        try:
            options = parser.parse_args(list(argv))
        except SystemExit as exc:
            status = exc.code
            return status if isinstance(status, int) else USAGE_EXIT_CODE
        if options.command == copy.VAULT_COMMAND and options.action == copy.CREATE_COMMAND:
            return afanes.cli.vault.VaultCommand.create(
                options.directory,
                remember=not options.no_remember,
                template=options.template,
                copy=copy,
            )
        if options.command == copy.VAULT_COMMAND and options.action == copy.ADOPT_COMMAND:
            return afanes.cli.vault.VaultCommand.adopt(
                options.directory,
                remember=not options.no_remember,
                copy=copy,
            )
        if options.command == copy.VAULT_COMMAND and options.action == copy.TEMPLATES_COMMAND:
            return afanes.cli.vault.VaultCommand.templates(copy=copy)
        return USAGE_EXIT_CODE

    @classmethod
    def main(cls, *args: str) -> int:
        """Run the headless command surface.

        Parameters
        ----------
        *args : str
            Arguments after the program name.

        Returns
        -------
        int
            Exit status for the process.

        Notes
        -----
        The active locale is resolved before the parser is built, so help,
        reports, usage errors, and operational failures share one language. A
        corrupt preferences file is reported once and the system locale is
        used.
        """
        copy, problem = cls.resolve_copy()
        if problem is not None:
            afanes.cli.vault.CommandOutput.error(copy.messages.render(problem))
        return cls.run(list(args), copy)
