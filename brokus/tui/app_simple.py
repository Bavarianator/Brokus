"""brokus – Einfacher, schöner CLI-Modus mit Rich.

Kein Full-Screen. Keine verwirrenden Tastenkürzel.
Einfach Tippen, Enter drücken, fertig.
Alle Eingaben über _read_line() (roher Zeichenleser) – behebt Paste-Probleme.
"""
import asyncio
import json
import os
import select
import sys
import termios
import tty
from dataclasses import dataclass, asdict, field
from getpass import getpass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule

from brokus.utils.i18n import (
    t, set_language, get_language, available_languages, language_name,
)
from brokus.utils.logger import log

console = Console()

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

GENRES = [
    ("fantasy", "Fantasy"),
    ("scifi", "Science Fiction"),
    ("drama", "Drama"),
    ("thriller", "Thriller"),
    ("romance", "Romance / Liebesroman"),
    ("horror", "Horror"),
    ("mystery", "Mystery / Krimi"),
    ("historical_fiction", "Historischer Roman"),
    ("adventure", "Abenteuer"),
    ("dystopian", "Dystopie"),
    ("young_adult", "Young Adult"),
    ("literary_fiction", "Literarische Fiktion"),
    ("paranormal", "Paranormal"),
    ("erotica", "Erotica"),
    ("comedy", "Comedy / Humor"),
    ("action", "Action"),
    ("post_apocalyptic", "Post-Apokalypse"),
    ("steampunk", "Steampunk"),
    ("cyberpunk", "Cyberpunk"),
    ("urban_fantasy", "Urban Fantasy"),
    ("magical_realism", "Magischer Realismus"),
    ("military", "Military / Kriegsroman"),
    ("western", "Western"),
    ("gothic", "Gothic"),
    ("noir", "Noir / Hardboiled"),
    ("fairy_tale", "Märchen / Fairy Tale"),
    ("slice_of_life", "Slice of Life"),
    ("superhero", "Superhelden"),
    ("survival", "Survival"),
    ("biography", "Biographie / Memoir"),
    ("children", "Kinderbuch"),
    ("satire", "Satire"),
    ("experimental", "Experimentell"),
]

LENGTHS = [
    ("Minigeschichte", 1500, 1, "~5 Seiten"),
    ("Kurzgeschichte", 5000, 3, "~17 Seiten"),
    ("Novelle", 20000, 8, "~67 Seiten"),
    ("Kurzroman", 35000, 10, "~117 Seiten"),
    ("Roman", 50000, 12, "~167 Seiten"),
    ("Epischer Roman", 75000, 16, "~250 Seiten"),
    ("Epos", 100000, 20, "~333 Seiten"),
    ("Megaroman", 150000, 30, "~500 Seiten"),
]  # (name, words, chapters, page_estimate)

WORD_TARGET_OPTION = "📏 Wörter-Ziel – ich lege die Gesamtwörterzahl fest"

AUDIENCES = ["Kinder (8-12)", "Jugendliche (13-17)", "Young Adult (18-25)", "Erwachsene"]
PERSPECTIVES = [
    "Ich-Perspektive (1. Person)",
    "Ich-Perspektive, mehrere Erzähler",
    "Dritte Person, personal (nah an einer Figur)",
    "Dritte Person, personal (multiple Perspektiven)",
    "Dritte Person, auktorial (allwissend)",
    "Dritte Person, neutral (Beobachter)",
    "Wechselnd: Ich & Dritte Person",
    "Briefroman / Tagebuchform",
]
TONES = ["Duester & melancholisch", "Spannend & dramatisch", "Hoffnungsvoll & warm", "Humorvoll & leicht", "Episch & ernst"]
EXPORT_FORMATS = [("md", "Markdown (.md)"), ("epub", "EPUB (.epub)"), ("pdf", "PDF (.pdf)"), ("docx", "Word (.docx)"), ("json", "JSON (.json)"), ("txt", "Nur Text (.txt)")]

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

LANG_TO_CODE: dict[str, str] = {
    "Deutsch": "de", "Englisch": "en", "Französisch": "fr",
    "Spanisch": "es", "Italienisch": "it", "Portugiesisch": "pt",
    "Niederländisch": "nl", "Russisch": "ru", "Polnisch": "pl",
    "Türkisch": "tr", "Japanisch": "ja", "Chinesisch": "zh",
}

DETAIL_LEVELS = [
    ("lockers", "Lockers – KI hat mehr Freiheit bei der Umsetzung"),
    ("standard", "Standard – Ausgewogene Treue zur Idee"),
    ("detailiert", "Detailiert – Idee wird genau umgesetzt"),
    ("streng", "Streng – Maximale Treue, minimale Abweichung"),
]

COMPLIANCE_OPTIONS = [
    (60, "Niedrig (60%) – Kreativ, weniger strikt"),
    (75, "Mittel (75%) – Ausgewogen"),
    (85, "Hoch (85%) – Strenge Einhaltung"),
    (95, "Sehr hoch (95%) – Maximale Kontrolle"),
]


# ─────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────

CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))) / "brokus" / "cli_settings.json"

