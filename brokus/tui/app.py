"""Main Textual application for brokus TUI."""

import asyncio
from textual.app import App
from textual.binding import Binding

from brokus.utils.logger import log
from brokus.tui.screens.welcome import WelcomeScreen
from brokus.tui.screens.new_book import NewBookScreen
from brokus.tui.screens.library import LibraryScreen
from brokus.tui.screens.generation import GenerationScreen
from brokus.tui.screens.editor import EditorScreen
from brokus.tui.screens.settings import SettingsScreen
from brokus.tui.screens.export import ExportScreen


# Theme CSS
BROKUS_CSS = """
/* ── Base ── */
Screen {
    background: $surface;
    color: $text;
}

/* ── Welcome Screen ── */
#welcome-container {
    width: 60;
    height: auto;
    margin: 2 0;
    align: center middle;
}

#welcome-ascii {
    content-align: center middle;
    color: $accent;
    background: $surface-darken-1;
    padding: 1 2;
    margin-bottom: 1;
}

#welcome-subtitle {
    content-align: center middle;
    color: $text-muted;
    margin-bottom: 2;
}

#welcome-buttons {
    width: 40;
    align: center middle;
}

#welcome-buttons Button {
    width: 100%;
    margin-bottom: 1;
}

/* ── Library ── */
#library-container {
    padding: 1 2;
}

#project-list {
    height: 1fr;
    border: solid $primary;
    margin: 1 0;
}

#library-stats {
    margin: 1 0;
    color: $text-muted;
}

#library-actions {
    align: center middle;
}

#library-actions Button {
    margin: 0 1;
}

/* ── New Book Wizard ── */
#wizard-main {
    padding: 1 2;
    height: 1fr;
}

#step-container {
    height: 1fr;
}

.wizard-header {
    color: $accent;
    text-style: bold;
    margin-bottom: 1;
}

.wizard-subtitle {
    color: $text-muted;
    margin-bottom: 1;
}

/* ── Navigation Bar ── */
#wizard-nav {
    dock: bottom;
    background: $surface-darken-2;
    padding: 0 2;
    height: 1;
}

#nav-bar {
    color: $text-disabled;
    content-align: center middle;
}

#hint-bar {
    dock: bottom;
    background: $surface-darken-2;
    padding: 0 2;
    height: 1;
}

.form-label {
    margin-top: 1;
    color: $text-muted;
}

.form-hint {
    color: $text-disabled;
}

.confirm-line {
    margin: 0;
    padding-left: 2;
    color: $text;
}

.confirm-question {
    color: $accent;
    text-style: bold;
    margin-top: 2;
}

.scope-line {
    color: $text;
    content-align: center middle;
    text-style: bold;
}

.scope-total {
    color: $accent;
    content-align: center middle;
}

.spacer {
    height: 1;
}

.spacer-h {
    width: 2;
}

#textarea-idea {
    height: 10;
    border: solid $primary;
}

#input-title {
    width: 100%;
}

.list-view {
    height: auto;
    border: solid $primary;
}

#char-count {
    color: $text-disabled;
    content-align: right middle;
}

/* ── Generation ── */
#generation-container {
    padding: 1 2;
}

#gen-title {
    color: $accent;
    text-style: bold;
}

#progress-container {
    margin: 1 0;
    padding: 1;
    border: solid $primary;
}

#progress-container Label {
    margin-bottom: 1;
}

#overall-bar, #current-bar {
    height: 1;
    margin-bottom: 1;
}

#pipeline-stages {
    margin: 1 0;
    padding: 1;
    border: solid $primary;
}

#pipeline-stages Static {
    margin: 0;
}

#log-container {
    margin: 1 0;
    height: 10;
}

#gen-actions {
    align: center middle;
}

#gen-actions Button {
    margin: 0 1;
}

/* ── Compliance Dashboard ── */
#gen-compliance-dash {
    margin: 1 0;
    padding: 1;
    border: solid $accent;
}

#compliance-dashboard {
    width: 100%;
}

#compliance-score-row {
    margin: 1 0;
}

#compliance-score-text {
    color: $text;
    text-style: bold;
}

#compliance-score-bar {
    height: 1;
    margin: 0 0 1 0;
}

#compliance-summary {
    color: $text-muted;
    margin-bottom: 1;
}

#compliance-checks {
    margin-bottom: 1;
}

#compliance-checks-text {
    color: $text-muted;
}

#compliance-tracker {
    color: $text-muted;
    padding: 1;
    border: dashed $primary;
}

/* ── Editor ── */
#editor-container {
    padding: 1 2;
}

#editor-main {
    height: 1fr;
}

#editor-content {
    width: 1fr;
    padding-left: 1;
}

#editor-title {
    color: $accent;
    text-style: bold;
}

#chapter-text {
    height: 1fr;
    border: solid $primary;
    margin: 1 0;
}

#editor-info {
    color: $text-muted;
}

#editor-actions {
    align: center middle;
    margin-top: 2;
}

#editor-actions Button {
    margin: 0 1;
}

/* ── Settings ── */
#settings-container {
    padding: 1 2;
}

.subsection-title {
    color: $accent;
    text-style: bold;
    margin-top: 1;
    margin-bottom: 1;
}

#settings-actions {
    align: center middle;
    margin-top: 2;
}

#settings-actions Button {
    margin: 0 1;
}

/* ── Export ── */
#export-container {
    padding: 1 2;
    width: 60;
}

#export-actions {
    align: center middle;
    margin-top: 2;
}

#export-actions Button {
    margin: 0 1;
}

#export-status {
    color: $text-muted;
    margin-top: 2;
    padding: 1;
}

/* ── Chapter Tree ── */
#chapter-tree {
    width: 25;
    border: solid $primary;
    padding: 1;
}

#chapter-tree ListView {
    height: 1fr;
}

/* ── Section Titles ── */
.section-title {
    color: $accent;
    text-style: bold;
    margin-bottom: 1;
}

/* ── Buttons ── */
Button {
    margin: 0;
}

/* ── Select ── */
Select {
    width: 30;
    margin-bottom: 1;
}

/* ── Input ── */
Input {
    width: 30;
    margin-bottom: 1;
}

/* ── TextArea ── */
TextArea {
    width: 100%;
}

/* ── RichLog ── */
RichLog {
    height: 1fr;
}

/* ── Switch ── */
Switch {
    margin-bottom: 1;
}
"""


