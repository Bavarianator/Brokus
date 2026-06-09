"""Unified AI client for brokus – supports 15+ providers.

OpenAI-compatible providers (Groq, DeepSeek, OpenRouter, Mistral, LM Studio,
Together, Perplexity, Azure OpenAI, Ollama Local, Huggingface) use the OpenAI
client library. Anthropic, Google, Cohere, and Ollama Cloud use their own SDKs.

All providers are accessed through a single unified interface.
"""

import os
import json
import re
import unicodedata
import asyncio
import time
from typing import Optional, Any, TypeVar, Type
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from brokus.utils.logger import log


# Type variable for Pydantic model generics
T = TypeVar("T", bound=BaseModel)


# ─────────────────────────────────────────────────────────────
# Provider Registry
# ─────────────────────────────────────────────────────────────

PROVIDER_REGISTRY: dict[str, "ProviderConfig"] = {}


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    key: str
    name: str
    base_url: Optional[str]
    api_key_env: str
    library: str  # "openai" | "anthropic" | "google" | "ollama_cloud" | "cohere" | "huggingface"
    models: list[str] = field(default_factory=list)
    cost_info: str = ""
    features: str = ""

    @property
    def api_key_value(self) -> str:
        """Read API key: encrypted store first, then env var fallback."""
        # Try encrypted SecretStore first
        try:
            from brokus.utils.crypto import SecretStore
            stored = SecretStore.instance().get(self.api_key_env)
            if stored:
                return stored
        except Exception:
            pass
        # Fall back to environment variable
        return os.getenv(self.api_key_env, "")


# ── Register all 15 providers ──

PROVIDER_REGISTRY["ollama_local"] = ProviderConfig(
    key="ollama_local",
    name="Ollama (Lokal)",
    base_url="http://localhost:11434/v1",
    api_key_env="OLLAMA_LOCAL_KEY",
    library="openai",
    models=["llama3.3:70b", "mistral:7b", "gemma3:27b", "phi4:14b", "qwen3:32b", "deepseek-r1:32b"],
    cost_info="Kostenlos (GPU erforderlich)",
    features="OpenAI-kompatibel, komplett offline",
)

PROVIDER_REGISTRY["ollama_cloud"] = ProviderConfig(
    key="ollama_cloud",
    name="Ollama Cloud",
    base_url="https://ollama.com",
    api_key_env="OLLAMA_API_KEY",
    library="ollama_cloud",
    models=["gpt-oss:120b-cloud", "kimi-k2.6", "minimax-m3", "glm-5.1", "qwen3.5", "deepseek-v4-flash"],
    cost_info="Pay-per-use",
    features="Keine GPU nötig, Cloud-basiert",
)

PROVIDER_REGISTRY["openai"] = ProviderConfig(
    key="openai",
    name="OpenAI",
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
    library="openai",
    models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3", "o4-mini"],
    cost_info="0.15–60$ / 1M Tokens",
    features="Beste Qualität, großes Ökosystem",
)

PROVIDER_REGISTRY["anthropic"] = ProviderConfig(
    key="anthropic",
    name="Anthropic (Claude)",
    base_url=None,
    api_key_env="ANTHROPIC_API_KEY",
    library="anthropic",
    models=["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-3-5"],
    cost_info="0.25–75$ / 1M Tokens",
    features="200k Kontext-Fenster, kreatives Schreiben",
)

PROVIDER_REGISTRY["groq"] = ProviderConfig(
    key="groq",
    name="Groq",
    base_url="https://api.groq.com/openai/v1",
    api_key_env="GROQ_API_KEY",
    library="openai",
    models=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    cost_info="0.05–0.79$ / 1M Tokens",
    features="Extrem schnell (500+ Tokens/Sek)",
)

PROVIDER_REGISTRY["deepseek"] = ProviderConfig(
    key="deepseek",
    name="DeepSeek",
    base_url="https://api.deepseek.com",
    api_key_env="DEEPSEEK_API_KEY",
    library="openai",
    models=["deepseek-chat", "deepseek-reasoner"],
    cost_info="0.07–2.19$ / 1M Tokens",
    features="Sehr günstig, gute Qualität",
)

PROVIDER_REGISTRY["openrouter"] = ProviderConfig(
    key="openrouter",
    name="OpenRouter",
    base_url="https://openrouter.ai/api/v1",
    api_key_env="OPENROUTER_API_KEY",
    library="openai",
    models=[
        "openai/gpt-4o", "anthropic/claude-sonnet-4-5", "google/gemini-2.5-pro",
        "meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-chat",
        "deepseek/deepseek-r1:free", "google/gemini-2.0-flash-exp:free",
        "mistralai/mistral-7b-instruct:free", "moonshotai/kimi-k2.6:free",
    ],
    cost_info="Provider-Preis + Aufschlag",
    features="Ein API-Key für 200+ Modelle",
)

PROVIDER_REGISTRY["google"] = ProviderConfig(
    key="google",
    name="Google Gemini",
    base_url=None,
    api_key_env="GOOGLE_API_KEY",
    library="google",
    models=["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash-lite"],
    cost_info="0.075–3.50$ / 1M Tokens",
    features="1M Token Kontext-Fenster",
)

PROVIDER_REGISTRY["mistral"] = ProviderConfig(
    key="mistral",
    name="Mistral AI",
    base_url="https://api.mistral.ai/v1",
    api_key_env="MISTRAL_API_KEY",
    library="openai",
    models=["mistral-large-latest", "mistral-small-latest", "codestral-latest", "open-mixtral-8x22b"],
    cost_info="0.1–4$ / 1M Tokens",
    features="Open-Source-Modelle verfügbar",
)

