"""brokus TUI – Thin orchestrator (prompt_toolkit).

Keybindings, navigation, business logic, layout, and run().
Rendering is delegated to pt_screens.py, state to pt_state.py.
"""
import asyncio
import os

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, ConditionalContainer
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.widgets import TextArea

from brokus.utils.logger import log
from brokus.tui.pt_state import (
    AppState, STYLE, GENRES, GENRE_NAMES, EXPORT_FORMATS, EXPORT_KEYS,
    AUDIENCES, PERSPECTIVES, TONES, LENGTHS, TEXT_SCREENS, LANGUAGES, LANG_TO_CODE,
)
from brokus.tui.pt_screens import render


# ─────────────────────────────────────────────────────────────
# Global state instance
# ─────────────────────────────────────────────────────────────

S = AppState()


# ─────────────────────────────────────────────────────────────
# Navigation helpers
# ─────────────────────────────────────────────────────────────

def _go(scr: str):
    S.scr = scr
    S.msg = ""
    _inv()


def _inv():
    if S.app:
        S.app.invalidate()


def _activate_input(text: str = ""):
    if S.input_buffer:
        S.input_buffer.text = text
        if S.input_window:
            S.app.layout.focus(S.input_window)


def _deactivate_input():
    if S.main_window:
        S.app.layout.focus(S.main_window)


# ─────────────────────────────────────────────────────────────
# Wizard navigation
# ─────────────────────────────────────────────────────────────

def _advance():
    if S.mode == "schnell":
        if S.step < 2:
            S.step += 1
            S.scr = f"schnell_{S.step}"
            if S.is_text_screen:
                _activate_input("")
            else:
                _deactivate_input()
        else:
            _deactivate_input()
            _start_gen()
    elif S.mode == "meister":
        if S.step < 8:
            S.step += 1
            S.scr = f"meister_{S.step}"
            if S.is_text_screen:
                _activate_input("")
            else:
                _deactivate_input()
        else:
            _deactivate_input()
            _start_gen()
    _inv()


def _menu_select(d: int):
    if d == 1:
        S.reset_wizard("schnell")
        S.scr = "schnell_0"
        _activate_input("")
    elif d == 2:
        S.reset_wizard("meister")
        S.scr = "meister_0"
        _activate_input("")
    elif d == 3:
        _go("library")
    elif d == 4:
        _go("settings")
    elif d == 5:
        _cancel_gen()
        S.app.exit()


# ─────────────────────────────────────────────────────────────
# Settings navigation
# ─────────────────────────────────────────────────────────────

def _settings_dispatch(d: int):
    if d == 1:
        _go_settings_prov()
    elif d == 2:
        _go("settings_m")
    elif d == 3:
        S.settings_buf = ""
        S.scr = "settings_k"
        S.msg = ""
        _inv()
        _activate_input(S.settings_buf)
    elif d == 4:
        _go("settings_f")


def _go_settings_prov():
    try:
        from brokus.ai.client import PROVIDER_REGISTRY
        S.settings_providers = []
        for i, (k, p) in enumerate(PROVIDER_REGISTRY.items()):
            S.settings_providers.append({
                "key": k, "name": p.name, "cost": p.cost_info,
                "models": p.models, "env": p.api_key_env, "feat": p.features,
            })
            if k == S.settings_cur_provider:
                S.settings_prov_idx = i
    except Exception:
        S.settings_providers = []
    _go("settings_p")


def _settings_pick_provider(d: int):
    if d - 1 < len(S.settings_providers):
        S.settings_prov_idx = d - 1
        p = S.settings_providers[S.settings_prov_idx]
        S.settings_cur_provider = p["key"]
        if p.get("models"):
            S.settings_cur_model = p["models"][0]
        _go("settings")


def _settings_pick_model(d: int):
    try:
        from brokus.ai.client import PROVIDER_REGISTRY
        pc = PROVIDER_REGISTRY.get(S.settings_cur_provider)
        models = list(pc.models) if pc else []

        # Providers that support custom model names
        _CUSTOM_MODEL_PROVIDERS = {"ollama_local", "lmstudio", "localai"}
        custom_offset = 0
        if pc and pc.key in _CUSTOM_MODEL_PROVIDERS:
            models.append("✏️  Benutzerdefiniert...")
            custom_offset = 1

        if d - 1 < len(models):
            selected = models[d - 1]
            if custom_offset and d - 1 == len(models) - 1:
                # Custom model selected – prompt user via text input
                S.scr = "settings_custom_model"
                S.msg = "Modellnamen eingeben (z.B. llama3.2:3b, qwen2.5:7b, ...)"
                _activate_input(S.settings_cur_model if S.settings_cur_model not in pc.models else "")
                _inv()
                return
            S.settings_cur_model = selected
            _go("settings")
            return
    except Exception:
        pass
    _inv()