class BrokusApp(App):
    """Main brokus Textual application."""

    CSS = BROKUS_CSS

    BINDINGS = [
        Binding("ctrl+q", "quit", "Beenden", show=False),
        Binding("ctrl+c", "quit", "Beenden", show=False),
    ]

    SCREENS = {
        "welcome": WelcomeScreen,
        "library": LibraryScreen,
        "new_book": NewBookScreen,
        "generation": GenerationScreen,
        "editor": EditorScreen,
        "settings": SettingsScreen,
        "export": ExportScreen,
    }

    def __init__(self):
        super().__init__()
        self.generation_params = {}
        self.selected_project_index = 0

    async def on_mount(self):
        """Initialize secrets, database, and show welcome screen."""
        try:
            from brokus.utils.crypto import load_secrets
            load_secrets()
            log.info("Secrets loaded")
        except Exception as e:
            log.warning(f"Secrets load failed: {e}")

        try:
            from brokus.storage.database import init_db
            await init_db()
            log.info("Database ready")
        except Exception as e:
            log.error(f"Database init failed: {e}")

        await self.push_screen("welcome")

    def navigate_to(self, name: str):
        """Switch to a named screen."""
        if name in self.SCREENS:
            screen_cls = self.SCREENS[name]
            screen = screen_cls()
            # Refresh screens that need it
            if name == "library":
                import asyncio
                asyncio.create_task(screen._refresh_projects())
            self.switch_screen(screen)
        else:
            log.warning(f"Unknown screen: {name}")


def run():
    """Entry point for the TUI application."""
    app = BrokusApp()
    app.run()


if __name__ == "__main__":
    run()