PROVIDER_REGISTRY["lmstudio"] = ProviderConfig(
    key="lmstudio",
    name="LM Studio (Lokal)",
    base_url="http://localhost:1234/v1",
    api_key_env="LMSTUDIO_KEY",
    library="openai",
    models=["local-model"],
    cost_info="Kostenlos",
    features="GUI, OpenAI-kompatibel, offline",
)

PROVIDER_REGISTRY["together"] = ProviderConfig(
    key="together",
    name="Together AI",
    base_url="https://api.together.xyz/v1",
    api_key_env="TOGETHER_API_KEY",
    library="openai",
    models=[
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "mistralai/Mixtral-8x22B-Instruct-v0.1",
        "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "deepseek-ai/DeepSeek-V3",
    ],
    cost_info="0.06–0.9$ / 1M Tokens",
    features="OpenAI-kompatibel, viele Open-Source-Modelle",
)

PROVIDER_REGISTRY["huggingface"] = ProviderConfig(
    key="huggingface",
    name="Hugging Face",
    base_url="https://api-inference.huggingface.co/v1",
    api_key_env="HF_TOKEN",
    library="openai",
    models=[
        "meta-llama/Llama-3.3-70B-Instruct",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "microsoft/Phi-4",
        "Qwen/Qwen2.5-72B-Instruct",
    ],
    cost_info="Kostenlos (begrenzt) / Pro ab 9$/Monat",
    features="Riesige Modellbibliothek, OpenAI-kompatibel",
)

PROVIDER_REGISTRY["azure_openai"] = ProviderConfig(
    key="azure_openai",
    name="Azure OpenAI",
    base_url=None,  # Set via AZURE_OPENAI_ENDPOINT env var
    api_key_env="AZURE_OPENAI_API_KEY",
    library="openai",
    models=["gpt-4o", "gpt-4-turbo", "gpt-35-turbo"],
    cost_info="OpenAI-Preis + Azure-Marge",
    features="DSGVO-konform, EU-Hosting",
)

PROVIDER_REGISTRY["perplexity"] = ProviderConfig(
    key="perplexity",
    name="Perplexity AI",
    base_url="https://api.perplexity.ai",
    api_key_env="PERPLEXITY_API_KEY",
    library="openai",
    models=["llama-3.1-sonar-huge-128k-online", "llama-3.1-sonar-large-128k-online"],
    cost_info="5–20$ / 1M Tokens",
    features="Mit Websuche, Online-Modelle",
)

PROVIDER_REGISTRY["cohere"] = ProviderConfig(
    key="cohere",
    name="Cohere",
    base_url=None,
    api_key_env="COHERE_API_KEY",
    library="cohere",
    models=["command-r-plus-08-2024", "command-r-08-2024", "command-light"],
    cost_info="0.075–2.50$ / 1M Tokens",
    features="Enterprise-fokussiert",
)

PROVIDER_REGISTRY["localai"] = ProviderConfig(
    key="localai",
    name="LocalAI",
    base_url="http://localhost:8080/v1",
    api_key_env="LOCALAI_KEY",
    library="openai",
    models=["local-model"],
    cost_info="Kostenlos",
    features="Docker, OpenAI-kompatibel, offline",
)

# ── 15+ zusätzliche Provider ──

PROVIDER_REGISTRY["xai"] = ProviderConfig(
    key="xai",
    name="xAI (Grok)",
    base_url="https://api.x.ai/v1",
    api_key_env="XAI_API_KEY",
    library="openai",
    models=[
        "grok-4-fast-reasoning",
        "grok-4-fast-non-reasoning",
        "grok-3",
        "grok-3-mini",
        "grok-2-vision",
    ],
    cost_info="0.20–15$ / 1M Tokens",
    features="Witzig, kreativ, 2M Kontext, Realtime-Suche",
)

PROVIDER_REGISTRY["fireworks"] = ProviderConfig(
    key="fireworks",
    name="Fireworks AI",
    base_url="https://api.fireworks.ai/inference/v1",
    api_key_env="FIREWORKS_API_KEY",
    library="openai",
    models=[
        "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "accounts/fireworks/models/mixtral-8x22b-instruct",
        "accounts/fireworks/models/qwen2p5-72b-instruct",
        "accounts/fireworks/models/deepseek-v3",
        "accounts/fireworks/models/llama-v3p1-8b-instruct",
    ],
    cost_info="0.20–0.90$ / 1M Tokens",
    features="Schnell, viele Open-Source-Modelle, fine-tuning",
)

PROVIDER_REGISTRY["cerebras"] = ProviderConfig(
    key="cerebras",
    name="Cerebras",
    base_url="https://api.cerebras.ai/v1",
    api_key_env="CEREBRAS_API_KEY",
    library="openai",
    models=[
        "llama-3.3-70b",
        "llama-3.1-8b",
        "qwen-2.5-32b",
        "llama-4-scout-17b-16e-instruct",
    ],
    cost_info="0.10–0.60$ / 1M Tokens",
    features="Weltweit schnellste Inferenz (1000+ Tokens/Sek)",
)

PROVIDER_REGISTRY["sambanova"] = ProviderConfig(
    key="sambanova",
    name="SambaNova",
    base_url="https://api.sambanova.ai/v1",
    api_key_env="SAMBANOVA_API_KEY",
    library="openai",
    models=[
        "Meta-Llama-3.3-70B-Instruct",
        "Meta-Llama-3.1-8B-Instruct",
        "DeepSeek-R1",
        "DeepSeek-V3-0324",
    ],
    cost_info="0.30–0.60$ / 1M Tokens",
    features="Schnelle RDU-Chips, Open-Source-Modelle",
)

