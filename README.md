<div align="center">
  <img src="https://img.shields.io/badge/version-1.1.1-blue?style=flat-square" alt="Version">
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
  <p><strong>AI-powered book generator – create complete novels in your terminal.</strong></p>
  <p><em>Three-layer AI architecture · 33+ providers · 33 genres · 6 languages · 6 export formats · 10+ CLI commands</em></p>
</div>

---

<br>

**brokus** turns your book idea into a complete novel – driven by an innovative **three-layer system**: DNA extraction, structured chapter generation, and automated compliance checking.

Write your idea, choose a genre and length, and brokus generates a coherent book chapter by chapter – with automatic fallback models for rate limits, a built-in update system, and support for 33+ AI providers.

---

## 📦 Features

### 🧬 DNA System (Core Innovation)

Before brokus writes a single word, it extracts the **immutable DNA** of your book idea:

| Layer | Phase | Description |
|-------|-------|-------------|
| **1. Pre-Generation Lock** | DNA Extraction | Extracts protagonist, setting, mandatory elements, taboos, tone – stored as JSON |
| **2. In-Generation Lock** | Every chapter prompt | DNA block embedded into every prompt → no thematic drift |
| **3. Post-Generation Audit** | Compliance check | Each chapter validated against the DNA (Score 0–100). Below threshold → re-generation flag |

### 🤖 Multi-Provider AI Engine

**33+ providers**, unified through a single client abstraction:

<table>
<tr><th>Cloud</th><th>Aggregators</th><th>Local</th><th>Custom</th></tr>
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
<b>OpenRouter</b> – 200+ models with one key<br>
<b>GitHub Models</b> – Free (rate-limited)<br>
<b>Hugging Face</b> – Open-source models<br>
<b>Ollama Cloud</b> – Hosted
</td><td>
<b>Ollama</b> – Fully offline, GPU required<br>
<b>LM Studio</b> – GUI, OpenAI-compatible<br>
<b>LocalAI</b> – Docker-based
</td><td>
<b>OpenAI-compatible</b> – Any API endpoint<br>
(vLLM, TabbyAPI, LiteLLM Proxy, …)
</td></tr>
</table>

### 🧠 Stage-Specific Model Chains

Each pipeline stage can use a different AI model – configured via OpenRouter's free-tier models by default:

| Stage | Description | Default Model |
|-------|-------------|---------------|
| **DNA** | Book DNA extraction | Primary provider model |
| **Core Elements** | Characters, setting, themes | Primary provider model |
| **Synopsis** | Story structure | Gemini Flash → Llama 3.3 → Kimi → DeepSeek → Mistral |
| **Characters** | Detailed character profiles | Llama 3.3 → Gemini Flash → Kimi → DeepSeek → Mistral |
| **Chapter Plan** | Chapter-by-chapter outline | Gemini Flash → Llama 3.3 → Kimi → DeepSeek → Mistral |
| **Chapter Writing** | Full chapter generation | Mistral → Llama 3.3 → DeepSeek → Gemini Flash → Kimi |

### 📚 33 Genres with Specialized Style Hints

Fantasy · Horror · Science Fiction · Romance · Thriller · Mystery · Historical Fiction · Adventure · Dystopia · Young Adult · Literary Fiction · Paranormal · Erotica · Comedy · Drama · Action · Post-Apocalyptic · Steampunk · Cyberpunk · Urban Fantasy · Magical Realism · Military · Western · Gothic · Noir · Fairy Tale · Slice of Life · Superhero · Survival · Biography · Children's Book · Satire · Experimental

### 🌍 6 Languages (UI & Generation)

| Language | Code | Translation Status |
|----------|------|-------------------|
| Deutsch | `de` | ✅ Complete (244 keys) |
| English | `en` | ✅ Complete (244 keys) |
| Français | `fr` | ✅ Complete (244 keys) |
| Español | `es` | ✅ Complete (244 keys) |
| Nederlands | `nl` | ✅ Complete (244 keys) |
| Italiano | `it` | ✅ Complete (244 keys) |

