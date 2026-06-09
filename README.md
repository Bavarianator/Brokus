# brokus – AI-Powered Book Generator

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-purple)

**Create complete novels with AI support – right in your terminal.**

brokus is an intelligent book generator that transforms your ideas into full-length novels through a sophisticated three-layer system: **DNA extraction**, **structured generation**, and **compliance auditing**.

---

## 🚀 Features

### 📖 Intelligent Book Generation
- **DNA System**: Before writing a single word, brokus extracts the immutable "book DNA" from your idea – protagonist, setting, mandatory plot elements, forbidden deviations, and tone. This DNA is embedded in every chapter prompt to prevent story drift.
- **Three-Layer Architecture**:
  1. **DNA Extraction** – Locks the core identity of your book
  2. **Chapter Generation** – Writes chapters with DNA context
  3. **Compliance Audit** – Validates each chapter against the DNA (0-100 score)

### 🤖 33+ AI Providers
- **Cloud**: OpenAI, Anthropic (Claude), Google Gemini, DeepSeek, Groq, Mistral, Cohere, and more
- **Local**: Ollama, LM Studio, LocalAI – fully offline generation
- **Aggregators**: OpenRouter (200+ models with one key), GitHub Models, Hugging Face
- **Custom endpoints**: Connect any OpenAI-compatible API (vLLM, TabbyAPI, LiteLLM Proxy)

### 📚 33 Genres
Each genre comes with specialized style hints:
Fantasy, Horror, Science Fiction, Romance, Thriller, Mystery, Historical Fiction, Adventure, Dystopia, Young Adult, Literary Fiction, Paranormal, Erotica, Comedy, Drama, Action, Post-Apocalyptic, Steampunk, Cyberpunk, Urban Fantasy, Magical Realism, Military, Western, Gothic, Noir, Fairy Tale, Slice of Life, Superhero, Survival, Biography, Children's Book, Satire, Experimental

### 🌍 6 Languages
Full UI translation: **English**, **Deutsch**, **Français**, **Español**, **Nederlands**, **Italiano**

### 📤 Export Options
- **Markdown** (.md) – For editing and version control
- **EPUB** (.epub) – For e-readers
- **PDF** (.pdf) – For printing
- **Word** (.docx) – For editors
- **JSON** (.json) – For developers
- **Plain Text** (.txt) – Universal compatibility

### 🔐 Security
- API keys are **encrypted** and stored in `secrets.enc`
- Optional **master passphrase** adds a password layer protection

### 💾 Project Management
- All books saved in a local SQLite database
- Backup before every generation (configurable)
- Library view with status tracking and word counts
- Pause/Resume generation at any time

---

## ⚡ Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-user/brokus.git
cd brokus

# Install dependencies
pip install -e .

# Run brokus
brokus
```

### First-Time Setup

On first launch, brokus runs an interactive **Setup Wizard**:
1. Choose your language
2. Select an AI provider
3. Pick a model
4. Enter your API key
5. (Optional) Set a master passphrase

That's it – start creating books!

---

## 📖 Usage Modes

### ⚡ Quick Book (3 steps)
```
Idee eingeben → Titel wählen → Genre auswählen → Generieren!
```
Perfect for rapid prototyping and getting a first draft quickly.

### ✨ Masterpiece Mode
Full configuration control:
- Target audience (Children, Young Adult, Adult, Mature)
- Narrative perspective (First person, Third person limited, Omniscient)
- Tense (Present, Past)
- Chapter count (5-50)
- Words per chapter (1,500-3,000)
- Story pace (Slow atmosphere, Balanced, Fast twists)
- Detail level (Loose → Strict fidelity to idea)

### 📖 Library
Browse all saved projects, read chapters, regenerate content, edit manually, and export in multiple formats.

---

## 🎛️ Configuration

All settings are in `config/settings.yaml`:

```yaml
ai:
  provider: anthropic
  model: claude-sonnet-4-5
  temperature: 0.7
  max_tokens: 4000
  max_retries: 3
  request_timeout: 300

generation:
  default_chapters: 20
  default_genre: drama
  compliance_threshold: 80
  auto_export: false
  export_formats: [md, epub]
  detail_level: standard
  story_pace: balanced
  chapter_delay: 2.0
  max_chapter_words: 3000
  min_chapter_words: 1500

advanced:
  cache_responses: true
  max_cache_size_mb: 500
  parallel_chapters: 1

providers:
  # 33+ providers pre-configured
  # Add your own custom endpoints
