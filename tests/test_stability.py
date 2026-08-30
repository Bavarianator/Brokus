#!/usr/bin/env python3
"""BrokuS Stabilitäts-Check – Tests für B und C (UI + Stabilität)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  [green]✓[/green] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [red]✗[/red] {name}: {e}")
        FAIL += 1

def import_core():
    from brokus.core.pipeline import BookPipeline
    from brokus.core.validator import ComplianceValidator
    from brokus.core.dna_extractor import DNAExtractor

def import_tui():
    from brokus.tui.app_simple import run, _app_entry, generate_book

def import_ai_client():
    from brokus.ai.client import BrokusAIClient
    from brokus.ai.model_discovery import ModelDiscovery

def api_key_check():
    from brokus.tui.app_simple import _has_api_key
    # Should return bool; if False, report clearly
    ok = _has_api_key()
    if not ok:
        raise RuntimeError("Kein API-Key konfiguriert (erwartet in Testumgebung ok)")

def progress_format():
    # Verify progress formatting logic exists
    assert "█" in open("brokus/tui/app_simple.py").read()

if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    console.print("[bold cyan]BrokuS Stabilitäts-Check[/bold cyan]  [dim]B + C[/dim]\n")
    check("Core-Imports (pipeline, validator, DNA)", import_core)
    check("TUI-Imports (app_simple, generate)", import_tui)
    check("AI-Client & Discovery", import_ai_client)
    check("Progress-Format (visuell)", progress_format)
    # API-Key check is optional in sandbox; don't hard-fail
    try:
        api_key_check()
        console.print("  [green]✓[/green] API-Key-Check (Konfiguration)")
        PASS += 1
    except Exception as e:
        console.print(f"  [yellow]⚠[/yellow] API-Key-Check: {e} (ok in Sandbox)")
    console.print(f"\n[bold]Ergebnis:[/bold] {PASS} bestanden, {FAIL} fehlgeschlagen")
    sys.exit(0 if FAIL == 0 else 1)