All 6 language files are kept **fully in sync** – unused keys are automatically cleaned up to maintain consistency.

### 📤 Export Formats

| Format | Library | Use Case |
|--------|---------|----------|
| **Markdown** (`.md`) | native | Editing, version control |
| **EPUB** (`.epub`) | `ebooklib` | E-readers (Kindle, Tolino) |
| **PDF** (`.pdf`) | `weasyprint` | Print, sharing |
| **Word** (`.docx`) | native (ZIP/XML) | Editing, publishers |
| **JSON** (`.json`) | native | Development, API |
| **Plain Text** (`.txt`) | native | Universal |

### ☁ Cloud-Upload

Upload finished books directly from the terminal – **three methods**:

| Method | Effort | Providers |
|---------|--------------|----------|
| **Nextcloud v2** ⭐ | 🔵 30s – Just URL + Browser login | Nextcloud (WebDAV) |
| **Google Drive** | 🟡 5min – Client ID + Secret (one-time) | Google Drive API |
| **rclone** | 🟢 One-time – `rclone config` + 40+ providers | GDrive, OneDrive, S3, Dropbox, … |

#### 🔵 Nextcloud – Login Flow v2 (empfohlen)

Browser-based app-password generation (Nextcloud built-in, no Keycloak required):

```
Setup:  URL eingeben → Browser öffnet sich → Einloggen + Erlauben ✅
Upload: WebDAV + automatischer Share-Link
```

Alternativ: App-Password manuell (Nextcloud → Einstellungen → Sicherheit)

#### 🟡 Google Drive – Einfacher OAuth Flow

Leichtgewichtig (kein `google-api-python-client`):

```
Setup:  Client ID + Secret eingeben → Browser öffnet sich → Erlauben ✅
Upload: Google Drive REST API + `webViewLink`
```

> One-time setup at Google Cloud Console: Create project → Enable Drive API → OAuth 2.0 Desktop credentials

#### 🟢 rclone – Universell (40+ Anbieter)

Systemweites Tool, kein brokus-internes Auth:

```
Setup:  rclone installieren + `rclone config` → Remote auswählen ✅
Upload: `rclone copy` → GDrive, OneDrive, S3, Dropbox, Nextcloud, …
```

```bash
# Installation (auto-installed by install.sh / bin/brokus)
brew install rclone    # macOS
apt install rclone    # Debian/Ubuntu
```

> **Auto-Install**: `install.sh` and `bin/brokus` detect missing rclone and offer to install it automatically using your system package manager (brew/apt/pacman/dnf).

#### Gemeinsame Features

- **Auto-upload** after export (optional)
- **Auto-folder creation** on the remote
- **Share-link generation** (Nextcloud OCS / Google Drive `webViewLink`)
- **CLI flags**: `--cloud-setup`, `--cloud-status`, `--no-cloud`
- **Encrypted credentials**: Nextcloud + GDrive creds in `secrets.enc` (AES-256-GCM); rclone nutzt eigene Config
- **Batch upload**: Single book → all configured providers

### 🔐 Security

- API keys are **encrypted** and stored in `secrets.enc` (machine-bound key)
- Cloud credentials are stored **inside the same encrypted file** as API keys
- Optional **master passphrase** for additional password protection
- Re-encryption on passphrase rotation

### 🛡️ Moderation & Fallback

- **ModerationError**: On 403 moderation (e.g. OpenRouter/OpenInference) → immediate abort, no pointless fallback
- **Rate-Limit Fallback**: Models in a configurable chain, no self-fallback (deduplicated)
- **Automatic Retry**: With backoff, configurable

### 🔄 Update System

- **Startup check**: Silent check on program start (5s timeout, only visible when update available)
- **Manual check**: Settings → Advanced → "🔄 Check & install update"
- **Installation**: Automatic via `git pull` + `pip install -e .` with live output streaming
- **Version detection**: Uses `git describe --tags --abbrev=0` (supports semver and non-semver tags)
- **PEP 668 support**: Automatic `--break-system-packages` fallback on Arch Linux
- **Source**: GitHub Releases API (with Tags API fallback)