def _save_custom_model():
    """Save a custom model name entered by the user."""
    txt = S.input_buffer.text.strip() if S.input_buffer else ""
    if txt:
        S.settings_cur_model = txt
        S.msg = f"Modell gesetzt: {txt}"
    else:
        S.msg = "Kein Modellname eingegeben."
    _deactivate_input()
    _go("settings")


def _settings_pick_fmt(d: int):
    """Toggle export formats. Press 1-6 to toggle, Enter/0 to save."""
    if d == 0:
        # Save and return
        S.settings_export_fmts = [k for k in S.settings_export_fmts if k in EXPORT_KEYS]
        if not S.settings_export_fmts:
            S.settings_export_fmts = ["md"]
        S.settings_export_fmt = EXPORT_KEYS.index(S.settings_export_fmts[0]) if S.settings_export_fmts[0] in EXPORT_KEYS else 0
        _go("settings")
        return
    if d - 1 < len(EXPORT_KEYS):
        key = EXPORT_KEYS[d - 1]
        if key in S.settings_export_fmts:
            S.settings_export_fmts.remove(key)
        else:
            S.settings_export_fmts.append(key)
        S.msg = f"Export-Formate: {', '.join(S.settings_export_fmts) or '(keine)'}"
        _inv()


def _save_api_key():
    k = S.settings_buf.strip()
    p = None
    for prov in S.settings_providers:
        if prov["key"] == S.settings_cur_provider:
            p = prov
            break
    ev = p.get("env", "") if p else ""

    if not k:
        try:
            if p:
                from brokus.utils.crypto import SecretStore
                store = SecretStore.instance()
                store.delete(ev)
                store.save()
                os.environ.pop(ev, None)
                S.msg = "API-Key geloescht."
        except Exception as e:
            S.msg = f"Fehler: {e}"
        _deactivate_input()
        _go("settings")
        return

    try:
        if p:
            from brokus.utils.crypto import SecretStore
            store = SecretStore.instance()
            store.set(ev, k)
            store.save()
            os.environ[ev] = k
            S.msg = "API-Key gespeichert."
    except Exception as e:
        S.msg = f"Fehler: {e}"
    _deactivate_input()
    _go("settings")


# ─────────────────────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────────────────────

def _cancel_gen():
    if S.gen_task and not S.gen_task.done():
        S.gen_task.cancel()
    S.gen_prog = 0
    S.gen_stage = ""
    S.scr = "menu"


def _start_gen():
    S.gen_title = S.display_title
    S.gen_prog = 0
    S.gen_stage = "Starte..."
    S.scr = "generating"
    S.msg = ""
    S.gen_task = asyncio.ensure_future(_run_gen())


async def _run_gen():
    from prompt_toolkit.application.current import get_app
    app = get_app()
    try:
        S.gen_stage = "Initialisiere..."
        S.gen_prog = 0.05
        app.invalidate()

        from brokus.storage.database import (
            create_project, save_chapter, update_project, log_generation_event,
        )
        from brokus.ai.client import BrokusAIClient
        from brokus.ai.prompts import PromptLoader, GenreLoader
        from brokus.core.pipeline import BookPipeline

        gn = S.genre_key
        ch = S.chapter_count
        lang = LANGUAGES[S.language] if S.language < len(LANGUAGES) else "Deutsch"

        pid = await create_project(
            title=S.display_title, genre=gn, idea=S.idea,
            total_chapters=ch, model=S.settings_cur_model,
        )
        client = BrokusAIClient(provider=S.settings_cur_provider, model=S.settings_cur_model)
        pipeline = BookPipeline(client=client, prompts=PromptLoader(), genres=GenreLoader())

        async def save_cb(cn, ct, tx, **kw):
            await save_chapter(
                project_id=pid, number=cn, title=ct, text=tx,
                word_count=kw.get("word_count", 0),
                compliance_score=kw.get("compliance_score"),
                status=kw.get("status", "completed"),
            )
            await update_project(pid, chapters_completed=cn, total_words=kw.get("word_count", 0), status="generating")
            S.gen_stage = f"Kapitel {cn}/{ch}"
            S.gen_prog = 0.1 + 0.85 * (cn / ch)
            S.gen_comp = kw.get("compliance_score", 0) or 0
            app.invalidate()

        async def log_cb(msg, **kw):
            await log_generation_event(
                pid, event=msg, level=kw.get("level", "INFO"),
                chapter_number=kw.get("chapter_number"), details=kw.get("details"),
            )
            log.info(msg)

        result = await pipeline.run(
            book_idea=S.idea, genre_key=gn, num_chapters=ch,
            save_chapter_cb=save_cb, log_event_cb=log_cb,
            language=lang,
        )

        await update_project(pid, status="completed", total_words=result.get("total_words", 0))

        # Export
        export_ok = True
        try:
            from brokus.storage.database import get_all_chapters
            from brokus.storage.exporter import Exporter
            chaps = await get_all_chapters(pid)
            ek_list = S.export_keys
            lang_code = LANG_TO_CODE.get(lang, "de")
            Exporter().export_multiple(
                {"title": S.display_title, "genre": gn, "idea": S.idea},
                chaps,
                formats=ek_list,
                language=lang_code,
            )
        except Exception as ex:
            log.warning(f"Export fehlgeschlagen: {ex}")
            export_ok = False

        S.gen_prog = 1.0
        S.gen_stage = "Fertig!"
        S.msg = (
            f"'{S.display_title}' erstellt! (Export: {', '.join(ek_list)})"
            if export_ok
            else f"'{S.display_title}' erstellt! (Export fehlgeschlagen)"
        )
        S.scr = "menu"
        app.invalidate()

    except asyncio.CancelledError:
        pass
    except Exception as ex:
        S.gen_stage = f"Fehler: {ex}"
        S.msg = str(ex)
        S.scr = "menu"
        app.invalidate()
        log.error(f"Gen: {ex}")


