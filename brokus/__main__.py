"""Allow running brokus via `python -m brokus` or the `brokus` CLI command."""

import getpass
import sys
import argparse


def _cli_set_master_password():
    """Interactive flow: set or rotate the master passphrase (non-TUI)."""
    import os
    from pathlib import Path
    from brokus.utils.crypto import set_passphrase, _get_passphrase, SecretStore

    print("🔐 brokus – Master-Passphrase setzen / rotieren")
    print("=" * 50)
    print()
    print("  ℹ️  Die Master-Passphrase ist ein ZUSÄTZLICHER Schutz für deine API-Keys")
    print("      in secrets.enc. Ohne sie reicht deine Maschinen-Identität als Schutz.")
    print("      MIT ihr braucht ein Angreifer BEIDES (Maschine + Passwort).")
    print()
    print("  ⚠️  Wenn du die Passphrase vergisst, sind alle gespeicherten API-Keys verloren!")
    print()

    if _get_passphrase() is not None:
        print("  🟡 Es ist bereits eine Master-Passphrase aktiv.")
        existing = SecretStore.instance()
        if not existing.is_loaded:
            existing.load()
        n = len(existing._secrets)
        print(f"     Aktuell sind {n} API-Key(s) damit verschlüsselt.")
        if input("     Wirklich ROTIEREN? Die alte Passphrase wird ungültig. [j/N]: ").strip().lower() not in ("j", "ja", "y", "yes"):
            print("  Abgebrochen.")
            return
        print()

    # ── Read new passphrase (min 12 chars) ──
    while True:
        pw1 = getpass.getpass("  Neue Master-Passphrase (min. 12 Zeichen): ")
        if not pw1:
            print("  ✗ Leere Eingabe – Abbruch.")
            return
        if len(pw1) < 12:
            print(f"  ⚠️  Nur {len(pw1)} Zeichen – min. 12 empfohlen.")
            if input("      Trotzdem fortfahren? [j/N]: ").strip().lower() not in ("j", "ja"):
                continue
        if len(pw1) < 8:
            print("  ✗ Mindestens 8 Zeichen erforderlich – Abbruch.")
            return
        pw2 = getpass.getpass("  Passphrase wiederholen (Bestätigung): ")
        if pw1 != pw2:
            print("  ✗ Passphrasen stimmen nicht überein.")
            continue
        break

    # ── Save ──
    try:
        path = set_passphrase(pw1)
        os.environ["BROKUS_MASTER_PASSWORD"] = pw1

        # Re-encrypt existing secrets
        existing = SecretStore.instance()
        if not existing.is_loaded:
            existing.load()
        n_existing = len(existing._secrets)
        if n_existing > 0:
            ok = existing.save()
            if ok:
                print(f"  ✓ Master-Passphrase gespeichert: {path}")
                print(f"  ✓ {n_existing} API-Key(s) mit neuer Passphrase re-verschlüsselt.")
            else:
                print(f"  ✓ Master-Passphrase gespeichert: {path}")
                print("  ⚠ Re-Verschlüsselung fehlgeschlagen – prüfe manuell.")
        else:
            print(f"  ✓ Master-Passphrase gespeichert: {path}")
            print("  ℹ️  (noch keine API-Keys gespeichert – secrets.enc wird beim ersten save() verschlüsselt)")

        print()
        print("  Nächste Schritte:")
        print("    • Für diese Shell-Session: export BROKUS_MASTER_PASSWORD='...' (bereits gesetzt)")
        print("    • Für dauerhafte Nutzung: master.key wird beim nächsten Start automatisch gelesen")
        print("    • Zum Rotieren: einfach erneut `brokus --set-master-password` ausführen")
    except Exception as e:
        print(f"  ✗ Fehler: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="brokus – KI-Buchgenerator im Terminal",
    )
    parser.add_argument(
        "--tui", action="store_true",
        help="Start in full-screen TUI mode (prompt_toolkit, advanced)",
    )
    parser.add_argument(
        "--set-master-password", action="store_true",
        help="Set or rotate the master passphrase (interactively, non-TUI)",
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

    if args.set_master_password:
        _cli_set_master_password()
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
