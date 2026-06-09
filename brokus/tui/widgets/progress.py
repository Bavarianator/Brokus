"""Progress display widgets for brokus TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, ProgressBar, Label
from textual.reactive import reactive


class GenerationProgress(Container):
    """Overall + current chapter progress display."""

    overall_progress = reactive(0.0)
    current_progress = reactive(0.0)
    overall_label = reactive("Gesamt: 0/0")
    current_label = reactive("Aktuell: -")

    def compose(self) -> ComposeResult:
        with Container(id="progress-container"):
            yield Label(self.overall_label, id="overall-label")
            yield ProgressBar(total=100, id="overall-bar")
            yield Label(self.current_label, id="current-label")
            yield ProgressBar(total=100, id="current-bar")

    def watch_overall_progress(self, value: float):
        bar = self.query_one("#overall-bar", ProgressBar)
        bar.progress = value
        self.query_one("#overall-label", Label).update(self.overall_label)

    def watch_current_progress(self, value: float):
        bar = self.query_one("#current-bar", ProgressBar)
        bar.progress = value
        self.query_one("#current-label", Label).update(self.current_label)


class PipelineStatus(Container):
    """Pipeline stage status indicators."""

    stages = reactive([])  # List of (name, status, detail) tuples

    def compose(self) -> ComposeResult:
        yield Container(id="pipeline-stages")

    def watch_stages(self, stages: list):
        container = self.query_one("#pipeline-stages")
        container.remove_children()

        for name, status, detail in stages:
            icon = {"done": "✅", "active": "🔄", "pending": "⏳", "failed": "❌"}.get(
                status, "⏳"
            )
            container.mount(Static(f"{icon} {name}: {detail}"))


class ComplianceDashboard(Container):
    """Compliance-Status Dashboard mit Score und Element-Tracker."""

    compliance_score = reactive(0)
    compliance_passed = reactive(True)
    elements_done = reactive(0)
    elements_total = reactive(0)
    status_lines = reactive([])  # List of (icon, text) tuples
    tracker_text = reactive("")

    def compose(self) -> ComposeResult:
        with Container(id="compliance-dashboard"):
            yield Static("🔒 Compliance-Status", classes="subsection-title")

            with Container(id="compliance-score-row"):
                yield Static("Score: --", id="compliance-score-text")
                yield ProgressBar(total=100, id="compliance-score-bar")

            yield Static("", id="compliance-summary", classes="form-label")

            with Container(id="compliance-checks"):
                yield Static("", id="compliance-checks-text")

            yield Static("", id="compliance-tracker", classes="form-label")

    def watch_compliance_score(self, value: int):
        """Update score display."""
        bar = self.query_one("#compliance-score-bar", ProgressBar)
        bar.progress = value

        passed = value >= 75
        icon = "✅" if passed else "❌"
        self.query_one("#compliance-score-text", Static).update(
            f"Score: {icon} {value}/100"
        )

        if passed:
            self.query_one("#compliance-summary", Static).update(
                "Compliance bestanden – Kapitel akzeptiert."
            )
        else:
            self.query_one("#compliance-summary", Static).update(
                f"⚠️ Compliance fehlgeschlagen – Score unter 75. Korrektur läuft..."
            )

    def watch_status_lines(self, lines: list):
        """Update detailed check results."""
        text = "\n".join(
            f"{icon} {msg}" for icon, msg in lines
        )
        self.query_one("#compliance-checks-text", Static).update(text)

    def watch_tracker_text(self, text: str):
        """Update element tracker display."""
        self.query_one("#compliance-tracker", Static).update(text)