PROVIDER_REGISTRY["novita"] = ProviderConfig(
    key="novita",
    name="Novita AI",
    base_url="https://api.novita.ai/v3/openai",
    api_key_env="NOVITA_API_KEY",
    library="openai",
    models=[
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-nemo",
        "qwen/qwen-2.5-72b-instruct",
        "deepseek/deepseek-v3",
        "minimax/minimax-m2",
    ],
    cost_info="0.10–0.50$ / 1M Tokens",
    features="Günstige Open-Source-Modelle, GPU-Cloud",
)

PROVIDER_REGISTRY["deepinfra"] = ProviderConfig(
    key="deepinfra",
    name="DeepInfra",
    base_url="https://api.deepinfra.com/v1/openai",
    api_key_env="DEEPINFRA_API_KEY",
    library="openai",
    models=[
        "meta-llama/Llama-3.3-70B-Instruct",
        "meta-llama/Meta-Llama-3.1-405B-Instruct",
        "mistralai/Mixtral-8x22B-Instruct-v0.1",
        "Qwen/Qwen2.5-72B-Instruct",
        "microsoft/Phi-4",
    ],
    cost_info="0.05–0.90$ / 1M Tokens",
    features="Sehr günstig, Open-Source-Modelle, Pay-per-use",
)

PROVIDER_REGISTRY["github_models"] = ProviderConfig(
    key="github_models",
    name="GitHub Models",
    base_url="https://models.inference.ai.azure.com",
    api_key_env="GITHUB_TOKEN",
    library="openai",
    models=[
        "gpt-4o",
        "gpt-4o-mini",
        "o1-preview",
        "o1-mini",
        "Phi-3.5-MoE-instruct",
        "Mistral-large",
        "Meta-Llama-3.1-405B-Instruct",
    ],
    cost_info="Kostenlos (für GitHub-Nutzer, Rate-Limits)",
    features="GitHub-Personal-Access-Token, kein extra Account nötig",
)

PROVIDER_REGISTRY["replicate"] = ProviderConfig(
    key="replicate",
    name="Replicate",
    base_url="https://openai-proxy.replicate.com/v1",
    api_key_env="REPLICATE_API_TOKEN",
    library="openai",
    models=[
        "meta/meta-llama-3-70b-instruct",
        "meta/meta-llama-3.1-405b-instruct",
        "mistralai/mixtral-8x7b-instruct-v0.1",
    ],
    cost_info="0.05–2.50$ / 1M Tokens",
    features="Zugriff auf tausende Open-Source-Modelle, BYO-Modelle",
)

PROVIDER_REGISTRY["anyscale"] = ProviderConfig(
    key="anyscale",
    name="Anyscale",
    base_url="https://api.endpoints.anyscale.com/v1",
    api_key_env="ANYSCALE_API_KEY",
    library="openai",
    models=[
        "meta-llama/Llama-3-70b-chat-hf",
        "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "google/gemma-2-9b-it",
    ],
    cost_info="0.50–1.00$ / 1M Tokens",
    features="Production-grade LLM-Serving auf Ray",
)

PROVIDER_REGISTRY["writer"] = ProviderConfig(
    key="writer",
    name="Writer (Palmyra)",
    base_url="https://api.writer.com/v1",
    api_key_env="WRITER_API_KEY",
    library="openai",
    models=[
        "palmyra-x5",
        "palmyra-x4",
        "palmyra-creative",
    ],
    cost_info="0.40–1.40$ / 1M Tokens",
    features="Spezialisiert auf Enterprise-Writing & Marketing",
)

PROVIDER_REGISTRY["reka"] = ProviderConfig(
    key="reka",
    name="Reka",
    base_url="https://api.reka.ai/v1",
    api_key_env="REKA_API_KEY",
    library="openai",
    models=[
        "reka-core",
        "reka-flash",
        "reka-edge",
    ],
    cost_info="0.40–1.50$ / 1M Tokens",
    features="Multimodal (Text/Bild/Audio/Video), 128k Kontext",
)

PROVIDER_REGISTRY["ai21"] = ProviderConfig(
    key="ai21",
    name="AI21 (Jamba)",
    base_url="https://api.ai21.com/studio/v1",
    api_key_env="AI21_API_KEY",
    library="openai",
    models=[
        "jamba-1.5-large",
        "jamba-1.5-mini",
    ],
    cost_info="0.20–2.00$ / 1M Tokens",
    features="Mamba+Transformer-Hybrid, 256k Kontext, Tool-Use",
)

PROVIDER_REGISTRY["moonshot"] = ProviderConfig(
    key="moonshot",
    name="Moonshot (Kimi)",
    base_url="https://api.moonshot.ai/v1",
    api_key_env="MOONSHOT_API_KEY",
    library="openai",
    models=[
        "moonshot-v1-128k",
        "moonshot-v1-32k",
        "moonshot-v1-8k",
        "kimi-k2.6",
    ],
    cost_info="0.20–2.00$ / 1M Tokens",
    features="Bis zu 128k Kontext, Chinesisch + Englisch",
)

PROVIDER_REGISTRY["zhipu"] = ProviderConfig(
    key="zhipu",
    name="Zhipu (GLM / z.ai)",
    base_url="https://api.z.ai/api/paas/v4",
    api_key_env="ZHIPU_API_KEY",
    library="openai",
    models=[
        "glm-4.6",
        "glm-4.5",
        "glm-4-plus",
        "glm-4-flash",
    ],
    cost_info="0.10–3.00$ / 1M Tokens",
    features="Top chinesisches Modell, mehrsprachig, 128k Kontext",
)