# ─────────────────────────────────────────────────────────────
# Library / Reading
# ─────────────────────────────────────────────────────────────

async def _load_reader(book: dict):
    try:
        from brokus.storage.database import get_all_chapters
        bid = book.get("id")
        if bid:
            S.chapters = await get_all_chapters(bid)
            S.ch_idx = 0
            S.scr = "reading"
            _inv()
            return
        S.msg = "Nicht gefunden."
        _inv()
    except Exception as e:
        S.msg = str(e)
        _inv()


async def _load_books():
    try:
        from brokus.storage.database import get_all_projects
        projects = await get_all_projects()
        S.books = []
        for p in projects:
            S.books.append({
                "title": p.get("title", "?"),
                "genre": p.get("genre", "?"),
                "chapters_total": p.get("total_chapters", 0),
                "chapters_done": p.get("chapters_completed", 0),
                "word_count": p.get("total_words", 0),
                "created": (p.get("created_at", "") or "")[:10],
                "status": p.get("status", "draft"),
                "id": p.get("id"),
            })
        S.books.sort(key=lambda b: b.get("created", ""), reverse=True)
    except Exception as e:
        log.error(f"Books: {e}")


# ─────────────────────────────────────────────────────────────
# Key Bindings
# ─────────────────────────────────────────────────────────────

kb = KeyBindings()


@kb.add("c-c")
def _(e):
    _cancel_gen()
    e.app.exit()


# ── Text input submit ──
@kb.add("escape")
@kb.add("c-d")
def _(e):
    if S.is_text_screen and S.input_buffer:
        txt = S.input_buffer.text.strip()
        if S.scr == "settings_k":
            S.settings_buf = txt
            _save_api_key()
        elif S.scr == "settings_custom_model":
            _save_custom_model()
        elif S.scr in ("schnell_0", "meister_0"):
            S.idea = txt
            _deactivate_input()
            _advance()
        elif S.scr in ("schnell_1", "meister_1"):
            S.title = txt
            _deactivate_input()
            _advance()


# ── Ctrl+V paste ──
@kb.add("c-v")
def _(e):
    if S.is_text_screen and S.input_buffer:
        try:
            data = e.app.clipboard.get_data()
            txt = data.text if hasattr(data, "text") else str(data)
            if txt:
                S.input_buffer.insert_text(txt)
        except Exception:
            pass


# ── 0 = Back ──
@kb.add("0")
def _(e):
    if S.is_text_screen:
        _deactivate_input()
        if S.scr == "settings_k":
            _go("settings")
            return
        if S.scr == "settings_custom_model":
            _go("settings")
            return
        _wiz_back()
        return
    if S.scr == "menu":
        e.app.exit()
    elif S.scr.startswith("schnell_"):
        _wiz_back()
    elif S.scr.startswith("meister_"):
        _wiz_back()
    elif S.scr in ("library", "reading"):
        _go("menu")
    elif S.scr == "settings":
        _go("menu")
    elif S.scr in ("settings_p", "settings_m", "settings_k", "settings_f", "settings_custom_model"):
        _go("settings")
    elif S.scr == "generating":
        _cancel_gen()
    _inv()