### 🛡️ Fallback Chain Control

Brokus uses **fallback model chains** per pipeline stage to handle rate limits and timeouts. You can control this behavior:

| Setting | Effect |
|---------|--------|
| **Enabled** (default) | Each stage tries models from its chain on failure (rate-limit → next model) |
| **Disabled** | Only the configured primary model is used – no hardcoded fallbacks |

Configure via: `Settings → Generation → [9] Fallback-Ketten deaktivieren`

> Useful when you want predictable costs, or when using local models that never hit rate limits.

### 📊 Project Management

- All books in a local SQLite database (`data/projects.db`)
- Automatic backups before each generation
- Library with status tracking, word counts, compliance scores
- Pause/Resume at the pipeline level (chapter granularity)
- Export with format selection after generation

### 🚀 Self-Installer (No Setup Required)

- `bin/brokus` auto-installs dependencies, creates a symlink, and adds `~/.local/bin` to PATH on first run
- No package manager, no `pip install` needed – just `./bin/brokus`
- Also ships `install.sh` as a convenience wrapper for traditional setups

### ⌨️ CLI Command Reference

| Command | Description |
|---------|-------------|
| `brokus` | Interactive mode – main menu with all options |
| `brokus --version` | Show version and exit |
| `brokus --tui` | (Legacy) Textual TUI mode |
| `brokus --set-master-password` | Set / rotate master passphrase |
| `brokus --cloud-setup` | Directly open cloud upload configuration wizard |
| `brokus --cloud-status` | Show connection status of all configured cloud providers |
| `BROKUS_NO_CLOUD=1 brokus` | Disable cloud upload prompts for this session |
| `python -m brokus` | Run without installation |
| `./bin/brokus` | Auto-installing wrapper – installs deps + creates symlink on first run |
| `./install.sh --uninstall` | Remove symlink and clean up |
| `BROKUS_MASTER_PASSWORD="..." brokus` | Use master passphrase from environment |

---

## ⚡ Quick Start

### Installation

#### 🚀 Recommended: Zero-Install (just clone and run)

```bash
git clone https://github.com/Bavarianator/Brokus.git
cd brokus
./bin/brokus                     # Auto-installs everything on first run
```

That's it. On first run, `bin/brokus`:
- Installs Python dependencies (`pip install -e .` with PEP 668 fallback)
- Creates a symlink: `bin/brokus` → `~/.local/bin/brokus`
- Adds `~/.local/bin` to your PATH (bashrc/zshrc + current session)
- Starts the app

After the first run, `brokus` works as a global command.

> **⚠️ Note:** `brokus/` **(with trailing slash) is the Python package** – a directory, not an executable.
> The actual executable is **`bin/brokus`**. The auto-installer creates a symlink from `bin/brokus` → `~/.local/bin/brokus`
> so you can run `brokus` from anywhere.

#### 📦 Alternative: install.sh

```bash
./install.sh                     # Installs deps + symlink + PATH
brokus                           # Global command after install
```

#### 🐍 Also possible: pip install

```bash
pip install -e .                 # Traditional Python installation
brokus
```

```bash
# Or run without any installation
python -m brokus
```

#### 🗑️ Uninstall

```bash
./install.sh --uninstall         # Removes symlink
pip uninstall brokus              # Removes Python package
```

### First-Run Wizard

On first start, brokus guides you through an interactive **setup wizard**:

1. **Choose language** – English, Deutsch, Français, Español, Nederlands, Italiano
2. **Choose AI provider** – OpenRouter, OpenAI, Anthropic, Ollama, … (33+)
3. **Choose model** – Live discovery from the API endpoint
4. **Enter API key** – Encrypted and stored securely
5. **(Optional) Master passphrase** – Extra protection for your keys

