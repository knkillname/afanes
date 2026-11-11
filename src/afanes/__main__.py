# SPDX-FileCopyrightText: 2026-present Mario Abarca <knkillname@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Graphical entry point for Afanes."""

import logging

import flet as ft

import afanes.ui.app


def main() -> None:
    """Launch the Afanes desktop application."""
    logging.basicConfig(level=logging.INFO)
    ft.run(afanes.ui.app.main)


if __name__ == "__main__":
    main()
