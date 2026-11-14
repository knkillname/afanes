# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compile every bundled gettext ``.po`` source into the standard ``.mo`` format.

Run with ``hatch run i18n-compile``. The compiler is offline and does not need
a GNU gettext installation.
"""

import sys

import afanes.i18n.po


def main() -> int:
    """Compile the default catalog directory.

    Returns
    -------
    int
        Process exit status.
    """
    compiled = afanes.i18n.po.CatalogCompiler().compile()
    for path in compiled:
        sys.stdout.write(f"compiled {path.as_posix()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