> **Tip**: With **OpenRouter**, a single API key gives you access to 200+ models – perfect for testing different models without managing multiple keys.

---

## 📖 Usage Modes

### ⚡ Quick Book (3 steps)

```
Enter idea → Choose title + genre → Set length → Generate!
```

Optimized for fast results: type your idea, pick a genre, set the length – done.

### ✨ Masterpiece (11 steps)

Full control over every parameter:

| Step | Parameter | Options |
|------|-----------|---------|
| 1 | Book idea | Free text |
| 2 | Title | Free text |
| 3 | Genre | 33 genres |
| 4 | Target audience | Children · Teens · Young Adult · Adults |
| 5 | Language | 12 languages |
| 6 | AI model | From selected provider |
| 7 | Narrative perspective | First person, third person (limited/omniscient), epistolary, … |
| 8 | Tone & mood | Dark · Suspenseful · Warm · Humorous · Epic |
| 9 | Book length | Mini story (1,500 words) to Mega novel (150,000 words) |
| 10 | Important info | Mandatory elements, facts, locations |
| 11 | Detail level | Loose · Standard · Detailed · Strict |

### 📖 Library

- All saved projects displayed as a table with status, word count, progress
- Read chapters and navigate (next/previous)
- Status: ✅ completed · ⏳ generating · ❌ failed · 📝 draft

---

## 🏗️ Architecture

```
brokus/
├── ai/                # Multi-provider AI client, models, schemas, discovery
│   ├── client.py      #   Abstraction layer (OpenAI, Anthropic, Ollama, …)
│   ├── model_discovery.py  # Live model list from API endpoint
│   ├── prompts.py     #   Prompt loader (from config/prompts.yaml)
│   ├── schemas.py     #   Pydantic models for structured outputs
│   └── models.py      #   Provider registry
├── core/              # Pipeline, DNA extraction, validation, tracker
│   ├── cloud/         #   ☁ Cloud-Upload (Nextcloud, Google Drive, rclone)
│   │   ├── base.py        #   ABC + UploadResult dataclass
│   │   ├── nextcloud.py   #   WebDAV + Login Flow v2 + OCS Share API
│   │   ├── gdrive.py      #   Google Drive OAuth 2.0 (REST API)
│   │   ├── rclone.py      #   rclone subprocess wrapper (40+ Anbieter)
│   │   ├── oauth.py       #   Keycloak OAuth2 helper
│   │   └── manager.py     #   Config, orchestration, setup wizard
│   ├── dna_extractor.py  # Layer 1: DNA extraction (Pre-Generation Lock)
│   ├── pipeline.py    #   Orchestration: DNA → Synopsis → Characters → Plan → Chapters
│   ├── validator.py   #   Layer 3: Compliance audit (Post-Generation)
│   ├── extractor.py   #   Core element extraction (Characters, Setting, …)
│   ├── context.py     #   Context management for chapter prompts
│   └── tracker.py     #   Compliance tracker with score calculation
├── storage/           # Database, exporter
│   ├── database.py    #   Async SQLite (aiosqlite)
│   └── exporter.py    #   Multi-format export (MD, EPUB, PDF, DOCX, JSON, TXT)
├── tui/               # Terminal User Interface
│   └── app_simple.py  #   Rich-based CLI (panels, tables, colors)
├── utils/             # Utility modules
│   ├── i18n.py        #   Internationalization (6 languages, 244 keys)
│   ├── crypto.py      #   AES-256 encryption for API keys
│   ├── updater.py     #   GitHub-based update system
│   ├── settings_loader.py  # YAML configuration load/save
│   ├── opener.py      #   System document reader
│   ├── logger.py      #   Structured logging
│   └── tokens.py      #   Token counting
├── config/            # YAML configuration
│   ├── settings.yaml  #   Main configuration (provider, AI, generation, UI)
│   ├── prompts.yaml   #   System prompts for all pipeline stages
│   └── genres.yaml    #   Genre definitions + style hints
├── data/              # Runtime data
│   ├── projects.db    #   SQLite database
│   ├── i18n/          #   Translation files (6 languages, 244 keys each)
│   ├── books/         #   Exported books (created at runtime)
│   └── backups/       #   Automatic DB backups (created at runtime)
├── bin/
│   └── brokus         #   Auto-installing shell wrapper
├── install.sh         #   Convenience installer (symlink + deps + PATH)
└── scripts/           #   Development utilities
```

