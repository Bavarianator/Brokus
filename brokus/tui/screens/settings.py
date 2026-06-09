"""Settings screen for brokus – provider selection, models, API keys."""

import yaml
import os
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import (
    Static, Input, Select, Button, Switch, Header, Footer,
)
from textual.binding import Binding

from brokus.utils.logger import log


class SettingsScreen(Screen):
    """Application settings screen with multi-provider support."""

    BINDINGS = [
        Binding("t", "test_connection", "Testen"),
        Binding("r", "reset", "Zurücksetzen"),
        Binding("escape", "go_back", "Zurück"),
        Binding("ctrl+s", "save", "Speichern"),
    ]

    def __init__(self):
        super().__init__()
        self._provider_data: dict = {}
        self._current_provider = "anthropic"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with ScrollableContainer(id="settings-scroll"):
            with Container(id="settings-container"):
                yield Static("⚙️ Einstellungen", classes="section-title")

                # ═══════════════════════════════════════════════════
                # 🤖 AI-PROVIDER
                # ═══════════════════════════════════════════════════
                yield Static("🤖 KI-Anbieter", classes="subsection-title")

                yield Static("Provider:", classes="form-label")
                yield Select([], id="select-provider")

                yield Static("Modell:", classes="form-label")
                yield Select([], id="select-model")

                yield Static("Benutzerdefiniertes Modell (optional):", classes="form-label")
                yield Input(placeholder="z.B. llama3.2:3b, qwen2.5:7b – überschreibt Auswahl", id="input-custom-model")

                yield Static("Eigene Base-URL (optional, für openai_compat / Proxies):", classes="form-label")
                yield Input(placeholder="https://api.example.com/v1", id="input-base-url")

                yield Static("API-Key:", classes="form-label")
                yield Input(
                    placeholder="API-Key (oder Umgebungsvariable setzen)",
                    id="input-api-key",
                    password=True,
                )

                yield Static("", id="provider-info", classes="form-label")
                yield Static("", id="provider-status")

                with Horizontal(id="provider-test-row"):
                    yield Button("🔍 Verbindung testen", id="btn-test", variant="default")
                    yield Button("🔧 Modelle neu laden", id="btn-refresh-models")

                # ═══════════════════════════════════════════════════
                # 🎛️ AI-PARAMETER
                # ═══════════════════════════════════════════════════
                yield Static("", classes="spacer")
                yield Static("🎛️ KI-Parameter", classes="subsection-title")

                yield Static("Temperature (0.0 = streng, 1.0 = kreativ):", classes="form-label")
                yield Input(value="0.7", id="input-temperature", type="number")

                yield Static("Max. Tokens (0 = Provider-Default):", classes="form-label")
                yield Input(value="4000", id="input-max-tokens", type="integer")

                yield Static("Top-P (0.0-1.0, leer = aus):", classes="form-label")
                yield Input(placeholder="z.B. 0.9", id="input-top-p", type="number")

                yield Static("Frequency-Penalty (-2.0 bis 2.0, leer = aus):", classes="form-label")
                yield Input(placeholder="z.B. 0.1", id="input-freq-penalty", type="number")

                yield Static("Presence-Penalty (-2.0 bis 2.0, leer = aus):", classes="form-label")
                yield Input(placeholder="z.B. 0.1", id="input-presence-penalty", type="number")

                yield Static("Request-Timeout (Sekunden):", classes="form-label")
                yield Input(value="300", id="input-timeout", type="integer")

                yield Static("Extended Thinking (Reasoning):", classes="form-label")
                yield Switch(value=False, id="switch-extended-thinking")

                # ═══════════════════════════════════════════════════
                # 📝 GENERIERUNG
                # ═══════════════════════════════════════════════════
                yield Static("", classes="spacer")
                yield Static("📝 Generierung", classes="subsection-title")

                yield Static("Min. Wörter pro Kapitel:", classes="form-label")
                yield Input(value="1500", id="input-min-words", type="integer")

                yield Static("Max. Wörter pro Kapitel:", classes="form-label")
                yield Input(value="3000", id="input-max-words", type="integer")

                yield Static("Compliance-Schwelle (%):", classes="form-label")
                yield Input(value="80", id="input-compliance", type="integer")

                yield Static("Detailgrad:", classes="form-label")
                yield Select(
                    [
                        ("Locker – KI hat mehr Freiheit", "loose"),
                        ("Standard – Ausgewogen", "standard"),
                        ("Detailliert – Idee genau umsetzen", "detailed"),
                        ("Streng – Maximale Treue", "strict"),
                    ],
                    id="select-detail-level",
                )

                yield Static("Erzähltempo:", classes="form-label")
                yield Select(
                    [
                        ("Langsam – viel Atmosphäre, ruhig", "slow"),
                        ("Ausgewogen – Standard", "balanced"),
                        ("Schnell – viele Wendungen", "fast"),
                    ],
                    id="select-story-pace",
                )

                yield Static("Default-Sprache:", classes="form-label")
                yield Select(
                    [
                        ("Deutsch", "Deutsch"), ("Englisch", "Englisch"),
                        ("Französisch", "Französisch"), ("Spanisch", "Spanisch"),
                        ("Italienisch", "Italienisch"), ("Portugiesisch", "Portugiesisch"),
                        ("Japanisch", "Japanisch"), ("Chinesisch", "Chinesisch"),
                    ],
                    id="select-language",
                )

                yield Static("Auto-Retry bei Fehlern:", classes="form-label")
                yield Switch(value=True, id="switch-auto-retry")

                yield Static("Max. Retries:", classes="form-label")
                yield Input(value="3", id="input-max-retries", type="integer")

                yield Static("Pause zwischen Kapiteln (Sekunden):", classes="form-label")
                yield Input(value="2.0", id="input-chapter-delay", type="number")

                yield Static("Standard-Kapitelanzahl:", classes="form-label")
                yield Input(value="20", id="input-default-chapters", type="integer")

                yield Static("Auto-Export nach Generation:", classes="form-label")
                yield Switch(value=False, id="switch-auto-export")

                yield Static("Datei nach Export automatisch öffnen:", classes="form-label")
                yield Switch(value=True, id="switch-auto-open")

                yield Static("Backup vor jeder Generation:", classes="form-label")
                yield Switch(value=True, id="switch-backup")

                # ═══════════════════════════════════════════════════
                # 🎨 UI & LOGGING
                # ═══════════════════════════════════════════════════
                yield Static("", classes="spacer")
                yield Static("🎨 UI & Logging", classes="subsection-title")

                yield Static("🌐 UI-Sprache (UI Language):", classes="form-label")
                yield Select(
                    [
                        ("🇩🇪 Deutsch", "de"),
                        ("🇬🇧 English", "en"),
                        ("🇫🇷 Français", "fr"),
                        ("🇪🇸 Español", "es"),
                        ("🇮🇹 Italiano", "it"),
                    ],
                    id="select-ui-language",
                    value="de",
                )
                yield Static("Hinweis: Sprache greift erst nach Neustart der TUI.", classes="form-hint")

                yield Static("Theme:", classes="form-label")
                yield Select(
                    [
                        ("Dark", "dark"),
                        ("Light", "light"),
                        ("Monokai", "monokai"),
                    ],
                    id="select-theme",
                )

                yield Static("Animationen:", classes="form-label")
                yield Switch(value=True, id="switch-animations")

                yield Static("Log-Level:", classes="form-label")
                yield Select(
                    [("DEBUG", "DEBUG"), ("INFO", "INFO"), ("WARNING", "WARNING"), ("ERROR", "ERROR")],
                    id="select-log-level",
                )

                yield Static("Token-Verbrauch anzeigen:", classes="form-label")
                yield Switch(value=True, id="switch-show-tokens")

                yield Static("Kosten-Schätzung anzeigen:", classes="form-label")
                yield Switch(value=True, id="switch-show-cost")

                # ═══════════════════════════════════════════════════
                # 🔧 ERWEITERT
                # ═══════════════════════════════════════════════════
                yield Static("", classes="spacer")
                yield Static("🔧 Erweitert", classes="subsection-title")

                yield Static("Cache AI-Antworten:", classes="form-label")
                yield Switch(value=True, id="switch-cache")

                yield Static("Max. Cache-Größe (MB):", classes="form-label")
                yield Input(value="500", id="input-cache-size", type="integer")

                yield Static("Vor Beenden nachfragen:", classes="form-label")
                yield Switch(value=True, id="switch-confirm-quit")

                # ═══════════════════════════════════════════════════
                # ACTIONS
                # ═══════════════════════════════════════════════════
                yield Static("", classes="spacer")
                with Horizontal(id="settings-actions"):
                    yield Button("💾 Speichern", id="btn-save", variant="primary")
                    yield Button("↩ Zurücksetzen", id="btn-reset")
                    yield Button("← Zurück", id="btn-back")

        yield Footer()

    async def on_mount(self):
        """Load settings and populate provider/model selects."""
        await self._load_settings()
        await self._populate_providers()

    async def _populate_providers(self):
        """Populate the provider dropdown from the registry."""
        from brokus.ai.client import PROVIDER_REGISTRY
        self._provider_data = {
            key: cfg for key, cfg in PROVIDER_REGISTRY.items()
        }

        provider_select = self.query_one("#select-provider", Select)
        options = [
            (f"{cfg.name} – {cfg.cost_info}", key)
            for key, cfg in self._provider_data.items()
        ]
        provider_select.set_options(options)
        provider_select.value = self._current_provider

        await self._on_provider_changed(self._current_provider)

    async def _on_provider_changed(self, provider_key: str):
        """Update model dropdown and provider info when provider changes."""
        self._current_provider = provider_key

        cfg = self._provider_data.get(provider_key)
        if not cfg:
            return

        # Update model dropdown from hardcoded list first (instant)
        model_select = self.query_one("#select-model", Select)
        model_options = [(m, m) for m in cfg.models]
        model_select.set_options(model_options)
        if cfg.models:
            model_select.value = cfg.models[0]

        # Update provider info
        status_icon = "✅" if cfg.api_key_value else "⚠️"
        info_text = f"Bibliothek: {cfg.library}"
        if cfg.features:
            info_text += f" | {cfg.features}"
        self.query_one("#provider-info", Static).update(info_text)

        status_text = (
            f"{status_icon} Key: {'Gesetzt' if cfg.api_key_value else 'Nicht gesetzt'}"
        )
        if cfg.base_url:
            status_text += f" | {cfg.base_url}"
        self.query_one("#provider-status", Static).update(status_text)

        # Hintergrund: Modelle live vom Endpoint laden
        asyncio.create_task(self._refresh_models_async(provider_key))

    async def _refresh_models_async(self, provider_key: str, force: bool = False):
        """Try to fetch live models; update dropdown + info on success."""
        try:
            from brokus.ai.model_discovery import get_provider_models_async
        except Exception as e:
            self.query_one("#provider-info", Static).update(f"⚠️ Discovery nicht verfügbar: {e}")
            return

        cfg = self._provider_data.get(provider_key)
        if not cfg:
            return

        # Custom-Base-URL aus dem Input-Feld lesen
        try:
            custom_url = self.query_one("#input-base-url", Input).value.strip() or None
        except Exception:
            custom_url = None

        self.query_one("#provider-info", Static).update("🔄 Lade Modelle vom Endpoint...")

        try:
            result = await get_provider_models_async(
                provider_key, custom_base_url=custom_url, force_refresh=force,
            )
        except Exception as e:
            self.query_one("#provider-info", Static).update(f"❌ Fehler: {str(e)[:80]}")
            return

        if not result.models:
            self.query_one("#provider-info", Static).update("⚠️ Keine Modelle entdeckt – Fallback-Liste aktiv")
            return

        # Dropdown aktualisieren
        model_select = self.query_one("#select-model", Select)
        model_select.set_options([(m, m) for m in result.models])
        if result.models:
            model_select.value = result.models[0]

        source_label = {
            "live": "🌐 Live vom Endpoint",
            "cache": "💾 Aus Cache (TTL)",
            "fallback": "📋 Fallback-Liste",
        }.get(result.source, result.source)
        n = len(result.models)
        self.query_one("#provider-info", Static).update(
            f"📋 {n} Modelle · {source_label}"
        )
        if result.error and result.source != "live":
            self.query_one("#provider-status", Static).update(
                f"ℹ️  {result.error[:80]}"
            )

    def action_refresh_models(self):
        """Force-refresh the model list from the live endpoint."""
        asyncio.create_task(self._refresh_models_async(self._current_provider, force=True))

    async def _load_settings(self):
        """Load settings from config file."""
        config_path = Path("config/settings.yaml")
        if not config_path.exists():
            return

        import asyncio
        loop = asyncio.get_event_loop()
        settings = await loop.run_in_executor(None, self._read_yaml, config_path)
        if not settings:
            return

        ai = settings.get("ai", {})
        self._current_provider = ai.get("provider", "anthropic")

        # AI-Parameter
        self.query_one("#input-temperature", Input).value = str(ai.get("temperature", 0.7))
        self.query_one("#input-max-tokens", Input).value = str(ai.get("max_tokens", 4000))
        self.query_one("#input-top-p", Input).value = "" if ai.get("top_p") is None else str(ai.get("top_p"))
        self.query_one("#input-freq-penalty", Input).value = "" if ai.get("frequency_penalty") is None else str(ai.get("frequency_penalty"))
        self.query_one("#input-presence-penalty", Input).value = "" if ai.get("presence_penalty") is None else str(ai.get("presence_penalty"))
        self.query_one("#input-base-url", Input).value = "" if not ai.get("custom_base_url") else str(ai.get("custom_base_url"))
        self.query_one("#input-custom-model", Input).value = ""

        adv = settings.get("advanced", {})
        try:
            self.query_one("#switch-extended-thinking", Switch).value = adv.get("use_extended_thinking", False)
        except Exception:
            pass
        self.query_one("#input-timeout", Input).value = str(adv.get("request_timeout", 300))
        try:
            self.query_one("#switch-cache", Switch).value = adv.get("cache_responses", True)
        except Exception:
            pass
        self.query_one("#input-cache-size", Input).value = str(adv.get("max_cache_size_mb", 500))

        gen = settings.get("generation", {})
        self.query_one("#input-min-words", Input).value = str(gen.get("min_chapter_words", 1500))
        self.query_one("#input-max-words", Input).value = str(gen.get("max_chapter_words", 3000))
        self.query_one("#input-compliance", Input).value = str(gen.get("compliance_threshold", 80))
        try:
            self.query_one("#switch-auto-retry", Switch).value = gen.get("auto_retry", True)
        except Exception:
            pass
        self.query_one("#input-max-retries", Input).value = str(gen.get("max_retries", 3))
        self.query_one("#input-chapter-delay", Input).value = str(gen.get("chapter_delay", 2.0))
        self.query_one("#input-default-chapters", Input).value = str(gen.get("default_chapters", 20))
        try:
            self.query_one("#switch-auto-export", Switch).value = gen.get("auto_export", False)
        except Exception:
            pass
        try:
            self.query_one("#switch-auto-open", Switch).value = gen.get("auto_open_after_export", True)
        except Exception:
            pass
        try:
            self.query_one("#switch-backup", Switch).value = gen.get("backup_enabled", True)
        except Exception:
            pass
        try:
            self.query_one("#select-detail-level", Select).value = gen.get("detail_level", "standard")
        except Exception:
            pass
        try:
            self.query_one("#select-story-pace", Select).value = gen.get("story_pace", "balanced")
        except Exception:
            pass
        try:
            self.query_one("#select-language", Select).value = gen.get("default_language", "Deutsch")
        except Exception:
            pass

        ui = settings.get("ui", {})
        try:
            self.query_one("#select-theme", Select).value = ui.get("theme", "dark")
        except Exception:
            pass
        try:
            self.query_one("#switch-animations", Switch).value = ui.get("animations", True)
        except Exception:
            pass
        try:
            self.query_one("#select-log-level", Select).value = ui.get("log_level", "INFO")
        except Exception:
            pass
        try:
            self.query_one("#switch-show-tokens", Switch).value = ui.get("show_token_count", True)
        except Exception:
            pass
        try:
            self.query_one("#switch-show-cost", Switch).value = ui.get("show_cost_estimate", True)
        except Exception:
            pass
        try:
            self.query_one("#switch-confirm-quit", Switch).value = ui.get("confirm_quit", True)
        except Exception:
            pass
        # UI-Sprache: setze aktiv + zeige im Select
        ui_lang = ui.get("language") or "de"
        try:
            from brokus.utils.i18n import set_language as _i18n_set
            _i18n_set(ui_lang)
        except Exception:
            pass
        try:
            self.query_one("#select-ui-language", Select).value = ui_lang
        except Exception:
            pass

    def _read_yaml(self, config_path: Path) -> dict:
        """Synchronous YAML read for executor."""
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    async def _save_settings(self):
        """Save settings to config file and persist encrypted API keys."""
        config_path = Path("config/settings.yaml")

        try:
            auto_retry = self.query_one("#switch-auto-retry", Switch).value
        except Exception:
            auto_retry = True
        try:
            animations = self.query_one("#switch-animations", Switch).value
        except Exception:
            animations = True
        try:
            ext_thinking = self.query_one("#switch-extended-thinking", Switch).value
        except Exception:
            ext_thinking = False
        try:
            cache_enabled = self.query_one("#switch-cache", Switch).value
        except Exception:
            cache_enabled = True
        try:
            show_tokens = self.query_one("#switch-show-tokens", Switch).value
        except Exception:
            show_tokens = True
        try:
            show_cost = self.query_one("#switch-show-cost", Switch).value
        except Exception:
            show_cost = True
        try:
            confirm_quit = self.query_one("#switch-confirm-quit", Switch).value
        except Exception:
            confirm_quit = True
        try:
            auto_export = self.query_one("#switch-auto-export", Switch).value
        except Exception:
            auto_export = False
        try:
            auto_open = self.query_one("#switch-auto-open", Switch).value
        except Exception:
            auto_open = True
        try:
            backup_enabled = self.query_one("#switch-backup", Switch).value
        except Exception:
            backup_enabled = True

        provider = self.query_one("#select-provider", Select).value or "anthropic"
        model = self.query_one("#select-model", Select).value or ""
        custom_model = self.query_one("#input-custom-model", Input).value.strip()
        if custom_model:
            model = custom_model
        base_url = self.query_one("#input-base-url", Input).value.strip()
        api_key_input = self.query_one("#input-api-key", Input).value

        # ── Persist encrypted API key ──
        if provider:
            try:
                cfg = self._provider_data.get(str(provider))
                if cfg:
                    from brokus.utils.crypto import SecretStore
                    store = SecretStore.instance()
                    key_value = api_key_input.strip()
                    if key_value:
                        store.set(cfg.api_key_env, key_value)
                        os.environ[cfg.api_key_env] = key_value
                        log.info(f"Encrypted API key saved for {cfg.name}")
                    else:
                        store.delete(cfg.api_key_env)
                        os.environ.pop(cfg.api_key_env, None)
                        log.info(f"API key deleted for {cfg.name}")
                    store.save()
            except Exception as e:
                self.notify(f"API-Key konnte nicht verschlüsselt werden: {e}", severity="warning")

        def _opt_float(val, default=None):
            try:
                s = (val or "").strip()
                return float(s) if s else default
            except (ValueError, TypeError):
                return default

        temperature = _opt_float(self.query_one("#input-temperature", Input).value, 0.7) or 0.7
        max_tokens = int(self.query_one("#input-max-tokens", Input).value or "4000")
        top_p = _opt_float(self.query_one("#input-top-p", Input).value)
        freq_pen = _opt_float(self.query_one("#input-freq-penalty", Input).value)
        pres_pen = _opt_float(self.query_one("#input-presence-penalty", Input).value)
        timeout = int(self.query_one("#input-timeout", Input).value or "300")
        cache_size = int(self.query_one("#input-cache-size", Input).value or "500")
        chapter_delay = _opt_float(self.query_one("#input-chapter-delay", Input).value, 2.0) or 0.0

        try:
            detail_level = str(self.query_one("#select-detail-level", Select).value or "standard")
        except Exception:
            detail_level = "standard"
        try:
            story_pace = str(self.query_one("#select-story-pace", Select).value or "balanced")
        except Exception:
            story_pace = "balanced"
        try:
            default_language = str(self.query_one("#select-language", Select).value or "Deutsch")
        except Exception:
            default_language = "Deutsch"
        try:
            log_level = str(self.query_one("#select-log-level", Select).value or "INFO")
        except Exception:
            log_level = "INFO"
        try:
            ui_language = str(self.query_one("#select-ui-language", Select).value or "de")
        except Exception:
            ui_language = "de"

        settings = {
            "ai": {
                "provider": str(provider),
                "model": str(model),
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "frequency_penalty": freq_pen,
                "presence_penalty": pres_pen,
                "max_retries": 3,
                "retry_delay": 1.0,
                "custom_base_url": base_url or None,
            },
            "generation": {
                "min_chapter_words": int(self.query_one("#input-min-words", Input).value or "1500"),
                "max_chapter_words": int(self.query_one("#input-max-words", Input).value or "3000"),
                "compliance_threshold": int(self.query_one("#input-compliance", Input).value or "80"),
                "auto_retry": auto_retry,
                "max_retries": int(self.query_one("#input-max-retries", Input).value or "3"),
                "default_chapters": int(self.query_one("#input-default-chapters", Input).value or "20"),
                "max_chapters": 50,
                "min_chapters": 5,
                "chapter_delay": chapter_delay,
                "default_language": default_language,
                "story_pace": story_pace,
                "detail_level": detail_level,
                "auto_export": auto_export,
                "auto_open_after_export": auto_open,
                "backup_enabled": backup_enabled,
            },
            "ui": {
                "theme": self.query_one("#select-theme", Select).value or "dark",
                "animations": animations,
                "log_level": log_level,
                "language": ui_language,
                "show_token_count": show_tokens,
                "show_cost_estimate": show_cost,
                "confirm_quit": confirm_quit,
            },
            "storage": {
                "database_path": "data/projects.db",
                "books_path": "data/books",
            },
            "advanced": {
                "use_extended_thinking": ext_thinking,
                "parallel_chapters": 1,
                "request_timeout": timeout,
                "streaming": False,
                "cache_responses": cache_enabled,
                "max_cache_size_mb": cache_size,
            },
        }

        # Preserve provider configs from existing settings if possible
        config_path.parent.mkdir(parents=True, exist_ok=True)

        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._write_yaml, config_path, settings)

        self.notify("Einstellungen gespeichert ✅", title="Erfolg")

    def _write_yaml(self, config_path: Path, settings: dict):
        """Synchronous YAML write for executor."""
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(settings, f, allow_unicode=True, default_flow_style=False)

    async def _test_connection(self):
        """Test the selected provider connection."""
        provider = self.query_one("#select-provider", Select).value
        model = self.query_one("#select-model", Select).value
        api_key_input = self.query_one("#input-api-key", Input).value

        # Temporarily set API key if provided (restore after)
        cfg = self._provider_data.get(str(provider) if provider else "")
        prev_key = None
        if cfg and api_key_input:
            prev_key = os.environ.get(cfg.api_key_env)
            os.environ[cfg.api_key_env] = api_key_input

        self.query_one("#provider-status", Static).update("🔄 Teste Verbindung...")

        try:
            from brokus.ai.client import BrokusAIClient
            client = BrokusAIClient(
                provider=str(provider) if provider else "anthropic",
                model=str(model) if model else "claude-sonnet-4-5",
            )
            success = await client.test_connection()

            if success:
                self.query_one("#provider-status", Static).update("✅ Verbindung OK – Modell verfügbar")
                self.notify("Verbindung erfolgreich! ✅", title="Erfolg")
            else:
                self.query_one("#provider-status", Static).update("❌ Verbindung fehlgeschlagen")
                self.notify("Verbindung fehlgeschlagen ❌", severity="error")
        except Exception as e:
            self.query_one("#provider-status", Static).update(f"❌ Fehler: {str(e)[:100]}")
            self.notify(f"Fehler: {e}", severity="error")
        finally:
            # Restore previous env state
            if cfg and api_key_input:
                if prev_key is not None:
                    os.environ[cfg.api_key_env] = prev_key
                else:
                    os.environ.pop(cfg.api_key_env, None)

    # ── Event Handlers ──

    def on_select_changed(self, event: Select.Changed):
        """Handle provider/model selection changes."""
        if event.select.id == "select-provider":
            import asyncio
            asyncio.create_task(self._on_provider_changed(str(event.value)))

    def action_test_connection(self):
        import asyncio
        asyncio.create_task(self._test_connection())

    def action_reset(self):
        import asyncio
        asyncio.create_task(self._load_settings())
        self.notify("Einstellungen zurückgesetzt.")

    async def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id
        if button_id == "btn-save":
            self.action_save()
        elif button_id == "btn-reset":
            self.action_reset()
        elif button_id == "btn-test":
            self.action_test_connection()
        elif button_id == "btn-refresh-models":
            self.action_refresh_models()
        elif button_id == "btn-back":
            self.action_go_back()

    def action_save(self):
        import asyncio
        asyncio.create_task(self._save_settings())

    def action_go_back(self):
        self.app.navigate_to("library")
