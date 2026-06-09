"""Export dialog for converting books to multiple user-selected formats."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Static, Button, Checkbox, Header, Footer
from textual.binding import Binding


EXPORT_OPTIONS = [
    ("md", "Markdown (.md)"),
    ("epub", "EPUB (.epub)"),
    ("pdf", "PDF (.pdf)"),
    ("docx", "Word (.docx)"),
    ("json", "JSON (.json)"),
    ("txt", "Nur Text (.txt)"),
]

DEFAULT_FORMATS = ["md", "epub"]


class ExportScreen(Screen):
    """Export dialog for book formats – multi-select."""

    BINDINGS = [
        Binding("x", "do_export", "Exportieren"),
        Binding("escape", "go_back", "Zurück"),
    ]

    def __init__(self):
        super().__init__()
        self._project_id = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="export-container"):
            yield Static("📤 Export", classes="section-title")
            yield Static("", classes="spacer")

            yield Static("Export-Formate (mehrere möglich):", classes="form-label")
            with VerticalScroll(id="format-list"):
                for key, label in EXPORT_OPTIONS:
                    yield Checkbox(label, value=(key in DEFAULT_FORMATS), id=f"fmt-{key}")

            yield Static("", classes="spacer")
            yield Static("Optionen:", classes="form-label")
            yield Checkbox("Synopsis einbinden", value=True, id="chk-synopsis")
            yield Checkbox("Metadaten hinzufügen", value=True, id="chk-metadata")

            yield Static("", classes="spacer")
            with Horizontal(id="export-actions"):
                yield Button("📤 Jetzt exportieren", id="btn-export", variant="success")
                yield Button("📂 Alle aktivieren", id="btn-all")
                yield Button("✖  Keine", id="btn-none")
                yield Button("← Zurück", id="btn-back")

            yield Static("", id="export-status", classes="spacer")

        yield Footer()

    async def on_mount(self):
        """Set project ID from app state and load saved preference."""
        project_index = getattr(self.app, "selected_project_index", 0)
        try:
            from brokus.storage.database import get_all_projects
            projects = await get_all_projects()
            if project_index < len(projects):
                self._project_id = projects[project_index]["id"]
                title = projects[project_index]["title"]
                self.query_one("#export-container Static:first-child").update(
                    f"📤 Export: {title}"
                )
        except Exception:
            pass

        # Load saved format preferences from CLI settings file (if any)
        try:
            import json
            from pathlib import Path
            cfg = Path.home() / ".config" / "brokus" / "cli_settings.json"
            if cfg.exists():
                data = json.loads(cfg.read_text(encoding="utf-8"))
                saved = data.get("export_formats")
                if isinstance(saved, list) and saved:
                    valid = {k for k, _ in EXPORT_OPTIONS}
                    for key, _ in EXPORT_OPTIONS:
                        cb = self.query_one(f"#fmt-{key}", Checkbox)
                        cb.value = key in saved
        except Exception:
            pass

    def action_do_export(self):
        self._do_export()

    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == "btn-export":
            self._do_export()
        elif button_id == "btn-all":
            for key, _ in EXPORT_OPTIONS:
                self.query_one(f"#fmt-{key}", Checkbox).value = True
        elif button_id == "btn-none":
            for key, _ in EXPORT_OPTIONS:
                self.query_one(f"#fmt-{key}", Checkbox).value = False
        elif button_id == "btn-back":
            self.action_go_back()

    def _get_selected_formats(self) -> list[str]:
        """Return list of currently checked format keys."""
        selected = []
        for key, _ in EXPORT_OPTIONS:
            try:
                if self.query_one(f"#fmt-{key}", Checkbox).value:
                    selected.append(key)
            except Exception:
                continue
        return selected

    def _do_export(self):
        """Execute the export for all selected formats."""
        import asyncio

        formats = self._get_selected_formats()
        if not formats:
            self.query_one("#export-status", Static).update(
                "❌ Kein Format ausgewählt – bitte mindestens ein Häkchen setzen."
            )
            return

        names = ", ".join(f.upper() for f in formats)
        self.query_one("#export-status", Static).update(f"Exportiere als {names}...")
        asyncio.create_task(self._run_export(formats))

    async def _run_export(self, formats: list[str]):
        """Run the export process for multiple formats."""
        if not self._project_id:
            self.query_one("#export-status", Static).update("❌ Kein Projekt ausgewählt.")
            return

        try:
            from brokus.storage.database import get_project, get_all_chapters
            from brokus.storage.exporter import Exporter

            project = await get_project(self._project_id)
            chapters = await get_all_chapters(self._project_id)

            if not project:
                self.query_one("#export-status", Static).update("❌ Projekt nicht gefunden.")
                return

            exporter = Exporter()
            # Persist selection for next time
            try:
                import json
                from pathlib import Path
                cfg = Path.home() / ".config" / "brokus" / "cli_settings.json"
                if cfg.exists():
                    data = json.loads(cfg.read_text(encoding="utf-8"))
                    data["export_formats"] = formats
                    cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

            results: list = []
            errors: list[str] = []
            for fmt in formats:
                try:
                    output_path = exporter.export(project, chapters, fmt=fmt)
                    results.append((fmt, output_path))
                except ImportError as e:
                    module = str(e).split("'")[1] if "'" in str(e) else str(e)
                    errors.append(f"{fmt.upper()}: Bibliothek fehlt ({module})")
                except Exception as e:
                    errors.append(f"{fmt.upper()}: {e}")

            # Status message
            status = self.query_one("#export-status", Static)
            if results:
                lines = [f"✅ {len(results)} Format(e) exportiert:"]
                for fmt, p in results:
                    lines.append(f"  • {fmt.upper()} → {p.name}")
                if errors:
                    lines.append("")
                    lines.append("⚠ Fehler:")
                    lines.extend(f"  • {e}" for e in errors)
                status.update("\n".join(lines))
                self.notify(
                    f"{len(results)} Export(s) abgeschlossen",
                    title="Erfolg",
                )
            else:
                status.update("❌ Kein Format konnte exportiert werden.")
                self.notify("Export fehlgeschlagen", severity="error")

        except Exception as e:
            self.query_one("#export-status", Static).update(f"❌ Fehler: {e}")
            self.notify(f"Export fehlgeschlagen: {e}", severity="error")

    def action_go_back(self):
        self.app.navigate_to("editor")