### Pipeline Flow

```
Book Idea
    │
    ▼
┌─────────────────┐
│  DNA Extraction  │  ← Protagonist, Setting, Mandatory elements, Taboos, Tone
│  (Layer 1)       │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Core Elements   │  ← Characters, arcs, world details
└────────┬────────┘
         ▼
┌─────────────────┐
│  Synopsis        │  ← Overall story structure
└────────┬────────┘
         ▼
┌─────────────────┐
│  Characters      │  ← Detailed character descriptions
└────────┬────────┘
         ▼
┌─────────────────┐
│  Chapter Plan    │  ← Chapter-by-chapter structure
└────────┬────────┘
         ▼
  ┌──────┴──────┐
  ▼             ▼
Chapter 1   Chapter 2  …  Chapter N
  │             │
  ▼             ▼
┌─────────────────────────┐
│  Compliance Check        │  ← Layer 3: Score 0–100 against DNA
│  (Layer 3)               │
└─────────────────────────┘
```

### Fallback Strategy

Each pipeline stage has its own model chain. If a model fails (rate limit, timeout), the next model in the chain is tried automatically. On **moderation (403)**, the entire process aborts immediately – no pointless fallback.

```
Pipeline Stage → model_A:free → model_B:free → model_C:free → … → Fallback text
                                ↑
                     Rate-Limit → next model
                     403/Auth   → immediate abort (ModerationError)
```

---

## 🎛️ Configuration

### Central YAML: `config/settings.yaml`

```yaml
ai:
  provider: anthropic           # Default provider
  model: claude-sonnet-4-5      # Default model
  temperature: 0.7
  max_tokens: 4000
  max_retries: 3
  fallback_models: []           # Comma-separated fallback list

generation:
  default_chapters: 20
  compliance_threshold: 80      # 0–100: Below this score → flagged
  detail_level: standard        # loose, standard, detailed, strict
  story_pace: balanced          # slow, balanced, fast
  chapter_delay: 2.0            # Seconds between chapters (rate-limit protection)
  export_formats: [md, epub]
  backup_enabled: true

advanced:
  cache_responses: true
  max_cache_size_mb: 500
  request_timeout: 300
  use_extended_thinking: false  # For reasoning models
```

### CLI Override: `~/.config/brokus/cli_settings.json`

Overrides selected values from settings.yaml – useful for OpenRouter-specific models:

```json
{
  "model": "openai/gpt-oss-120b:free",
  "fallback_models_str": "meta-llama/llama-3.3-70b-instruct:free, google/gemini-2.0-flash-exp:free"
}
```

### Environment Variables

```bash
# API keys (per provider – see config/settings.yaml)
export OPENROUTER_API_KEY="sk-or-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Master passphrase (optional – for encrypted secrets)
export BROKUS_MASTER_PASSWORD="your-secure-passphrase"

# Python interpreter override (optional)
export BROKUS_PYTHON="python3.12"

# Editor for YAML editing (optional)
export EDITOR="code --wait"
```

---

## 🛠️ Development

### Scripts

```bash
# Check i18n completeness (all keys in all 6 languages)
python scripts/check_i18n.py

# Git safety check (no committed secrets?)
python scripts/check_git_safety.py

# Add YAML labels to translations
python scripts/add_yaml_labels.py
```

### Adding Features

- **New provider**: Add entry in `config/settings.yaml` under `providers:` + translation keys in all 6 i18n files
- **New prompt**: Edit `config/prompts.yaml` – system prompts for each pipeline stage
- **New genre**: Add to `config/genres.yaml` + entry in `GENRES` list in `app_simple.py`
- **New translation**: Add key in all 6 `data/i18n/*.json` files

