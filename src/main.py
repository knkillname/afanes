# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Packaged desktop entry point used by ``flet build``.

``flet build`` requires a module file in the Flet app directory. A packaged
build bundles the interface client, so the source-run runtime check does not
apply; this launcher delegates to the bundled path in
:mod:`afanes.__main__` instead of duplicating the interface wiring.
"""

import afanes.__main__

afanes.__main__.Launcher.launch_packaged()