# ── Enter ──
@kb.add("enter")
def _(e):
    if S.is_text_screen and S.input_buffer:
        txt = S.input_buffer.text.strip()
        if S.scr == "settings_k":
            S.settings_buf = txt
            _save_api_key()
            return
        elif S.scr == "settings_custom_model":
            _save_custom_model()
            return
        elif txt:
            if S.scr in ("schnell_0", "meister_0"):
                S.idea = txt
                _deactivate_input()
                _advance()
                return
            elif S.scr in ("schnell_1", "meister_1"):
                S.title = txt
                _deactivate_input()
                _advance()
                return
        return
    if S.scr == "library" and S.books:
        asyncio.ensure_future(_load_reader(S.books[S.book_sel]))


# ── Digits 1-9 ──
for _digit in range(1, 10):
    @kb.add(str(_digit))
    def _handler(e, d=_digit):
        if S.is_text_screen:
            return
        if S.scr == "menu":
            _menu_select(d)
        elif S.scr == "schnell_2":
            if d - 1 < len(GENRES):
                S.genre = d - 1
                _advance()
        elif S.scr == "meister_2":
            if d - 1 < len(GENRES):
                S.genre = d - 1
                _advance()
        elif S.scr == "meister_3":
            if d - 1 < len(AUDIENCES):
                S.audience = d - 1
                _advance()
        elif S.scr == "meister_4":
            if d - 1 < len(LANGUAGES):
                S.language = d - 1
                _advance()
        elif S.scr == "meister_5":
            if d - 1 < len(PERSPECTIVES):
                S.perspective = d - 1
                _advance()
        elif S.scr == "meister_6":
            if d - 1 < len(TONES):
                S.tone = d - 1
                _advance()
        elif S.scr == "meister_7":
            if d - 1 < len(LENGTHS):
                S.length = d - 1
                _advance()
        elif S.scr == "meister_8" and d == 1:
            _start_gen()
        elif S.scr == "library":
            S.book_sel = d - 1
        elif S.scr == "settings":
            _settings_dispatch(d)
        elif S.scr == "settings_p":
            _settings_pick_provider(d)
        elif S.scr == "settings_m":
            _settings_pick_model(d)
        elif S.scr == "settings_f":
            _settings_pick_fmt(d)
        _inv()


@kb.add("left")
def _(e):
    if S.scr == "reading" and S.ch_idx > 0:
        S.ch_idx -= 1
        _inv()


@kb.add("right")
def _(e):
    if S.scr == "reading" and S.ch_idx < len(S.chapters) - 1:
        S.ch_idx += 1
        _inv()


# ─────────────────────────────────────────────────────────────
# Layout & App
# ─────────────────────────────────────────────────────────────

async def _run_async():
    S.input_buffer = Buffer(multiline=True)
    S.input_area = TextArea(
        text="", prompt="  > ", style="class:text-area",
        height=6, multiline=True,
    )
    S.input_area.buffer = S.input_buffer

    input_window = Window(
        content=S.input_area.control,
        height=lambda: 3 if S.scr in ("settings_k", "settings_custom_model") else 6,
        wrap_lines=False,
    )
    main_window = Window(
        FormattedTextControl(lambda: to_formatted_text(render(S))),
        wrap_lines=False,
    )

    layout = Layout(HSplit([
        ConditionalContainer(main_window, filter=Condition(lambda: not S.is_text_screen)),
        ConditionalContainer(HSplit([main_window, input_window]), filter=Condition(lambda: S.is_text_screen)),
        Window(FormattedTextControl(lambda: [
            ("class:bar", " brokus | [0]=Zurueck  [1-9]=Waehlen  [Enter]=Speichern  [Ctrl+C]=Ende ")
        ]), height=1),
    ]))

    app = Application(
        layout=layout, key_bindings=kb, style=STYLE,
        full_screen=True, mouse_support=False,
    )
    S.app = app
    S.main_window = main_window
    S.input_window = input_window

    async def init():
        try:
            from brokus.storage.database import init_db
            await init_db()
        except Exception as ex:
            log.warning(f"DB: {ex}")
        try:
            from brokus.utils.crypto import load_secrets
            load_secrets()
        except Exception:
            pass
        try:
            from brokus.ai.client import PROVIDER_REGISTRY
            S.settings_providers = []
            for i, (k, p) in enumerate(PROVIDER_REGISTRY.items()):
                S.settings_providers.append({
                    "key": k, "name": p.name, "cost": p.cost_info,
                    "models": p.models, "env": p.api_key_env, "feat": p.features,
                })
                if k == S.settings_cur_provider:
                    S.settings_prov_idx = i
        except Exception:
            pass
        await _load_books()

    asyncio.create_task(init())
    await app.run_async()


def run():
    asyncio.run(_run_async())
