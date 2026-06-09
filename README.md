<div align="center">
  <img src="https://img.shields.io/badge/version-1.1.0-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-purple?style=flat-square" alt="License">
  <br>
  <pre>
██████  ██████   ██████  ██   ██ ██    ██ ███████
██   ██ ██   ██ ██    ██ ██  ██  ██    ██ ██
██████  ██████  ██    ██ █████   ██    ██ ███████
██   ██ ██   ██ ██    ██ ██  ██  ██    ██      ██
██████  ██   ██  ██████  ██   ██  ██████  ███████
  </pre>
  <p><strong>KI-gestützter Buch-Generator – erstelle komplette Romane im Terminal.</strong></p>
  <p><em>Three-layer AI architecture · 33+ providers · 33 genres · 6 languages · 6 export formats</em></p>
</div>

---

<br>

**brokus** verwandelt deine Buchidee in einen vollständigen Roman – gesteuert durch ein innovatives **Drei-Schichten-System**: DNA-Extraktion, strukturierte Kapitel-Generierung und automatisierte Compliance-Prüfung.

Schreibe deine Idee, wähle Genre und Länge, und brokus generiert Kapitel für Kapitel ein stimmiges Buch – mit automatischen Fallback-Modellen bei Rate-Limits und einem eingebauten Update-System.

---

## 📦 Features

### 🧬 DNA-System (Kern-Innovation)

Bevor brokus ein einziges Wort schreibt, extrahiert es die **unveränderliche DNA** deiner Buchidee:

| Schicht | Phase | Beschreibung |
|---------|-------|--------------|
| **1. Pre-Generation Lock** | DNA-Extraktion | Extrahiert Protagonist, Setting, Pflicht-Elemente, Tabus, Grundton – gespeichert als JSON |
| **2. In-Generation Lock** | Jeder Kapitel-Prompt | DNA-Block wird in jeden Prompt eingebettet → kein thematischer Drift |
| **3. Post-Generation Audit** | Compliance-Prüfung | Jedes Kapitel wird gegen die DNA validiert (Score 0–100). Unterhalb der Schwelle → Flag für Neugenerierung |

### 🤖 Multi-Provider AI-Engine

**33+ Provider**, einheitlich über eine Client-Abstraktion:

<table>
<tr><th>Cloud</th><th>Aggregatoren</th><th>Lokal</th><th>Custom</th></tr>
<tr><td>
OpenAI · Anthropic (Claude)<br>
Google Gemini · DeepSeek<br>
Mistral AI · Groq (⚡500+ t/s)<br>
Cerebras · xAI (Grok)<br>
Cohere · AI21 · Perplexity<br>
Novita · DeepInfra · Together<br>
Fireworks · SambaNova<br>
NVIDIA NIM · Replicate<br>
Anyscale · Reka · Writer<br>
Moonshot (Kimi) · Zhipu (GLM)
</td><td>
<b>OpenRouter</b> – 200+ Modelle mit einem Key<br>
<b>GitHub Models</b> – Kostenlos (Rate-Limits)<br>
<b>Hugging Face</b> – Open-Source-Modelle<br>
<b>Ollama Cloud</b> – Hosted
</td><td>
<b>Ollama</b> – Komplett offline, GPU nötig<br>
<b>LM Studio</b> – GUI, OpenAI-kompatibel<br>
<b>LocalAI</b> – Docker-basiert
</td><td>
<b>OpenAI-kompatibel</b> – Jeder API-Endpoint<br>
(vLLM, TabbyAPI, LiteLLM Proxy, …)
</td></tr>
</table>

### 📚 33 Genres mit spezialisierten Style-Hints

Fantasy · Horror · Science Fiction · Romance · Thriller · Mystery · Historical Fiction · Adventure · Dystopia · Young Adult · Literary Fiction · Paranormal · Erotica · Comedy · Drama · Action · Post-Apocalyptic · Steampunk · Cyberpunk · Urban Fantasy · Magical Realism · Military · Western · Gothic · Noir · Fairy Tale · Slice of Life · Superhero · Survival · Biography · Children's Book · Satire · Experimental