```

### Environment Variables

```bash
# API Keys (set before running brokus)
export ANTHROPIC_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."

# Optional: Master passphrase for the session
export BROKUS_MASTER_PASSWORD="your-secure-passphrase"
```

---

## 🏗️ Architecture

```
brokus/
├── ai/              # AI client, models, schemas, model discovery
├── core/            # DNA extraction, pipeline orchestration, validation, tracker
├── storage/         # Database, exporter (MD, EPUB, PDF, DOCX, JSON, TXT)
├── tui/             # Terminal UI (simple CLI + prompt_toolkit advanced)
├── utils/           # Logger, crypto, settings loader, i18n
├── config/          # Settings, prompts, genre definitions
├── data/            # SQLite database, exports, backups, i18n translations
└── __main__.py      # CLI entry point (argparse)
```

**Core Modules:**
- `ai/client.py` – Multi-provider AI abstraction (OpenAI, Anthropic, Ollama, etc.)
- `core/dna_extractor.py` – Layer 1: Pre-Generation Lock (DNA extraction)
- `core/pipeline.py` – Orchestrates: DNA → Synopsis → Characters → Chapter Plan → Chapters
- `core/validator.py` – Layer 3: Post-Generation Compliance Audit
- `storage/exporter.py` – Multi-format export (Markdown, EPUB, PDF, DOCX, JSON, TXT)

### The DNA System (Innovation)

The core innovation is the **three-layer compliance system**:

1. **Pre-Generation Lock (DNA Extraction)**
   - Analyzes your book idea
   - Extracts: protagonist details, setting, mandatory elements, forbidden deviations, themes, tone
   - Stored as immutable JSON

2. **In-Generation Lock (DNA in Every Prompt)**
   - Every chapter prompt includes the full DNA block
   - AI is constantly reminded of the book identity
   - Prevents gradual drift away from the original concept

3. **Post-Generation Audit (Compliance Check)**
   - Each chapter is validated against the DNA
   - Score 0-100: does it follow the protagonist age? setting? mandatory elements?
   - Below threshold? Chapter is flagged for regeneration

---

## 🛠️ Development

### Run Tests
```bash
# Check i18n completeness
python scripts/check_i18n.py

# Validate git safety
python scripts/check_git_safety.py

# Add YAML labels
python scripts/add_yaml_labels.py
```

### Add a New Provider

1. Add provider config to `config/settings.yaml` under `providers:`
2. Add translation keys to all 6 language files
3. Implement client in `brokus/ai/client.py`

---

## 📋 Requirements

- Python 3.10+
- Terminal with ANSI color support
- API key for your chosen AI provider (or local model)

### Python Dependencies

```
rich>=13.0.0
prompt-toolkit>=3.0.0
pyyaml>=6.0
openai>=1.0.0
anthropic>=0.25.0
ollama>=0.1.0
ebooklib>=0.18
weasyprint>=60.0
markdown>=3.5.0
tiktoken>=0.5.0
aiosqlite>=0.19.0
pydantic>=2.0.0
groq>=0.8.0
google-generativeai>=0.8.0
cohere>=5.0.0
mistralai>=0.4.0
aiohttp>=3.9.0
```

---

## 🎨 Screenshots

```
╔══════════════════════════════════════════════════════════╗
║                     🏠 BROKUS                            ║
║          AI-powered book generator                       ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║    ⚡  Quick book – enter an idea and go!                ║
║                                                          ║
║    ✨  Masterpiece – configure every detail              ║
║                                                          ║
║    📖  Library – read saved books                        ║
║                                                          ║
║    ⚙️   Settings – API key, model, export                ║
║                                                          ║
║    🚪  Quit                                              ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

---

## 📄 License

MIT License – see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Anthropic** – Claude API
- **OpenAI** – GPT models
- **Ollama** – Local AI infrastructure
- **prompt_toolkit** – Terminal UI framework
- **Rich** – Beautiful terminal output

---

## 🐛 Troubleshooting

**Q: "Module not found" errors**
```bash
pip install -e .
```

**Q: API key not working**
- Check environment variable name matches provider
- Verify key has not expired
- Try setting key directly in settings UI

**Q: Generation is slow**
- Enable cache in settings (caches AI responses)
- Use local models (Ollama, LM Studio) for offline speed
- Increase `max_retries` for rate limit handling

**Q: Chapters don't follow my idea**
- Increase `compliance_threshold` to 90+
- Check the DNA extraction output in logs
- Regenerate with specific chapter

---

*Made with ❤️ for writers who dream in terminal green.*