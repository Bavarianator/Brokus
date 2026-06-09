"""Live log viewer widget."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, RichLog
from textual.reactive import reactive


class LiveLogViewer(Container):
    """Scrollable live log display for generation events."""

    max_lines = reactive(100)

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Live-Log", classes="section-title"),
            RichLog(highlight=True, markup=True, max_lines=100, id="live-log"),
            id="log-container",
        )

    def add_entry(self, timestamp: str, level: str, message: str):
        """Add a log entry to the live view."""
        log = self.query_one("#live-log", RichLog)

        colors = {
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "DEBUG": "dim",
        }
        color = colors.get(level.upper(), "white")

        log.write(f"[{color}][{timestamp}] [{level}] {message}[/{color}]")

    def clear(self):
        """Clear the log."""
        self.query_one("#live-log", RichLog).clear()
