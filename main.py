#!/usr/bin/env python3
"""Calculadora TUI — punto de entrada."""

import argparse
import curses
import sys

from tui.app import App

VERSION = "v0.5"


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculadora TUI (curses)")
    parser.add_argument("--version", action="version", version=f"calc {VERSION}")
    args = parser.parse_args()

    try:
        curses.wrapper(lambda stdscr: App(stdscr).run())
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # noqa: BLE001 — proteger la terminal
        try:
            curses.endwin()
        except Exception:
            pass
        print(f"Error fatal: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
