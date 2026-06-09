"""One-shot helper to add genre.* and provider.* keys to all i18n files.

Usage: python scripts/add_yaml_labels.py
"""
import json
from pathlib import Path

I18N_DIR = Path("data/i18n")

# Genre names: key -> translations (de, en, fr, es, it, nl)
GENRE_NAMES = {
    "fantasy": {"de": "Fantasy", "en": "Fantasy", "fr": "Fantaisie", "es": "Fantasía", "it": "Fantasy", "nl": "Fantasy"},
    "horror": {"de": "Horror", "en": "Horror", "fr": "Horreur", "es": "Terror", "it": "Horror", "nl": "Horror"},
    "scifi": {"de": "Science Fiction", "en": "Science Fiction", "fr": "Science-Fiction", "es": "Ciencia ficción", "it": "Fantascienza", "nl": "Sciencefiction"},
    "romance": {"de": "Romance / Liebesroman", "en": "Romance", "fr": "Romance", "es": "Romance", "it": "Romanzo rosa", "nl": "Romantiek"},
    "thriller": {"de": "Thriller", "en": "Thriller", "fr": "Thriller", "es": "Thriller", "it": "Thriller", "nl": "Thriller"},
    "mystery": {"de": "Mystery / Krimi", "en": "Mystery / Crime", "fr": "Mystère / Policier", "es": "Misterio / Crimen", "it": "Giallo", "nl": "Mysterie / Misdaad"},
    "historical_fiction": {"de": "Historischer Roman", "en": "Historical Fiction", "fr": "Roman historique", "es": "Novela histórica", "it": "Romanzo storico", "nl": "Historische roman"},
    "adventure": {"de": "Abenteuer", "en": "Adventure", "fr": "Aventure", "es": "Aventura", "it": "Avventura", "nl": "Avontuur"},
    "dystopian": {"de": "Dystopie", "en": "Dystopia", "fr": "Dystopie", "es": "Distopía", "it": "Distopia", "nl": "Dystopie"},
    "young_adult": {"de": "Young Adult", "en": "Young Adult", "fr": "Young Adult", "es": "Juvenil", "it": "Young Adult", "nl": "Young Adult"},
    "literary_fiction": {"de": "Literarische Fiktion", "en": "Literary Fiction", "fr": "Fiction littéraire", "es": "Ficción literaria", "it": "Narrativa letteraria", "nl": "Literaire fictie"},
    "paranormal": {"de": "Paranormal", "en": "Paranormal", "fr": "Paranormal", "es": "Paranormal", "it": "Paranormale", "nl": "Paranormaal"},
    "erotica": {"de": "Erotica", "en": "Erotica", "fr": "Érotique", "es": "Erótica", "it": "Erotica", "nl": "Erotiek"},
    "comedy": {"de": "Comedy / Humor", "en": "Comedy / Humor", "fr": "Comédie / Humour", "es": "Comedia / Humor", "it": "Commedia / Umorismo", "nl": "Komedie / Humor"},
    "drama": {"de": "Drama", "en": "Drama", "fr": "Drame", "es": "Drama", "it": "Dramma", "nl": "Drama"},
    "action": {"de": "Action", "en": "Action", "fr": "Action", "es": "Acción", "it": "Azione", "nl": "Actie"},
    "post_apocalyptic": {"de": "Post-Apokalypse", "en": "Post-Apocalyptic", "fr": "Post-apocalyptique", "es": "Post-apocalíptico", "it": "Post-apocalittico", "nl": "Post-apocalyptisch"},
    "steampunk": {"de": "Steampunk", "en": "Steampunk", "fr": "Steampunk", "es": "Steampunk", "it": "Steampunk", "nl": "Steampunk"},
    "cyberpunk": {"de": "Cyberpunk", "en": "Cyberpunk", "fr": "Cyberpunk", "es": "Cyberpunk", "it": "Cyberpunk", "nl": "Cyberpunk"},
    "urban_fantasy": {"de": "Urban Fantasy", "en": "Urban Fantasy", "fr": "Urban Fantasy", "es": "Fantasía urbana", "it": "Urban Fantasy", "nl": "Urban Fantasy"},
    "magical_realism": {"de": "Magischer Realismus", "en": "Magical Realism", "fr": "Réalisme magique", "es": "Realismo mágico", "it": "Realismo magico", "nl": "Magisch realisme"},
    "military": {"de": "Military / Kriegsroman", "en": "Military / War", "fr": "Militaire / Guerre", "es": "Militar / Bélico", "it": "Militare / Guerra", "nl": "Militair / Oorlog"},
    "western": {"de": "Western", "en": "Western", "fr": "Western", "es": "Western", "it": "Western", "nl": "Western"},
    "gothic": {"de": "Gothic", "en": "Gothic", "fr": "Gothique", "es": "Gótico", "it": "Gotico", "nl": "Gotisch"},
    "noir": {"de": "Noir / Hardboiled", "en": "Noir / Hardboiled", "fr": "Noir / Hardboiled", "es": "Noir / Hardboiled", "it": "Noir / Hardboiled", "nl": "Noir / Hardboiled"},
    "fairy_tale": {"de": "Märchen / Fairy Tale", "en": "Fairy Tale", "fr": "Conte de fées", "es": "Cuento de hadas", "it": "Fiaba", "nl": "Sprookje"},
    "slice_of_life": {"de": "Slice of Life", "en": "Slice of Life", "fr": "Tranche de vie", "es": "Costumbrista", "it": "Slice of Life", "nl": "Slice of Life"},
    "superhero": {"de": "Superhelden", "en": "Superhero", "fr": "Super-héros", "es": "Superhéroe", "it": "Supereroe", "nl": "Superheld"},
    "survival": {"de": "Survival", "en": "Survival", "fr": "Survie", "es": "Supervivencia", "it": "Sopravvivenza", "nl": "Overleven"},
    "biography": {"de": "Biographie / Memoir", "en": "Biography / Memoir", "fr": "Biographie / Mémoires", "es": "Biografía / Memorias", "it": "Biografia / Memorie", "nl": "Biografie / Memoires"},
    "children": {"de": "Kinderbuch", "en": "Children's Book", "fr": "Livre pour enfants", "es": "Libro infantil", "it": "Libro per bambini", "nl": "Kinderboek"},
    "satire": {"de": "Satire", "en": "Satire", "fr": "Satire", "es": "Sátira", "it": "Satira", "nl": "Satire"},
    "experimental": {"de": "Experimentell", "en": "Experimental", "fr": "Expérimental", "es": "Experimental", "it": "Sperimentale", "nl": "Experimenteel"},
}

