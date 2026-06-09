"""Welcome / start screen for brokus."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Center, Vertical
from textual.widgets import Static, Button, Header, Footer
from textual.binding import Binding


class WelcomeScreen(Screen):
    """Welcome screen with ASCII art and main menu."""

    BINDINGS = [
        Binding("n", "new_book", "Neues Buch"),
        Binding("o", "open_library", "Bibliothek"),
        Binding("e", "open_settings", "Einstellungen"),
        Binding("q", "quit", "Beenden"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Center():
            with Vertical(id="welcome-container"):
                yield Static(
                    r"""
   ___
  / _ )_______  __ ___  ______
 / _  / __/ _ \/ //_/ / / / __/
/____/_/  \___/\___/\_//_/\__/

        KI-Buchgenerator v1.0
""",
                    id="welcome-ascii",
                )
                yield Static(
                    "Erstelle komplette Romane mit KI-Unterstützung – "
                    "direkt im Terminal.",
                    id="welcome-subtitle",
                )
                with Container(id="welcome-buttons"):
                    yield Button("📖 Neues Buch", id="btn-new", variant="primary")
                    yield Button("📚 Bibliothek öffnen", id="btn-library")
                    yield Button("⚙️ Einstellungen", id="btn-settings")
                    yield Button("❓ Hilfe", id="btn-help")

        yield Footer()

    def action_new_book(self):
        self.app.navigate_to("new_book")

    def action_open_library(self):
        self.app.navigate_to("library")

    def action_open_settings(self):
        self.app.navigate_to("settings")

    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == "btn-new":
            self.action_new_book()
        elif button_id == "btn-library":
            self.action_open_library()
        elif button_id == "btn-settings":
            self.action_open_settings()
        elif button_id == "btn-help":
            self.notify("brokus v1.0 – Nutze [N] für neues Buch, [O] für Bibliothek.", title="Hilfe")
