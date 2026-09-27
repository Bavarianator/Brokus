#!/usr/bin/env python3
"""
BrokuS – Modern Desktop GUI (CustomTkinter)
Dark, premium design mit Glassmorphism-Elementen.
"""
import threading, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from PIL import Image, ImageTk
from customtkinter import CTkFrame, CTkLabel, CTkButton, CTkEntry, CTkComboBox, CTkProgressBar, CTkTextbox, CTkSwitch

# ── Design System ───────────────────────────────────────────
BG = "#0a0e17"
CARD = "#12162b"
CARD_BORDER = "#1e2538"
ACCENT_CYAN = "#00e6ff"
ACCENT_MAGENTA = "#ff00aa"
TEXT = "#e8ecf3"
TEXT_DIM = "#8a92a8"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ── Data ────────────────────────────────────────────────────
GENRES = [
    "Fantasy", "Science Fiction", "Drama", "Thriller", "Romance",
    "Horror", "Mystery / Krimi", "Historischer Roman", "Abenteuer",
    "Dystopie", "Young Adult", "Literarische Fiktion", "Paranormal",
    "Erotica", "Comedy / Humor", "Action", "Post-Apokalypse",
    "Steampunk", "Cyberpunk", "Urban Fantasy", "Magischer Realismus",
    "Military / Kriegsroman", "Western", "Noir / Hardboiled",
    "Märchen / Fairy Tale", "Slice of Life", "Superhelden",
    "Survival", "Biographie / Memoir", "Kinderbuch", "Satire", "Experimentell"
]
LENGTHS = [
    ("Minigeschichte (~5 Seiten)", 1500, 1),
    ("Kurzgeschichte (~17 Seiten)", 5000, 3),
    ("Novelle (~67 Seiten)", 20000, 8),
    ("Kurzroman (~117 Seiten)", 35000, 10),
    ("Roman (~167 Seiten)", 50000, 12),
    ("Epischer Roman (~250 Seiten)", 75000, 16),
    ("Epos (~333 Seiten)", 100000, 20),
    ("Megaroman (~500 Seiten)", 150000, 30),
]
LANGS = ["Deutsch", "Englisch", "Französisch", "Spanisch", "Italienisch", "Niederländisch"]


class ModernCard(CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=CARD, border_color=CARD_BORDER,
                         border_width=1, corner_radius=24, **kwargs)


class BrokusGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("BrokuS — KI-Buchgenerator")
        self.geometry("1280x820")
        self.configure(fg_color=BG)
        self.minsize(1100, 700)

        # Icon
        try:
            self.iconbitmap("gui/logo.png")
        except Exception:
            pass

        # Splash
        splash = ctk.CTkToplevel(self)
        splash.overrideredirect(True)
        splash.geometry("500x320+%d+%d" % (self.winfo_screenwidth()//2 - 250,
                                            self.winfo_screenheight()//2 - 160))
        splash.configure(fg_color=BG)
        splash.lift()
        splash.attributes("-topmost", True)

        # Logo in splash
        try:
            img = ctk.CTkImage(light_image=Image.open("gui/logo.png"), dark_image=Image.open("gui/logo.png"), size=(100, 100))
            splash_logo = ctk.CTkLabel(splash, image=img, text="", fg_color="transparent")
            splash_logo.pack(pady=(40, 10))
        except Exception:
            pass

        title_splash = ctk.CTkLabel(splash, text="BrokuS", font=("Segoe UI", 32, "bold"),
                                     text_color=ACCENT_CYAN, fg_color="transparent")
        title_splash.pack()
        sub_splash = ctk.CTkLabel(splash, text="KI-Buchgenerator  ·  Modern Desktop GUI",
                                  font=("Segoe UI", 12), text_color=TEXT_DIM,
                                  fg_color="transparent")
        sub_splash.pack(pady=(6, 30))

        # Gradient line under splash title
        line = ctk.CTkFrame(splash, width=200, height=4, fg_color=ACCENT_CYAN, corner_radius=2)
        line.pack()

        # Auto-close splash after 1.5s
        self.after(1500, lambda: (splash.destroy(), self.deiconify()))
        self.withdraw()  # hide main until splash done

        # ── Header ──────────────────────────────────────────────
        header = ModernCard(self, width=1240, height=110)
        header.pack(pady=(20, 10), padx=20, fill="x")
        header.grid_rowconfigure(0, weight=1)

        title = CTkLabel(header, text="BrokuS", font=("Segoe UI", 36, "bold"),
                         text_color=TEXT, fg_color="transparent")
        title.place(x=40, y=25)
        subtitle = CTkLabel(header, text="KI-Buchgenerator · Drei-Schichten-System · DNA-Extraktion",
                            font=("Segoe UI", 13), text_color=TEXT_DIM,
                            fg_color="transparent")
        subtitle.place(x=40, y=70)

        # Gradient accent line
        accent = CTkFrame(header, width=220, height=6, fg_color=CARD_BORDER,
                          corner_radius=3)
        accent.place(x=40, y=95)
        accent_fill = CTkFrame(header, width=120, height=6, fg_color=ACCENT_CYAN,
                               corner_radius=3)
        accent_fill.place(x=40, y=95)

        # Status pill
        self.status_pill = CTkLabel(header, text="● Bereit",
                                    font=("Segoe UI", 11, "bold"),
                                    text_color=ACCENT_CYAN,
                                    fg_color=CARD_BORDER,
                                    corner_radius=10, padx=14, pady=4)
        self.status_pill.place(x=1010, y=35)

        # ── Main 3-Column Layout ───────────────────────────────
        main = CTkFrame(self, fg_color=BG)
        main.pack(pady=10, padx=20, fill="both", expand=True)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)
        main.grid_columnconfigure(2, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # ── LEFT: Project / Quick Info ──────────────────────────
        left = ModernCard(main, width=350)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)

        CTkLabel(left, text="PROJEKT", font=("Segoe UI", 10, "bold"),
                 text_color=ACCENT_MAGENTA).pack(anchor="w", padx=24, pady=(24, 6))

        self.project_list = CTkTextbox(left, fg_color="#0f1320", border_color=CARD_BORDER,
                                       border_width=1, corner_radius=16, font=("Segoe UI", 11),
                                       text_color=TEXT, height=220)
        self.project_list.pack(padx=24, pady=6, fill="both", expand=True)
        self.project_list.insert("0.0", "• Noch kein Projekt\n• Starte eine Generierung, um hier Projekte zu sehen")
        self.project_list.configure(state="disabled")

        # Quick-check button
        self.quick_btn = CTkButton(left, text="🔍 Schnell-Check starten",
                                   font=("Segoe UI", 13, "bold"),
                                   fg_color=ACCENT_CYAN, hover_color="#00b3d8",
                                   text_color="#000000", corner_radius=12,
                                   height=42, command=self.run_quick_check)
        self.quick_btn.pack(padx=24, pady=(10, 8), fill="x")

        # Provider info
        info = CTkLabel(left, text="33+ Provider · Multi-Language\nAuto-Fallback · DNA-Lock",
                         font=("Segoe UI", 10), text_color=TEXT_DIM,
                         fg_color="transparent", justify="left")
        info.pack(padx=24, pady=(6, 10), anchor="w")

        # ── CENTER: Input Form ──────────────────────────────────
        center = ModernCard(main, width=680)
        center.grid(row=0, column=1, sticky="nsew", padx=10)
        center.grid_rowconfigure(4, weight=1)

        CTkLabel(center, text="BUCH IDEE", font=("Segoe UI", 10, "bold"),
                 text_color=ACCENT_CYAN).pack(anchor="w", padx=28, pady=(28, 6))

        self.idea_text = CTkTextbox(center, height=100, fg_color="#0f1320",
                                    border_color=CARD_BORDER, border_width=1,
                                    corner_radius=16, font=("Segoe UI", 13),
                                    text_color=TEXT)
        self.idea_text.pack(padx=28, pady=6, fill="x")
        self.idea_text.insert("0.0", "Ein junger Magier findet einen alten Spiegel, der nicht sein eigenes Bild zeigt...")

        # Row of combos
        row = CTkFrame(center, fg_color="transparent")
        row.pack(padx=28, pady=10, fill="x")
        row.grid_columnconfigure((0, 1, 2), weight=1)

        CTkLabel(row, text="GENRE", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.genre_combo = CTkComboBox(row, values=GENRES, width=180,
                                       fg_color="#0f1320", border_color=CARD_BORDER,
                                       dropdown_fg_color=CARD, button_color=ACCENT_CYAN,
                                       button_hover_color="#00b3d8", text_color=TEXT,
                                       font=("Segoe UI", 11))
        self.genre_combo.set("Fantasy")
        self.genre_combo.grid(row=1, column=0, sticky="w", pady=(0, 8))

        CTkLabel(row, text="LÄNGE", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(row=0, column=1, sticky="w", pady=(0, 2))
        self.length_combo = CTkComboBox(row, values=[l[0] for l in LENGTHS], width=220,
                                        fg_color="#0f1320", border_color=CARD_BORDER,
                                        dropdown_fg_color=CARD, button_color=ACCENT_CYAN,
                                        button_hover_color="#00b3d8", text_color=TEXT,
                                        font=("Segoe UI", 11))
        self.length_combo.set("Kurzroman (~117 Seiten)")
        self.length_combo.grid(row=1, column=1, sticky="w", pady=(0, 8))

        CTkLabel(row, text="SPRACHE", font=("Segoe UI", 9, "bold"), text_color=TEXT_DIM).grid(row=0, column=2, sticky="w", pady=(0, 2))
        self.lang_combo = CTkComboBox(row, values=LANGS, width=160,
                                      fg_color="#0f1320", border_color=CARD_BORDER,
                                      dropdown_fg_color=CARD, button_color=ACCENT_CYAN,
                                      button_hover_color="#00b3d8", text_color=TEXT,
                                      font=("Segoe UI", 11))
        self.lang_combo.set("Deutsch")
        self.lang_combo.grid(row=1, column=2, sticky="w", pady=(0, 8))

        # Action row
        action_row = CTkFrame(center, fg_color="transparent")
        action_row.pack(padx=28, pady=(10, 20), fill="x")

        self.gen_btn = CTkButton(action_row, text="▶  BUCH GENERIEREN",
                                 font=("Segoe UI", 15, "bold"),
                                 fg_color=ACCENT_CYAN, hover_color="#00b3d8",
                                 text_color="#000000", corner_radius=16,
                                 height=56, command=self.start_generation)
        self.gen_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = CTkButton(action_row, text="⏹  ABBRECHEN",
                                    font=("Segoe UI", 13), fg_color=CARD_BORDER,
                                    hover_color=CARD, text_color=TEXT,
                                    corner_radius=16, height=56, command=self.cancel_generation)
        self.cancel_btn.pack(side="left", fill="x", expand=True)

        # ── RIGHT: Status / Progress / Settings ─────────────────
        right = ModernCard(main, width=350)
        right.grid(row=0, column=2, sticky="nsew", padx=(10, 0))

        CTkLabel(right, text="STATUS", font=("Segoe UI", 10, "bold"),
                 text_color=ACCENT_MAGENTA).pack(anchor="w", padx=24, pady=(24, 6))

        self.status_label = CTkLabel(right, text="Bereit für Generierung",
                                     font=("Segoe UI", 13, "bold"),
                                     text_color=TEXT, fg_color="transparent")
        self.status_label.pack(anchor="w", padx=24)

        self.progress = CTkProgressBar(right, height=14, corner_radius=10,
                                       progress_color=ACCENT_CYAN,
                                       fg_color="#0f1320", border_color=CARD_BORDER,
                                       border_width=1)
        self.progress.pack(padx=24, pady=(10, 4), fill="x")
        self.progress.set(0)

        self.detail_label = CTkLabel(right, text="Warte auf Eingabe...",
                                     font=("Segoe UI", 11), text_color=TEXT_DIM,
                                     fg_color="transparent")
        self.detail_label.pack(anchor="w", padx=24, pady=(0, 10))

        # Settings card inside right
        settings = ModernCard(right, width=300)
        settings.pack(padx=24, pady=(10, 24), fill="both", expand=True)

        CTkLabel(settings, text="EINSTELLUNGEN", font=("Segoe UI", 9, "bold"),
                 text_color=TEXT_DIM).pack(anchor="w", padx=20, pady=(16, 6))

        self.model_combo = CTkComboBox(settings, values=["gpt-4o", "claude-3-opus", "mistral-large",
                                                          "gemini-1.5-pro", "llama-3-70b"],
                                        width=260, fg_color="#0f1320",
                                        border_color=CARD_BORDER,
                                        dropdown_fg_color=CARD, button_color=ACCENT_CYAN,
                                        button_hover_color="#00b3d8", text_color=TEXT,
                                        font=("Segoe UI", 11))
        self.model_combo.set("gpt-4o")
        self.model_combo.pack(padx=20, pady=(0, 8), fill="x")

        self.fallback_switch = CTkSwitch(settings, text="Auto-Fallback aktiv",
                                         font=("Segoe UI", 11), text_color=TEXT,
                                         button_color=ACCENT_CYAN, button_hover_color="#00b3d8",
                                         progress_color=ACCENT_MAGENTA, fg_color="transparent")
        self.fallback_switch.select()
        self.fallback_switch.pack(anchor="w", padx=20, pady=(6, 6))

        self.theme_switch = CTkSwitch(settings, text="Light / Dark Modus",
                                      font=("Segoe UI", 11), text_color=TEXT,
                                      button_color=ACCENT_MAGENTA, button_hover_color="#ff55cc",
                                      progress_color=ACCENT_CYAN, fg_color="transparent",
                                      command=self.toggle_theme)
        self.theme_switch.pack(anchor="w", padx=20, pady=(8, 10))

        self.export_combo = CTkComboBox(settings, values=["Markdown (.md)", "EPUB (.epub)",
                                                          "PDF (.pdf)", "DOCX (.docx)", "JSON (.json)"],
                                        width=260, fg_color="#0f1320",
                                        border_color=CARD_BORDER,
                                        dropdown_fg_color=CARD, button_color=ACCENT_CYAN,
                                        button_hover_color="#00b3d8", text_color=TEXT,
                                        font=("Segoe UI", 11))
        self.export_combo.set("Markdown (.md)")
        self.export_combo.pack(padx=20, pady=(0, 10), fill="x")

        # Footer branding
        CTkLabel(self, text="BrokuS v1.2.0 · Arena-Branch · Modern Desktop GUI",
                 font=("Segoe UI", 9), text_color=TEXT_DIM).pack(side="bottom", pady=6)

        self._generation_thread = None
        self._cancelled = False

    # ── Actions ─────────────────────────────────────────────────
    def run_quick_check(self):
        self.status_pill.configure(text="● Check läuft...", text_color=ACCENT_MAGENTA)
        self.detail_label.configure(text="Prüfe Provider-Konfiguration...")
        def check():
            try:
                time.sleep(1.2)
                from brokus.ai.model_discovery import ModelDiscovery
                md = ModelDiscovery()
                count = len(md.discover()) if hasattr(md, 'discover') else 0
                self.after(0, lambda: self.update_status(f"● {count} Modelle gefunden", ACCENT_CYAN,
                                                         f"Schnell-Check abgeschlossen · {count} Provider"))
            except Exception as e:
                self.after(0, lambda: self.update_status("● Fehler", "#ff5555", str(e)))
        threading.Thread(target=check, daemon=True).start()

    def update_status(self, pill_text, pill_color, detail):
        self.status_pill.configure(text=pill_text, text_color=pill_color)
        self.status_label.configure(text=pill_text.replace("● ", ""))
        self.detail_label.configure(text=detail)

    def start_generation(self):
        idea = self.idea_text.get("1.0", "end-1c").strip()
        if not idea or len(idea) < 5:
            self.status_pill.configure(text="● Eingabe fehlt", text_color="#ff5555")
            self.detail_label.configure(text="Bitte mindestens 5 Zeichen eingeben.")
            return
        self._cancelled = False
        selected_len = self.length_combo.get()
        # Find chapter count
        chapters = 10
        words = 35000
        for label, w, c in LENGTHS:
            if label == selected_len:
                words, chapters = w, c; break

        self.gen_btn.configure(state="disabled", text="▶ Läuft...")
        self.cancel_btn.configure(state="normal")
        self.progress.set(0)
        self.update_status("● Generiert...", ACCENT_CYAN, "Starte DNA-Extraktion...")

        def work():
            # Simulate pipeline steps with realistic delay for demo
            stages = [
                ("DNA-Extraktion", 0.15),
                ("Kapitel 1–3", 0.35),
                ("Kapitel 4–8", 0.60),
                ("Komformitätsprüfung", 0.80),
                ("Export", 1.0),
            ]
            for stage, pct in stages:
                if self._cancelled:
                    break
                for i in range(10):
                    if self._cancelled:
                        break
                    time.sleep(0.25)
                    current = pct - (0.10 if i < 9 else 0) + (i/10)*(0.10)
                    self.after(0, lambda p=pct, s=stage: self.progress.set(p))
                    self.after(0, lambda s=stage: self.detail_label.configure(text=f"{s} ..."))
            if not self._cancelled:
                self.after(0, lambda: self.finish_generation())
            else:
                self.after(0, lambda: self.cancel_done())

        self._generation_thread = threading.Thread(target=work, daemon=True)
        self._generation_thread.start()


    def toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Light")
            self.configure(fg_color="#f0f2f8")
        else:
            ctk.set_appearance_mode("Dark")
            self.configure(fg_color=BG)

    def finish_generation(self):
        self.progress.set(1)
        self.gen_btn.configure(state="normal", text="▶ BUCH GENERIEREN")
        self.cancel_btn.configure(state="disabled")
        self.update_status("● Fertig", "#00ff88", "Buch erfolgreich generiert · Export bereit")
        # Add to project list
        idea_short = self.idea_text.get("1.0", "end-1c").strip()[:50]
        self.project_list.configure(state="normal")
        self.project_list.insert("end", f"\n• {idea_short}... (fertig)\n")
        self.project_list.configure(state="disabled")

    def cancel_generation(self):
        self._cancelled = True
        self.detail_label.configure(text="Abbruch angefordert...")

    def cancel_done(self):
        self.progress.set(0)
        self.gen_btn.configure(state="normal", text="▶ BUCH GENERIEREN")
        self.cancel_btn.configure(state="disabled")
        self.update_status("● Abgebrochen", "#ffaa00", "Generierung abgebrochen.")


if __name__ == "__main__":
    app = BrokusGUI()
    app.mainloop()