PROVIDER_REGISTRY["nvidia"] = ProviderConfig(
    key="nvidia",
    name="NVIDIA NIM",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key_env="NVIDIA_API_KEY",
    library="openai",
    models=[
        "meta/llama-3.3-70b-instruct",
        "meta/llama-3.1-405b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "mistralai/mistral-large",
        "google/gemma-2-27b-it",
    ],
    cost_info="Kostenlose Tier / Enterprise verfügbar",
    features="NVIDIA-Hardware, 1000+ Modelle, kostenlose Tier",
)

PROVIDER_REGISTRY["openai_compat"] = ProviderConfig(
    key="openai_compat",
    name="🔧 Eigener OpenAI-Endpunkt",
    base_url=None,  # Wird vom User konfiguriert
    api_key_env="OPENAI_COMPAT_KEY",
    library="openai",
    models=["custom-model"],
    cost_info="Variabel (je nach Anbieter)",
    features="Beliebiger OpenAI-kompatibler Endpunkt (vLLM, TabbyAPI, ...)",
)

# Bedrock und Vertex sind absichtlich nicht in der OpenAI-kompatiblen Registry,
# da sie eigene SDKs benötigen. Stattdessen via 'openai_compat' mit passender
# base_url konfigurierbar (z.B. LiteLLM-Proxy davor).


# ─────────────────────────────────────────────────────────────
# Fallback Models (per Provider)
# ─────────────────────────────────────────────────────────────

DEFAULT_FALLBACK_MODELS: dict[str, list[str]] = {
    "openrouter": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
        "google/gemini-2.0-flash-exp:free",
        "mistralai/mistral-7b-instruct:free",
        "moonshotai/kimi-k2.6:free",
    ],
}


# ─────────────────────────────────────────────────────────────
# Response Model
# ─────────────────────────────────────────────────────────────

@dataclass
class AIResponse:
    """Response from an AI call."""
    text: str
    model: str
    tokens_used: int = 0
    cost_estimate: float = 0.0
    provider: str = ""


# ─────────────────────────────────────────────────────────────
# AIConfig (backward-compatible with pipeline.py)
# ─────────────────────────────────────────────────────────────

@dataclass
class AIConfig:
    """Configuration for AI calls (backward-compatible)."""
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5"
    temperature: float = 0.7
    max_tokens: int = 4000
    base_url: Optional[str] = None
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    ollama_base_url: str = "http://localhost:11434"
    # Erweiterte Sampling-Parameter
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    # Erweiterte Generierungs-Settings
    chapter_delay: float = 2.0
    default_language: str = "Deutsch"
    log_level: str = "INFO"


# ─────────────────────────────────────────────────────────────
# BrokusAIClient – Unified Multi-Provider Client
# ─────────────────────────────────────────────────────────────

