"""Library screen – browse and manage saved projects."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Static, ListView, ListItem, Label, Button, Header, Footer
from textual.binding import Binding


class LibraryScreen(Screen):
    """Main library showing all book projects."""

    BINDINGS = [
        Binding("n", "new_book", "Neues Buch"),
        Binding("enter", "open_project", "Öffnen"),
        Binding("d", "delete_project", "Löschen"),
        Binding("e", "open_settings", "Einstellungen"),
        Binding("q", "quit", "Beenden"),
        Binding("escape", "go_back", "Zurück"),
        Binding("up", "move_up", "Auf"),
        Binding("down", "move_down", "Ab"),
        Binding("1", "select_project(1)", ""),
        Binding("2", "select_project(2)", ""),
        Binding("3", "select_project(3)", ""),
        Binding("4", "select_project(4)", ""),
        Binding("5", "select_project(5)", ""),
        Binding("6", "select_project(6)", ""),
        Binding("7", "select_project(7)", ""),
        Binding("8", "select_project(8)", ""),
        Binding("9", "select_project(9)", ""),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="library-container"):
            yield Static("📚 Deine Bibliothek", classes="section-title")
            yield ListView(id="project-list")
            with Container(id="library-stats"):
                yield Static("📊 Statistiken: Lade...", id="stats-label")
            with Horizontal(id="library-actions"):
                yield Button("📖 Neu", id="btn-new", variant="primary")
                yield Button("📂 Öffnen", id="btn-open")
                yield Button("🗑️ Löschen", id="btn-delete", variant="error")
                yield Button("⚙️ Einstellungen", id="btn-settings")
        yield Footer()

    async def on_mount(self):
        """Load projects on mount."""
        await self._refresh_projects()

    async def _refresh_projects(self):
        """Load projects from database and update the list."""
        try:
            from brokus.storage.database import get_all_projects
            projects = await get_all_projects()
        except Exception as e:
            self.query_one("#stats-label", Static).update(f"Fehler beim Laden: {e}")
            return

        list_view = self.query_one("#project-list", ListView)
        list_view.clear()

        total_words = 0
        status_counts = {"completed": 0, "generating": 0, "paused": 0, "draft": 0, "failed": 0}

        for p in projects:
            total_words += p.get("total_words", 0)
            status = p.get("status", "draft")
            status_counts[status] = status_counts.get(status, 0) + 1

            status_icon = {
                "completed": "✅ Fertig",
                "generating": "🔄 Aktiv",
                "paused": "⏸ Pausiert",
                "draft": "📝 Entwurf",
                "failed": "❌ Fehler",
            }.get(status, "❓")

            chapters_done = p.get("chapters_completed", 0)
            chapters_total = p.get("total_chapters", 20)
            genre = p.get("genre", "?")
            title = p.get("title", "Unbenannt")

            list_view.append(
                ListItem(
                    Static(
                        f"▸ {title[:40]:<40} [{genre[:12]:<12}] "
                        f"{chapters_done}/{chapters_total} Kap.  {status_icon}"
                    )
                )
            )

        stats = (
            f"📊 {len(projects)} Projekte | {total_words:,} Wörter | "
            + " | ".join(
                f"{v} {k}" for k, v in status_counts.items() if v > 0
            )
        )
        self.query_one("#stats-label", Static).update(stats)

    async def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == "btn-new":
            self.action_new_book()
        elif button_id == "btn-open":
            await self.action_open_project()
        elif button_id == "btn-delete":
            await self.action_delete_project()
        elif button_id == "btn-settings":
            self.action_open_settings()

    def action_new_book(self):
        self.app.navigate_to("new_book")

    def action_open_project(self):
        list_view = self.query_one("#project-list", ListView)
        if list_view.index is not None and list_view.index < len(list_view.children):
            self.app.selected_project_index = list_view.index
            # Navigate to editor
            self.app.navigate_to("editor")
        else:
            self.notify("Kein Projekt ausgewählt.", severity="warning")

    async def action_delete_project(self):
        list_view = self.query_one("#project-list", ListView)
        if list_view.index is not None and list_view.index < len(list_view.children):
            try:
                from brokus.storage.database import get_all_projects, delete_project
                projects = await get_all_projects()
                if list_view.index < len(projects):
                    project = projects[list_view.index]
                    await delete_project(project["id"])
                    self.notify(f"'{project['title']}' gelöscht.")
                    await self._refresh_projects()
            except Exception as e:
                self.notify(f"Fehler beim Löschen: {e}", severity="error")
        else:
            self.notify("Kein Projekt ausgewählt.", severity="warning")

    def action_move_up(self):
        list_view = self.query_one("#project-list", ListView)
        idx = list_view.index or 0
        if idx > 0:
            list_view.index = idx - 1

    def action_move_down(self):
        list_view = self.query_one("#project-list", ListView)
        idx = list_view.index or 0
        if idx < len(list_view.children) - 1:
            list_view.index = idx + 1

    def action_select_project(self, num: int):
        list_view = self.query_one("#project-list", ListView)
        idx = int(num) - 1  # 1-based → 0-based (num is str from binding)
        if 0 <= idx < len(list_view.children):
            list_view.index = idx

    def action_open_settings(self):
        self.app.navigate_to("settings")

    def action_go_back(self):
        self.app.navigate_to("welcome")
