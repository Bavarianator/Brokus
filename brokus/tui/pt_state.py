"""brokus TUI – Application state and constants (prompt_toolkit).

Separated from the main app for clean architecture.
"""
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from prompt_toolkit.styles import Style
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout import Window


# ─────────────────────────────────────────────────────────────
# Style
# ─────────────────────────────────────────────────────────────

STYLE = Style.from_dict({
    "title": "bold",
    "sel": "bold reverse",
    "hint": "#888888",
    "ok": "#00ff00",
    "err": "#ff0000 bold",
    "bar": "bg:#333333 #ffffff",
    "sep": "#555555",
    "dim": "#666666",
    "cursor": "bold reverse",
    "text-area": "bg:#222222 #ffffff",
})

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

GENRES = [
    "fantasy", "scifi", "drama", "thriller", "romance",
    "horror", "mystery", "historical_fiction", "adventure",
    "dystopian", "young_adult", "literary_fiction", "paranormal",
    "erotica", "comedy", "action", "post_apocalyptic",
    "steampunk", "cyberpunk", "urban_fantasy", "magical_realism",
    "military", "western", "gothic", "noir", "fairy_tale",
    "slice_of_life", "superhero", "survival", "biography",
    "children", "satire", "experimental",
]
GENRE_NAMES = [
    "Fantasy", "Science Fiction", "Drama", "Thriller", "Romance / Liebesroman",
    "Horror", "Mystery / Krimi", "Historischer Roman", "Abenteuer",
    "Dystopie", "Young Adult", "Literarische Fiktion", "Paranormal",
    "Erotica", "Comedy / Humor", "Action", "Post-Apokalypse",
    "Steampunk", "Cyberpunk", "Urban Fantasy", "Magischer Realismus",
    "Military / Kriegsroman", "Western", "Gothic", "Noir / Hardboiled", "Märchen / Fairy Tale",
    "Slice of Life", "Superhelden", "Survival", "Biographie / Memoir",
    "Kinderbuch", "Satire", "Experimentell",
]
EXPORT_FORMATS = ["Markdown (.md)", "EPUB (.epub)", "PDF (.pdf)", "Word (.docx)", "JSON (.json)", "Nur Text (.txt)"]
EXPORT_KEYS = ["md", "epub", "pdf", "docx", "json", "txt"]

LANGUAGES = [
    "Deutsch",
    "Englisch",
    "Französisch",
    "Spanisch",
    "Italienisch",
    "Portugiesisch",
    "Niederländisch",
    "Russisch",
    "Polnisch",
    "Türkisch",
    "Japanisch",
    "Chinesisch",
]

# Map language names to ISO codes (for export)
LANG_TO_CODE: dict[str, str] = {
    "Deutsch": "de", "Englisch": "en", "Französisch": "fr",
    "Spanisch": "es", "Italienisch": "it", "Portugiesisch": "pt",
    "Niederländisch": "nl", "Russisch": "ru", "Polnisch": "pl",
    "Türkisch": "tr", "Japanisch": "ja", "Chinesisch": "zh",
}
AUDIENCES = ["Kinder (8-12)", "Jugendliche (13-17)", "Young Adult (18-25)", "Erwachsene"]
PERSPECTIVES = ["Ich-Perspektive", "Dritte Person (personal)", "Dritte Person (auktorial)", "Wechselnde Perspektiven"]
TONES = ["Duester & melancholisch", "Spannend & dramatisch", "Hoffnungsvoll & warm", "Humorvoll & leicht", "Episch & ernst"]
LENGTHS = [
    ("Kurzgeschichte  (~5.000 W,  3 Kap.)", 5000, 3),
    ("Novelle         (~20.000 W,  8 Kap.)", 20000, 8),
    ("Roman           (~50.000 W, 12 Kap.)", 50000, 12),
    ("Epos            (~90.000 W, 20 Kap.)", 90000, 20),
]