class BrokusAIClient:
    """Universal AI client for all 15+ providers.

    Usage:
        client = BrokusAIClient(provider="openrouter", model="anthropic/claude-sonnet-4-5")
        response = await client.generate("You are a writer.", "Write a story...")
        print(response.text)

    OpenAI-compatible providers use the OpenAI client library.
    Anthropic, Google, and Cohere use their own SDKs.
    """

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-5",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        fallback_models: Optional[list[str]] = None,
        config: Optional[AIConfig] = None,
        custom_base_url: Optional[str] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
    ):
        """Initialize the client.

        Args:
            provider: Provider key (e.g., "openrouter", "anthropic", "openai").
            model: Model name for the selected provider.
            temperature: Generation temperature.
            max_tokens: Maximum tokens to generate.
            max_retries: Number of retries on failure.
            retry_delay: Base delay between retries (exponential backoff).
            fallback_models: Models to try on rate limit (per-provider defaults used if None).
            config: Optional AIConfig for backward compatibility.
            custom_base_url: Override the provider's default base URL (for "openai_compat" or proxies).
            top_p: Nucleus sampling parameter (0.0–1.0). None = provider default.
            frequency_penalty: Penalize repeated tokens (-2.0–2.0). None = provider default.
            presence_penalty: Penalize tokens that have appeared (-2.0–2.0). None = provider default.
        """
        # Support backward-compatible AIConfig
        if config is not None:
            provider = config.provider
            model = config.model
            temperature = config.temperature
            max_tokens = config.max_tokens

        self.provider_key = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.custom_base_url = custom_base_url
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

        # Fallback-Modelle: eigener Parameter > Provider-Default > keine
        if fallback_models is not None:
            self.fallback_models = list(fallback_models)
        else:
            self.fallback_models = list(DEFAULT_FALLBACK_MODELS.get(provider, []))

        self.provider_config = PROVIDER_REGISTRY.get(provider)
        if not self.provider_config:
            log.warning(f"Unknown provider '{provider}', falling back to OpenAI-compatible")
            self.provider_config = ProviderConfig(
                key=provider, name=provider, base_url=None,
                api_key_env=f"{provider.upper()}_API_KEY", library="openai",
            )
            PROVIDER_REGISTRY[provider] = self.provider_config

        self._clients: dict[str, Any] = {}

    # ── Public API ───────────────────────────────────────────

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retry: bool = True,
        model: Optional[str] = None,
    ) -> AIResponse:
        """Generate text from the configured AI provider.

        Args:
            system_prompt: System instruction.
            user_prompt: User message/prompt.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.
            retry: Enable automatic retry on failure.
            model: Override model for this call only (for multi-model setups).

        Returns:
            AIResponse with generated text and metadata.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        max_attempts = self.max_retries if retry else 1
        attempt = 0
        last_error = None

        # Temporarily override model for this call (multi-model support)
        original_model = self.model
        if model is not None:
            self.model = model

        try:
            while attempt < max_attempts:
                try:
                    return await asyncio.wait_for(
                        self._chat(messages, temp, max_tok),
                        timeout=300,
                    )
                except Exception as e:
                    err_str = str(e).lower()

                    # ── Moderation / 403 → sofort abbrechen ──
                    is_moderation = any(
                        kw in err_str
                        for kw in ["403", "moderation", "flagged", "content_filter",
                                   "sexual", "minors", "openinference"]
                    )
                    if is_moderation:
                        log.warning(
                            f"🛑 Moderation flag on '{self.model}': {str(e)[:200]}"
                        )
                        raise ModerationError(
                            f"Content moderation flagged by {self.provider_key}: {str(e)[:300]}",
                            schema_name="",
                            last_raw=str(e),
                            last_error=e,
                        )

                    is_rate_limit = any(
                        kw in err_str
                        for kw in ["rate_limit", "rate limit", "429", "too many requests",
                                   "temporarily rate-limited"]
                    )

                    # Rate-Limit: use fallback model without consuming an attempt
                    # WICHTIG: Pop aus self.fallback_models (nicht lokale Kopie),
                    # damit die exhausted-Branch nicht dieselben Modelle wiederholt.
                    if is_rate_limit and self.fallback_models:
                        # Überspringe Fallback-Modelle == aktuellem Modell
                        while self.fallback_models and self.fallback_models[0] == self.model:
                            log.info(f"Skipping rate-limit fallback '{self.fallback_models[0]}' (same model)")
                            self.fallback_models.pop(0)
                        if self.fallback_models:
                            next_model = self.fallback_models.pop(0)
                            task_hint = (system_prompt[:80] + "...") if len(system_prompt) > 80 else system_prompt
                            log.warning(
                                f"⚠️ Rate-Limit on '{self.model}' → "
                                f"Fallback to '{next_model}' (task: {task_hint})"
                            )
                            self.model = next_model
                            await asyncio.sleep(2)
                            last_error = e
                            continue
                        else:
                            log.warning(f"⚠️ Rate-Limit on '{self.model}' → No more fallbacks available")

                    last_error = e
                    attempt += 1
                    log.warning(
                        f"Provider '{self.provider_key}' attempt {attempt}/{max_attempts} "
                        f"failed: {e}"
                    )
                    if attempt < max_attempts:
                        delay = self.retry_delay * (2 ** (attempt - 1))
                        await asyncio.sleep(delay)
                    else:
                        # ── Fallback-Kaskade: Wenn alle Retries fehlschlagen,
                        #    versuche nacheinander Fallback-Modelle, dann Default.
                        fell_back = False

                        # Fallback-Modelle durchgehen, bis ein neues gefunden wird
                        while self.fallback_models:
                            fb_model = self.fallback_models[0]
                            if fb_model == self.model:
                                log.info(f"Skipping fallback '{fb_model}' (same as current model)")
                                self.fallback_models.pop(0)
                                continue
                            if fb_model == original_model:
                                log.info(f"Skipping fallback '{fb_model}' (same as already-exhausted original)")
                                self.fallback_models.pop(0)
                                continue
                            break

                        if self.fallback_models:
                            fb_model = self.fallback_models.pop(0)
                            log.warning(
                                f"Model '{self.model}' exhausted, "
                                f"falling back to '{fb_model}'"
                            )
                            self.model = fb_model
                            fell_back = True
                        elif original_model and self.model != original_model:
                            log.warning(
                                f"Model '{self.model}' exhausted, "
                                f"falling back to default '{original_model}'"
                            )
                            self.model = original_model
                            fell_back = True

                        if fell_back:
                            attempt = 0
                            last_error = None
                            continue

                        log.error(
                            f"All {max_attempts} attempts exhausted for provider '{self.provider_key}'"
                        )

            raise RuntimeError(
                f"AI generation failed after {max_attempts} attempts: {last_error}"
            )
        finally:
            # Restore original model
            self.model = original_model

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 8000,
        expected_type: Optional[type] = None,
    ) -> dict | list:
        """Generate and parse JSON response.

        Uses a higher max_tokens (8000) by default to prevent truncation
        of large JSON arrays like chapter plans.

        Args:
            system_prompt: System instruction for the AI.
            user_prompt: User message.
            temperature: Override default temperature.
            max_tokens: Max tokens for the response.
            expected_type: If set (e.g. dict, list), validates the parsed JSON
                           matches this type. Returns {"error": ...} on mismatch.

        Returns:
            Parsed JSON as dict, list, or {"error": ...} on failure/type mismatch.
        """
        response = await self.generate(
            system_prompt, user_prompt, temperature, max_tokens=max_tokens, retry=False
        )

        parsed = self._extract_json(response.text)

        if parsed is None:
            log.warning(f"Failed to parse JSON from AI response. Raw: {response.text[:200]}...")
            return {"error": "failed_to_parse_json", "raw": response.text[:300]}

        if expected_type is not None and not isinstance(parsed, expected_type):
            log.warning(
                f"JSON response type mismatch: expected {expected_type.__name__}, "
                f"got {type(parsed).__name__}. Raw: {response.text[:200]}..."
            )
            return {"error": f"expected {expected_type.__name__}, got {type(parsed).__name__}", "raw": response.text[:300]}

        return parsed

    async def generate_model(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        temperature: Optional[float] = None,
        max_tokens: int = 8000,
        retries: int = 3,
        model: Optional[str] = None,
    ) -> T:
        """Generate a response and validate it against a Pydantic schema.

        Parses JSON from the LLM response, validates it against ``schema``,
        and returns a typed instance. On failure, retries with a correction
        prompt telling the LLM what went wrong.

        Args:
            system_prompt: System instruction.
            user_prompt: User message/prompt.
            schema: Pydantic BaseModel subclass to validate against.
            temperature: Override default temperature.
            max_tokens: Max tokens for the response.
            retries: Number of correction retries before raising.

        Returns:
            An instance of ``schema``.

        Raises:
            LLMResponseError: If all retries are exhausted.
        """
        schema_name = schema.__name__
        schema_hint = (
            f"\n\nAntworte NUR mit einem JSON-Objekt, das diesem Schema entspricht:\n"
            f"Respond ONLY with a JSON object that matches this schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2, ensure_ascii=False)}\n\n"
            f"WICHTIG: KEIN Text vor/nach dem JSON. KEINE Codeblöcke (```). KEINE Erklärungen. NUR das reine JSON-Objekt.\n"
            f"IMPORTANT: NO text before/after the JSON. NO code fences (```). NO explanations. ONLY the raw JSON object."
        )
        current_prompt = user_prompt + schema_hint
        last_raw = ""
        last_error: Optional[Exception] = None

        for attempt in range(retries + 1):
            response = await self.generate(
                system_prompt, current_prompt, temperature, max_tokens=max_tokens, retry=True,
                model=model,
            )
            last_raw = response.text.strip()

            # Try parsing JSON (with fallback cascade)
            parsed = self._extract_json(last_raw)
            if parsed is None:
                # Refusal-Erkennung: Modell verweigert Content → sofort abbrechen
                if self._is_refusal(last_raw):
                    log.info(
                        f"{schema_name} attempt {attempt + 1}: model refused "
                        f"(preview: {last_raw[:150]}) — fallback chain will handle"
                    )
                    raise LLMResponseError(
                        f"Model refused content generation: {last_raw[:300]}",
                        schema_name=schema_name,
                        last_raw=last_raw,
                        last_error=Exception("refusal"),
                    )

                preview = last_raw[:500]
                last_error = json.JSONDecodeError("No JSON found", preview, 0)
                log.info(
                    f"{schema_name} attempt {attempt + 1}: no JSON found, "
                    f"trying fallback..."
                )
                # Rate-Limit-Erkennung: rohe Antwort auf 429/Error prüfen
                if any(kw in last_raw[:200].lower() for kw in ["rate", "429", "too many", "error", "offline"]):
                    wait = min(2 ** (attempt + 1), 30)
                    log.info(f"Rate-limit or error detected, sleeping {wait}s")
                    await asyncio.sleep(wait)
            else:
                try:
                    return schema.model_validate(parsed)
                except ValidationError as e:
                    last_error = e
                    log.warning(f"{schema_name} attempt {attempt + 1}: validation failed: {e}")

            if attempt < retries:
                # Build correction prompt
                correction = (
                    f"\n\nDeine letzte Antwort war ungültig / Your last response was invalid:\n"
                    f"{last_error}\n\n"
                    f"Antworte NUR mit gültigem JSON. Keine Erklärungen. Kein Präfix. Kein Suffix. Keine Codeblöcke.\n"
                    f"Respond ONLY with valid JSON. No explanations. No prefix. No suffix. No code fences.\n"
                    f"Das JSON MUSS exakt dem Schema entsprechen / The JSON MUST match the schema exactly.\n\n"
                    f"URSPRÜNGLICHE AUFGABE / ORIGINAL TASK:\n{user_prompt}"
                )
                current_prompt = correction

        raise LLMResponseError(
            f"{schema_name} failed after {retries + 1} attempts: {last_error}",
            schema_name=schema_name,
            last_raw=last_raw,
            last_error=last_error,
        )

    # ── Refusal-Erkennung ──
    # Content-Policy-Verweigerungen frühzeitig erkennen und abbrechen.
    # Nutzt Unicode-Normalisierung (NFKC) für Smart Quotes u.ä.
    REFUSAL_PATTERNS: list[str] = [
        r"i['\u2019\u2018]?m sorry",           # I'm / I am / Im sorry (mit Unicode ')
        r"i am sorry",
        r"i can'?t (help|assist|do|provide) (with )?that",
        r"i'?m (unable|not able) to",
        r"i cannot (provide|generate|create|help|assist)",
        r"sorry,?\s*(but )?i (can'?t|cannot)",
        r"as an ai (language )?model",
        r"entschuldigung,?\s*(aber )?ich kann",
        r"ich kann (dir |dabei |damit )?nicht helfen",
        r"ich kann (das |diese |so )?nicht",
        r"das kann ich (leider )?nicht",
        r"tut mir leid,?\s*(aber )?ich",
        r"i don'?t (have|meet) the (capability|requirement)",
    ]
    # Einmal kompilieren (IGNORECASE) — effizienter
    _REFUSAL_REGEXES: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in REFUSAL_PATTERNS]

    @staticmethod
    def _normalize_refusal_text(text: str) -> str:
        """Normalisiert Unicode-Smart-Quotes, NBSP etc. zu ASCII."""
        if not text:
            return ""
        # NFKC normalisiert viele typografische Zeichen
        text = unicodedata.normalize("NFKC", text)
        # Smart Quotes → ASCII (zusätzliche Sicherheit)
        replacements = {
            "\u2018": "'", "\u2019": "'",  # ' '
            "\u201C": '"', "\u201D": '"',  # " "
            "\u2032": "'", "\u2035": "'",  # ′ ‵
            "\u00A0": " ",                  # NBSP
            "\u2013": "-", "\u2014": "-",  # – —
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return text.lower().strip()

    def _is_refusal(self, text: str) -> bool:
        """Check if the AI response is a content policy refusal.

        Normalisiert zuerst Unicode (Smart Quotes → ASCII) und matched
        dann gegen kompilierte Regexes (IGNORECASE).
        """
        if not text:
            return False
        normalized = self._normalize_refusal_text(text)[:300]
        return any(rx.search(normalized) for rx in self._REFUSAL_REGEXES)

    def _extract_json(self, text: str) -> Optional[dict | list]:
        """Extract and parse JSON from LLM response text.

        Mehrere Strategien:
        1. Markdown-Codeblock-Fenster (```json ... ```)
        2. Direkter Parse (wenn Text mit { oder [ beginnt)
        3. Balanciertes JSON-Objekt/Array via Klammerzählung
        4. Trailing-Comma-Reparatur als letzter Versuch

        Returns:
            Geparstes dict oder list, oder None.
        """
        if not text or not text.strip():
            return None

        t = text.strip()

        # Strategie 1: Markdown-Codeblock (```json ... ```)
        fence_match = re.search(
            r"```(?:json|JSON)?\s*(.*?)\s*```",
            t,
            re.DOTALL,
        )
        if fence_match:
            candidate = fence_match.group(1).strip()
            parsed = self._try_parse_json(candidate)
            if parsed is not None:
                return parsed

        # Strategie 2: Direkter Parse (Antwort beginnt mit JSON)
        if t and t[0] in "{[":
            parsed = self._try_parse_json(t)
            if parsed is not None:
                return parsed

        # Strategie 3: Balanciertes JSON irgendwo im Text finden
        candidate = self._find_balanced_json(t)
        if candidate:
            parsed = self._try_parse_json(candidate)
            if parsed is not None:
                return parsed

        # Strategie 4: Mit Trailing-Comma-Reparatur
        if candidate:
            repaired = re.sub(r",(\s*[\}\]])+", r"\1", candidate)
            if repaired != candidate:
                parsed = self._try_parse_json(repaired)
                if parsed is not None:
                    return parsed

        # Strategie 5: Alles {…} oder […] mit Regex finden (als letzter Versuch)
        for pattern in [r"\{(.*?)\}", r"\[(.*?)\]"]:
            match = re.search(pattern, t, re.DOTALL)
            if match:
                candidate = match.group(0)
                parsed = self._try_parse_json(candidate)
                if parsed is not None:
                    return parsed

        return None

    def _try_parse_json(self, text: str) -> Optional[dict | list]:
        """Versuche, einen String als JSON zu parsen."""
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

    def _find_balanced_json(self, text: str) -> Optional[str]:
        """Findet das erste balancierte JSON-Objekt oder -Array (string-aware)."""
        start = -1
        for i, ch in enumerate(text):
            if ch in "{[":
                start = i
                break
        if start == -1:
            return None

        open_ch = text[start]
        close_ch = "}" if open_ch == "{" else "]"
        depth = 0
        in_string = False
        escape = False

        for i in range(start, len(text)):
            ch = text[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    async def test_connection(self) -> bool:
        """Test if the provider is reachable and the model is available."""
        try:
            response = await self.generate(
                "Du bist ein hilfreicher Assistent.",
                "Sage nur 'OK'.",
                temperature=0.0,
                max_tokens=10,
                retry=False,
            )
            return "OK" in response.text or len(response.text) > 0
        except Exception as e:
            log.warning(f"Connection test failed for {self.provider_key}: {e}")
            return False

    # ── Internal: Dispatch to correct provider library ────────

    async def _chat(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AIResponse:
        """Route the chat request to the appropriate provider implementation."""
        lib = self.provider_config.library

        if lib == "openai":
            return await self._chat_openai(messages, temperature, max_tokens)
        elif lib == "anthropic":
            return await self._chat_anthropic(messages, temperature, max_tokens)
        elif lib == "google":
            return await self._chat_google(messages, temperature, max_tokens)
        elif lib == "ollama_cloud":
            return await self._chat_ollama_cloud(messages, temperature, max_tokens)
        elif lib == "cohere":
            return await self._chat_cohere(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown library type: {lib}")

    # ── OpenAI-compatible providers ───────────────────────────
    # Covers: openai, groq, deepseek, openrouter, mistral,
    #         lmstudio, together, perplexity, azure_openai,
    #         ollama_local, localai

    async def _chat_openai(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AIResponse:
        """Generate using OpenAI-compatible API."""
        from openai import AsyncOpenAI

        client_key = f"openai_{self.provider_key}"

        if client_key not in self._clients:
            kwargs: dict[str, Any] = {"api_key": self.provider_config.api_key_value}

            if self.provider_key == "azure_openai":
                # Azure OpenAI: use azure_endpoint + api_version
                base_url = os.getenv("AZURE_OPENAI_ENDPOINT", "")
                if not base_url:
                    raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
                kwargs["azure_endpoint"] = base_url
                kwargs["api_version"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
            else:
                # Custom base_url wins over provider default (für openai_compat / Proxies)
                effective_base_url = self.custom_base_url or self.provider_config.base_url
                if effective_base_url:
                    kwargs["base_url"] = effective_base_url

            self._clients[client_key] = AsyncOpenAI(**kwargs)

        client = self._clients[client_key]

        # Build call kwargs
        extra_kwargs: dict[str, Any] = {}
        if self.provider_key == "azure_openai":
            extra_kwargs["max_tokens"] = max_tokens
        else:
            extra_kwargs["temperature"] = temperature
            extra_kwargs["max_tokens"] = max_tokens
            # Optionale Sampling-Parameter (nur senden, wenn gesetzt)
            if self.top_p is not None:
                extra_kwargs["top_p"] = self.top_p
            if self.frequency_penalty is not None:
                extra_kwargs["frequency_penalty"] = self.frequency_penalty
            if self.presence_penalty is not None:
                extra_kwargs["presence_penalty"] = self.presence_penalty

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            **extra_kwargs,
        )

        return AIResponse(
            text=response.choices[0].message.content or "",
            model=self.model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            provider=self.provider_config.name,
        )

    # ── Anthropic (Claude) ────────────────────────────────────

    async def _chat_anthropic(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AIResponse:
        """Generate using Anthropic API."""
        from anthropic import AsyncAnthropic

        if "anthropic" not in self._clients:
            self._clients["anthropic"] = AsyncAnthropic(
                api_key=self.provider_config.api_key_value
            )

        client = self._clients["anthropic"]

        # Separate system message from user messages
        system = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_messages.append(m)

        response = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system if system else None,
            messages=user_messages,
        )

        text = ""
        if response.content:
            block = response.content[0]
            text = block.text if hasattr(block, "text") else str(block)

        return AIResponse(
            text=text,
            model=self.model,
            tokens_used=(response.usage.input_tokens + response.usage.output_tokens)
            if response.usage else 0,
            provider=self.provider_config.name,
        )

    # ── Google Gemini ─────────────────────────────────────────

    async def _chat_google(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AIResponse:
        """Generate using Google Gemini API."""
        import google.generativeai as genai

        if "google" not in self._clients:
            genai.configure(api_key=self.provider_config.api_key_value)
            self._clients["google"] = genai

        # Combine messages into a single prompt (Gemini format)
        system = ""
        user = ""
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                user = m["content"]

        full_prompt = f"{system}\n\n{user}" if system else user

        model = genai.GenerativeModel(
            self.model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        response = await asyncio.to_thread(
            model.generate_content,
            full_prompt,
        )

        text = response.text if response.text else ""

        return AIResponse(
            text=text,
            model=self.model,
            tokens_used=response.usage_metadata.total_token_count
            if hasattr(response, "usage_metadata") and response.usage_metadata else 0,
            provider=self.provider_config.name,
        )

    # ── Ollama Cloud ──────────────────────────────────────────

    async def _chat_ollama_cloud(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AIResponse:
        """Generate using Ollama Cloud API (ollama.com/api/chat)."""
        import ollama

        if "ollama_cloud" not in self._clients:
            self._clients["ollama_cloud"] = ollama.AsyncClient(
                host=self.provider_config.base_url,
                headers={
                    "Authorization": f"Bearer {self.provider_config.api_key_value}"
                },
            )

        client = self._clients["ollama_cloud"]
        response = await client.chat(
            model=self.model,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )

        text = ""
        if hasattr(response, "message") and response.message:
            text = response.message.content or ""
        elif isinstance(response, dict):
            msg = response.get("message", {})
            text = msg.get("content", "") if isinstance(msg, dict) else str(msg)

        return AIResponse(
            text=text,
            model=self.model,
            tokens_used=0,
            provider=self.provider_config.name,
        )

    # ── Cohere ────────────────────────────────────────────────

    async def _chat_cohere(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> AIResponse:
        """Generate using Cohere API."""
        import cohere

        if "cohere" not in self._clients:
            self._clients["cohere"] = cohere.AsyncClient(
                api_key=self.provider_config.api_key_value
            )

        # Combine into single message (Cohere format)
        system = ""
        user = ""
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                user = m["content"]

        preamble = system if system else None

        client = self._clients["cohere"]
        response = await client.chat(
            model=self.model,
            message=user,
            preamble=preamble,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return AIResponse(
            text=response.text if response.text else "",
            model=self.model,
            tokens_used=(response.meta.tokens.input_tokens + response.meta.tokens.output_tokens)
            if hasattr(response, "meta") and response.meta and response.meta.tokens else 0,
            provider=self.provider_config.name,
        )


# ─────────────────────────────────────────────────────────────
# AI Error Hierarchy
# ─────────────────────────────────────────────────────────────

class LLMResponseError(Exception):
    """Raised when the LLM response cannot be parsed or validated.

    Attributes:
        message: Human-readable error description.
        schema_name: Name of the Pydantic schema that failed.
        last_raw: Last raw text from the LLM (truncated).
        last_error: Original exception (ValidationError, JSONDecodeError).
    """

    def __init__(
        self,
        message: str,
        schema_name: str = "",
        last_raw: str = "",
        last_error: Optional[Exception] = None,
    ):
        self.schema_name = schema_name
        self.last_raw = last_raw[:500]
        self.last_error = last_error
        super().__init__(message)


class ModerationError(Exception):
    """Raised when the provider flags the content for moderation (e.g. 403).

    This is a separate error class because moderation errors should NOT
    trigger fallback — the prompt itself is the problem, not the model.
    Trying other models after a moderation flag risks account-level consequences.
    """
    pass


# ─────────────────────────────────────────────────────────────
# Backward-Compatible AIClient Wrapper
# ─────────────────────────────────────────────────────────────

class AIClient(BrokusAIClient):
    """Backward-compatible wrapper that accepts AIConfig.

    This exists so that pipeline.py and other existing code continues
    to work without changes.
    """

    def __init__(self, config: Optional[AIConfig] = None, **kwargs):
        super().__init__(config=config, **kwargs)


# Convenience function
def get_provider_list() -> list[dict]:
    """Get all registered providers with their metadata."""
    return [
        {
            "key": p.key,
            "name": p.name,
            "models": p.models,
            "cost_info": p.cost_info,
            "features": p.features,
            "library": p.library,
            "has_key": bool(p.api_key_value),
        }
        for p in PROVIDER_REGISTRY.values()
    ]
