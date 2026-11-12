# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Headless command surface for Afanes.

The package is a thin adapter over ``core`` and ``models``. It never imports the
graphical toolkit or the interface package, so every command works without a
display server.
"""