### 🌍 6 Sprachen (UI & Generation)

| Sprache | Code | Übersetzung |
|---------|------|-------------|
| Deutsch | `de` | Vollständig |
| English | `en` | Vollständig |
| Français | `fr` | Vollständig |
| Español | `es` | Vollständig |
| Nederlands | `nl` | Vollständig |
| Italiano | `it` | Vollständig |

### 📤 Export-Formate

| Format | Tool | Anwendung |
|--------|------|-----------|
| **Markdown** (`.md`) | nativ | Bearbeitung, Versionierung |
| **EPUB** (`.epub`) | `ebooklib` | E-Reader (Kindle, Tolino) |
| **PDF** (`.pdf`) | `weasyprint` | Druck, Weitergabe |
| **Word** (`.docx`) | nativ (ZIP/XML) | Lektorat, Verlage |
| **JSON** (`.json`) | nativ | Entwicklung, API |
| **Plain Text** (`.txt`) | nativ | Universell |

### 🔐 Security

- API-Keys werden **verschlüsselt** in `secrets.enc` gespeichert (maschinen-gebundener Schlüssel)
- Optionale **Master-Passphrase** für zusätzlichen Password-Schutz
- Re-Encryption bei Passphrase-Rotation

### 🛡️ Moderation & Fallback

- **ModerationError**: Bei 403-Moderation (z.B. OpenRouter/OpenInference) → sofortiger Abbruch, kein sinnloser Fallback
- **Rate-Limit-Fallback**: Modelle in einer konfigurierbaren Chain, kein Self-Fallback (dedupliziert)
- **Automatische Retry**: Mit Backoff, konfigurierbar

### 🔄 Update-System

- **Startup-Check**: Leise Prüfung beim Programmstart (5s Timeout, nur sichtbar bei Update)
- **Manueller Check**: Einstellungen → Erweitert → "🔄 Update suchen & installieren"
- **Installation**: Automatisch via `git pull` + `pip install -e .`
- **Versionserkennung**: Semver und Non-Semver-Tags (z.B. `ai`)
- **Quelle**: GitHub Releases API (mit Fallback auf Tags-API)

### 📊 Projekt-Management

- Alle Bücher in einer lokalen SQLite-Datenbank (`data/projects.db`)
- Automatische Backups vor jeder Generierung
- Bibliothek mit Status-Tracking, Wortzahlen, Compliance-Scores
- Pause/Resume auf Pipeline-Ebene (Kapitel-Ebene)
- Export mit Format-Auswahl nach der Generierung

---

## ⚡ Quick Start

### Installation

#### 🚀 Empfohlen: install.sh (Ein-Befehl-Setup)

```bash
git clone https://github.com/Bavarianator/Brokus.git
cd brokus
./install.sh                     # Symlink + Dependencies + PATH
brokus                           # Direkt aufrufbar!
```

> **⚠️ Wichtig:** `brokus/` **(mit Schrägstrich) ist das Python-Paket** – ein Ordner, kein Executable.
> Das ausführbare Skript ist **`bin/brokus`**. `install.sh` erstellt einen Symlink von `bin/brokus` → `~/.local/bin/brokus`,
> damit `brokus` danach als globaler Befehl zur Verfügung steht.

`install.sh` erledigt alles:
- Symlinkt `bin/brokus` → `~/.local/bin/brokus` (das **Executable**, nicht den Paket-Ordner!)
- Installiert Python-Dependencies (mit PEP 668 Fallback für Arch Linux)
- Trägt `~/.local/bin` in die Shell-Config ein (zsh/bash)

#### 📦 Alternativ: pip install

```bash
pip install -e .                 # Klassische Installation
brokus
```

```bash
# Direkt via python -m (ohne Installation)
python -m brokus
```

#### 🗑️ Deinstallieren

```bash
./install.sh --uninstall         # Entfernt Symlink
pip uninstall brokus              # Entfernt Python-Paket
```

### First-Run Wizard

Beim ersten Start führt brokus durch einen interaktiven **Setup-Assistenten**:

