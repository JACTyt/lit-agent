"""Launcher for the Lit-Agent console UI.

The interactive UI logic lives in `ui/console_ui.py`. This module simply
imports and runs it. Old UI/streaming code was moved to `ui/console_ui.py`.
"""

from ui.console_ui import run


def main():
    run()


if __name__ == "__main__":
    main()
