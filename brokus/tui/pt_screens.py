"""brokus TUI – Screen renderers (prompt_toolkit).

Each function takes an AppState and returns FormattedText (list of tuples).
Pure rendering – no mutation, no I/O.
"""
from brokus.tui.pt_state import (
    AppState, GENRES, GENRE_NAMES, EXPORT_FORMATS, AUDIENCES, LANGUAGES,
    PERSPECTIVES, TONES, LENGTHS, SEP,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _progress(n: int, total: int) -> str:
    return "".join("\u25cf" if i < n else "\u25cb" for i in range(total))


def _wiz_header(icon: str, mode: str, step: int, total: int, title: str) -> list:
    return [
        ("class:title", f"\n  {icon} {mode} \u00b7 {step}/{total}\n"),
        ("", f"\n  {title}\n\n"),
        SEP,
    ]


def _hint_save() -> list:
    return [SEP, ("class:hint", "   [Enter]=Speichern & weiter    [0]=Zurueck\n")]


def _hint_apikey() -> list:
    return [SEP, ("class:hint", "   [Enter]=Speichern    [0]=Zurueck\n")]


# ─────────────────────────────────────────────────────────────
# Menu
# ─────────────────────────────────────────────────────────────

def render_menu(s: AppState) -> list:
    L = [
        ("class:title", "\n              \U0001f4d6  B R O K U S\n\n\n"),
        ("", "    [1]  \u26a1  Schnell-Buch \u2013 Idee & Titel, los!\n"),
        ("", "    [2]  \u2728  Meisterwerk \u2013 Alle Details konfigurieren\n"),
        ("", "    [3]  \U0001f4d6  Bibliothek \u2013 Gespeicherte Buecher lesen\n"),
        ("", "    [4]  \u2699\ufe0f   Einstellungen \u2013 API-Key, Modell, Export\n"),
        ("", "    [5]  \U0001f6aa  Beenden\n\n"),
        SEP,
        ("class:hint", "   Auswahl: _\n"),
    ]
    if s.msg:
        L.append(("class:ok", f"  {s.msg}"))
    return L


# ─────────────────────────────────────────────────────────────
# Wizard: Schnell-Buch
# ─────────────────────────────────────────────────────────────

def render_schnell_0(s: AppState) -> list:
    L = _wiz_header("\u26a1", "Schnell-Buch", 1, 3, "\U0001f4a1 Deine Buchidee")
    L += _hint_save()
    return L


def render_schnell_1(s: AppState) -> list:
    L = _wiz_header("\u26a1", "Schnell-Buch", 2, 3, "\U0001f4d5 Titel")
    L += _hint_save()
    return L


def render_schnell_2(s: AppState) -> list:
    L = _wiz_header("\u26a1", "Schnell-Buch", 3, 3, "\U0001f3ad Genre auswaehlen")
    L += _genre_list(s.genre)
    L += [SEP, ("class:hint", f"   {_progress(3, 3)}    Auswahl: _    [0] Zurueck\n")]
    return L


# ─────────────────────────────────────────────────────────────
# Wizard: Meisterwerk
# ─────────────────────────────────────────────────────────────

_MEISTER_TITLES = [
    "\U0001f4a1 Beschreibe deine Buchidee ausfuehrlich",
    "\U0001f4d5 Titel",
    "\U0001f3ad Genre",
    "\U0001f465 Zielgruppe",
    "\U0001f30d Sprache",
    "\U0001f441\ufe0f  Erzaehlperspektive",
    "\U0001f3a8 Stimmung & Ton",
    "\U0001f4cf Buchlaenge",
    "\u2705 Alles bereit?",
]


def render_meister(s: AppState, step: int) -> list:
    total = 9
    L = _wiz_header("\u2728", "Meisterwerk", step + 1, total, _MEISTER_TITLES[step])

    if step <= 1:
        L += _hint_save()
    elif step == 2:
        L += _genre_list(s.genre)
        L += [SEP, ("class:hint", f"   {_progress(3, total)}    Auswahl: _    [0] Zurueck\n")]
    elif step == 3:
        for i, a in enumerate(AUDIENCES):
            L.append(("class:sel" if i == s.audience else "", f"    [{i + 1}] {a}\n"))
        L += [SEP, ("class:hint", f"   {_progress(4, total)}    Auswahl: _    [0] Zurueck\n")]
    elif step == 4:
        for i, lang in enumerate(LANGUAGES):
            L.append(("class:sel" if i == s.language else "", f"    [{i + 1}] {lang}\n"))
        L += [SEP, ("class:hint", f"   {_progress(5, total)}    Auswahl: _    [0] Zurueck\n")]
    elif step == 5:
        for i, p in enumerate(PERSPECTIVES):
            L.append(("class:sel" if i == s.perspective else "", f"    [{i + 1}] {p}\n"))
        L += [SEP, ("class:hint", f"   {_progress(6, total)}    Auswahl: _    [0] Zurueck\n")]
    elif step == 6:
        for i, t in enumerate(TONES):
            L.append(("class:sel" if i == s.tone else "", f"    [{i + 1}] {t}\n"))
        L += [SEP, ("class:hint", f"   {_progress(7, total)}    Auswahl: _    [0] Zurueck\n")]
    elif step == 7:
        for i, (label, _, _) in enumerate(LENGTHS):
            L.append(("class:sel" if i == s.length else "", f"    [{i + 1}] {label}\n"))
        L += [SEP, ("class:hint", f"   {_progress(8, total)}    Auswahl: _    [0] Zurueck\n")]
    elif step == 8:
        ln = LENGTHS[s.length][0].split("(")[0].strip() if s.length < len(LENGTHS) else "?"
        lang = LANGUAGES[s.language] if s.language < len(LANGUAGES) else "Deutsch"
        L += [
            ("", f"   Titel:       {s.display_title}\n"),
            ("", f"   Genre:       {s.genre_name}\n"),
            ("", f"   Sprache:     {lang}\n"),
            ("", f"   Zielgruppe:  {AUDIENCES[s.audience] if s.audience < len(AUDIENCES) else '?'}\n"),
            ("", f"   Perspektive: {PERSPECTIVES[s.perspective] if s.perspective < len(PERSPECTIVES) else '?'}\n"),
            ("", f"   Stimmung:    {TONES[s.tone] if s.tone < len(TONES) else '?'}\n"),
            ("", f"   Laenge:      {ln}\n\n"),
            SEP,
            ("class:hint", f"   {_progress(9, total)}    [1] Generieren    [0] Zurueck\n"),
        ]
    return L


def _genre_list(selected: int) -> list:
    L = []
    for i, g in enumerate(GENRE_NAMES):
        L.append(("class:sel" if i == selected else "", f"    [{i + 1}] {g:<20}"))
        if (i + 1) % 2 == 0:
            L.append(("", "\n"))
    if len(GENRE_NAMES) % 2 == 1:
        L.append(("", "\n"))
    return L


# ─────────────────────────────────────────────────────────────
# Library
# ─────────────────────────────────────────────────────────────

def render_library(s: AppState) -> list:
    L = [
        ("class:title", "\n\U0001f4d6 Meine Buecher\n"),
        ("", f"\n   {len(s.books)} Buecher gespeichert\n\n"),
        SEP,
    ]
    if not s.books:
        L.append(("class:dim", "   Noch keine Buecher erstellt.\n"))
    for i, b in enumerate(s.books):
        title = b.get("title", "?")
        L.append(("class:sel" if i == s.book_sel else "", f"    [{i + 1}] {title[:38]}\n"))
        L.append(("class:dim",
                  f"         {b.get('genre', '?')} \u00b7 "
                  f"{b.get('chapters_done', 0)}/{b.get('chapters_total', 0)} Kap. \u00b7 "
                  f"{b.get('created', '')}\n\n"))
    L += [SEP, ("class:hint", "   [Enter]=Lesen    Auswahl: _    [0] Zurueck\n")]
    if s.msg:
        L.append(("class:ok", f"  {s.msg}"))
    return L


def render_reading(s: AppState) -> list:
    if not s.chapters:
        return [("class:dim", "\n  Keine Kapitel\n")]
    ch = s.chapters[s.ch_idx]
    lines = ch.get("text", "").split("\n")
    L = [
        ("class:title", f"\n\U0001f4d6 {ch.get('title', '?')}\n"),
        ("class:dim", f"   Kapitel {s.ch_idx + 1} von {len(s.chapters)}  \u00b7  {len(ch.get('text', '').split())} Woerter\n\n"),
        SEP,
    ]
    for line in lines:
        L.append(("", f"  {line[:80]}\n"))
    L += [SEP, ("class:hint", f"  [\u2190] Zurueck  [\u2192] Weiter  [0] Menue\n")]
    return L


# ─────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────




def render_settings(s: AppState) -> list:
    p = s.get_cur_provider()
    pn = p["name"] if p else s.settings_cur_provider
    hk = s.has_api_key()
    ks = "\u2705 gesetzt" if hk else "\u274c nicht gesetzt"
    ef = EXPORT_FORMATS[s.settings_export_fmt] if s.settings_export_fmt < len(EXPORT_FORMATS) else "?"
    L = [
        ("class:title", "\n  \u2699\ufe0f  Einstellungen\n\n"),
        ("", f"   Provider:  {pn}\n"),
        ("", f"   Modell:    {s.settings_cur_model}\n"),
        ("", f"   API-Key:   {ks}\n"),
        ("", f"   Export:    {ef}\n\n"),
        SEP,
        ("", "    [1] Provider wechseln\n"),
        ("", "    [2] Modell wechseln\n"),
        ("", "    [3] API-Key eingeben\n"),
        ("", "    [4] Export-Format\n\n"),
        SEP,
        ("class:hint", "   Auswahl: _    [0] Zurueck\n"),
    ]
    if s.msg:
        L.append(("class:ok", f"  {s.msg}"))
    return L


def render_settings_provider(s: AppState) -> list:
    L = [("class:title", "\n\U0001f916 Provider auswaehlen (1 Taste = fertig)\n\n")]
    for i, p in enumerate(s.settings_providers):
        mk = " (" + (p.get("models", ["?"]) or ["?"])[0] + ")" if p.get("models") else ""
        L.append(("class:sel" if i == s.settings_prov_idx else "",
                   f"    [{i + 1}] {p['name'][:30]}{mk[:28]}\n"))
        L.append(("class:dim", f"         {p.get('cost', '')[:48]}\n"))
    extra = len(s.settings_providers) - 9
    L += [SEP]
    if extra > 0:
        L.append(("class:dim", f"   +{extra} weitere (nur 1-9 waehlbar)\n"))
    L.append(("class:hint", "   Taste [1]-[9]=Auswaehlen  [0]=Zurueck\n"))
    return L


def render_settings_model(s: AppState) -> list:
    from brokus.ai.client import PROVIDER_REGISTRY

    _CUSTOM_MODEL_PROVIDERS = {"ollama_local", "lmstudio", "localai"}
    pc = PROVIDER_REGISTRY.get(s.settings_cur_provider)

    if pc:
        models = list(pc.models)
        has_custom = pc.key in _CUSTOM_MODEL_PROVIDERS
        if has_custom:
            models.append("\u270f\ufe0f  Benutzerdefiniert...")
    else:
        models = []
        has_custom = False

    L = [
        ("class:title", "\n\U0001f9e0 Modell wechseln (1 Taste = fertig)\n\n"),
        ("", f"   Provider: {s.settings_cur_provider}\n\n"),
    ]

    for i, m in enumerate(models):
        is_custom = m.startswith("\u270f")
        # Highlight: either exact match or custom-option when current model isn't predefined
        if is_custom:
            is_sel = has_custom and s.settings_cur_model not in pc.models
        else:
            is_sel = m == s.settings_cur_model
        L.append(("class:sel" if is_sel else "", f"    [{i + 1}] {m[:52]}\n"))

    count = len(models) - (1 if has_custom else 0)
    L += [SEP, ("class:hint", f"   [{count} Modelle + Benutzerdefiniert]  [1]-[9]=Auswaehlen  [0]=Zurueck\n")]
    return L


def render_settings_apikey(s: AppState) -> list:
    p = s.get_cur_provider()
    L = [
        ("class:title", "\n\U0001f511 API-Key eingeben\n\n"),
        ("", f"   Provider: {p['name'] if p else '?'}\n"),
        ("", f"   Variable: {p.get('env', '?') if p else '?'}\n\n"),
    ]
    L += _hint_apikey()
    return L


def render_settings_custom_model(s: AppState) -> list:
    L = [
        ("class:title", "\n\U0001f9e0 Benutzerdefiniertes Modell\n\n"),
        ("", f"   Provider: {s.settings_cur_provider}\n\n"),
        ("", "   Modellnamen eingeben (z.B. llama3.2:3b, qwen2.5:7b, ...)\n"),
    ]
    L += _hint_apikey()
    return L


def render_settings_format(s: AppState) -> list:
    L = [("class:title", "\n\U0001f4c4 Export-Format (1 Taste = fertig)\n\n"),
         ("", "   Format nach der Generierung:\n\n")]
    for i, f in enumerate(EXPORT_FORMATS):
        L.append(("class:sel" if i == s.settings_export_fmt else "", f"    [{i + 1}] {f}\n"))
    L += [SEP, ("class:hint", "   Taste [1]-[9]=Auswaehlen  [0]=Zurueck\n")]
    return L


# ─────────────────────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────────────────────

def render_generating(s: AppState) -> list:
    bw = 40
    filled = int(s.gen_prog * bw)
    L = [
        ("class:title", f"\n\U0001f4d6 Generiere: {s.gen_title}\n\n"),
        ("", f"  {s.gen_stage}\n"),
        ("", f"  [{'#' * filled}{' ' * (bw - filled)}] {int(s.gen_prog * 100)}%\n"),
    ]
    if s.gen_comp:
        L.append(("", f"\n  Compliance: {s.gen_comp}/100\n"))
    if s.msg:
        L.append(("class:ok", f"\n  {s.msg}"))
    L.append(("class:hint", "\n  Bitte warten...  [0] Abbrechen\n"))
    return L


# ─────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────

def render(s: AppState) -> list:
    """Route to the correct screen renderer based on state.scr."""
    scr = s.scr

    if scr == "menu":
        return render_menu(s)
    if scr == "schnell_0":
        return render_schnell_0(s)
    if scr == "schnell_1":
        return render_schnell_1(s)
    if scr == "schnell_2":
        return render_schnell_2(s)
    if scr.startswith("meister_"):
        try:
            step = int(scr.split("_")[1])
            return render_meister(s, step)
        except (ValueError, IndexError):
            pass
    if scr == "library":
        return render_library(s)
    if scr == "reading":
        return render_reading(s)
    if scr == "settings":
        return render_settings(s)
    if scr == "settings_p":
        return render_settings_provider(s)
    if scr == "settings_m":
        return render_settings_model(s)
    if scr == "settings_k":
        return render_settings_apikey(s)
    if scr == "settings_custom_model":
        return render_settings_custom_model(s)
    if scr == "settings_f":
        return render_settings_format(s)
    if scr == "generating":
        return render_generating(s)

    return [("", f"? (unbekannter Screen: {scr})")]

