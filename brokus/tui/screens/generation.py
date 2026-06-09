"""Generation screen – live view with compliance dashboard and book opener."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button, Header, Footer
from textual.binding import Binding

from brokus.tui.widgets.progress import GenerationProgress, PipelineStatus, ComplianceDashboard
from brokus.tui.widgets.log_viewer import LiveLogViewer
from brokus.utils.i18n import t


class GenerationScreen(Screen):
    """Live generation view with compliance dashboard and book opener."""

    BINDINGS = [
        Binding("p", "toggle_pause", t("tui.generation.binding_pause")),
        Binding("s", "stop_generation", t("tui.generation.binding_stop")),
        Binding("o", "open_book", t("tui.generation.binding_open")),
        Binding("f2", "show_compliance", t("tui.generation.binding_compliance")),
        Binding("escape", "go_back", t("tui.generation.binding_back")),
    ]

    def __init__(self):
        super().__init__()
        self._generation_active = False
        self._paused = False
        self._pipeline = None
        self._book_path = None
        self._book_path_epub = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="generation-container"):
            yield Static(t("section.generation"), id="gen-title", classes="section-title")
            yield GenerationProgress(id="gen-progress")
            yield PipelineStatus(id="pipeline-status")
            with Container(id="gen-compliance-dash"):
                yield ComplianceDashboard(id="compliance-dashboard")
            yield LiveLogViewer(id="live-log-viewer")
            with Horizontal(id="gen-actions"):
                yield Button(t("tui.generation.btn_pause"), id="btn-pause", variant="primary")
                yield Button(t("tui.generation.btn_stop"), id="btn-stop", variant="error")
                yield Button(t("tui.generation.btn_folder"), id="btn-open-folder")
                yield Button(t("tui.generation.btn_open_book"), id="btn-open-book")
                yield Button(t("tui.generation.btn_log"), id="btn-export-log")
        yield Footer()

    async def on_mount(self):
        """Start generation when screen mounts."""
        await self._start_generation()

    async def _start_generation(self):
        """Begin the book generation pipeline."""
        params = getattr(self.app, "generation_params", None)
        if not params:
            self.notify(t("tui.generation.no_params"), severity="error")
            self.app.navigate_to("library")
            return

        title = params.get("title", t("tui.library.untitled"))
        self.query_one("#gen-title", Static).update(
            t("tui.generation.title_prefix", title=title)
        )

        self._generation_active = True
        self._paused = False

        try:
            from brokus.storage.database import (
                create_project, update_project, save_chapter, log_generation_event,
            )
            project_id = await create_project(
                title=title,
                genre=params.get("genre", "fantasy"),
                idea=params.get("idea", ""),
                total_chapters=params.get("num_chapters", 20),
                model=params.get("model", "claude-sonnet-4-5"),
            )
        except Exception as e:
            self._add_log("ERROR", t("tui.generation.db_error", error=e))
            self.notify(t("common.error_prefix", default="") + str(e), severity="error")
            return

        from brokus.ai.client import BrokusAIClient
        from brokus.ai.prompts import PromptLoader, GenreLoader
        from brokus.core.pipeline import BookPipeline

        client = BrokusAIClient(
            provider=params.get("provider", "anthropic"),
            model=params.get("model", "claude-sonnet-4-5"),
            temperature=0.7,
            max_tokens=4000,
        )
        prompts = PromptLoader()
        genres = GenreLoader()

        pipeline = BookPipeline(client=client, prompts=prompts, genres=genres)
        self._pipeline = pipeline

        def on_progress(stage, progress, message):
            self._update_progress(stage, progress, message)

        pipeline.set_progress_callback(on_progress)

        def on_compliance(score, status_lines, tracker_text):
            self._update_compliance(score, status_lines, tracker_text)

        pipeline.set_compliance_callback(on_compliance)

        async def log_cb(event, level="INFO", chapter_number=None, details=None):
            await log_generation_event(project_id, event, level, chapter_number, details)
            self._add_log(level, event)

        async def save_cb(chapter_num, chapter_title, text, **kwargs):
            await save_chapter(
                project_id=project_id, number=chapter_num, title=chapter_title,
                text=text, word_count=kwargs.get("word_count", 0),
                compliance_score=kwargs.get("compliance_score"),
                status=kwargs.get("status", "completed"),
                elements_covered=kwargs.get("elements_covered", []),
            )
            await update_project(
                project_id,
                chapters_completed=chapter_num,
                total_words=kwargs.get("word_count", 0),
                status="generating",
            )

        try:
            self._add_log("INFO", t("tui.generation.starting", title=title, n=params.get('num_chapters', 20)))
            result = await pipeline.run(
                book_idea=params.get("idea", ""),
                genre_key=params.get("genre", "fantasy"),
                num_chapters=params.get("num_chapters", 20),
                save_chapter_cb=save_cb,
                log_event_cb=log_cb,
            )
            await update_project(project_id, status="completed",
                total_words=result.get("total_words", 0),
                synopsis=result.get("synopsis", ""),
            )
            self._generation_active = False
            self._add_log("INFO", t("tui.generation.finished", n=result.get('total_chapters', 0), w=result.get('total_words', 0)))
            self.notify(t("tui.generation.done_title"), title=t("tui.generation.success"))
            await self._export_for_opening(project_id)
        except Exception as e:
            self._add_log("ERROR", f"{t('common.error_prefix', default='Fehler: ')}{e}")
            await update_project(project_id, status="failed")
            self._generation_active = False
            self.notify(f"{t('common.error_prefix', default='Fehler: ')}{e}", severity="error")

    def _update_compliance(self, score, status_lines, tracker_text):
        """Update compliance dashboard."""
        try:
            dash = self.query_one("#compliance-dashboard", ComplianceDashboard)
            dash.compliance_score = score
            dash.status_lines = status_lines
            dash.tracker_text = tracker_text
        except Exception:
            pass

    async def _export_for_opening(self, project_id):
        """Export completed book for opening."""
        try:
            from brokus.storage.database import get_project, get_all_chapters
            from brokus.storage.exporter import Exporter
            project = await get_project(project_id)
            chapters = await get_all_chapters(project_id)
            if project and chapters:            exporter = Exporter()
            self._book_path = str(exporter.export(project, chapters, fmt="md"))
            self._add_log("INFO", t("tui.generation.export_done", path=self._book_path))
        except Exception as e:
            self._add_log("WARNING", t("tui.generation.export_warning", error=e))

    def _update_progress(self, stage, progress, message):
        """Update progress bars and pipeline status."""
        try:
            overall = self.query_one("#gen-progress", GenerationProgress)
            overall.overall_progress = progress * 100
            overall.overall_label = message
            stages = self.query_one("#pipeline-status", PipelineStatus)
            all_stages = ["DNA", "Kernelemente", "Synopsis", "Charaktere", "Kapitelplan", "Kapitel"]
            stage_list = []
            for s in all_stages:
                thresholds = {"DNA": 0.04, "Kernelemente": 0.08, "Synopsis": 0.15,
                            "Charaktere": 0.22, "Kapitelplan": 0.30}
                status = "done" if progress > thresholds.get(s, 0) else "pending"
                if progress > 0.90:
                    status = "done"
                stage_list.append((s, status, ""))
            stages.stages = stage_list
            self._add_log("DEBUG", message)
        except Exception:
            pass

    def _add_log(self, level, message):
        """Add entry to live log viewer."""
        try:
            from datetime import datetime
            log_viewer = self.query_one("#live-log-viewer", LiveLogViewer)
            log_viewer.add_entry(datetime.now().strftime("%H:%M:%S"), level, message)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == "btn-pause":
            self.action_toggle_pause()
        elif button_id == "btn-stop":
            self.action_stop_generation()
        elif button_id == "btn-open-folder":
            self.action_open_book_folder()
        elif button_id == "btn-open-book":
            self.action_open_book()
        elif button_id == "btn-export-log":
            self.action_export_log()

    def action_toggle_pause(self):
        if not self._generation_active:
            return
        self._paused = not self._paused
        label = (
            t("tui.generation.btn_open_book") if self._paused
            else t("tui.generation.btn_pause")
        )
        self.query_one("#btn-pause", Button).label = label
        status = (
            t("tui.generation.notify_pause") if self._paused
            else t("tui.generation.notify_resume")
        )
        self._add_log("INFO", status)
        self.notify(status)

    def action_stop_generation(self):
        if self._pipeline:
            self._pipeline.stop()
        self._generation_active = False
        self._add_log("WARNING", t("tui.generation.stopped"))
        self.notify(t("tui.generation.notify_stop"), severity="warning")

    def action_open_book(self):
        if self._book_path:
            try:
                from brokus.utils.opener import BookOpener
                BookOpener.open_file(self._book_path)
                self.notify(t("tui.generation.book_opened"), title=t("tui.generation.book_open_info"))
            except Exception as e:
                self.notify(f"{t('common.error_prefix', default='Fehler: ')}{e}", severity="error")
        else:
            self.notify(t("tui.generation.no_export"), severity="warning")

    def action_open_book_folder(self):
        path = self._book_path or "data/books"
        try:
            from brokus.utils.opener import BookOpener
            BookOpener.open_folder(path)
            self.notify(t("tui.generation.folder_opened"), title=t("tui.generation.book_open_info"))
        except Exception as e:
            self.notify(f"{t('common.error_prefix', default='Fehler: ')}{e}", severity="error")

    def action_export_log(self):
        self.notify(t("tui.generation.log_export_todo"))

    def action_go_back(self):
        if self._generation_active:
            self.notify(t("tui.generation.running_hint"), severity="warning")
        else:
            self.app.navigate_to("library")
