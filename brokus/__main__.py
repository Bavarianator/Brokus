"""Allow running brokus via `python -m brokus` or the `brokus` CLI command."""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="brokus – KI-Buchgenerator im Terminal",
    )
    parser.add_argument(
        "--tui", action="store_true",
        help="Start in full-screen TUI mode (prompt_toolkit, advanced)",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Show version",
    )
    args = parser.parse_args()

    if args.version:
        from brokus import __version__
        print(f"brokus v{__version__}")
        return

    if args.tui:
        try:
            from brokus.tui.app_pt import run
            run()
        except ImportError as e:
            print(f"❌ Fehler: {e}")
            sys.exit(1)
        return

    # Start simple CLI (default)
    try:
        from brokus.tui.app_simple import run
        run()
    except ImportError as e:
        print(f"❌ Fehler: {e}")
        print("Installiere Abhängigkeiten mit: pip install -e .")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Auf Wiedersehen!")
        sys.exit(0)


if __name__ == "__main__":
    main()
