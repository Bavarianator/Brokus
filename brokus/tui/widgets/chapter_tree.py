"""Chapter tree widget for navigation in the editor."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, ListView, ListItem
from textual.reactive import reactive
from textual.message import Message


class ChapterTree(Container):
    """Chapter navigation tree for the editor."""

    class ChapterSelected(Message):
        """Emitted when a chapter is selected."""
        def __init__(self, chapter_number: int):
            super().__init__()
            self.chapter_number = chapter_number

    chapters = reactive([])  # List of (number, title, status) tuples
    selected_chapter = reactive(1)

    def compose(self) -> ComposeResult:
        yield Container(
            Static("Kapitel", classes="section-title"),
            ListView(id="chapter-list"),
            id="chapter-tree",
        )

    def watch_chapters(self, chapters: list):
        """Update the chapter list when chapters change."""
        list_view = self.query_one("#chapter-list", ListView)
        list_view.clear()

        status_icons = {
            "completed": "✅",
            "generating": "🔄",
            "planned": "▸",
            "failed": "❌",
        }

        for num, title, status in chapters:
            icon = status_icons.get(status, "▸")
            marker = "▶" if num == self.selected_chapter else " "
            list_view.append(
                ListItem(
                    Static(f"{marker} {icon} {num:2d}. {title[:30]}")
                )
            )

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle chapter selection."""
        if event.item_index is not None and self.chapters:
            chapter_num = self.chapters[event.item_index][0]
            self.selected_chapter = chapter_num
            self.post_message(self.ChapterSelected(chapter_num))
