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
from collections.abc import Sequence
from pathlib import Path

import afanes.cli.strings
import afanes.cli.vault

USAGE_EXIT_CODE = 2


class CommandLine:
    """Parse and run one headless command."""

    @classmethod
    def build_parser(cls) -> argparse.ArgumentParser:
        """Build the command-line parser.

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
            prog=afanes.cli.strings.PROGRAM,
            description=afanes.cli.strings.DESCRIPTION,
        )
        commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
        vault = commands.add_parser(
            afanes.cli.strings.VAULT_COMMAND,
            help=afanes.cli.strings.VAULT_HELP,
            description=afanes.cli.strings.VAULT_HELP,
        )
        actions = vault.add_subparsers(dest="action", required=True, metavar="ACTION")
        create = actions.add_parser(
            afanes.cli.strings.CREATE_COMMAND,
            help=afanes.cli.strings.CREATE_HELP,
            description=afanes.cli.strings.CREATE_HELP,
        )
        create.add_argument(
            "directory",
            metavar="DIR",
            type=Path,
            help=afanes.cli.strings.CREATE_DIRECTORY_HELP,
        )
        create.add_argument(
            "--no-remember",
            action="store_true",
            dest="no_remember",
            help=afanes.cli.strings.NO_REMEMBER_HELP,
        )
        create.add_argument(
            "--template",
            metavar="ID",
            dest="template",
            default=None,
            help=afanes.cli.strings.TEMPLATE_OPTION_HELP,
        )
        adopt = actions.add_parser(
            afanes.cli.strings.ADOPT_COMMAND,
            help=afanes.cli.strings.ADOPT_HELP,
            description=afanes.cli.strings.ADOPT_HELP,
        )
        adopt.add_argument(
            "directory",
            metavar="DIR",
            type=Path,
            help=afanes.cli.strings.ADOPT_DIRECTORY_HELP,
        )
        adopt.add_argument(
            "--no-remember",
            action="store_true",
            dest="no_remember",
            help=afanes.cli.strings.ADOPT_NO_REMEMBER_HELP,
        )
        actions.add_parser(
            afanes.cli.strings.TEMPLATES_COMMAND,
            help=afanes.cli.strings.TEMPLATES_HELP,
            description=afanes.cli.strings.TEMPLATES_HELP,
        )
        return parser

    @classmethod
    def run(cls, argv: Sequence[str]) -> int:
        """Parse arguments and run the requested command.

        Parameters
        ----------
        argv : collections.abc.Sequence[str]
            Arguments after the program name. The sequence is parsed, never
            modified.

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
        parser = cls.build_parser()
        try:
            options = parser.parse_args(list(argv))
        except SystemExit as exc:
            status = exc.code
            return status if isinstance(status, int) else USAGE_EXIT_CODE
        if options.command == afanes.cli.strings.VAULT_COMMAND and options.action == afanes.cli.strings.CREATE_COMMAND:
            return afanes.cli.vault.VaultCommand.create(
                options.directory,
                remember=not options.no_remember,
                template=options.template,
            )
        if options.command == afanes.cli.strings.VAULT_COMMAND and options.action == afanes.cli.strings.ADOPT_COMMAND:
            return afanes.cli.vault.VaultCommand.adopt(
                options.directory,
                remember=not options.no_remember,
            )
        if (
            options.command == afanes.cli.strings.VAULT_COMMAND
            and options.action == afanes.cli.strings.TEMPLATES_COMMAND
        ):
            return afanes.cli.vault.VaultCommand.templates()
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
        """
        return cls.run(list(args))