### Requirements

- Python 3.10+
- Terminal with ANSI color support
- API key for your chosen provider (or local model)

### Python Dependencies

```
rich>=13.0.0            # Terminal UI (panels, tables, colors)
pyyaml>=6.0             # YAML configuration
openai>=1.0.0           # OpenAI-compatible providers (OpenRouter, Groq, DeepSeek, …)
anthropic>=0.25.0       # Anthropic Claude
ollama>=0.1.0           # Local models
ebooklib>=0.18          # EPUB export
weasyprint>=60.0        # PDF export
markdown>=3.5.0         # Markdown → HTML (for EPUB/PDF)
tiktoken>=0.5.0         # Token counting
aiosqlite>=0.19.0       # Async SQLite
pydantic>=2.0.0         # Data validation
groq>=0.8.0             # Groq API
google-generativeai>=0.8.0  # Google Gemini
cohere>=5.0.0           # Cohere API
mistralai>=0.4.0        # Mistral AI
aiohttp>=3.9.0          # Async HTTP

# Cloud-Upload (optional)
requests>=2.31.0          # Nextcloud (WebDAV) + Google Drive (REST API)
```

> **Note**: Cloud upload needs only `requests` (always installed).
> Google Drive no longer requires `google-api-python-client` – uses simple REST API calls.
> rclone is external – auto-installed during `install.sh` / `bin/brokus` setup, or manually: `brew install rclone` / `apt install rclone`.
> Cloud credentials are stored encrypted inside `secrets.enc` alongside API keys.

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| **Module not found** | `pip install -e .` (or `uv pip install -e .`) |
| **API key not working** | Check provider in settings → re-enter API key (`BROKUS_MASTER_PASSWORD` set?) |
| **403 Moderation error** | OpenAI models on OpenRouter block some content → switch to non-OpenAI models (e.g. `meta-llama/llama-3.3-70b-instruct:free`) |
| **Generation too slow** | Enable cache in settings · Use local model (Ollama) · Configure fallback models |
| **Chapters drift from idea** | Increase compliance threshold to 90+ · Set `detail_level` to `strict` · Check DNA extraction |
| **Fallback loop** | Model in `fallback_models_str` identical to default model → check settings, remove duplicate |
| **Update stuck** | pip output is now live-streamed with a 300s timeout – should no longer hang. If it does, run manually: `pip install --break-system-packages -e .` |
| **Update fails (PEP 668)** | Arch/Manjaro blocks system-wide `pip install` → `install.sh` uses `--break-system-packages` automatically. Manual: `pip install --break-system-packages -e .` |
| **Update fails (general)** | Git repository present? → `git status` · `pip install -e .` manually |
| **Update finds same release repeatedly** | Fixed: Version is now detected via `git describe --tags --abbrev=0`, not hardcoded |
| **Cloud-Upload not offered** | Enable in Settings → Advanced → Cloud-Upload |
| **Nextcloud connection fails** | Generate an app-password (Nextcloud → Settings → Security) – normal password won't work with WebDAV · Or use Login Flow v2 (browser-based, kein App-Passwort nötig) |
| **Google Drive auth fails** | Create OAuth 2.0 Desktop credentials in Google Cloud Console → paste Client ID + Secret · Token is cached in `~/.brokus/gdrive_token.json` |
| **Cloud credentials still ask** | Credentials are stored encrypted in `secrets.enc` – if you rotated the master passphrase, re-save the cloud config |
| **rclone not found** | Install rclone: `brew install rclone` (macOS) / `apt install rclone` (Debian) / https://rclone.org/install/ |
| **No rclone remotes listed** | Run `rclone config` to set up a remote (supports 40+ providers: GDrive, Nextcloud, OneDrive, S3, …)

---

## 📄 License

MIT License – see [LICENSE](LICENSE) for details.

---

*Made with ❤️ for writers who dream in terminal green.*
