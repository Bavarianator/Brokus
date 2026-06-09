"""Chapter editor screen with side panel and text editing."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import (
    Static, TextArea, Button, ListView, ListItem, Header, Footer,
)
from textual.binding import Binding

from brokus.tui.widgets.chapter_tree import ChapterTree


class EditorScreen(Screen):
    """Chapter editor with navigation tree and text area."""

    BINDINGS = [
        Binding("r", "regenerate", "Regenerieren"),
        Binding("e", "edit_mode", "Editieren"),
        Binding("f", "continue_gen", "Fortsetzen"),
        Binding("right", "next_chapter", "Nächstes Kap."),
        Binding("left", "prev_chapter", "Vorheriges Kap."),
        Binding("escape", "go_back", "Zurück"),
    ]

    def __init__(self):
        super().__init__()
        self._project_id = None
        self._chapters = []
        self._current_chapter = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="editor-container"):
            with Horizontal(id="editor-main"):
                yield ChapterTree(id="chapter-tree")
                with Container(id="editor-content"):
                    yield Static("Kapitel: ", id="editor-title", classes="section-title")
                    yield TextArea(id="chapter-text", read_only=True)
                    yield Static("Wörter: 0 | Lesezeit: ~0 Min | Compliance: -", id="editor-info")
            with Horizontal(id="editor-actions"):
                yield Button("🔄 Regenerieren", id="btn-regenerate")
                yield Button("✏️ Editieren", id="btn-edit")
                yield Button("▶ Fortsetzen", id="btn-continue")
                yield Button("→ Nächstes", id="btn-next")
                yield Button("📤 Export", id="btn-export", variant="primary")
        yield Footer()

    async def on_mount(self):
        """Load project chapters on mount."""
        project_index = getattr(self.app, "selected_project_index", 0)
        try:
            from brokus.storage.database import get_all_projects, get_all_chapters
            projects = await get_all_projects()
            if project_index < len(projects):
                p = projects[project_index]
                self._project_id = p["id"]
                self._chapters = await get_all_chapters(self._project_id)

            if self._chapters:
                self._current_chapter = 0
                self._load_chapter()
            else:
                self.query_one("#editor-title", Static).update("Keine Kapitel gefunden")
        except Exception as e:
            self.query_one("#editor-title", Static).update(f"Fehler: {e}")

    def _load_chapter(self):
        """Load the current chapter into the editor."""
        if not self._chapters or self._current_chapter >= len(self._chapters):
            return

        ch = self._chapters[self._current_chapter]
        self.query_one("#editor-title", Static).update(
            f'Kapitel {ch["number"]}: "{ch["title"]}"'
        )
        self.query_one("#chapter-text", TextArea).load_text(ch.get("text", ""))
        words = ch.get("word_count", 0)
        compliance = ch.get("compliance_score", "-")
        mins = max(1, words // 250)
        self.query_one("#editor-info", Static).update(
            f"Wörter: {words:,} | Lesezeit: ~{mins} Min | Compliance: {compliance}"
        )

        # Update chapter tree
        tree = self.query_one("#chapter-tree", ChapterTree)
        tree.chapters = [
            (c["number"], c["title"], c.get("status", "planned"))
            for c in self._chapters
        ]
        tree.selected_chapter = ch["number"]

    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == "btn-regenerate":
            self.action_regenerate()
        elif button_id == "btn-edit":
            self.action_edit_mode()
        elif button_id == "btn-continue":
            self.action_continue_gen()
        elif button_id == "btn-next":
            self.action_next_chapter()
        elif button_id == "btn-export":
            self.app.navigate_to("export")

    def on_chapter_tree_chapter_selected(self, message: ChapterTree.ChapterSelected):
        """Handle chapter selection from tree widget."""
        for i, ch in enumerate(self._chapters):
            if ch["number"] == message.chapter_number:
                self._current_chapter = i
                self._load_chapter()
                break

    def action_regenerate(self):
        self.notify("Regenerierung startet...")
        # TODO: implement chapter regeneration

    def action_edit_mode(self):
        text_area = self.query_one("#chapter-text", TextArea)
        text_area.read_only = not text_area.read_only
        status = "aktiviert" if not text_area.read_only else "deaktiviert"
        self.notify(f"Editieren {status}")

    def action_continue_gen(self):
        self.notify("Fortsetzung startet...")
        # TODO: implement continuation

    def action_next_chapter(self):
        if self._current_chapter < len(self._chapters) - 1:
            self._current_chapter += 1
            self._load_chapter()

    def action_prev_chapter(self):
        if self._current_chapter > 0:
            self._current_chapter -= 1
            self._load_chapter()

    def action_go_back(self):
        self.app.navigate_to("library")