# Provider names + notes
PROVIDER_LABELS = {
    "ollama_local": {
        "name": {"de": "Ollama (Lokal)", "en": "Ollama (Local)", "fr": "Ollama (Local)", "es": "Ollama (Local)", "it": "Ollama (Locale)", "nl": "Ollama (Lokaal)"},
        "note": {"de": "GPU erforderlich, komplett offline", "en": "GPU required, fully offline", "fr": "GPU requis, entièrement hors ligne", "es": "Requiere GPU, totalmente sin conexión", "it": "GPU richiesta, completamente offline", "nl": "GPU vereist, volledig offline"},
    },
    "ollama_cloud": {
        "name": {"de": "Ollama Cloud", "en": "Ollama Cloud", "fr": "Ollama Cloud", "es": "Ollama Cloud", "it": "Ollama Cloud", "nl": "Ollama Cloud"},
        "note": {"de": "Keine GPU nötig", "en": "No GPU needed", "fr": "Pas de GPU nécessaire", "es": "Sin GPU", "it": "Nessuna GPU richiesta", "nl": "Geen GPU nodig"},
    },
    "lmstudio": {
        "name": {"de": "LM Studio (Lokal)", "en": "LM Studio (Local)", "fr": "LM Studio (Local)", "es": "LM Studio (Local)", "it": "LM Studio (Locale)", "nl": "LM Studio (Lokaal)"},
        "note": {"de": "GUI, OpenAI-kompatibel, offline", "en": "GUI, OpenAI-compatible, offline", "fr": "GUI, compatible OpenAI, hors ligne", "es": "GUI, compatible con OpenAI, sin conexión", "it": "GUI, compatibile OpenAI, offline", "nl": "GUI, OpenAI-compatibel, offline"},
    },
    "localai": {
        "name": {"de": "LocalAI", "en": "LocalAI", "fr": "LocalAI", "es": "LocalAI", "it": "LocalAI", "nl": "LocalAI"},
        "note": {"de": "Docker, OpenAI-kompatibel", "en": "Docker, OpenAI-compatible", "fr": "Docker, compatible OpenAI", "es": "Docker, compatible con OpenAI", "it": "Docker, compatibile OpenAI", "nl": "Docker, OpenAI-compatibel"},
    },
    "openai": {"name": {"de": "OpenAI", "en": "OpenAI", "fr": "OpenAI", "es": "OpenAI", "it": "OpenAI", "nl": "OpenAI"}},
    "anthropic": {
        "name": {"de": "Anthropic (Claude)", "en": "Anthropic (Claude)", "fr": "Anthropic (Claude)", "es": "Anthropic (Claude)", "it": "Anthropic (Claude)", "nl": "Anthropic (Claude)"},
        "note": {"de": "200k Kontext-Fenster", "en": "200k context window", "fr": "Fenêtre de contexte 200k", "es": "Ventana de contexto de 200k", "it": "Finestra di contesto 200k", "nl": "Contextvenster van 200k"},
    },
    "google": {
        "name": {"de": "Google Gemini", "en": "Google Gemini", "fr": "Google Gemini", "es": "Google Gemini", "it": "Google Gemini", "nl": "Google Gemini"},
        "note": {"de": "1M Token Kontext-Fenster", "en": "1M token context window", "fr": "Fenêtre de contexte 1M tokens", "es": "Ventana de contexto de 1M tokens", "it": "Finestra di contesto 1M token", "nl": "Contextvenster van 1M tokens"},
    },
    "xai": {
        "name": {"de": "xAI (Grok)", "en": "xAI (Grok)", "fr": "xAI (Grok)", "es": "xAI (Grok)", "it": "xAI (Grok)", "nl": "xAI (Grok)"},
        "note": {"de": "Witzig, kreativ, 2M Kontext", "en": "Witty, creative, 2M context", "fr": "Spirituel, créatif, contexte 2M", "es": "Ingenioso, creativo, contexto 2M", "it": "Arguto, creativo, contesto 2M", "nl": "Grappig, creatief, 2M context"},
    },
    "openrouter": {
        "name": {"de": "OpenRouter", "en": "OpenRouter", "fr": "OpenRouter", "es": "OpenRouter", "it": "OpenRouter", "nl": "OpenRouter"},
        "note": {"de": "Ein Key für 200+ Modelle", "en": "One key for 200+ models", "fr": "Une clé pour 200+ modèles", "es": "Una clave para 200+ modelos", "it": "Una chiave per 200+ modelli", "nl": "Eén sleutel voor 200+ modellen"},
    },
    "github_models": {
        "name": {"de": "GitHub Models", "en": "GitHub Models", "fr": "GitHub Models", "es": "GitHub Models", "it": "GitHub Models", "nl": "GitHub Models"},
        "note": {"de": "GitHub-Personal-Access-Token genügt", "en": "GitHub Personal Access Token is enough", "fr": "Un Personal Access Token GitHub suffit", "es": "Basta con un Personal Access Token de GitHub", "it": "Basta un Personal Access Token di GitHub", "nl": "GitHub Personal Access Token is voldoende"},
    },
    "groq": {
        "name": {"de": "Groq", "en": "Groq", "fr": "Groq", "es": "Groq", "it": "Groq", "nl": "Groq"},
        "note": {"de": "⚡ 500+ Tokens/Sekunde", "en": "⚡ 500+ tokens/second", "fr": "⚡ 500+ tokens/seconde", "es": "⚡ 500+ tokens/segundo", "it": "⚡ 500+ token/secondo", "nl": "⚡ 500+ tokens/seconde"},
    },
    "cerebras": {
        "name": {"de": "Cerebras", "en": "Cerebras", "fr": "Cerebras", "es": "Cerebras", "it": "Cerebras", "nl": "Cerebras"},
        "note": {"de": "Weltweit schnellste Inferenz", "en": "World's fastest inference", "fr": "Inférence la plus rapide au monde", "es": "Inferencia más rápida del mundo", "it": "Inferenza più veloce al mondo", "nl": "Snelste inferentie ter wereld"},
    },
    "sambanova": {"name": {"de": "SambaNova", "en": "SambaNova", "fr": "SambaNova", "es": "SambaNova", "it": "SambaNova", "nl": "SambaNova"}},
    "fireworks": {"name": {"de": "Fireworks AI", "en": "Fireworks AI", "fr": "Fireworks AI", "es": "Fireworks AI", "it": "Fireworks AI", "nl": "Fireworks AI"}},
    "deepseek": {"name": {"de": "DeepSeek", "en": "DeepSeek", "fr": "DeepSeek", "es": "DeepSeek", "it": "DeepSeek", "nl": "DeepSeek"}},
    "mistral": {"name": {"de": "Mistral AI", "en": "Mistral AI", "fr": "Mistral AI", "es": "Mistral AI", "it": "Mistral AI", "nl": "Mistral AI"}},
    "novita": {"name": {"de": "Novita AI", "en": "Novita AI", "fr": "Novita AI", "es": "Novita AI", "it": "Novita AI", "nl": "Novita AI"}},
    "deepinfra": {"name": {"de": "DeepInfra", "en": "DeepInfra", "fr": "DeepInfra", "es": "DeepInfra", "it": "DeepInfra", "nl": "DeepInfra"}},
    "together": {"name": {"de": "Together AI", "en": "Together AI", "fr": "Together AI", "es": "Together AI", "it": "Together AI", "nl": "Together AI"}},
    "huggingface": {
        "name": {"de": "Hugging Face", "en": "Hugging Face", "fr": "Hugging Face", "es": "Hugging Face", "it": "Hugging Face", "nl": "Hugging Face"},
        "note": {"de": "Kostenlos (begrenzt) / Pro ab 9$/Monat", "en": "Free (limited) / Pro from $9/month", "fr": "Gratuit (limité) / Pro dès 9$/mois", "es": "Gratis (limitado) / Pro desde 9$/mes", "it": "Gratis (limitato) / Pro da 9$/mese", "nl": "Gratis (beperkt) / Pro vanaf $9/maand"},
    },
    "azure_openai": {
        "name": {"de": "Azure OpenAI", "en": "Azure OpenAI", "fr": "Azure OpenAI", "es": "Azure OpenAI", "it": "Azure OpenAI", "nl": "Azure OpenAI"},
        "note": {"de": "DSGVO-konform, EU-Hosting", "en": "GDPR-compliant, EU hosting", "fr": "Conforme RGPD, hébergement UE", "es": "Conforme RGPD, hosting UE", "it": "Conforme GDPR, hosting UE", "nl": "AVG-conform, EU-hosting"},
    },
    "nvidia": {
        "name": {"de": "NVIDIA NIM", "en": "NVIDIA NIM", "fr": "NVIDIA NIM", "es": "NVIDIA NIM", "it": "NVIDIA NIM", "nl": "NVIDIA NIM"},
        "note": {"de": "1000+ Modelle, NVIDIA-Hardware", "en": "1000+ models, NVIDIA hardware", "fr": "1000+ modèles, matériel NVIDIA", "es": "1000+ modelos, hardware NVIDIA", "it": "1000+ modelli, hardware NVIDIA", "nl": "1000+ modellen, NVIDIA-hardware"},
    },
    "replicate": {"name": {"de": "Replicate", "en": "Replicate", "fr": "Replicate", "es": "Replicate", "it": "Replicate", "nl": "Replicate"}},
    "anyscale": {"name": {"de": "Anyscale", "en": "Anyscale", "fr": "Anyscale", "es": "Anyscale", "it": "Anyscale", "nl": "Anyscale"}},
    "perplexity": {
        "name": {"de": "Perplexity AI", "en": "Perplexity AI", "fr": "Perplexity AI", "es": "Perplexity AI", "it": "Perplexity AI", "nl": "Perplexity AI"},
        "note": {"de": "Mit Websuche", "en": "With web search", "fr": "Avec recherche web", "es": "Con búsqueda web", "it": "Con ricerca web", "nl": "Met webzoekfunctie"},
    },
    "cohere": {"name": {"de": "Cohere", "en": "Cohere", "fr": "Cohere", "es": "Cohere", "it": "Cohere", "nl": "Cohere"}},
    "ai21": {
        "name": {"de": "AI21 (Jamba)", "en": "AI21 (Jamba)", "fr": "AI21 (Jamba)", "es": "AI21 (Jamba)", "it": "AI21 (Jamba)", "nl": "AI21 (Jamba)"},
        "note": {"de": "256k Kontext, Mamba+Transformer", "en": "256k context, Mamba+Transformer", "fr": "Contexte 256k, Mamba+Transformer", "es": "Contexto 256k, Mamba+Transformer", "it": "Contesto 256k, Mamba+Transformer", "nl": "256k context, Mamba+Transformer"},
    },
    "writer": {
        "name": {"de": "Writer (Palmyra)", "en": "Writer (Palmyra)", "fr": "Writer (Palmyra)", "es": "Writer (Palmyra)", "it": "Writer (Palmyra)", "nl": "Writer (Palmyra)"},
        "note": {"de": "Enterprise-Writing & Marketing", "en": "Enterprise writing & marketing", "fr": "Rédaction et marketing entreprise", "es": "Escritura empresarial y marketing", "it": "Scrittura aziendale e marketing", "nl": "Enterprise schrijven en marketing"},
    },
    "reka": {
        "name": {"de": "Reka", "en": "Reka", "fr": "Reka", "es": "Reka", "it": "Reka", "nl": "Reka"},
        "note": {"de": "Multimodal (Text/Bild/Audio/Video)", "en": "Multimodal (text/image/audio/video)", "fr": "Multimodal (texte/image/audio/vidéo)", "es": "Multimodal (texto/imagen/audio/vídeo)", "it": "Multimodale (testo/immagine/audio/video)", "nl": "Multimodaal (tekst/afbeelding/audio/video)"},
    },
    "moonshot": {
        "name": {"de": "Moonshot (Kimi)", "en": "Moonshot (Kimi)", "fr": "Moonshot (Kimi)", "es": "Moonshot (Kimi)", "it": "Moonshot (Kimi)", "nl": "Moonshot (Kimi)"},
        "note": {"de": "128k Kontext, Chinesisch + Englisch", "en": "128k context, Chinese + English", "fr": "Contexte 128k, chinois + anglais", "es": "Contexto 128k, chino + inglés", "it": "Contesto 128k, cinese + inglese", "nl": "128k context, Chinees + Engels"},
    },
    "zhipu": {
        "name": {"de": "Zhipu (GLM / z.ai)", "en": "Zhipu (GLM / z.ai)", "fr": "Zhipu (GLM / z.ai)", "es": "Zhipu (GLM / z.ai)", "it": "Zhipu (GLM / z.ai)", "nl": "Zhipu (GLM / z.ai)"},
        "note": {"de": "Top chinesisches Modell, mehrsprachig", "en": "Top Chinese model, multilingual", "fr": "Meilleur modèle chinois, multilingue", "es": "El mejor modelo chino, multilingüe", "it": "Miglior modello cinese, multilingue", "nl": "Top Chinees model, meertalig"},
    },
    "mammouth": {
        "name": {"de": "Mammouth AI", "en": "Mammouth AI", "fr": "Mammouth AI", "es": "Mammouth AI", "it": "Mammouth AI", "nl": "Mammouth AI"},
        "note": {"de": "OpenAI-kompatibel, Top-Modelle, Embeddings, Aliase", "en": "OpenAI-compatible, top models, embeddings, aliases", "fr": "Compatible OpenAI, meilleurs modèles, embeddings, alias", "es": "Compatible con OpenAI, mejores modelos, embeddings, alias", "it": "Compatibile OpenAI, migliori modelli, embeddings, alias", "nl": "OpenAI-compatibel, topmodellen, embeddings, aliassen"},
    },
    "openai_compat": {
        "name": {"de": "🔧 Eigener OpenAI-Endpunkt", "en": "🔧 Custom OpenAI Endpoint", "fr": "🔧 Endpoint OpenAI personnalisé", "es": "🔧 Endpoint OpenAI personalizado", "it": "🔧 Endpoint OpenAI personalizzato", "nl": "🔧 Aangepaste OpenAI-endpoint"},
        "note": {"de": "Beliebiger OpenAI-kompatibler Endpunkt (vLLM, TabbyAPI, LiteLLM-Proxy, ...)", "en": "Any OpenAI-compatible endpoint (vLLM, TabbyAPI, LiteLLM Proxy, ...)", "fr": "Tout endpoint compatible OpenAI (vLLM, TabbyAPI, LiteLLM Proxy, ...)", "es": "Cualquier endpoint compatible con OpenAI (vLLM, TabbyAPI, LiteLLM Proxy, ...)", "it": "Qualsiasi endpoint compatibile OpenAI (vLLM, TabbyAPI, LiteLLM Proxy, ...)", "nl": "Elke OpenAI-compatibele endpoint (vLLM, TabbyAPI, LiteLLM Proxy, ...)"},
    },
}


def main():
    for lang in ("de", "en", "fr", "es", "it", "nl"):
        path = I18N_DIR / f"{lang}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        added = 0
        # Genre names
        for key, translations in GENRE_NAMES.items():
            full = f"genre.{key}.name"
            if full not in data:
                data[full] = translations[lang]
                added += 1
        # Provider names
        for key, fields in PROVIDER_LABELS.items():
            for field_name, translations in fields.items():
                full = f"provider.{key}.{field_name}"
                if full not in data:
                    data[full] = translations[lang]
                    added += 1

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"  {lang}: +{added} keys ({len(data)} total)")


if __name__ == "__main__":
    main()