1. **Sprache wählen** – Deutsch, English, Français, Español, Nederlands, Italiano
2. **KI-Provider wählen** – OpenRouter, OpenAI, Anthropic, Ollama, … (33+)
3. **Modell wählen** – Live-Discovery vom API-Endpoint
4. **API-Key eingeben** – Wird verschlüsselt gespeichert
5. **(Optional) Master-Passphrase** – Zusätzlicher Schutz für Keys

> **Tipp**: Mit **OpenRouter** hast du mit einem einzigen API-Key Zugriff auf 200+ Modelle – ideal zum Ausprobieren verschiedener Modelle.

---

## 📖 Nutzungsmodi

### ⚡ Schnell-Buch (3 Schritte)

```
Idee eingeben → Titel + Genre wählen → Länge festlegen → Generieren!
```

Optimiert für schnelle Ergebnisse: Idee eintippen, Genre wählen, Länge bestimmen – los geht's.

### ✨ Meisterwerk (11 Schritte)

Vollständige Kontrolle über alle Parameter:

| Schritt | Parameter | Optionen |
|---------|-----------|----------|
| 1 | Buchidee | Freitext |
| 2 | Titel | Freitext |
| 3 | Genre | 33 Genres |
| 4 | Zielgruppe | Kinder · Jugendliche · Young Adult · Erwachsene |
| 5 | Sprache | 12 Sprachen |
| 6 | KI-Modell | Aus gewähltem Provider |
| 7 | Erzählperspektive | Ich-Perspektive, Dritte Person (personal/auktorial), Briefroman, … |
| 8 | Stimmung & Ton | Düster · Spannend · Warmherzig · Humorvoll · Episch |
| 9 | Buchlänge | Minigeschichte (1.500 W.) bis Megaroman (150.000 W.) |
| 10 | Wichtige Infos | Pflicht-Elemente, Fakten, Orte |
| 11 | Detailgrad | Lockers · Standard · Detailiert · Streng |

### 📖 Bibliothek

- Alle gespeicherten Projekte als Tabelle mit Status, Wortzahl, Fortschritt
- Kapitel lesen und navigieren (nächstes/vorheriges)
- Status: ✅ abgeschlossen · ⏳ in Generierung · ❌ fehlgeschlagen · 📝 Entwurf

---

## 🏗️ Architektur

```
brokus/
├── ai/                # Multi-Provider AI-Client, Modelle, Schemata, Discovery
│   ├── client.py      #   Abstraktionsschicht (OpenAI, Anthropic, Ollama, …)
│   ├── model_discovery.py  # Live-Modell-Liste vom API-Endpoint
│   ├── prompts.py     #   Prompt-Loader (aus config/prompts.yaml)
│   ├── schemas.py     #   Pydantic-Modelle für strukturierte Outputs
│   └── models.py      #   Provider-Registry
├── core/              # Pipeline, DNA-Extraktion, Validierung, Tracker
│   ├── dna_extractor.py  # Layer 1: DNA-Extraktion (Pre-Generation Lock)
│   ├── pipeline.py    #   Orchestrierung: DNA → Synopsis → Charaktere → Plan → Kapitel
│   ├── validator.py   #   Layer 3: Compliance-Audit (Post-Generation)
│   ├── extractor.py   #   Kernelement-Extraktion (Charaktere, Setting, …)
│   ├── context.py     #   Kontext-Management für Kapitel-Prompts
│   └── tracker.py     #   Compliance-Tracker mit Score-Berechnung
├── storage/           # Datenbank, Exporter
│   ├── database.py    #   Async SQLite (aiosqlite)
│   └── exporter.py    #   Multi-Format Export (MD, EPUB, PDF, DOCX, JSON, TXT)
├── tui/               # Terminal User Interface
│   └── app_simple.py  #   Rich-basierte CLI (Panels, Tabellen, Farben)
├── utils/             # Hilfsmodule
│   ├── i18n.py        #   Internationalisierung (6 Sprachen, 460+ Keys)
│   ├── crypto.py      #   AES-256-Verschlüsselung für API-Keys
│   ├── updater.py     #   GitHub-basiertes Update-System
│   ├── settings_loader.py  # YAML-Konfiguration laden/speichern
│   ├── opener.py      #   System-Dokumenten-Reader
│   ├── logger.py      #   Strukturiertes Logging
│   ├── tokens.py      #   Token-Zählung
├── config/            # YAML-Konfiguration
│   ├── settings.yaml  #   Hauptkonfiguration (Provider, AI, Generation, UI)
│   ├── prompts.yaml   #   System-Prompts für alle Pipeline-Stages
│   └── genres.yaml    #   Genre-Definitionen + Style-Hints
├── data/              # Laufzeitdaten
│   ├── projects.db    #   SQLite-Datenbank
│   ├── i18n/          #   Übersetzungsdateien (6 Sprachen, 460+ Keys)
│   ├── books/         #   Exportierte Bücher
│   └── backups/       #   Automatische DB-Backups
└── bin/brokus         # Shell-Wrapper
```

