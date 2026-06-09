"""New book wizard – Zwei-Modus-System: ⚡ Schnell & 🎛️ Detailliert.

Schnell:    Idee → Titel&Genre → Bestätigung (3 Schritte)
Detailliert: Idee → Titel → Genre → Zielgruppe → Perspektive → Umfang → Bestätigung (7 Schritte)
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Static, Input, TextArea, Button, Header, Footer, ListView, ListItem, Label,
)
from textual.binding import Binding
from textual import events


class NewBookScreen(Screen):
    """Two-mode wizard for creating a new book."""

    BINDINGS = [
        Binding("escape", "go_back", "Zurück"),
        Binding("enter", "next_step", "Weiter"),
        Binding("up", "move_up", "Auf"),
        Binding("down", "move_down", "Ab"),
        Binding("tab", "toggle_focus", "Fokus"),
        Binding("1", "mode_schnell", "Schnell"),
        Binding("2", "mode_detailliert", "Detailliert"),
    ]

    TOP_GENRES = [
        ("Drama", "drama"), ("Thriller", "thriller"), ("Fantasy", "fantasy"),
        ("Science-Fiction", "scifi"), ("Horror", "horror"), ("Abenteuer", "adventure"),
        ("Coming-of-Age", "young_adult"), ("Philosophisch", "literary_fiction"),
        ("Dystopie", "dystopian"), ("Romance", "romance"),
    ]
    MORE_GENRES = [
        ("Mystery / Krimi", "mystery"), ("Historischer Roman", "historical_fiction"),
        ("Paranormal", "paranormal"), ("Post-Apokalypse", "post_apocalyptic"),
        ("Cyberpunk", "cyberpunk"), ("Urban Fantasy", "urban_fantasy"),
        ("Magischer Realismus", "magical_realism"), ("Noir / Hardboiled", "noir"),
        ("Märchen / Fairy Tale", "fairy_tale"), ("Satire", "satire"),
        ("Steampunk", "steampunk"), ("Gothic", "gothic"), ("Western", "western"),
        ("Military", "military"), ("Slice of Life", "slice_of_life"),
        ("Superhelden", "superhero"), ("Survival", "survival"),
        ("Biographie", "biography"), ("Experimentell", "experimental"),
    ]
    TARGET_AUDIENCES = [
        ("Kinder (6–12)", "children"), ("Jugendliche (13–17)", "young_adult_audience"),
        ("Erwachsene (18+)", "adult"), ("Alle Altersgruppen", "all"),
    ]
    PERSPECTIVES = [
        ("Ich-Erzähler", "Ich stand am Strand...", "first_person"),
        ("Dritte Person nah", "Lena stand am Strand...", "third_person_close"),
        ("Allwissend", "Alle Figuren sichtbar", "omniscient"),
    ]
    TENSES = [
        ("Präteritum", "präteritum"), ("Präsens", "präsens"), ("KI entscheidet", "auto"),
    ]

    def __init__(self):
        super().__init__()
        self._mode = "select"
        self._step = 0
        self._scope_focus = 0  # 0=chapters, 1=words

        self._title = ""
        self._genre = "drama"
        self._idea = ""
        self._num_chapters = 20
        self._words_per_chapter = 1800
        self._provider = "anthropic"
        self._model = "claude-sonnet-4-5"
        self._audience = "adult"
        self._perspective = "third_person_close"
        self._tense = "präteritum"
        self._show_more_genres = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(id="wizard-main")
        with Container(id="wizard-nav"):
            yield Static(
                "Ziffern: Auswahl  |  ENTER: Weiter  |  ESC: Zurück  |  TAB: Fokus",
                id="nav-bar",
            )
        yield Footer()

    def on_mount(self):
        self._show_step()

    def _show_step(self):
        container = self.query_one("#wizard-main")
        container.remove_children()
        if self._mode == "select":
            container.mount(self._step_mode_select())
        elif self._mode == "schnell":
            steps = [self._step_idea, self._step_title_genre, self._step_confirm_schnell]
            if 0 <= self._step < len(steps):
                container.mount(steps[self._step]())
        elif self._mode == "detailliert":
            steps = [
                self._step_idea, self._step_title, self._step_genre,
                self._step_audience, self._step_perspective, self._step_scope,
                self._step_confirm_detailed,
            ]
            if 0 <= self._step < len(steps):
                container.mount(steps[self._step]())

    # ── Mode Selection ───────────────────────────────────────

    def _step_mode_select(self) -> Container:
        return Container(
            Static("📖 Neues Buch", classes="wizard-header"),
            Static("Wie möchtest du starten?", classes="wizard-subtitle"),
            Static("", classes="spacer"),
            Button("⚡ Schnell – Idee + Titel + Genre", id="btn-mode-schnell", variant="primary"),
            Static("", classes="spacer"),
            Button("🎛️  Detailliert – Alle Optionen", id="btn-mode-detailliert"),
            Static("", classes="spacer"),
            Static("Taste [1] oder [2] zum Auswählen", classes="form-hint"),
            id="step-container",
        )

    # ── Idea step (shared) ───────────────────────────────────

    def _step_idea(self) -> Container:
        total = 3 if self._mode == "schnell" else 7
        icon = "⚡" if self._mode == "schnell" else "🎛️"
        return Container(
            Static(f"{icon} {self._mode.title()} · Schritt {self._step + 1}/{total}: Deine Idee", classes="wizard-header"),
            Static("Beschreibe dein Buch so detailliert wie möglich:", classes="form-label"),
            TextArea(id="textarea-idea"),
            id="step-container",
        )

    # ── Schnell: Step 2 – Title & Genre ──────────────────────

    def _step_title_genre(self) -> Container:
        items = [ListItem(Label(f"  [{i + 1}] {name}")) for i, (name, _) in enumerate(self.TOP_GENRES)]
        items.append(ListItem(Label("  [0] Mehr...")))
        return Container(
            Static("⚡ Schnell · Schritt 2/3: Titel & Genre", classes="wizard-header"),
            Static("Titel:", classes="form-label"),
            Input(placeholder="z.B. Die Insel-Utopie", id="input-title"),
            Static("", classes="spacer"),
            Static("Genre (Zahl wählen):", classes="form-label"),
            ListView(*items, id="list-genre"),
            Static("", classes="spacer"),
            Container(Static("TAB: Titel↔Genre  |  ENTER: Weiter  |  ESC: Zurück", classes="form-hint"), id="hint-bar"),
            id="step-container",
        )

    # ── Detailliert: Step 2 – Title ──────────────────────────

    def _step_title(self) -> Container:
        return Container(
            Static("🎛️  Detailliert · Schritt 2/7: Titel", classes="wizard-header"),
            Static("Buchtitel:", classes="form-label"),
            Input(placeholder="z.B. Die Insel-Utopie", id="input-title"),
            Static("", classes="spacer"),
            Container(Static("K  KI schlägt 3 Titel vor", classes="form-hint"), id="hint-bar"),
            id="step-container",
        )

    # ── Detailliert: Step 3 – Genre ──────────────────────────

    def _step_genre(self) -> Container:
        genres = self.TOP_GENRES + self.MORE_GENRES if self._show_more_genres else self.TOP_GENRES
        items = [ListItem(Label(f"  [{i + 1}] {'>' if g[1] == self._genre else ' '} {g[0]}")) for i, g in enumerate(genres)]
        if not self._show_more_genres:
            items.append(ListItem(Label("  [0] Mehr...")))
        return Container(
            Static("🎛️  Detailliert · Schritt 3/7: Genre (Zahl wählen)", classes="wizard-header"),
            ListView(*items, id="list-genre"),
            id="step-container",
        )

    # ── Detailliert: Step 4 – Zielgruppe ─────────────────────

    def _step_audience(self) -> Container:
        items = [
            ListItem(Label(f"  [{i + 1}] {'>' if key == self._audience else ' '} {name}"))
            for i, (name, key) in enumerate(self.TARGET_AUDIENCES)
        ]
        return Container(
            Static("🎛️  Detailliert · Schritt 4/7: Zielgruppe (Zahl wählen)", classes="wizard-header"),
            ListView(*items, id="list-audience"),
            id="step-container",
        )

    # ── Detailliert: Step 5 – Perspektive ────────────────────

    def _step_perspective(self) -> Container:
        p_items = [
            ListItem(Label(f"  [{i + 1}] {'>' if key == self._perspective else ' '} {name:<22} \"{example}\""))
            for i, (name, example, key) in enumerate(self.PERSPECTIVES)
        ]
        t_items = [
            ListItem(Label(f"  [{i + 1}] {'>' if key == self._tense else ' '} {name}"))
            for i, (name, key) in enumerate(self.TENSES)
        ]
        return Container(
            Static("🎛️  Detailliert · Schritt 5/7: Perspektive", classes="wizard-header"),
            Static("Erzählperspektive (Zahl wählen):", classes="form-label"),
            ListView(*p_items, id="list-perspective"),
            Static("", classes="spacer"),
            Static("Zeitform (Zahl wählen):", classes="form-label"),
            ListView(*t_items, id="list-tense"),
            Static("", classes="spacer"),
            Container(Static("TAB: Persp.↔Zeitform  |  Ziffer: Auswahl  |  ENTER: Weiter", classes="form-hint"), id="hint-bar"),
            id="step-container",
        )

    # ── Detailliert: Step 6 – Umfang ─────────────────────────

    def _step_scope(self) -> Container:
        total_words = self._num_chapters * self._words_per_chapter
        pages = total_words // 250
        return Container(
            Static("🎛️  Detailliert · Schritt 6/7: Umfang", classes="wizard-header"),
            Static("", classes="spacer"),
            Static(f"Kapitel:       ◀  {self._num_chapters:2d}  ▶   (← →)", classes="scope-line"),
            Static("", classes="spacer"),
            Static(f"Wörter/Kap.:   ◀  {self._words_per_chapter:4d}  ▶   (← →)", classes="scope-line"),
            Static("", classes="spacer"),
            Static(f"Gesamt: ~{total_words:,} Wörter  (~{pages} Seiten)", classes="scope-total"),
            Static("", classes="spacer"),
            Container(Static("TAB wechselt  |  ← → ändert Wert  |  ENTER Weiter", classes="form-hint"), id="hint-bar"),
            id="step-container",
        )

    # ── Confirmations ─────────────────────────────────────────

    def _step_confirm_schnell(self) -> Container:
        genre_name = dict(self.TOP_GENRES + self.MORE_GENRES).get(self._genre, self._genre)
        return Container(
            Static("✅ Schnell · Schritt 3/3: Bereit!", classes="wizard-header"),
            Static("", classes="spacer"),
            Static(f"Titel    {self._title or '(keiner)'}", classes="confirm-line"),
            Static(f"Genre    {genre_name}", classes="confirm-line"),
            Static(f"Idee     {self._idea[:60]}{'...' if len(self._idea) > 60 else ''}", classes="confirm-line"),
            Static("", classes="spacer"),
            Static("KI wählt automatisch:", classes="form-label"),
            Static("Stil, Perspektive, Kapitelanzahl, Sprache", classes="confirm-line"),
            Static("", classes="spacer"),
            Static("M  Mehr Optionen    ENTER Generieren", classes="form-hint"),
            id="step-container",
        )

    def _step_confirm_detailed(self) -> Container:
        genre_name = dict(self.TOP_GENRES + self.MORE_GENRES).get(self._genre, self._genre)
        audience_name = dict(self.TARGET_AUDIENCES).get(self._audience, self._audience)
        persp_name = dict((k, n) for n, _, k in self.PERSPECTIVES).get(self._perspective, self._perspective)
        tense_name = dict(self.TENSES).get(self._tense, self._tense)
        total_words = self._num_chapters * self._words_per_chapter
        pages = total_words // 250
        return Container(
            Static("✅ Detailliert · Schritt 7/7: Übersicht", classes="wizard-header"),
            Static("", classes="spacer"),
            Static(f"Titel        {self._title or '(keiner)'}", classes="confirm-line"),
            Static(f"Genre        {genre_name}", classes="confirm-line"),
            Static(f"Zielgruppe   {audience_name}", classes="confirm-line"),
            Static(f"Perspektive  {persp_name} / {tense_name}", classes="confirm-line"),
            Static(f"Kapitel      {self._num_chapters}  │  Wörter/Kap  {self._words_per_chapter}", classes="confirm-line"),
            Static(f"Gesamt       ~{total_words:,} Wörter  (~{pages} Seiten)", classes="confirm-line"),
            Static("", classes="spacer"),
            Container(Static("ENTER Generieren    ESC Zurück", classes="form-hint"), id="hint-bar"),
            id="step-container",
        )

    # ── Event Handlers ────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed):
        """Handle mode selection and other button clicks."""
        if event.button.id == "btn-mode-schnell":
            self._mode = "schnell"
            self._step = 0
            self._show_step()
        elif event.button.id == "btn-mode-detailliert":
            self._mode = "detailliert"
            self._step = 0
            self._show_step()

    def on_key(self, event: events.Key):
        """Handle key events for special actions."""
        # Number keys for list selection (0-9)
        if event.key in tuple(str(i) for i in range(10)):
            self._handle_digit_select(int(event.key))
            return

        # Detailliert step 6 (index 5): Umfang steppers
        if self._mode == "detailliert" and self._step == 5:
            if event.key == "left":
                if self._scope_focus == 0:
                    self._num_chapters = max(5, self._num_chapters - 1)
                else:
                    self._words_per_chapter = max(500, self._words_per_chapter - 100)
                self._show_step()
                return
            elif event.key == "right":
                if self._scope_focus == 0:
                    self._num_chapters = min(50, self._num_chapters + 1)
                else:
                    self._words_per_chapter = min(5000, self._words_per_chapter + 100)
                self._show_step()
                return
            elif event.key == "tab":
                self._scope_focus = 1 if self._scope_focus == 0 else 0
                self._show_step()
                return

        # KI-Titelvorschläge
        if event.key == "k" and self._mode == "detailliert" and self._step == 1:
            self._suggest_titles()
            return

        # Schnell confirm: M for more options
        if event.key == "m" and self._mode == "schnell" and self._step == 2:
            self._mode = "detailliert"
            self._step = 0
            self._show_step()
            return

    def _handle_digit_select(self, digit: int):
        """Select list item by number key (0-9). 1-9 → items 0-8, 0 → last item (Mehr...)."""
        idx = digit - 1 if digit > 0 else 9

        # Genre selection (Schnell: step 1, Detailliert: step 2)
        if (self._mode == "schnell" and self._step == 1) or \
           (self._mode == "detailliert" and self._step == 2):
            if self._mode == "detailliert" and self._show_more_genres:
                all_genres = self.TOP_GENRES + self.MORE_GENRES
            else:
                all_genres = self.TOP_GENRES
            if idx < len(all_genres):
                self._genre = all_genres[idx][1]
                self._show_step()
            elif not self._show_more_genres and idx >= len(self.TOP_GENRES):
                self._show_more_genres = True
                self._show_step()

        # Audience selection (Detailliert: step 3)
        elif self._mode == "detailliert" and self._step == 3:
            if idx < len(self.TARGET_AUDIENCES):
                self._audience = self.TARGET_AUDIENCES[idx][1]
                self._show_step()

        # Perspective + Tense selection (Detailliert: step 4)
        elif self._mode == "detailliert" and self._step == 4:
            # Check which ListView is focused (perspective or tense)
            focused = self.screen.focused
            if focused and getattr(focused, "id", "") == "list-tense":
                if idx < len(self.TENSES):
                    self._tense = self.TENSES[idx][1]
                    self._show_step()
            else:
                if idx < len(self.PERSPECTIVES):
                    self._perspective = self.PERSPECTIVES[idx][2]
                    self._show_step()

    def on_list_view_selected(self, event: ListView.Selected):
        """Handle selections in list views."""
        # In Textual, the widget that posted the message is event.control
        list_id = event.control.id if hasattr(event.control, 'id') else ""
        idx = event.item_index

        if list_id == "list-genre":
            if self._mode == "schnell" and self._step == 1:
                if idx is not None and idx < len(self.TOP_GENRES):
                    self._genre = self.TOP_GENRES[idx][1]
                    self._show_step()
                elif not self._show_more_genres and idx == len(self.TOP_GENRES):
                    self._show_more_genres = True
                    self._show_step()
            elif self._mode == "detailliert" and self._step == 2:
                all_genres = (self.TOP_GENRES + self.MORE_GENRES) if self._show_more_genres else self.TOP_GENRES
                if idx is not None and idx < len(all_genres):
                    self._genre = all_genres[idx][1]
                    self._show_step()
                elif not self._show_more_genres and idx == len(self.TOP_GENRES):
                    self._show_more_genres = True
                    self._show_step()
        elif list_id == "list-audience":
            if idx is not None and idx < len(self.TARGET_AUDIENCES):
                self._audience = self.TARGET_AUDIENCES[idx][1]
                self._show_step()
        elif list_id == "list-perspective":
            if idx is not None and idx < len(self.PERSPECTIVES):
                self._perspective = self.PERSPECTIVES[idx][2]
                self._show_step()
        elif list_id == "list-tense":
            if idx is not None and idx < len(self.TENSES):
                self._tense = self.TENSES[idx][1]
                self._show_step()

    # ── KI Title Suggestions ──────────────────────────────────

    def _suggest_titles(self):
        if not self._idea.strip():
            self.notify("Bitte erst die Idee eingeben.", severity="warning")
            return
        self.notify("Titelvorschläge werden generiert...", title="KI")
        import asyncio
        asyncio.create_task(self._generate_titles())

    async def _generate_titles(self):
        try:
            from brokus.ai.client import BrokusAIClient
            client = BrokusAIClient(provider="anthropic", model="claude-sonnet-4-5")
            response = await client.generate(
                "Du bist ein kreativer Lektor. Schlage 3 Buchtitel vor.",
                f"Buchidee: {self._idea}\n\nSchlage 3 Titel vor. Nur die Titel, je eine Zeile.",
                temperature=0.9, max_tokens=200,
            )
            titles = [t.strip().lstrip("0123456789. -") for t in response.text.split("\n") if t.strip()]
            if titles:
                self._title = titles[0]
                self.notify(f"Titel gesetzt: {self._title}", title="KI")
                self._show_step()
        except Exception as e:
            self.notify(f"Fehler: {e}", severity="error")

    # ── Actions ───────────────────────────────────────────────

    def action_next_step(self):
        """ENTER = Weiter."""
        self._collect_step_data()
        if self._mode == "select":
            return  # Use buttons or 1/2 keys
        elif self._mode == "schnell":
            if self._step < 2:
                self._step += 1; self._show_step()
            elif self._step == 2:
                self._start_generation()
        elif self._mode == "detailliert":
            if self._step < 6:
                self._step += 1; self._show_step()
            elif self._step == 6:
                self._start_generation()

    def action_mode_schnell(self):
        """Key [1]: Schnell mode."""
        if self._mode == "select":
            self._mode = "schnell"; self._step = 0; self._show_step()

    def action_mode_detailliert(self):
        """Key [2]: Detailliert mode."""
        if self._mode == "select":
            self._mode = "detailliert"; self._step = 0; self._show_step()

    def action_go_back(self):
        """ESC = Zurück."""
        if self._mode == "select":
            self.app.navigate_to("library")
        elif self._step > 0:
            self._collect_step_data(); self._step -= 1; self._show_step()
        else:
            self._mode = "select"; self._step = 0; self._show_step()

    def action_toggle_focus(self):
        """TAB = Focus between Input and ListView widgets."""
        try:
            container = self.query_one("#wizard-main")
            # Find only focusable input widgets (Input, TextArea, ListView)
            focusable = []
            for w in container.query("*"):
                if isinstance(w, (Input, TextArea, ListView)):
                    focusable.append(w)
            if not focusable:
                return
            # Find currently focused and move to next
            focused = self.screen.focused
            if focused in focusable:
                idx = focusable.index(focused)
                next_idx = (idx + 1) % len(focusable)
                focusable[next_idx].focus()
            elif focusable:
                focusable[0].focus()
        except Exception:
            pass

    # ── Data Collection ───────────────────────────────────────

    def _collect_step_data(self):
        """Collect data from current step's inputs."""
        try:
            if self._step == 0:
                try:
                    ta = self.query_one("#textarea-idea", TextArea)
                    self._idea = ta.text
                except Exception:
                    pass
            if (self._mode == "schnell" and self._step == 1) or \
               (self._mode == "detailliert" and self._step == 1):
                try:
                    self._title = self.query_one("#input-title", Input).value.strip()
                except Exception:
                    pass
        except Exception:
            pass

    # ── Generation ────────────────────────────────────────────

    def _start_generation(self):
        if not self._title:
            self.notify("Bitte gib einen Titel ein.", severity="warning"); return
        if not self._idea.strip():
            self.notify("Bitte beschreibe deine Buchidee.", severity="warning"); return
        if self._mode == "schnell":
            idea_lower = self._idea.lower()
            if any(w in idea_lower for w in ["jugend", "teenager", "jung", "coming"]):
                self._audience = "young_adult_audience"
            self._perspective = "third_person_close"
            self._tense = "präteritum"
            self._num_chapters = 20
            self._words_per_chapter = 1800
        self.app.generation_params = {
            "title": self._title, "genre": self._genre, "idea": self._idea,
            "num_chapters": self._num_chapters, "provider": self._provider,
            "model": self._model, "audience": self._audience,
            "perspective": self._perspective, "tense": self._tense,
            "words_per_chapter": self._words_per_chapter,
        }
        self.app.navigate_to("generation")