@dataclass
class Settings:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5"
    export_fmt: int = 0  # Legacy – wird auf export_formats migriert
    export_formats: list[str] = field(default_factory=lambda: ["md", "epub"])
    compliance_threshold: int = 80
    detail_level: str = "standard"  # loose, standard, detailed, strict
    auto_retry: bool = True
    wizard_model_picker: bool = True  # Modell-Auswahl im Wizard anzeigen
    fallback_models_str: str = ""  # Komma-getrennte Fallback-Modelle (leer = Standard)
    chapter_delay_enabled: bool = True  # 2s Delay zwischen Kapiteln
    # ── Erweiterte AI-Parameter ──
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    custom_base_url: str = ""
    # ── Generierungs-Verhalten ──
    story_pace: str = "balanced"  # slow, balanced, fast
    default_language: str = "Deutsch"
    default_chapters: int = 20
    use_extended_thinking: bool = False
    auto_export: bool = False
    auto_open_after_export: bool = True
    backup_enabled: bool = True
    # ── UI ──
    log_level: str = "INFO"
    show_token_count: bool = True
    show_cost_estimate: bool = True
    confirm_quit: bool = True
    # ── Advanced ──
    request_timeout: int = 300
    cache_responses: bool = True
    max_cache_size_mb: int = 500
    max_retries: int = 3

    def load(self):
        # 1) Versuche zuerst die zentrale settings.yaml (Single-Source-of-Truth)
        try:
            from brokus.utils.settings_loader import load_settings
            yaml_cfg = load_settings()
            ai = yaml_cfg.get("ai", {})
            gen = yaml_cfg.get("generation", {})
            ui = yaml_cfg.get("ui", {})
            adv = yaml_cfg.get("advanced", {})
            # Nur überschreiben, wenn nicht leer / sinnvoll
            if ai.get("provider"):
                self.provider = ai["provider"]
            if ai.get("model"):
                self.model = ai["model"]
            if ai.get("temperature") is not None:
                self.temperature = float(ai["temperature"])
            if ai.get("max_tokens"):
                self.max_tokens = int(ai["max_tokens"])
            self.top_p = ai.get("top_p")
            self.frequency_penalty = ai.get("frequency_penalty")
            self.presence_penalty = ai.get("presence_penalty")
            self.custom_base_url = ai.get("custom_base_url") or ""
            if gen.get("compliance_threshold"):
                self.compliance_threshold = int(gen["compliance_threshold"])
            if gen.get("detail_level"):
                self.detail_level = gen["detail_level"]
            if gen.get("story_pace"):
                self.story_pace = gen["story_pace"]
            if gen.get("default_language"):
                self.default_language = gen["default_language"]
            if gen.get("default_chapters"):
                self.default_chapters = int(gen["default_chapters"])
            if gen.get("auto_retry") is not None:
                self.auto_retry = bool(gen["auto_retry"])
            if gen.get("chapter_delay") is not None:
                self.chapter_delay_enabled = float(gen["chapter_delay"]) > 0
            if gen.get("auto_export") is not None:
                self.auto_export = bool(gen["auto_export"])
            if gen.get("auto_open_after_export") is not None:
                self.auto_open_after_export = bool(gen["auto_open_after_export"])
            if gen.get("backup_enabled") is not None:
                self.backup_enabled = bool(gen["backup_enabled"])
            if gen.get("export_formats"):
                valid = {k for k, _ in EXPORT_FORMATS}
                self.export_formats = [f for f in gen["export_formats"] if f in valid] or ["md", "epub"]
            self.use_extended_thinking = bool(adv.get("use_extended_thinking", False))
            self.request_timeout = int(adv.get("request_timeout", 300))
            self.cache_responses = bool(adv.get("cache_responses", True))
            self.max_cache_size_mb = int(adv.get("max_cache_size_mb", 500))
            self.log_level = ui.get("log_level", "INFO")
            self.show_token_count = bool(ui.get("show_token_count", True))
            self.show_cost_estimate = bool(ui.get("show_cost_estimate", True))
            self.confirm_quit = bool(ui.get("confirm_quit", True))
        except Exception as e:
            log.debug(f"CLI: load from settings.yaml failed, falling back to legacy: {e}")

        # 2) Legacy-Override aus cli_settings.json (für CLI-spezifische Werte)
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if "provider" in data:
                    self.provider = data["provider"]
                if "model" in data:
                    self.model = data["model"]
                # Migration: altes export_fmt (int) → neues export_formats (list)
                if "export_formats" in data and isinstance(data["export_formats"], list):
                    valid = {k for k, _ in EXPORT_FORMATS}
                    self.export_formats = [f for f in data["export_formats"] if f in valid]
                    if not self.export_formats:
                        self.export_formats = ["md", "epub"]
                elif "export_fmt" in data:
                    try:
                        idx = int(data["export_fmt"])
                        if 0 <= idx < len(EXPORT_FORMATS):
                            self.export_formats = [EXPORT_FORMATS[idx][0]]
                    except (ValueError, TypeError):
                        pass
                if "compliance_threshold" in data:
                    self.compliance_threshold = int(data["compliance_threshold"])
                if "detail_level" in data:
                    self.detail_level = data["detail_level"]
                if "auto_retry" in data:
                    self.auto_retry = bool(data["auto_retry"])
                if "wizard_model_picker" in data:
                    self.wizard_model_picker = bool(data["wizard_model_picker"])
                if "fallback_models_str" in data:
                    self.fallback_models_str = data["fallback_models_str"]
                if "chapter_delay_enabled" in data:
                    self.chapter_delay_enabled = bool(data["chapter_delay_enabled"])
                # Neue Felder (falls im Legacy-File vorhanden)
                for k in ("temperature", "max_tokens", "top_p", "frequency_penalty",
                          "presence_penalty", "story_pace", "default_language",
                          "default_chapters", "request_timeout", "max_cache_size_mb",
                          "log_level", "custom_base_url"):
                    if k in data:
                        setattr(self, k, data[k])
                for k in ("use_extended_thinking", "auto_export", "auto_open_after_export",
                          "backup_enabled", "show_token_count", "show_cost_estimate",
                          "confirm_quit", "cache_responses"):
                    if k in data:
                        setattr(self, k, bool(data[k]))
            except Exception:
                pass

    def save(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(
                json.dumps(asdict(self), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

settings = Settings()
settings.load()


# ─────────────────────────────────────────────────────────────
# Raw character reader – definitive paste fix
# ─────────────────────────────────────────────────────────────

def _read_line(prompt: str = "", mask: bool = False) -> str:
    """Read one line from terminal, treating both \\r and \\n as Enter.

    Uses tty.setraw() so we get characters immediately, not line-buffered.
    This is the definitive fix for paste overflow – the terminal sends
    all pasted chars at once and we consume them character by character,
    stopping at the first \\r or \\n.

    Args:
        prompt: Text to display before the input.
        mask: If True, don't echo typed characters (for passwords).
    """
    if prompt:
        sys.stdout.write(prompt)
        sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    chars = []
    try:
        tty.setraw(fd)
        while True:
            b = os.read(fd, 1)
            if not b:  # EOF
                break
            # ── Control characters ──
            if b in (b'\r', b'\n', b'\x04'):  # Enter (CR, NL) or Ctrl+D
                break
            if b == b'\x7f':  # Backspace
                if chars:
                    chars.pop()
                    if not mask:
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                continue
            if b == b'\x03':  # Ctrl+C
                raise KeyboardInterrupt
            if b == b'\x1b':  # Escape sequence (arrow keys etc.) – consume and skip
                # Read remaining bytes of the escape sequence (e.g. [A)
                while True:
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
                    if not rlist:
                        break
                    os.read(fd, 1)
                continue
            if b[0] < 0x20:  # Other control chars – ignore
                continue
            # ── UTF-8 multi-byte handling ──
            if b[0] & 0xE0 == 0xC0:      # 2-byte sequence (ä, ö, ü, ß)
                b += os.read(fd, 1)
            elif b[0] & 0xF0 == 0xE0:    # 3-byte sequence (CJK, most emoji)
                b += os.read(fd, 2)
            elif b[0] & 0xF8 == 0xF0:    # 4-byte sequence (some emoji)
                b += os.read(fd, 3)
            decoded = b.decode('utf-8', errors='replace')
            chars.append(decoded)
            if not mask:
                sys.stdout.write(decoded)
                sys.stdout.flush()
        # ── Drain remaining stdin buffer (paste overflow fix) ──
        # When a user pastes multi-line text, only the first line was
        # consumed above. Drain everything else so it doesn't leak
        # into subsequent _read_line() calls.
        while True:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
            if not rlist:
                break
            leftover = os.read(fd, 4096)
            if not leftover:
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    if not mask:
        sys.stdout.write('\n')
        sys.stdout.flush()

    return ''.join(chars)


# ─────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    """Print the BROKUS block-letter ASCII banner."""
    console.print()
    console.print(
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
        + "[/bold bright_blue]"
    )
    console.print()


def section(title: str):
    console.print()
    console.print(Rule(title, style="bright_blue"))
    console.print()


def ask_text(prompt_text: str, default: str = "") -> str:
    """Ask for free text using raw character reader."""
    console.print(f"\n[bold]{prompt_text}[/bold]")
    if default:
        console.print(f"  [dim](Standard: {default} – Enter für Standard)[/dim]")
    try:
        result = _read_line("  > ")
    except (KeyboardInterrupt, EOFError):
        return ""
    result = result.strip()
    if not result and default:
        return default
    return result


def ask_password(prompt_text: str) -> str:
    """Ask for password (hidden input)."""
    console.print(f"\n[bold]{prompt_text}[/bold]")
    console.print("[dim](Eingabe wird versteckt)[/dim]")
    try:
        return _read_line("  > ", mask=True).strip()
    except (KeyboardInterrupt, EOFError):
        return ""


def choose(prompt_text: str, options: list[str]) -> int:
    """Show numbered options, read choice via raw reader."""
    if prompt_text:
        console.print(f"\n[bold]{prompt_text}[/bold]")
    console.print()
    for i, opt in enumerate(options, 1):
        console.print(f"  [cyan]{i}[/cyan]. {opt}")
    console.print()
    while True:
        try:
            raw = _read_line("  Deine Wahl (Nummer): ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Abgebrochen.[/dim]")
            return -1
        raw = raw.strip()
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(options):
                return choice - 1
        console.print(f"  [red]Bitte eine Zahl von 1 bis {len(options)} eingeben.[/red]")


def confirm(prompt_text: str) -> bool:
    """Ask y/n using raw reader."""
    console.print(f"\n[bold]{prompt_text}[/bold]")
    try:
        raw = _read_line("  (j/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return False
    return raw in ("j", "ja", "y", "yes", "")


def ask_multi(prompt_text: str, options: list[tuple[str, str]], defaults: list[str] | None = None) -> list[str]:
    """Multi-select prompt. Returns list of selected keys.

    Args:
        prompt_text: Header text
        options: List of (key, label) tuples
        defaults: List of keys to pre-select

    User can type a number to toggle that option, or press Enter to confirm.
    """
    if defaults is None:
        defaults = []
    selected = {k: (k in defaults) for k, _ in options}

    while True:
        console.print()
        console.print(Rule(prompt_text, style="bright_blue"))
        console.print("  [dim](Nummer zum Umschalten, Enter = Bestätigen)[/dim]\n")
        for i, (key, label) in enumerate(options, 1):
            mark = "[green]\u2713[/green]" if selected[key] else "[  ]"
            console.print(f"  {mark} [cyan]{i}[/cyan]. {label}")
        console.print()
        try:
            raw = _read_line("  Toggle oder Enter: ")
        except (KeyboardInterrupt, EOFError):
            return [k for k, v in selected.items() if v]
        raw = raw.strip()
        if not raw:
            return [k for k, v in selected.items() if v]
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                key = options[idx][0]
                selected[key] = not selected[key]
                clear()
                banner()
            else:
                console.print(f"  [red]Bitte eine Zahl von 1 bis {len(options)} eingeben.[/red]")
        else:
            console.print("  [red]Bitte eine Zahl eingeben oder Enter zum Bestätigen.[/red]")


def pause():
    """Wait for Enter."""
    console.print("\n[dim]Enter zum Fortfahren...[/dim]")
    try:
        _read_line("")
    except (KeyboardInterrupt, EOFError):
        pass


# ─────────────────────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────────────────────

async def init():
    try:
        from brokus.storage.database import init_db
        await init_db()
    except Exception as e:
        console.print(f"[yellow]Warnung: DB-Init fehlgeschlagen: {e}[/yellow]")
    try:
        from brokus.utils.crypto import load_secrets
        load_secrets()
    except Exception:
        pass



# ─────────────────────────────────────────────────────────────
# Main Menu
# ─────────────────────────────────────────────────────────────

async def main_menu():
    await init()

    while True:
        clear()
        banner()

        has_key = _has_api_key()
        key_status = "[green]✓ gesetzt[/green]" if has_key else "[red]✗ fehlt[/red]"
        lang_label = language_name(get_language())
        console.print(f"  {t('label.provider')} [bold]{settings.provider}[/bold]  |  {t('label.model')} [bold]{settings.model}[/bold]  |  {t('label.api_key')} {key_status}  |  🌐 [bold]{lang_label}[/bold]")
        console.print()

        choice = choose(t("main.title"), [
            t("main.quick_book"),
            t("main.master"),
            t("main.library"),
            t("main.settings"),
            f"🌐  Sprache / Language (aktuell: {lang_label})",
            t("main.quit"),
        ])

        if choice == 0:
            await wizard_quick()
        elif choice == 1:
            await wizard_master()
        elif choice == 2:
            await library()
        elif choice == 3:
            await settings_menu()
        elif choice == 4:
            _change_language()
        elif choice == 5:
            console.print(f"\n[cyan]{t('main.goodbye')}[/cyan]\n")
            break


# ─────────────────────────────────────────────────────────────
# Quick Book Wizard
# ─────────────────────────────────────────────────────────────

async def wizard_quick():
    section("⚡ Schnell-Buch")

    idea = ask_text("Beschreibe deine Buchidee (je mehr Details, desto besser):")
    if not idea:
        return

    title = ask_text("Wie soll das Buch heißen?", default=idea[:40])

    genre_names = [g[1] for g in GENRES]
    gi = choose("Wähle ein Genre:", genre_names)
    if gi < 0:
        return
    genre_key = GENRES[gi][0]

    # ── Länge ──
    section("📏 Länge")
    length_labels = [f"{l[0]} ({l[3]})" for l in LENGTHS]
    length_labels.append(WORD_TARGET_OPTION)
    li = choose("Buchlänge:", length_labels)
    if li < 0:
        return

    num_chapters = 12
    if li < len(LENGTHS):
        num_chapters = LENGTHS[li][2]
    else:
        section("📏 Wörter-Ziel")
        raw = ask_text("Wieviele Wörter soll dein Buch haben?", default="50000")
        try:
            total_words_target = int(raw.replace(".", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            total_words_target = 50000
        num_chapters = max(3, round(total_words_target / 2500))

    # ── Story-Info ──
    section("ℹ️ Wichtige Informationen (optional)")
    console.print("  [dim]Was MUSS unbedingt in der Geschichte vorkommen? (Enter = überspringen)[/dim]")
    story_info = ask_text("Diese Dinge müssen in der Geschichte vorkommen:")

    # ── Sprache ──
    li = choose("Sprache:", LANGUAGES)
    language = LANGUAGES[li] if li >= 0 else "Deutsch"

    # ── Modell (optional) ──
    if settings.wizard_model_picker:
        models = _get_current_models()
        if models:
            mi = choose("KI-Modell:", models)
            if mi >= 0:
                settings.model = models[mi]
                settings.save()
    console.print(f"  [dim]Modell: {settings.model}[/dim]")

    # ── Vorschau & Bestätigung ──
    console.print()
    console.print(Panel(
        f"[bold]Titel:[/bold]       {title}\n"
        f"[bold]Genre:[/bold]       {GENRES[gi][1]}\n"
        f"[bold]Sprache:[/bold]     {language}\n"
        f"[bold]Modell:[/bold]      {settings.model}\n"
        f"[bold]Kapitel:[/bold]     {num_chapters}\n"
        + (f"[bold]Story-Infos:[/bold] {story_info[:80]}{'...' if len(story_info) > 80 else ''}\n" if story_info else "")
        + f"[bold]Idee:[/bold]        {idea[:100]}{'...' if len(idea) > 100 else ''}",
        title="📋 Zusammenfassung",
        border_style="bright_blue",
    ))

    if not confirm("Buch generieren?"):
        return

    await generate_book(idea, title, genre_key, num_chapters, language, story_info)


# ─────────────────────────────────────────────────────────────
# Master Wizard
# ─────────────────────────────────────────────────────────────

async def wizard_master():
    section("✨ Meisterwerk")

    idea = ask_text("Schritt 1/11 – Beschreibe deine Buchidee ausführlich:")
    if not idea:
        return

    title = ask_text("Schritt 2/11 – Wie soll das Buch heißen?", default=idea[:40])

    # ── Schritt 3/11: Genre ──
    genre_names = [g[1] for g in GENRES]
    gi = choose("Schritt 3/11 – Genre:", genre_names)
    if gi < 0:
        return
    genre_key = GENRES[gi][0]

    # ── Schritt 4/11: Zielgruppe ──
    ai = choose("Schritt 4/11 – Zielgruppe:", AUDIENCES)
    if ai < 0:
        return

    # ── Schritt 5/11: Sprache ──
    li = choose("Schritt 5/11 – Sprache:", LANGUAGES)
    if li < 0:
        return
    language = LANGUAGES[li]

    # ── Schritt 6/11: Modell (optional) ──
    if settings.wizard_model_picker:
        models = _get_current_models()
        if models:
            mi = choose("Schritt 6/11 – KI-Modell:", models)
            if mi >= 0:
                settings.model = models[mi]
                settings.save()
    else:
        console.print(f"  [dim]Modell: {settings.model}[/dim]")

    # ── Schritt 7/11: Erzaehlperspektive ──
    pi = choose("Schritt 7/11 – Erzaehlperspektive:", PERSPECTIVES)
    if pi < 0:
        return

    # ── Schritt 8/11: Stimmung & Ton ──
    ti = choose("Schritt 8/11 – Stimmung & Ton:", TONES)
    if ti < 0:
        return

    # ── Schritt 9/11: Buchlänge ──
    length_labels = [f"{l[0]} ({l[3]}, ~{l[1]:,} Wörter, {l[2]} Kap.)" for l in LENGTHS]
    length_labels.append(WORD_TARGET_OPTION)
    li = choose("Schritt 9/11 – Buchlänge:", length_labels)
    if li < 0:
        return

    num_chapters = 12
    total_words_target = 0
    if li < len(LENGTHS):
        # Festgelegte Länge
        total_words_target = LENGTHS[li][1]
        num_chapters = LENGTHS[li][2]
        length_label = f"{LENGTHS[li][0]} ({LENGTHS[li][3]}, {num_chapters} Kapitel)"
    else:
        # Benutzerdefiniertes Wörter-Ziel
        section("📏 Wörter-Ziel")
        console.print("  [dim]Gib die gewünschte Gesamtwörterzahl ein (z.B. 50000 für 50.000 Wörter).[/dim]")
        raw = ask_text("Wieviele Wörter soll dein Buch haben?", default="50000")
        try:
            total_words_target = int(raw.replace(".", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            total_words_target = 50000
            console.print(f"  [yellow]Ungültige Eingabe, verwende 50.000 Wörter.[/yellow]")
        # Kapitel berechnen: ~2500 Wörter pro Kapitel
        WORDS_PER_CHAPTER = 2500
        num_chapters = max(3, round(total_words_target / WORDS_PER_CHAPTER))
        length_label = f"~{total_words_target:,} Wörter ({num_chapters} Kapitel, ~{total_words_target // 300} Seiten)"

    # ── Schritt 10/11: Wichtige Informationen ──
    section("ℹ️ Schritt 10/11 – Wichtige Informationen")
    console.print("  [dim]Was MUSS unbedingt in der Geschichte vorkommen?[/dim]")
    console.print("  [dim]Fakten, Ereignisse, Orte, Namen, oder Details, die die KI beachten soll.[/dim]")
    console.print("  [dim](Leer lassen = keine zusätzlichen Vorgaben)[/dim]")
    story_info = ask_text("Diese Dinge müssen in der Geschichte vorkommen:")

    # ── Schritt 11/11: Detailgrad ──
    dl_names = [d[1] for d in DETAIL_LEVELS]
    dl_keys = [d[0] for d in DETAIL_LEVELS]
    dl_i = choose("Schritt 11/11 – Detailgrad der Umsetzung:", dl_names)
    if dl_i >= 0:
        settings.detail_level = dl_keys[dl_i]
        settings.save()

    # ── Vorschau & Bestätigung ──
    dl_label = dict(DETAIL_LEVELS).get(settings.detail_level, settings.detail_level)
    console.print()
    console.print(Panel(
        f"[bold]Titel:[/bold]         {title}\n"
        f"[bold]Genre:[/bold]         {GENRES[gi][1]}\n"
        f"[bold]Sprache:[/bold]       {language}\n"
        f"[bold]Modell:[/bold]        {settings.model}\n"
        f"[bold]Zielgruppe:[/bold]    {AUDIENCES[ai]}\n"
        f"[bold]Perspektive:[/bold]   {PERSPECTIVES[pi]}\n"
        f"[bold]Stimmung:[/bold]      {TONES[ti]}\n"
        f"[bold]Länge:[/bold]         {length_label}\n"
        f"[bold]Detailgrad:[/bold]    {dl_label}\n"
        + (f"[bold]Story-Infos:[/bold]   {story_info[:80]}{'...' if len(story_info) > 80 else ''}\n" if story_info else "")
        + f"[bold]Idee:[/bold]          {idea[:100]}{'...' if len(idea) > 100 else ''}",
        title="📋 Zusammenfassung",
        border_style="bright_blue",
    ))

    if not confirm("Buch generieren?"):
        return

    await generate_book(idea, title, genre_key, num_chapters, language, story_info)


# ─────────────────────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────────────────────

async def generate_book(idea: str, title: str, genre_key: str, num_chapters: int, language: str = "Deutsch", story_info: str = ""):
    section("📖 Generierung")

    if not _has_api_key():
        console.print("[red]❌ Kein API-Key gesetzt! Gehe zuerst zu Einstellungen → API-Key.[/red]")
        pause()
        return

    console.print(f"  [bold]{title}[/bold] – {num_chapters} Kapitel werden generiert...\n")

    try:
        from brokus.storage.database import (
            create_project, save_chapter, update_project, log_generation_event,
        )
        from brokus.ai.client import BrokusAIClient
        from brokus.ai.prompts import PromptLoader, GenreLoader
        from brokus.core.pipeline import BookPipeline

        # Story-Info in die Idee einbetten, damit sie in DNA und Prompts einfließt
        full_idea = idea
        if story_info:
            full_idea = f"{idea}\n\n📌 WICHTIGE ZUSATZINFORMATIONEN:\n{story_info}"

        pid = await create_project(
            title=title, genre=genre_key, idea=full_idea,
            total_chapters=num_chapters, model=settings.model,
        )
        # Zusätzlich story_info im Config-Feld speichern
        try:
            from brokus.storage.database import update_project
            await update_project(pid, config=json.dumps({"story_info": story_info}))
        except Exception:
            pass
        # Fallback-Modelle aus Settings parsen
        fb_raw = settings.fallback_models_str
        if fb_raw == " ":
            fallback_list = []       # Explizit deaktiviert
        elif fb_raw.strip():
            fallback_list = [m.strip() for m in fb_raw.split(",") if m.strip()]
        else:
            fallback_list = None     # None = Provider-Default
        # BrokusAIClient: alle erweiterten AI-Parameter durchreichen
        client = BrokusAIClient(
            provider=settings.provider, model=settings.model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            top_p=settings.top_p,
            frequency_penalty=settings.frequency_penalty,
            presence_penalty=settings.presence_penalty,
            custom_base_url=(settings.custom_base_url or None),
            max_retries=3,
            retry_delay=1.0,
            fallback_models=fallback_list,
        )
        # BookPipeline: alle Generierungs-Settings durchreichen
        pipeline = BookPipeline(
            client=client,
            prompts=PromptLoader(),
            genres=GenreLoader(),
            temperature=settings.temperature,
            chapter_delay=2.0 if settings.chapter_delay_enabled else 0.0,
            default_language=settings.default_language,
            detail_level=settings.detail_level,
            story_pace=settings.story_pace,
            use_extended_thinking=settings.use_extended_thinking,
            auto_export=settings.auto_export,
            auto_open_after_export=settings.auto_open_after_export,
            backup_enabled=settings.backup_enabled,
        )

        chapter_count = [0]

        # ── Progress callback: live updates during generation ──
        def on_progress(stage: str, progress: float, message: str):
            bar_len = 20
            filled = int(progress * bar_len)
            bar = f"[{'#' * filled}{'·' * (bar_len - filled)}]"
            pct = int(progress * 100)
            console.print(f"  {bar} {pct:>3}%  {stage}: {message}")

        pipeline.set_progress_callback(on_progress)

        # ── Compliance callback ──
        def on_compliance(score: int, status_lines: list, tracker_text: str):
            passed = score >= settings.compliance_threshold
            icon = "[green]✓[/green]" if passed else "[red]✗[/red]"
            console.print(f"  {icon} Compliance: {score}/100")

        pipeline.set_compliance_callback(on_compliance)

        async def save_cb(cn, ct, tx, **kw):
            await save_chapter(
                project_id=pid, number=cn, title=ct, text=tx,
                word_count=kw.get("word_count", 0),
                compliance_score=kw.get("compliance_score"),
                status=kw.get("status", "completed"),
            )
            await update_project(pid, chapters_completed=cn, total_words=kw.get("word_count", 0), status="generating")
            chapter_count[0] = cn
            score = kw.get("compliance_score", 0) or 0
            words = kw.get("word_count", 0)
            console.print(f"  [green]✓[/green] Kapitel {cn}/{num_chapters}: [bold]{ct}[/bold] ({words} Wörter, Score: {score})")

        async def log_cb(msg, **kw):
            await log_generation_event(
                pid, event=msg, level=kw.get("level", "INFO"),
                chapter_number=kw.get("chapter_number"), details=kw.get("details"),
            )

        result = await pipeline.run(
            book_idea=idea, genre_key=genre_key, num_chapters=num_chapters,
            save_chapter_cb=save_cb, log_event_cb=log_cb,
            language=language,
        )

        await update_project(pid, status="completed", total_words=result.get("total_words", 0))

        exported_paths = []
        try:
            from brokus.storage.database import get_all_chapters
            from brokus.storage.exporter import Exporter
            chaps = await get_all_chapters(pid)
            lang_code = LANG_TO_CODE.get(language, "de")
            exporter = Exporter()
            project_meta = {"title": title, "genre": genre_key, "idea": full_idea}

            # Benutzer wählt Export-Formate (Default aus settings)
            console.print()
            console.print(Rule("📤 Export-Formate wählen", style="bright_blue"))
            current_names = [f[1] for f in EXPORT_FORMATS if f[0] in settings.export_formats]
            if current_names:
                console.print(f"  [dim]Aktuell: {', '.join(current_names)}[/dim]")
            selected_formats = ask_multi(
                "In welche Dateiformate soll exportiert werden?",
                list(EXPORT_FORMATS),
                defaults=settings.export_formats,
            )
            if not selected_formats:
                console.print("  [yellow]⚠ Kein Format gewählt – Export übersprungen.[/yellow]")
            else:
                # Auswahl für nächste Generierung speichern
                settings.export_formats = selected_formats
                settings.save()

                console.print()
                for ef in selected_formats:
                    try:
                        path = exporter.export(project_meta, chaps, fmt=ef, language=lang_code)
                        exported_paths.append(str(path))
                        console.print(f"  [green]✓[/green] {ef.upper():5s} → {path.name}")
                    except ImportError:
                        console.print(f"  [yellow]⚠[/yellow] {ef.upper():5s} → Bibliothek fehlt (übersprungen)")
                    except Exception as e:
                        console.print(f"  [yellow]⚠[/yellow] {ef.upper():5s} → {e}")

                # Auto-Open mit Standard-Dokumentenreader anbieten
                if exported_paths:
                    first_path = exported_paths[0]
                    if confirm("📂 Datei mit Standard-Reader öffnen?"):
                        try:
                            from brokus.utils.opener import BookOpener
                            BookOpener.open_file(first_path)
                        except Exception as oe:
                            console.print(f"  [yellow]Konnte Datei nicht öffnen: {oe}[/yellow]")
        except Exception as ex:
            console.print(f"\n  [yellow]⚠ Export fehlgeschlagen: {ex}[/yellow]")

        total_words = result.get("total_words", 0)
        console.print(f"\n  [bold green]🎉 '{title}' erfolgreich erstellt![/bold green]")
        console.print(f"  {chapter_count[0]} Kapitel · {total_words:,} Wörter\n")

    except asyncio.CancelledError:
        console.print("\n[yellow]Generierung abgebrochen.[/yellow]")
    except Exception as ex:
        console.print(f"\n[red]❌ Fehler: {ex}[/red]")
        log.exception(f"Generation error: {ex}")

    pause()


# ─────────────────────────────────────────────────────────────
# Library
# ─────────────────────────────────────────────────────────────

async def library():
    section("📖 Bibliothek")

    try:
        from brokus.storage.database import get_all_projects
        projects = await get_all_projects()
    except Exception as e:
        console.print(f"[red]Fehler: {e}[/red]")
        pause()
        return

    if not projects:
        console.print("  [dim]Noch keine Bücher erstellt.[/dim]")
        pause()
        return

    table = Table(show_header=True, header_style="bold cyan", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Titel", style="bold")
    table.add_column("Genre")
    table.add_column("Kapitel", justify="center")
    table.add_column("Wörter", justify="right")
    table.add_column("Status")
    table.add_column("Datum")

    for i, p in enumerate(projects, 1):
        status = p.get("status", "draft")
        status_icon = {"completed": "✅", "generating": "⏳", "failed": "❌"}.get(status, "📝")
        table.add_row(
            str(i),
            p.get("title", "?"),
            p.get("genre", "?"),
            f"{p.get('chapters_completed', 0)}/{p.get('total_chapters', 0)}",
            f"{p.get('total_words', 0):,}",
            f"{status_icon} {status}",
            (p.get("created_at", "") or "")[:10],
        )

    console.print(table)
    console.print(f"\n  [dim]1-{len(projects)} = Buch lesen  |  Enter = Zurück[/dim]")

    try:
        raw = _read_line("  > ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if raw and raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(projects):
            await read_book(projects[idx])


async def read_book(project: dict):
    try:
        from brokus.storage.database import get_all_chapters
        chapters = await get_all_chapters(project["id"])
    except Exception as e:
        console.print(f"[red]Fehler: {e}[/red]")
        return

    if not chapters:
        console.print("[dim]Keine Kapitel gefunden.[/dim]")
        pause()
        return

    idx = 0
    while True:
        ch = chapters[idx]
        clear()
        section(f"📖 {project.get('title', '?')}")
        console.print(f"  [bold]Kapitel {ch['number']}: {ch.get('title', '?')}[/bold]")
        console.print(f"  [dim]{ch.get('word_count', 0)} Wörter · Score: {ch.get('compliance_score', '?')}[/dim]\n")

        text = ch.get("text", "")
        lines = text.split("\n")
        for line in lines[:40]:
            console.print(f"  {line}")
        if len(lines) > 40:
            console.print(f"\n  [dim]... ({len(lines) - 40} weitere Zeilen)[/dim]")

        console.print(f"\n  [dim][n]ächstes  [p] vorheriges  Enter = Zurück  [{idx+1}/{len(chapters)}][/dim]")
        try:
            raw = _read_line("  > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        if raw == "" or raw == "q":
            break
        elif raw in ("p", "z"):
            if idx > 0:
                idx -= 1
        elif raw == "n":
            if idx < len(chapters) - 1:
                idx += 1
        elif raw.isdigit() and int(raw) > 0:
            idx = max(0, min(len(chapters) - 1, int(raw) - 1))


# ─────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────

def _has_api_key() -> bool:
    try:
        from brokus.ai.client import PROVIDER_REGISTRY
        pc = PROVIDER_REGISTRY.get(settings.provider)
        if not pc:
            return False
        ev = pc.api_key_env
        if not ev:
            return True
        try:
            from brokus.utils.crypto import SecretStore
            if SecretStore.instance().get(ev):
                return True
        except Exception:
            pass
        return bool(os.getenv(ev, ""))
    except Exception:
        return False


def _get_current_models() -> list[str]:
    """Get available models for the current provider."""
    providers = _get_providers()
    for p in providers:
        if p["key"] == settings.provider:
            return p["models"]
    return []


def _get_providers() -> list[dict]:
    try:
        from brokus.ai.client import PROVIDER_REGISTRY
        from brokus.utils.i18n import t_label
        return [
            {
                "key": k,
                "name": t_label("provider", f"{k}.name", default=p.name),
                "models": p.models,
                "cost": p.cost_info,
                "env": p.api_key_env,
            }
            for k, p in PROVIDER_REGISTRY.items()
        ]
    except Exception:
        return []


async def settings_menu():
    """Top-level settings menu with clean sub-menus.

    Struktur:
      1. Übersicht (alle Werte auf einen Blick)
      2. Provider & Modell    → Sub-Menu
      3. KI-Parameter        → Sub-Menu
      4. Generierung         → Sub-Menu
      5. UI & Logging        → Sub-Menu
      6. Erweitert           → Sub-Menu
      7. YAML im Editor öffnen
      8. Auf Standard zurücksetzen
      9. Zurück zum Hauptmenü
    """
    while True:
        section(t("section.settings"))

        # ── Kompakte Zusammenfassung (Top 6 wichtigste Werte) ──
        has_key = _has_api_key()
        key_status = "[green]✓[/green]" if has_key else "[red]✗[/red]"
        ek = ", ".join(settings.export_formats) or f"[dim]{t('status.empty')}[/dim]"
        lang_label = language_name(get_language())
        console.print(f"  {t('label.provider')} {settings.provider}  |  {t('label.model')} {settings.model}  |  Key: {key_status}  |  🌐 {lang_label}")
        console.print(f"  {t('label.temp_short')} {settings.temperature}  |  {t('label.top_p')} {settings.top_p if settings.top_p is not None else '–'}  |  {t('label.tokens')} {settings.max_tokens}")
        console.print(f"  {t('label.language')} {settings.default_language}  |  {t('label.chapters')} {settings.default_chapters}  |  {t('label.pace')} {settings.story_pace}")
        console.print(f"  {t('label.detail_level')} {settings.detail_level}  |  {t('label.compliance')} {settings.compliance_threshold}%  |  {t('label.log_level')} {settings.log_level}")
        console.print(f"  Export: {ek}  |  {t('label.cache')} {'✓' if settings.cache_responses else '✗'}  |  {t('label.backup')} {'✓' if settings.backup_enabled else '✗'}")

        choice = choose("", [
            t("settings.overview"),
            "───────────────────",
            t("settings.provider"),
            t("settings.ai"),
            t("settings.generation"),
            t("settings.ui"),
            t("settings.advanced"),
            "───────────────────",
            t("settings.open_yaml"),
            t("settings.reset"),
            t("settings.back"),
        ])

        if choice in (1, 7):
            continue  # Separator
        if choice == 0:
            _view_all_settings()
        elif choice == 2:
            await _settings_provider_menu()
        elif choice == 3:
            await _settings_ai_menu()
        elif choice == 4:
            await _settings_generation_menu()
        elif choice == 5:
            await _settings_ui_menu()
        elif choice == 6:
            await _settings_advanced_menu()
        elif choice == 8:
            _open_settings_yaml()
        elif choice == 9:
            _reset_settings_to_defaults()
        elif choice == 10:
            break


# ─────────────────────────────────────────────────────────────
# Sub-Menüs (alle via t() übersetzbar)
# ─────────────────────────────────────────────────────────────

def _on_off(b: bool) -> str:
    return f"[green]{t('status.on')}[/green]" if b else f"[red]{t('status.off')}[/red]"


async def _settings_provider_menu():
    """Sub-Menu: Provider, Modell, API-Key, URL, Fallbacks, Discovery."""
    while True:
        section(t("settings.provider.title"))
        has_key = _has_api_key()
        key_status = f"[green]{t('status.set')}[/green]" if has_key else f"[red]{t('status.unset')}[/red]"
        console.print(f"  {t('label.provider')}   {settings.provider}")
        console.print(f"  {t('label.model')}     {settings.model}")
        console.print(f"  {t('label.api_key')}    {key_status}")
        if settings.custom_base_url:
            console.print(f"  {t('label.custom_url')} {settings.custom_base_url}")
        if settings.fallback_models_str.strip():
            n = len([m for m in settings.fallback_models_str.split(",") if m.strip()])
            console.print(f"  {t('label.fallbacks')}  {n} Modelle konfiguriert")
        else:
            console.print(f"  {t('label.fallbacks')}  [dim]{t('status.provider_default')}[/dim]")

        choice = choose("", [
            t("settings.provider.change"),
            t("settings.provider.model"),
            t("settings.provider.api_key"),
            t("settings.provider.custom_url"),
            t("settings.provider.fallback"),
            t("settings.provider.refresh"),
            t("settings.back_to_settings"),
        ])
        if choice == 0: _pick_provider()
        elif choice == 1: _pick_model()
        elif choice == 2: _enter_api_key()
        elif choice == 3: _set_custom_base_url()
        elif choice == 4: _configure_fallback_models()
        elif choice == 5: _force_refresh_models()
        elif choice == 6: break


async def _settings_ai_menu():
    """Sub-Menu: Sampling-Parameter, Compliance, Retries."""
    while True:
        section(t("settings.ai.title"))
        off = f"[dim]{t('status.disabled')}[/dim]"
        top_p_v = settings.top_p if settings.top_p is not None else off
        freq_v = settings.frequency_penalty if settings.frequency_penalty is not None else off
        pres_v = settings.presence_penalty if settings.presence_penalty is not None else off
        console.print(f"  {t('label.temperature')}    {settings.temperature}")
        console.print(f"  {t('label.max_tokens')}     {settings.max_tokens}")
        console.print(f"  {t('label.top_p')}          {top_p_v}")
        console.print(f"  {t('label.freq_pen')}  {freq_v}")
        console.print(f"  {t('label.pres_pen')}   {pres_v}")
        console.print(f"  {t('label.compliance')}     {settings.compliance_threshold}%")
        console.print(f"  {t('label.retries')}    {settings.max_retries}")

        choice = choose("", [
            t("settings.ai.edit"),
            t("settings.ai.compliance"),
            t("settings.ai.retries"),
            t("settings.back_to_settings"),
        ])
        if choice == 0: _edit_ai_params()
        elif choice == 1: _set_compliance_threshold()
        elif choice == 2: _set_max_retries()
        elif choice == 3: break


async def _settings_generation_menu():
    """Sub-Menu: Sprache, Kapitel, Tempo, Detailgrad, Toggles, Export."""
    while True:
        section(t("settings.generation.title"))
        none_v = f"[dim]{t('status.none')}[/dim]"
        export_v = ", ".join(settings.export_formats) or none_v
        console.print(f"  {t('label.language')}      {settings.default_language}")
        console.print(f"  {t('label.chapters')}      {settings.default_chapters}")
        console.print(f"  {t('label.pace')}        {settings.story_pace}")
        console.print(f"  {t('label.detail_level')}   {settings.detail_level}")
        console.print(f"  {t('label.delay')} {_on_off(settings.chapter_delay_enabled)}")
        console.print(f"  {t('label.thinking')} {_on_off(settings.use_extended_thinking)}")
        console.print(f"  {t('label.backup')}       {_on_off(settings.backup_enabled)}")
        console.print(f"  {t('label.auto_export')}  {_on_off(settings.auto_export)}")
        console.print(f"  {t('label.auto_open')}    {_on_off(settings.auto_open_after_export)}")
        console.print(f"  {t('label.export_formats')} {export_v}")
        console.print(f"  {t('label.wizard_picker')} {_on_off(settings.wizard_model_picker)}")

        choice = choose("", [
            t("settings.generation.edit"),
            t("settings.generation.delay"),
            t("settings.generation.thinking"),
            t("settings.generation.backup"),
            t("settings.generation.auto_export"),
            t("settings.generation.auto_open"),
            t("settings.generation.export_formats"),
            t("settings.generation.wizard_picker"),
            t("settings.back_to_settings"),
        ])
        if choice == 0: _edit_generation_params()
        elif choice == 1: _toggle_chapter_delay()
        elif choice == 2: _toggle_extended_thinking()
        elif choice == 3: _toggle_backup()
        elif choice == 4: _toggle_auto_export()
        elif choice == 5: _toggle_auto_open()
        elif choice == 6: _pick_export_formats()
        elif choice == 7: _toggle_wizard_model_picker()
        elif choice == 8: break


async def _settings_ui_menu():
    """Sub-Menu: Log-Level, Token/Kosten-Anzeige, Beenden-Bestätigung, Sprache."""
    while True:
        section(t("settings.ui.title"))
        console.print(f"  {t('label.log_level')}       {settings.log_level}")
        console.print(f"  {t('label.tokens')}   {_on_off(settings.show_token_count)}")
        console.print(f"  {t('label.cache')}  {_on_off(settings.show_cost_estimate)}")
        console.print(f"  Beenden-Bestätigung {_on_off(settings.confirm_quit)}")
        console.print(f"  🌐 Sprache:           {language_name(get_language())}")

        choice = choose("", [
            t("settings.ui.edit"),
            t("settings.ui.show_tokens"),
            t("settings.ui.show_cost"),
            t("settings.ui.confirm_quit"),
            t("settings.ui.language"),
            t("settings.back_to_settings"),
        ])
        if choice == 0: _edit_ui_params()
        elif choice == 1: _toggle_show_tokens()
        elif choice == 2: _toggle_show_cost()
        elif choice == 3: _toggle_confirm_quit()
        elif choice == 4: _change_language()
        elif choice == 5: break


async def _settings_advanced_menu():
    """Sub-Menu: Timeout, Cache, Cache-Größe."""
    while True:
        section(t("settings.advanced.title"))
        console.print(f"  {t('label.timeout')}  {settings.request_timeout}s")
        console.print(f"  {t('label.cache')}         {_on_off(settings.cache_responses)}")
        console.print(f"  Max. Cache-Größe: {settings.max_cache_size_mb} MB")

        choice = choose("", [
            t("settings.advanced.edit"),
            t("settings.advanced.cache"),
            t("settings.back_to_settings"),
        ])
        if choice == 0: _edit_advanced_params()
        elif choice == 1: _toggle_cache()
        elif choice == 2: break


# ─────────────────────────────────────────────────────────────
# Language switcher
# ─────────────────────────────────────────────────────────────

def _change_language():
    """Let the user pick the UI language and persist the choice."""
    section(t("language.choose"))
    langs = available_languages()
    labels = [f"{language_name(l)} ({l})" for l in langs]
    cur_idx = langs.index(get_language()) if get_language() in langs else 0
    console.print(f"  [dim]{t('language.current', name=language_name(get_language()))}[/dim]")
    console.print()
    for i, lbl in enumerate(labels, 1):
        marker = " ←" if i - 1 == cur_idx else ""
        console.print(f"  [cyan]{i}[/cyan]. {lbl}{marker}")
    console.print()
    try:
        raw = _read_line("  Deine Wahl (Nummer): ")
    except (KeyboardInterrupt, EOFError):
        return
    raw = raw.strip()
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(langs):
            new_lang = langs[idx]
            if set_language(new_lang):
                # Persist in settings
                # Load settings.yaml to store ui.language
                try:
                    from brokus.utils.settings_loader import load_settings, save_settings
                    cfg = load_settings()
                    cfg.setdefault("ui", {})["language"] = new_lang
                    save_settings(cfg)
                except Exception:
                    pass
                console.print(f"  [green]{t('language.changed', name=language_name(new_lang))}[/green]")
            else:
                console.print(f"  [red]{t('common.error_prefix')}{new_lang}[/red]")
    pause()


def _pick_provider():
    providers = _get_providers()
    if not providers:
        console.print("[red]Keine Provider verfügbar.[/red]")
        return

    names = [f"{p['name']}  ({p['cost']})" for p in providers]
    idx = choose("Provider wählen:", names)
    if idx < 0:
        return

    p = providers[idx]
    settings.provider = p["key"]
    if p["models"]:
        settings.model = p["models"][0]
    settings.save()
    console.print(f"\n  [green]✓ Provider: {p['name']}[/green]")


def _pick_model():
    providers = _get_providers()
    pc = None
    for p in providers:
        if p["key"] == settings.provider:
            pc = p
            break

    if not pc or not pc["models"]:
        console.print("[yellow]Keine Modelle für diesen Provider.[/yellow]")
        return

    # ── Live-Model-Discovery: versuche Modelle vom Endpoint zu holen ──
    try:
        from brokus.ai.model_discovery import get_provider_models_sync
        result = get_provider_models_sync(settings.provider, force_refresh=False)
        if result.models and result.source in ("live", "cache"):
            old_count = len(pc["models"])
            pc["models"] = result.models
            icon = "🌐" if result.source == "live" else "💾"
            label = "Live vom Endpoint" if result.source == "live" else "Aus Cache"
            console.print(f"  {icon} [cyan]{len(result.models)} Modelle entdeckt ({label})[/cyan]")
            if result.source == "cache":
                console.print("  [dim](Tipp: 'Modelle neu laden' für frische Liste)[/dim]")
    except Exception as e:
        log.debug(f"Discovery skipped: {e}")

    # Providers that support custom model names (user types any name)
    _CUSTOM_MODEL_PROVIDERS = {"ollama_local", "lmstudio", "localai", "openrouter", "openai_compat", "huggingface"}

    options = list(pc["models"])
    if pc["key"] in _CUSTOM_MODEL_PROVIDERS:
        options.append("✏️  Benutzerdefiniert – Namen eingeben...")

    idx = choose(f"Modell wählen ({settings.provider}, {len(pc['models'])} verfügbar):", options)
    if idx < 0:
        return

    if idx < len(pc["models"]):
        # Predefined model selected
        settings.model = pc["models"][idx]
    elif pc["key"] in _CUSTOM_MODEL_PROVIDERS:
        # Custom model – ask user to type a name
        custom = ask_text("Modellnamen eingeben (z.B. llama3.2:3b, qwen2.5:7b, ...):")
        if not custom:
            console.print("[yellow]Kein Modellname eingegeben.[/yellow]")
            return
        settings.model = custom.strip()

    settings.save()
    console.print(f"\n  [green]✓ Modell: {settings.model}[/green]")


def _force_refresh_models():
    """Force-refresh the model list (bypass TTL cache)."""
    try:
        from brokus.ai.model_discovery import get_provider_models_sync
        console.print(f"  🔄 Lade Modelle für [cyan]{settings.provider}[/cyan] vom Endpoint...")
        result = get_provider_models_sync(settings.provider, force_refresh=True)
        if result.models:
            icon = "🌐" if result.source == "live" else "💾"
            console.print(f"  {icon} [green]✓ {len(result.models)} Modelle entdeckt ({result.source})[/green]")
            for m in result.models[:15]:
                console.print(f"     • {m}")
            if len(result.models) > 15:
                console.print(f"     [dim]… und {len(result.models) - 15} weitere[/dim]")
        else:
            console.print(f"  [yellow]⚠ Keine Modelle entdeckt: {result.error or 'leere Antwort'}[/yellow]")
    except Exception as e:
        console.print(f"  [red]Fehler: {e}[/red]")
    pause()


def _enter_api_key():
    section("🔑 API-Key eingeben")

    providers = _get_providers()
    pc = None
    for p in providers:
        if p["key"] == settings.provider:
            pc = p
            break

    if not pc:
        console.print("[red]Provider nicht gefunden.[/red]")
        pause()
        return

    env_var = pc["env"]
    console.print(f"  Provider: [bold]{pc['name']}[/bold]")
    console.print(f"  Env-Variable: [cyan]{env_var}[/cyan]")
    console.print()
    console.print("  [dim]Tippe deinen API-Key ein und drücke Enter.[/dim]")
    console.print("  [dim]Leer lassen um den Key zu löschen.[/dim]")

    key = ask_password("API-Key:")

    if not key:
        try:
            from brokus.utils.crypto import SecretStore
            store = SecretStore.instance()
            store.delete(env_var)
            store.save()
            os.environ.pop(env_var, None)
            console.print("\n  [green]✓ API-Key gelöscht.[/green]")
        except Exception as e:
            console.print(f"\n  [red]Fehler: {e}[/red]")
        pause()
        return

    try:
        from brokus.utils.crypto import SecretStore
        store = SecretStore.instance()
        store.set(env_var, key)
        store.save()
        os.environ[env_var] = key
        console.print(f"\n  [green]✓ API-Key gespeichert![/green]")
    except Exception as e:
        console.print(f"\n  [red]Fehler beim Speichern: {e}[/red]")
        os.environ[env_var] = key
        console.print(f"  [yellow]Key wurde als Umgebungsvariable gesetzt (temporär).[/yellow]")

    pause()


def _configure_fallback_models():
    """Configure fallback models for rate-limit handling."""
    section("🔄 Fallback-Modelle")

    # Parse aktuell gespeicherte Liste
    current_list = [m.strip() for m in settings.fallback_models_str.split(",") if m.strip()]

    if current_list:
        console.print("  [bold]Aktuelle Fallback-Reihenfolge:[/bold]")
        for i, m in enumerate(current_list, 1):
            console.print(f"    {i}. {m}")
    else:
        console.print("  [dim]Keine eigenen Fallbacks gesetzt – Standard-Liste wird verwendet.[/dim]")

    console.print()
    console.print("  [bold]Optionen:[/bold]")
    console.print("    [cyan]1[/cyan]. Eigene Modelle eingeben (komma-getrennt)")
    console.print("    [cyan]2[/cyan]. Zurücksetzen auf Standard-Liste")
    console.print("    [cyan]3[/cyan]. Fallbacks deaktivieren (leere Liste)")
    console.print("    [cyan]Enter[/cyan]. Abbrechen")
    console.print()

    try:
        raw = _read_line("  Deine Wahl: ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if raw == "1":
        console.print("\n  [dim]Gib die Modelle komma-getrennt ein, in der Reihenfolge des Fallbacks.[/dim]")
        console.print("  [dim]Z.B.: [cyan]meta-llama/llama-3.3-70b-instruct:free, deepseek/deepseek-r1:free[/cyan][/dim]")
        val = ask_text("Fallback-Modelle:")
        if val:
            cleaned = ", ".join(m.strip() for m in val.split(",") if m.strip())
            settings.fallback_models_str = cleaned
            settings.save()
            models = cleaned.split(", ")
            console.print(f"\n  [green]✓ {len(models)} Fallback-Modelle gespeichert![/green]")
            for m in models:
                console.print(f"    • {m}")
    elif raw == "2":
        settings.fallback_models_str = ""
        settings.save()
        from brokus.ai.client import DEFAULT_FALLBACK_MODELS
        defaults = DEFAULT_FALLBACK_MODELS.get(settings.provider, [])
        if defaults:
            console.print(f"\n  [green]✓ Zurückgesetzt auf Standard ({len(defaults)} Modelle)[/green]")
            for m in defaults:
                console.print(f"    • {m}")
        else:
            console.print(f"\n  [green]✓ Für '{settings.provider}' sind keine Standard-Fallbacks definiert.[/green]")
    elif raw == "3":
        settings.fallback_models_str = " "  # Leerzeichen = explizit leer
        settings.save()
        console.print("\n  [green]✓ Fallbacks deaktiviert – Fehler werden nicht abgefangen.[/green]")
    pause()


def _toggle_chapter_delay():
    """Toggle 2-second delay between chapters on/off."""
    settings.chapter_delay_enabled = not settings.chapter_delay_enabled
    settings.save()
    status = "[green]AN[/green]" if settings.chapter_delay_enabled else "[red]AUS[/red]"
    console.print(f"\n  Kapitel-Delay (2s): {status}")
    if settings.chapter_delay_enabled:
        console.print("  [dim]Zwischen jedem Kapitel wird 2 Sekunden gewartet, um Rate-Limits zu vermeiden.[/dim]")
    else:
        console.print("  [dim]Kapitel werden ohne Verzögerung direkt nacheinander generiert.[/dim]")
    pause()


def _toggle_extended_thinking():
    """Toggle extended thinking (reasoning models)."""
    settings.use_extended_thinking = not settings.use_extended_thinking
    settings.save()
    status = "[green]AN[/green]" if settings.use_extended_thinking else "[red]AUS[/red]"
    console.print(f"\n  Extended Thinking: {status}")
    if settings.use_extended_thinking:
        console.print("  [dim]Die KI plant vor dem Schreiben ausführlich (nur bei Reasoning-Modellen sinnvoll).[/dim]")
    else:
        console.print("  [dim]Standard-Modus ohne zusätzliche Planungs-Anweisungen.[/dim]")
    pause()


def _toggle_auto_export():
    """Toggle automatic export after generation."""
    settings.auto_export = not settings.auto_export
    settings.save()
    status = "[green]AN[/green]" if settings.auto_export else "[red]AUS[/red]"
    console.print(f"\n  Auto-Export: {status}")
    if settings.auto_export:
        console.print(f"  [dim]Nach der Generierung wird automatisch in {', '.join(settings.export_formats)} exportiert.[/dim]")
    else:
        console.print("  [dim]Nach der Generierung wird manuell nach dem Export-Format gefragt.[/dim]")
    pause()


def _set_custom_base_url():
    """Set or clear a custom base URL (e.g. for openai_compat, proxies, LiteLLM)."""
    section("🔧 Custom Base-URL")
    console.print(f"  Aktuell: [cyan]{settings.custom_base_url or '(nicht gesetzt)'}[/cyan]")
    console.print("  [dim]Nützlich für eigene OpenAI-kompatible Endpoints (vLLM, TabbyAPI, LiteLLM, ...)[/dim]")
    console.print("  [dim]Leer lassen um die URL zu entfernen.[/dim]")
    val = ask_text("Base-URL (z.B. https://api.example.com/v1):")
    settings.custom_base_url = val.strip() if val else ""
    settings.save()
    if settings.custom_base_url:
        console.print(f"\n  [green]✓ Custom-URL gesetzt: {settings.custom_base_url}[/green]")
    else:
        console.print("\n  [green]✓ Custom-URL entfernt – Provider-Default wird verwendet.[/green]")
    pause()


def _edit_ai_params():
    """Edit AI sampling parameters (temperature, top_p, penalties)."""
    section("🎛️ AI-Parameter")
    console.print(f"  Temperature:      [bold]{settings.temperature}[/bold]")
    console.print(f"  Max-Tokens:       [bold]{settings.max_tokens}[/bold]")
    console.print(f"  Top-P:            [bold]{settings.top_p if settings.top_p is not None else '(aus)'}[/bold]")
    console.print(f"  Frequency-Pen.:   [bold]{settings.frequency_penalty if settings.frequency_penalty is not None else '(aus)'}[/bold]")
    console.print(f"  Presence-Pen.:    [bold]{settings.presence_penalty if settings.presence_penalty is not None else '(aus)'}[/bold]")
    console.print()
    console.print("  [cyan]1[/cyan]. Temperature ändern (0.0 – 2.0)")
    console.print("  [cyan]2[/cyan]. Max-Tokens ändern")
    console.print("  [cyan]3[/cyan]. Top-P setzen / zurücksetzen")
    console.print("  [cyan]4[/cyan]. Frequency-Penalty setzen / zurücksetzen")
    console.print("  [cyan]5[/cyan]. Presence-Penalty setzen / zurücksetzen")
    console.print("  [cyan]6[/cyan]. Alle auf Standard zurücksetzen")
    console.print("  [cyan]Enter[/cyan]. Abbrechen")
    console.print()
    try:
        raw = _read_line("  Deine Wahl: ").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if raw == "1":
        v = ask_text("Temperature (0.0 = deterministisch, 1.0 = Standard, 2.0 = sehr kreativ):", default=str(settings.temperature))
        try:
            settings.temperature = max(0.0, min(2.0, float(v)))
        except ValueError:
            console.print("  [red]Ungültiger Wert.[/red]")
    elif raw == "2":
        v = ask_text("Max-Tokens (z.B. 4000):", default=str(settings.max_tokens))
        try:
            settings.max_tokens = max(100, int(v))
        except ValueError:
            console.print("  [red]Ungültiger Wert.[/red]")
    elif raw == "3":
        v = ask_text("Top-P (0.0–1.0, leer = aus):", default="" if settings.top_p is None else str(settings.top_p))
        try:
            settings.top_p = None if not v.strip() else max(0.0, min(1.0, float(v)))
        except ValueError:
            console.print("  [red]Ungültiger Wert.[/red]")
    elif raw == "4":
        v = ask_text("Frequency-Penalty (-2.0–2.0, leer = aus):", default="" if settings.frequency_penalty is None else str(settings.frequency_penalty))
        try:
            settings.frequency_penalty = None if not v.strip() else max(-2.0, min(2.0, float(v)))
        except ValueError:
            console.print("  [red]Ungültiger Wert.[/red]")
    elif raw == "5":
        v = ask_text("Presence-Penalty (-2.0–2.0, leer = aus):", default="" if settings.presence_penalty is None else str(settings.presence_penalty))
        try:
            settings.presence_penalty = None if not v.strip() else max(-2.0, min(2.0, float(v)))
        except ValueError:
            console.print("  [red]Ungültiger Wert.[/red]")
    elif raw == "6":
        settings.temperature = 0.7
        settings.max_tokens = 4000
        settings.top_p = None
        settings.frequency_penalty = None
        settings.presence_penalty = None
        console.print("  [green]✓ Auf Standard zurückgesetzt.[/green]")
    else:
        pause()
        return
    settings.save()
    console.print("  [green]✓ Gespeichert.[/green]")
    pause()


def _edit_generation_params():
    """Edit generation parameters (language, chapters, pace, detail)."""
    section("📝 Generierung")
    lang_keys = [l for l in LANGUAGES]
    li = choose("Default-Sprache:", lang_keys)
    if li >= 0:
        settings.default_language = lang_keys[li]
    cap = ask_text("Default-Kapitelanzahl:", default=str(settings.default_chapters))
    try:
        settings.default_chapters = max(3, min(100, int(cap)))
    except ValueError:
        pass
    paces = ["slow (viel Atmosphäre)", "balanced (Standard)", "fast (viele Wendungen)"]
    pkeys = ["slow", "balanced", "fast"]
    pi = choose("Erzähltempo:", paces)
    if pi >= 0:
        settings.story_pace = pkeys[pi]
    details = ["loose (KI hat mehr Freiheit)", "standard (ausgewogen)", "detailed (Idee genau umsetzen)", "strict (maximale Treue)"]
    dkeys = ["loose", "standard", "detailed", "strict"]
    di = choose("Detailgrad der Umsetzung:", details)
    if di >= 0:
        settings.detail_level = dkeys[di]
    # Compliance-Schwelle
    ct = ask_text(
        f"Compliance-Schwelle 0–100% (aktuell: {settings.compliance_threshold}):",
        default=str(settings.compliance_threshold),
    )
    try:
        settings.compliance_threshold = max(0, min(100, int(ct)))
    except ValueError:
        pass
    settings.save()
    console.print("  [green]✓ Generierung gespeichert.[/green]")
    pause()


def _toggle_backup():
    """Toggle backup before each generation."""
    settings.backup_enabled = not settings.backup_enabled
    settings.save()
    status = "[green]AN[/green]" if settings.backup_enabled else "[red]AUS[/red]"
    console.print(f"\n  Backup vor Generation: {status}")
    if settings.backup_enabled:
        console.print("  [dim]Vor jeder Buch-Generierung wird ein DB-Backup angelegt.[/dim]")
    else:
        console.print("  [dim]⚠ Kein automatisches Backup – Datenverlust möglich.[/dim]")
    pause()


def _toggle_auto_open():
    """Toggle auto-open of exported file."""
    settings.auto_open_after_export = not settings.auto_open_after_export
    settings.save()
    status = "[green]AN[/green]" if settings.auto_open_after_export else "[red]AUS[/red]"
    console.print(f"\n  Auto-Open nach Export: {status}")
    if settings.auto_open_after_export:
        console.print("  [dim]Nach dem Export wird die Datei automatisch mit dem System-Reader geöffnet.[/dim]")
    else:
        console.print("  [dim]Du wirst nach dem Export gefragt, ob du die Datei öffnen möchtest.[/dim]")
    pause()


def _toggle_confirm_quit():
    """Toggle quit confirmation."""
    settings.confirm_quit = not settings.confirm_quit
    settings.save()
    status = "[green]AN[/green]" if settings.confirm_quit else "[red]AUS[/red]"
    console.print(f"\n  Beenden-Bestätigung: {status}")
    if settings.confirm_quit:
        console.print("  [dim]Du wirst vor dem Beenden gefragt, ob du wirklich abbrechen willst.[/dim]")
    else:
        console.print("  [dim]Brokus beendet sich sofort – vorsichtig![/dim]")
    pause()


def _toggle_cache():
    """Toggle AI response cache."""
    settings.cache_responses = not settings.cache_responses
    settings.save()
    status = "[green]AN[/green]" if settings.cache_responses else "[red]AUS[/red]"
    console.print(f"\n  AI-Antworten cachen: {status}")
    if settings.cache_responses:
        console.print(f"  [dim]Cache aktiv, max. {settings.max_cache_size_mb} MB.[/dim]")
    else:
        console.print("  [dim]Kein Cache – jede Anfrage geht direkt zum Provider (langsamer, teurer).[/dim]")
    pause()


def _toggle_show_tokens():
    """Toggle token count display."""
    settings.show_token_count = not settings.show_token_count
    settings.save()
    status = "[green]AN[/green]" if settings.show_token_count else "[red]AUS[/red]"
    console.print(f"\n  Token-Verbrauch anzeigen: {status}")
    pause()


def _toggle_show_cost():
    """Toggle cost estimate display."""
    settings.show_cost_estimate = not settings.show_cost_estimate
    settings.save()
    status = "[green]AN[/green]" if settings.show_cost_estimate else "[red]AUS[/red]"
    console.print(f"\n  Kosten-Schätzung anzeigen: {status}")
    pause()


def _set_max_retries():
    """Set max retries for AI calls."""
    val = ask_text(
        f"Max. Retries bei Fehlern (aktuell: {getattr(settings, 'max_retries', 3)}):",
        default="3",
    )
    try:
        settings.max_retries = max(0, min(10, int(val)))
        settings.save()
        console.print(f"  [green]✓ Max-Retries auf {settings.max_retries} gesetzt.[/green]")
    except ValueError:
        console.print("  [red]Ungültiger Wert.[/red]")
    pause()


def _set_compliance_threshold():
    """Set compliance threshold (0–100)."""
    val = ask_text(
        f"Compliance-Schwelle 0–100 (aktuell: {settings.compliance_threshold}):",
        default=str(settings.compliance_threshold),
    )
    try:
        settings.compliance_threshold = max(0, min(100, int(val)))
        settings.save()
        console.print(f"  [green]✓ Compliance-Schwelle auf {settings.compliance_threshold}% gesetzt.[/green]")
    except ValueError:
        console.print("  [red]Ungültiger Wert.[/red]")
    pause()


def _view_all_settings():
    """Show all current settings in a comprehensive overview table."""
    section("📋 Alle Einstellungen")
    table = Table(show_header=True, header_style="bold cyan", show_lines=False, padding=(0, 1))
    table.add_column("Kategorie", style="bold bright_blue", width=18)
    table.add_column("Setting", width=28)
    table.add_column("Wert", style="green")

    def yesno(b): return "[green]✓ AN[/green]" if b else "[red]✗ AUS[/red]"
    def opt(v): return f"{v}" if v is not None else "[dim]aus[/dim]"

    # Provider / API
    has_key = _has_api_key()
    table.add_row("🤖 Provider", "Provider", settings.provider)
    table.add_row("", "Modell", settings.model)
    table.add_row("", "API-Key", "[green]✓ gesetzt[/green]" if has_key else "[red]✗ fehlt[/red]")
    table.add_row("", "Custom-Base-URL", settings.custom_base_url or "[dim](default)[/dim]")

    # AI-Parameter
    table.add_row("🎛️ AI-Parameter", "Temperature", f"{settings.temperature}")
    table.add_row("", "Max-Tokens", f"{settings.max_tokens}")
    table.add_row("", "Top-P", opt(settings.top_p))
    table.add_row("", "Frequency-Penalty", opt(settings.frequency_penalty))
    table.add_row("", "Presence-Penalty", opt(settings.presence_penalty))

    # Generierung
    table.add_row("📝 Generierung", "Default-Sprache", settings.default_language)
    table.add_row("", "Default-Kapitel", f"{settings.default_chapters}")
    table.add_row("", "Detailgrad", settings.detail_level)
    table.add_row("", "Erzähltempo", settings.story_pace)
    table.add_row("", "Compliance-Schwelle", f"{settings.compliance_threshold}%")
    table.add_row("", "Kapitel-Delay", yesno(settings.chapter_delay_enabled))
    table.add_row("", "Auto-Retry", yesno(settings.auto_retry))
    table.add_row("", "Backup vor Generation", yesno(settings.backup_enabled))
    table.add_row("", "Auto-Export", yesno(settings.auto_export))
    table.add_row("", "Auto-Open nach Export", yesno(settings.auto_open_after_export))
    table.add_row("", "Export-Formate", ", ".join(settings.export_formats) or "[dim]keine[/dim]")

    # Reasoning / Fallback
    table.add_row("🧠 Erweitert", "Extended Thinking", yesno(settings.use_extended_thinking))
    table.add_row("", "Wizard-Modellauswahl", yesno(settings.wizard_model_picker))
    fb = settings.fallback_models_str or "[dim]Provider-Default[/dim]"
    table.add_row("", "Fallback-Modelle", fb.strip() or "[dim]Provider-Default[/dim]")

    # UI
    table.add_row("🎨 UI & Logging", "Log-Level", settings.log_level)
    table.add_row("", "Token-Anzeige", yesno(settings.show_token_count))
    table.add_row("", "Kosten-Anzeige", yesno(settings.show_cost_estimate))
    table.add_row("", "Beenden-Bestätigung", yesno(settings.confirm_quit))

    # Advanced
    table.add_row("⚙️ Technisch", "Request-Timeout", f"{settings.request_timeout}s")
    table.add_row("", "Cache aktiv", yesno(settings.cache_responses))
    table.add_row("", "Max. Cache-Größe", f"{settings.max_cache_size_mb} MB")

    console.print(table)
    pause()


def _edit_ui_params():
    """Edit UI / logging parameters."""
    section("🎨 UI & Logging")
    levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    li = choose("Log-Level:", levels)
    if li >= 0:
        settings.log_level = levels[li]
    # Toggles mit klarer UX
    if confirm(f"Token-Verbrauch anzeigen? (aktuell: {'ja' if settings.show_token_count else 'nein'})"):
        settings.show_token_count = True
    else:
        settings.show_token_count = False
    if confirm(f"Kosten-Schätzung anzeigen? (aktuell: {'ja' if settings.show_cost_estimate else 'nein'})"):
        settings.show_cost_estimate = True
    else:
        settings.show_cost_estimate = False
    settings.save()
    console.print("  [green]✓ UI gespeichert.[/green]")
    pause()


def _edit_advanced_params():
    """Edit advanced parameters (cache, timeout)."""
    section("🔧 Erweitert")
    to = ask_text("Request-Timeout (Sekunden):", default=str(settings.request_timeout))
    try:
        settings.request_timeout = max(30, int(to))
    except ValueError:
        pass
    cs = ask_text("Max. Cache-Größe (MB):", default=str(settings.max_cache_size_mb))
    try:
        settings.max_cache_size_mb = max(50, int(cs))
    except ValueError:
        pass
    if confirm(f"AI-Antworten cachen? (aktuell: {'ja' if settings.cache_responses else 'nein'})"):
        settings.cache_responses = True
    else:
        settings.cache_responses = False
    settings.save()
    console.print("  [green]✓ Erweiterte Einstellungen gespeichert.[/green]")
    pause()


def _reset_settings_to_defaults():
    """Reset all settings to their default values."""
    if not confirm("⚠ Wirklich ALLE Einstellungen auf Standard zurücksetzen?"):
        return
    global settings
    # Re-create with defaults
    fresh = Settings()
    # Preserve provider/model (so we don't lock out users)
    fresh.provider = settings.provider
    fresh.model = settings.model
    fresh.custom_base_url = settings.custom_base_url
    fresh.fallback_models_str = settings.fallback_models_str
    settings = fresh
    settings.save()
    console.print("  [green]✓ Alle Einstellungen auf Standard zurückgesetzt (Provider/Model/API behalten).[/green]")
    pause()


def _open_settings_yaml():
    """Open config/settings.yaml in the user's default editor."""
    import subprocess
    config_path = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"
    editor = os.environ.get("EDITOR", "").split()
    if not editor:
        for fallback in (["nano"], ["vi"], ["code", "--wait"], ["xdg-open"]):
            try:
                subprocess.run([fallback[0], "--version"], capture_output=True, timeout=2)
                editor = fallback
                break
            except Exception:
                continue
    if not editor:
        console.print(f"  [yellow]Kein Editor gefunden. Datei: {config_path}[/yellow]")
        console.print("  [dim]Setze $EDITOR oder installiere nano/vi/code.[/dim]")
        pause()
        return
    try:
        console.print(f"  Öffne [cyan]{config_path}[/cyan] mit [cyan]{' '.join(editor)}[/cyan]...")
        subprocess.run(editor + [str(config_path)])
    except Exception as e:
        console.print(f"  [red]Fehler: {e}[/red]")
    pause()


def _toggle_wizard_model_picker():
    """Toggle model selection step in the wizard on/off."""
    settings.wizard_model_picker = not settings.wizard_model_picker
    settings.save()
    status = "[green]AN[/green]" if settings.wizard_model_picker else "[red]AUS[/red]"
    console.print(f"\n  Modell-Auswahl im Wizard: {status}")
    if settings.wizard_model_picker:
        console.print("  [dim]Beim Buch-Erstellen erscheint ein Schritt zur Modell-Auswahl.\n  Im Schnell-Modus wird nach der Sprache gefragt, im Meisterwerk als Schritt 6/11.[/dim]")
    else:
        console.print("  [dim]Der Wizard überspringt die Modell-Auswahl.\n  Es wird immer das aktuell eingestellte Modell verwendet.[/dim]")
    pause()


def _pick_export_formats():
    """Multi-select dialog for choosing export formats."""
    clear()
    banner()
    selected = ask_multi(
        "Wähle die Dateiformate für den Export:",
        list(EXPORT_FORMATS),
        defaults=settings.export_formats,
    )
    settings.export_formats = selected
    settings.save()
    if selected:
        names = [f[1] for f in EXPORT_FORMATS if f[0] in selected]
        console.print(f"\n  [green]✓ {len(selected)} Format(e) gesetzt: {', '.join(names)}[/green]")
    else:
        console.print("\n  [yellow]⚠ Keine Formate gewählt – Export wird übersprungen.[/yellow]")
    pause()


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def run():
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        console.print("\n[cyan]Auf Wiedersehen! 👋[/cyan]\n")
        sys.exit(0)