### Pipeline-Ablauf

```
Buchidee
    │
    ▼
┌─────────────────┐
│  DNA-Extraktion  │  ← Protagonist, Setting, Pflicht-Elemente, Tabus, Ton
│  (Layer 1)       │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Kernelemente    │  ← Charaktere, Handlungsbögen, Weltendetails
└────────┬────────┘
         ▼
┌─────────────────┐
│  Synopsis        │  ← Gesamtstruktur der Handlung
└────────┬────────┘
         ▼
┌─────────────────┐
│  Charaktere      │  ← Detaillierte Figurenbeschreibungen
└────────┬────────┘
         ▼
┌─────────────────┐
│  Kapitelplan     │  ← Kapitel-für-Kapitel Struktur
└────────┬────────┘
         ▼
  ┌──────┴──────┐
  ▼             ▼
Kapitel 1   Kapitel 2  …  Kapitel N
  │             │
  ▼             ▼
┌─────────────────────────┐
│  Compliance-Prüfung      │  ← Layer 3: Score 0–100 gegen DNA
│  (Layer 3)               │
└─────────────────────────┘
```

### Fallback-Strategie

Jede Pipeline-Stage hat eine eigene Modell-Chain. Fällt ein Modell aus (Rate-Limit, Timeout), wird automatisch das nächste in der Chain probiert. Bei **Moderation (403)** bricht der gesamte Vorgang sofort ab – kein sinnloser Fallback auf andere Modelle.

```
Pipeline-Stage → model_A:free → model_B:free → model_C:free → … → Fallback-Text
                                ↑
                     Rate-Limit → nächstes Modell
                     403/Auth   → sofortiger Abbruch (ModerationError)
```

---

## 🎛️ Konfiguration

### Zentrale YAML: `config/settings.yaml`

```yaml
ai:
  provider: anthropic           # Standard-Provider
  model: claude-sonnet-4-5      # Standard-Modell
  temperature: 0.7
  max_tokens: 4000
  max_retries: 3
  fallback_models: []           # Komma-getrennte Fallback-Liste

generation:
  default_chapters: 20
  compliance_threshold: 80      # 0–100: Unter diesem Score wird geflagged
  detail_level: standard        # loose, standard, detailed, strict
  story_pace: balanced          # slow, balanced, fast
  chapter_delay: 2.0            # Sekunden zwischen Kapiteln (Rate-Limit-Schutz)
  export_formats: [md, epub]
  backup_enabled: true

advanced:
  cache_responses: true
  max_cache_size_mb: 500
  request_timeout: 300
  use_extended_thinking: false  # Für Reasoning-Modelle
```

### CLI-Override: `~/.config/brokus/cli_settings.json`

Überschreibt ausgewählte Werte aus der settings.yaml – z.B. für OpenRouter-spezifische Modelle:

```json
{
  "model": "openai/gpt-oss-120b:free",
  "fallback_models_str": "meta-llama/llama-3.3-70b-instruct:free, google/gemini-2.0-flash-exp:free"
}
```