# Text-input screens (where the TextArea is visible)
TEXT_SCREENS = frozenset({"schnell_0", "schnell_1", "meister_0", "meister_1", "settings_k", "settings_custom_model"})

SEP = ("class:sep", "  " + "\u2500" * 44 + "\n")


# ─────────────────────────────────────────────────────────────
# Application State
# ─────────────────────────────────────────────────────────────

@dataclass
class AppState:
    """Mutable application state – replaces the old global class S."""

    # Current screen
    scr: str = "menu"
    msg: str = ""

    # Wizard state
    mode: str = ""          # "schnell" | "meister"
    step: int = 0
    idea: str = ""
    title: str = ""
    genre: int = 0
    language: int = 0  # 0 = Deutsch
    audience: int = 1
    perspective: int = 0
    tone: int = 1
    length: int = 2

    # Library
    books: list[dict] = field(default_factory=list)
    book_sel: int = 0

    # Generation
    gen_title: str = ""
    gen_prog: float = 0.0
    gen_stage: str = ""
    gen_comp: int = 0
    gen_task: Any = None      # asyncio.Task

    # Reading
    chapters: list[dict] = field(default_factory=list)
    ch_idx: int = 0

    # Settings
    settings_providers: list[dict] = field(default_factory=list)
    settings_prov_idx: int = 0
    settings_buf: str = ""
    settings_cur_provider: str = "anthropic"
    settings_cur_model: str = "claude-sonnet-4-5"
    settings_export_fmt: int = 0  # Legacy – von settings_export_fmts abgelöst
    settings_export_fmts: list[str] = field(default_factory=lambda: ["md", "epub"])

    # prompt_toolkit widgets (set at runtime)
    app: Any = None
    input_buffer: Optional[Buffer] = None
    input_area: Optional[TextArea] = None
    input_window: Optional[Window] = None
    main_window: Optional[Window] = None

    # ── Derived properties ──

    @property
    def is_text_screen(self) -> bool:
        return self.scr in TEXT_SCREENS

    @property
    def genre_key(self) -> str:
        if 0 <= self.genre < len(GENRES):
            return GENRES[self.genre]
        return "fantasy"

    @property
    def genre_name(self) -> str:
        if 0 <= self.genre < len(GENRE_NAMES):
            return GENRE_NAMES[self.genre]
        return "?"

    @property
    def export_key(self) -> str:
        if 0 <= self.settings_export_fmt < len(EXPORT_KEYS):
            return EXPORT_KEYS[self.settings_export_fmt]
        return "md"

    @property
    def export_keys(self) -> list[str]:
        """List of currently selected export format keys (defaults to ['md', 'epub'])."""
        if self.settings_export_fmts:
            valid = set(EXPORT_KEYS)
            keys = [k for k in self.settings_export_fmts if k in valid]
            if keys:
                return keys
        return ["md"]

    @property
    def chapter_count(self) -> int:
        if 0 <= self.length < len(LENGTHS):
            return LENGTHS[self.length][2]
        return 20

    @property
    def display_title(self) -> str:
        return self.title or (self.idea[:40] if self.idea else "?")

    def reset_wizard(self, mode: str):
        """Reset wizard state for a new book."""
        self.mode = mode
        self.step = 0
        self.idea = ""
        self.title = ""
        self.genre = 0
        self.language = 0
        self.audience = 1
        self.perspective = 0
        self.tone = 1
        self.length = 2

    def get_cur_provider(self) -> dict | None:
        """Get the current provider config dict."""
        for p in self.settings_providers:
            if p["key"] == self.settings_cur_provider:
                return p
        return None

    def has_api_key(self) -> bool:
        """Check if the current provider has an API key set."""
        p = self.get_cur_provider()
        if not p:
            return False
        ev = p.get("env", "")
        if not ev:
            return False
        try:
            from brokus.utils.crypto import SecretStore
            if SecretStore.instance().get(ev):
                return True
        except Exception:
            pass
        return bool(os.getenv(ev, ""))
