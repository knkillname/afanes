# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Graphical entry point for Afanes.

The entry point selects one of two presentations before any interface code
loads. The desktop window is the default; ``--web`` serves the same interface
from a loopback web server. Runtime packages are checked here, before Flet
starts, because Flet installs a missing runtime package from the network on
first use, which an offline application must never do.
"""

import argparse
import dataclasses
import importlib.util
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

import afanes.cli.main
import afanes.core.vault
import afanes.ui.strings
from afanes.core.errors import VaultError

WEB_RUNTIME_MODULE = "flet_web"
DESKTOP_RUNTIME_MODULE = "flet_desktop"
LOOPBACK_HOST = "127.0.0.1"
PORT_LIMIT = 65535
SUBCOMMANDS = ("vault",)

# Read before the interface import so the missing-SDK message is available even
# when the import of ``afanes.ui.app`` fails.
_SDK_MISSING_MESSAGE = afanes.ui.strings.LAUNCH_MISSING_SDK


@dataclasses.dataclass(frozen=True, slots=True)
class LaunchOptions:
    """Command-line options for one Afanes launch.

    Attributes
    ----------
    web : bool
        Serve the interface in a browser instead of opening a desktop window.
    vault : pathlib.Path | None
        Vault directory supplied for this run only, or ``None`` to use the
        remembered vault. A supplied path never replaces the remembered one.
    port : int
        Port for the browser presentation. ``0`` asks the operating system for
        a free port.
    """

    web: bool
    vault: Path | None
    port: int

    @classmethod
    def parse(cls, argv: Sequence[str]) -> "LaunchOptions":
        """Parse command-line options for the graphical entry point.

        Parameters
        ----------
        argv : collections.abc.Sequence[str]
            Arguments after the program name. The sequence is parsed, never
            modified.

        Returns
        -------
        LaunchOptions
            Parsed presentation, optional vault, and port.

        Raises
        ------
        SystemExit
            If the arguments are invalid. ``argparse`` exits with status ``2``
            for a usage error and ``0`` for ``--help``.

        Notes
        -----
        Parsing is pure: it touches no filesystem path and imports no
        interface module, so tests can exercise it without a display.
        """
        parser = argparse.ArgumentParser(prog="afanes", description=afanes.ui.strings.LAUNCH_DESCRIPTION)
        parser.add_argument("--web", action="store_true", help=afanes.ui.strings.LAUNCH_WEB_HELP)
        parser.add_argument("--vault", metavar="DIR", type=Path, help=afanes.ui.strings.LAUNCH_VAULT_HELP)
        parser.add_argument(
            "--port",
            metavar="N",
            type=_port_number,
            default=0,
            help=afanes.ui.strings.LAUNCH_PORT_HELP,
        )
        namespace = parser.parse_args(list(argv))
        return cls(web=bool(namespace.web), vault=namespace.vault, port=namespace.port)


class Launcher:
    """Process-level launch guards for the graphical entry point."""

    @staticmethod
    def dispatch(argv: Sequence[str]) -> int | None:
        """Run a headless subcommand when the first argument names one.

        Parameters
        ----------
        argv : collections.abc.Sequence[str]
            Arguments after the program name.

        Returns
        -------
        int | None
            Exit status of the subcommand, or ``None`` when the arguments
            describe a graphical launch.

        Notes
        -----
        Dispatch runs before the runtime check and before any toolkit import,
        so a headless command works on a machine with no graphical runtime
        installed.
        """
        if not argv or argv[0] not in SUBCOMMANDS:
            return None
        return afanes.cli.main.main(argv)

    @staticmethod
    def fail(message: str) -> NoReturn:
        """Write an actionable message to standard error and exit.

        Parameters
        ----------
        message : str
            Message naming the problem and, where known, the command that fixes
            it.

        Raises
        ------
        SystemExit
            Always, with status ``1``.
        """
        sys.stderr.write(f"{message}\n")
        sys.stderr.flush()
        raise SystemExit(1)

    @staticmethod
    def require_runtime(*, web: bool) -> None:
        """Check the runtime package for the requested presentation.

        Parameters
        ----------
        web : bool
            Whether the browser presentation was requested.

        Raises
        ------
        SystemExit
            If the runtime package is absent, with a message naming the install
            command. The check runs before Flet starts so no package is
            installed at runtime.
        """
        if web:
            module = WEB_RUNTIME_MODULE
            message = afanes.ui.strings.LAUNCH_MISSING_WEB
        else:
            module = DESKTOP_RUNTIME_MODULE
            message = afanes.ui.strings.LAUNCH_MISSING_DESKTOP
        if importlib.util.find_spec(module) is None:
            Launcher.fail(message)

    @staticmethod
    def checked_vault(path: Path | None) -> Path | None:
        """Validate a vault supplied on the command line.

        Parameters
        ----------
        path : pathlib.Path | None
            Candidate vault directory, or ``None`` when the option was omitted.

        Returns
        -------
        pathlib.Path | None
            Resolved vault root, or ``None`` when no vault was supplied.

        Raises
        ------
        SystemExit
            If the supplied path is missing, is not a directory, or cannot be
            read.
        """
        if path is None:
            return None
        try:
            return afanes.core.vault.Vault.open(path).root
        except (VaultError, OSError) as exc:
            Launcher.fail(afanes.ui.strings.LAUNCH_VAULT_INVALID.format(path=path, detail=exc))


def _port_number(text: str) -> int:
    """Parse a TCP port number for ``argparse``.

    Parameters
    ----------
    text : str
        Raw command-line value.

    Returns
    -------
    int
        Port between ``0`` and :data:`PORT_LIMIT` inclusive.

    Raises
    ------
    argparse.ArgumentTypeError
        If the value is not a whole number or is outside the valid range.
    """
    try:
        port = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(afanes.ui.strings.LAUNCH_PORT_NOT_NUMBER) from exc
    if not 0 <= port <= PORT_LIMIT:
        raise argparse.ArgumentTypeError(
            afanes.ui.strings.LAUNCH_PORT_OUT_OF_RANGE.format(limit=PORT_LIMIT),
        )
    return port


def main(argv: Sequence[str] | None = None) -> None:
    """Launch Afanes in the requested presentation.

    Parameters
    ----------
    argv : collections.abc.Sequence[str] | None
        Arguments after the program name. ``None`` reads :data:`sys.argv`.

    Raises
    ------
    SystemExit
        If the arguments are invalid, a runtime package is missing, a supplied
        vault is unusable, or the desktop window cannot start.

    Notes
    -----
    The interface modules are imported inside this function so a missing Flet
    SDK produces one actionable message instead of an import traceback. The
    import is a deliberate runtime check, not an attempt to hide a dependency
    cycle.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    status = Launcher.dispatch(arguments)
    if status is not None:
        raise SystemExit(status)
    options = LaunchOptions.parse(arguments)
    logging.basicConfig(level=logging.INFO)
    Launcher.require_runtime(web=options.web)
    launch_vault = Launcher.checked_vault(options.vault)
    try:
        # The interface is imported here on purpose: a missing SDK must be
        # reported as one message, not as an import traceback. This is a
        # runtime availability check, not a dependency cycle.
        import flet as ft  # noqa: PLC0415

        import afanes.ui.app  # noqa: PLC0415
    except ModuleNotFoundError:
        Launcher.fail(_SDK_MISSING_MESSAGE)

    async def entry(page: ft.Page) -> None:
        await afanes.ui.app.main(page, launch_vault=launch_vault)

    if options.web:
        ft.run(
            entry,
            view=ft.AppView.WEB_BROWSER,
            host=LOOPBACK_HOST,
            port=options.port,
            no_cdn=True,
        )
        return
    try:
        ft.run(entry)
    except (OSError, SystemExit) as exc:
        Launcher.fail(afanes.ui.strings.LAUNCH_DESKTOP_FAILED.format(detail=exc))


if __name__ == "__main__":
    main()