### Environment-Variablen

```bash
# API-Keys (per Provider – siehe config/settings.yaml)
export OPENROUTER_API_KEY="sk-or-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Master-Passphrase (optional – für verschlüsselte Secrets)
export BROKUS_MASTER_PASSWORD="your-secure-passphrase"

# Editor für YAML-Bearbeitung (optional)
export EDITOR="code --wait"
```

---

## 🛠️ Entwicklung

### Skripte

```bash
# i18n-Completeness prüfen (alle Keys in allen 6 Sprachen?)
python scripts/check_i18n.py

# Git-Safety-Check (keine uncommitteten Secrets?)
python scripts/check_git_safety.py

# YAML-Labels zu Übersetzungen hinzufügen
python scripts/add_yaml_labels.py
```

### Projekt-Struktur verstehen

- **Neuen Provider hinzufügen**: Eintrag in `config/settings.yaml` unter `providers:` + Übersetzungs-Keys in allen 6 i18n-Dateien
- **Neuen Prompt ändern**: `config/prompts.yaml` – System-Prompts für jede Pipeline-Stage
- **Neues Genre hinzufügen**: `config/genres.yaml` + Eintrag in `GENRES`-Liste in `app_simple.py`
- **Übersetzung hinzufügen**: Key in allen 6 `data/i18n/*.json`-Dateien

### Anforderungen

- Python 3.10+
- Terminal mit ANSI-Color-Unterstützung
- API-Key für den gewählten Provider (oder lokales Modell)

### Python-Dependencies

```
rich>=13.0.0            # Terminal-UI (Panels, Tabellen, Farben)
pyyaml>=6.0             # YAML-Konfiguration
openai>=1.0.0           # OpenAI-kompatible Provider (OpenRouter, Groq, DeepSeek, …)
anthropic>=0.25.0       # Anthropic Claude
ollama>=0.1.0           # Lokale Modelle
ebooklib>=0.18          # EPUB-Export
weasyprint>=60.0        # PDF-Export
markdown>=3.5.0         # Markdown → HTML (für EPUB/PDF)
tiktoken>=0.5.0         # Token-Zählung
aiosqlite>=0.19.0       # Async SQLite
pydantic>=2.0.0         # Datenvalidierung
groq>=0.8.0             # Groq-API
google-generativeai>=0.8.0  # Google Gemini
cohere>=5.0.0           # Cohere-API
mistralai>=0.4.0        # Mistral AI
aiohttp>=3.9.0          # Async HTTP
```

---

## ❓ Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| **Module not found** | `pip install -e .` (oder ggf. `uv pip install -e .`) |
| **API-Key funktioniert nicht** | Provider in Einstellungen prüfen → API-Key neu eingeben (`BROKUS_MASTER_PASSWORD` gesetzt?) |
| **403 Moderation-Fehler** | OpenAI-Modelle auf OpenRouter blockieren manche Inhalte → zu nicht-OpenAI-Modellen wechseln (z.B. `meta-llama/llama-3.3-70b-instruct:free`) |
| **Generation zu langsam** | Cache in Einstellungen aktivieren · Lokales Modell verwenden (Ollama) · Fallback-Modelle konfigurieren |
| **Kapitel weichen von der Idee ab** | Compliance-Schwelle auf 90+ erhöhen · `detail_level` auf `strict` stellen · DNA-Extraktion prüfen |
| **Endlosschleife bei Fallback** | Modell in `fallback_models_str` identisch mit Default-Modell → Einstellungen prüfen, Duplikat entfernen |
| **Update schlägt fehl (PEP 668)** | Arch/Manjaro blockiert systemweites `pip install` → `install.sh` nutzt automatisch `--break-system-packages` oder manuell: `pip install --break-system-packages -e .` |
| **Update schlägt fehl (allgemein)** | Git-Repository vorhanden? → `git status` prüfen · `pip install -e .` manuell ausführen |

---

## 📄 Lizenz

MIT License – siehe [LICENSE](LICENSE) für Details.

---

*Made with ❤️ for writers who dream in terminal green.*
