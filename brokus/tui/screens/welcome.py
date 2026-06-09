"""Welcome / start screen for brokus."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Center, Vertical
from textual.widgets import Static, Button, Header, Footer
from textual.binding import Binding

from brokus.utils.i18n import t


class WelcomeScreen(Screen):
    """Welcome screen with ASCII art and main menu."""

    BINDINGS = [
        Binding("n", "new_book", t("tui.welcome.binding_new")),
        Binding("o", "open_library", t("tui.welcome.binding_library")),
        Binding("e", "open_settings", t("tui.welcome.binding_settings")),
        Binding("q", "quit", t("tui.welcome.binding_quit")),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Center():
            with Vertical(id="welcome-container"):
                yield Static(
                    "[bold bright_blue]"
                    + "\n".join(
                        [
                            "██████  ██████   ██████  ██   ██ ██    ██ ███████ ",
                            "██   ██ ██   ██ ██    ██ ██  ██  ██    ██ ██      ",
                            "██████  ██████  ██    ██ █████   ██    ██ ███████ ",
                            "██   ██ ██   ██ ██    ██ ██  ██  ██    ██      ██ ",
                            "██████  ██   ██  ██████  ██   ██  ██████  ███████ ",
                        ]
                    )
                    + "[/bold bright_blue]",
                    id="welcome-ascii",
                )
                yield Static(
                    t("tui.welcome.subtitle_long"),
                    id="welcome-subtitle",
                )
                with Container(id="welcome-buttons"):
                    yield Button(t("tui.welcome.btn_new"), id="btn-new", variant="primary")
                    yield Button(t("tui.welcome.btn_library"), id="btn-library")
                    yield Button(t("tui.welcome.btn_settings"), id="btn-settings")
                    yield Button(t("tui.welcome.btn_help"), id="btn-help")

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
            self.notify(
                t("tui.welcome.help_notify_msg"),
                title=t("tui.welcome.help_notify_title"),
            )
