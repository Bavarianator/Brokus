"""Live model discovery cache for OpenAI-compatible providers.

Fetches the actual model list from a provider's ``/v1/models`` (or
``/api/tags`` for Ollama Cloud) endpoint and caches the result on disk
with a TTL. The TUI "Modelle neu laden" button and the CLI model
picker use this instead of the hard-coded ``models`` list in
``PROVIDER_REGISTRY``.

If the endpoint is unreachable, the previously cached list (if any) is
returned, or the hard-coded fallback. This way the UI never breaks even
when the local Ollama is offline.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from brokus.utils.logger import log


# ─────────────────────────────────────────────────────────────
# Cache constants
# ─────────────────────────────────────────────────────────────

_CACHE_DIR = Path("data/cache")
_CACHE_PATH = _CACHE_DIR / "model_discovery.json"
_DEFAULT_TTL = 86_400          # 24 hours
_LOCAL_TTL = 3_600             # 1 hour  (ollama/lmstudio/localai)
_FETCH_TIMEOUT = 10            # seconds


# ─────────────────────────────────────────────────────────────
# Result
# ─────────────────────────────────────────────────────────────

@dataclass
class DiscoveryResult:
    """Result of a discovery call."""
    models: list[str]
    source: str          # "cache" | "live" | "fallback"
    error: Optional[str] = None
    fetched_at: float = 0.0

    def __bool__(self) -> bool:                # truthy if we have models
        return bool(self.models)


# ─────────────────────────────────────────────────────────────
# ModelDiscovery – TTL cache + live fetch
# ─────────────────────────────────────────────────────────────

class ModelDiscovery:
    """TTL-based model list cache.

    The cache is in-memory (for fast UI lookups) and mirrored to disk
    (so it survives restarts). Each cache entry holds the list of model
    IDs and the timestamp of the last successful fetch.
    """

    # Providers that should be queried via /v1/models (OpenAI-compat).
    # Anything in the openai-library + openai_compat + ollama_local.
    OPENAI_COMPAT_KEYS = {
        "openai", "groq", "deepseek", "openrouter", "mistral",
        "lmstudio", "together", "perplexity", "ollama_local", "localai",
        "xai", "fireworks", "cerebras", "sambanova", "novita", "deepinfra",
        "github_models", "replicate", "anyscale", "writer", "reka", "ai21",
        "moonshot", "zhipu", "nvidia", "huggingface", "openai_compat",
    }

    # Provider that uses Ollama's own /api/tags endpoint.
    OLLAMA_CLOUD_KEYS = {"ollama_cloud"}

    def __init__(
        self,
        cache_path: Path = _CACHE_PATH,
        ttl: int = _DEFAULT_TTL,
        local_ttl: int = _LOCAL_TTL,
    ):
        self.cache_path = cache_path
        self.ttl = ttl
        self.local_ttl = local_ttl
        # In-memory: { provider_key: { "models": [...], "ts": float, "source": "live" } }
        self._mem: dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._load_disk()

    # ── Public API ───────────────────────────────────────────

    def is_eligible(self, provider_key: str, library: str) -> bool:
        """Return True if this provider supports live model discovery."""
        return (
            provider_key in self.OPENAI_COMPAT_KEYS
            or provider_key in self.OLLAMA_CLOUD_KEYS
            or library in ("openai", "ollama_cloud")
        )

    def get_cached(self, provider_key: str) -> Optional[list[str]]:
        """Return the cached model list for ``provider_key`` (no fetch)."""
        entry = self._mem.get(provider_key)
        if entry:
            return list(entry.get("models", []))
        return None

    def is_cache_fresh(self, provider_key: str, library: str) -> bool:
        entry = self._mem.get(provider_key)
        if not entry:
            return False
        ts = float(entry.get("ts", 0))
        ttl = self.local_ttl if library in ("openai",) and provider_key in {
            "ollama_local", "lmstudio", "localai",
        } else self.ttl
        return (time.time() - ts) < ttl

    def invalidate(self, provider_key: str) -> None:
        self._mem.pop(provider_key, None)
        self._save_disk()

    def invalidate_all(self) -> None:
        self._mem.clear()
        self._save_disk()

    async def discover(
        self,
        provider_key: str,
        base_url: str,
        api_key: str = "",
        force: bool = False,
        library: str = "openai",
    ) -> DiscoveryResult:
        """Fetch models from the live endpoint, with cache fallback.

        Args:
            provider_key: Key into ``PROVIDER_REGISTRY``.
            base_url: Endpoint base URL (e.g. ``https://api.openai.com/v1``).
            api_key: Optional API key (sent as ``Authorization: Bearer ...``).
            force: If True, bypass the TTL cache and re-fetch.
            library: ``openai`` or ``ollama_cloud`` – drives the fetch logic.

        Returns:
            DiscoveryResult with the model list and the source
            (``"cache"``, ``"live"``, or ``"fallback"``).
        """
        async with self._lock:
            # 1) Cache hit (and fresh)?
            if not force and self.is_cache_fresh(provider_key, library):
                cached = self.get_cached(provider_key) or []
                return DiscoveryResult(
                    models=cached, source="cache",
                    fetched_at=float(self._mem[provider_key].get("ts", 0)),
                )

            # 2) Live fetch
            if not base_url:
                # No URL → can't fetch, return whatever we have in cache
                cached = self.get_cached(provider_key) or []
                return DiscoveryResult(
                    models=cached, source="cache" if cached else "fallback",
                    error="no base_url",
                )

            try:
                models = await asyncio.to_thread(
                    self._fetch_sync, base_url, api_key, provider_key, library,
                )
            except Exception as e:
                log.warning(f"Model discovery for {provider_key} failed: {e}")
                cached = self.get_cached(provider_key) or []
                return DiscoveryResult(
                    models=cached, source="cache" if cached else "fallback",
                    error=str(e),
                )

            if not models:
                cached = self.get_cached(provider_key) or []
                return DiscoveryResult(
                    models=cached, source="cache" if cached else "fallback",
                    error="endpoint returned no models",
                )

            # 3) Save to cache
            self._mem[provider_key] = {
                "models": models, "ts": time.time(), "source": "live",
            }
            self._save_disk()
            return DiscoveryResult(models=models, source="live", fetched_at=time.time())

    # ── Disk persistence ─────────────────────────────────────

    def _load_disk(self) -> None:
        try:
            if self.cache_path.exists():
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._mem = data
                    log.debug(f"Loaded discovery cache: {len(self._mem)} providers")
        except Exception as e:
            log.debug(f"Failed to load discovery cache: {e}")

    def _save_disk(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._mem, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.cache_path)
        except Exception as e:
            log.debug(f"Failed to save discovery cache: {e}")

    # ── Synchronous fetch helpers (run in thread) ────────────

    def _fetch_sync(
        self,
        base_url: str,
        api_key: str,
        provider_key: str,
        library: str,
    ) -> list[str]:
        if library == "ollama_cloud" or provider_key in self.OLLAMA_CLOUD_KEYS:
            return self._fetch_ollama_cloud(base_url, api_key)
        return self._fetch_openai_compat(base_url, api_key)

    def _fetch_openai_compat(self, base_url: str, api_key: str) -> list[str]:
        """GET {base_url}/models → parse OpenAI-style {data:[{id:...}]}."""
        url = base_url.rstrip("/") + "/models"
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = Request(url, headers=headers)
        with urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"non-JSON response from {url}: {e}")

        models: list[str] = []

        # OpenAI format: {"data": [{"id": "..."}]}
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            for m in data["data"]:
                if isinstance(m, dict):
                    mid = m.get("id") or m.get("name") or m.get("model")
                    if mid:
                        models.append(str(mid))

        # Ollama native /api/tags format: {"models": [{"name": "..."}]}
        if not models and isinstance(data, dict) and isinstance(data.get("models"), list):
            for m in data["models"]:
                if isinstance(m, dict):
                    name = m.get("name") or m.get("model") or m.get("id")
                    if name:
                        models.append(str(name))
                elif isinstance(m, str):
                    models.append(m)

        # Plain list of strings (some proxies)
        if not models and isinstance(data, list):
            for m in data:
                if isinstance(m, str):
                    models.append(m)
                elif isinstance(m, dict) and (m.get("id") or m.get("name")):
                    models.append(str(m.get("id") or m.get("name")))

        # Dedupe, preserve order
        return list(dict.fromkeys(models))

    def _fetch_ollama_cloud(self, base_url: str, api_key: str) -> list[str]:
        """Ollama Cloud uses /api/tags (not /v1/models)."""
        url = "https://ollama.com/api/tags"
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = Request(url, headers=headers)
        with urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        models: list[str] = []
        if isinstance(data, dict) and isinstance(data.get("models"), list):
            for m in data["models"]:
                if isinstance(m, dict) and m.get("name"):
                    models.append(str(m["name"]))
                elif isinstance(m, str):
                    models.append(m)
        return list(dict.fromkeys(models))


# ─────────────────────────────────────────────────────────────
# Singleton + provider-aware helper
# ─────────────────────────────────────────────────────────────

_discovery: Optional[ModelDiscovery] = None


def get_discovery() -> ModelDiscovery:
    """Return the process-wide ModelDiscovery singleton."""
    global _discovery
    if _discovery is None:
        _discovery = ModelDiscovery()
    return _discovery


async def get_provider_models_async(
    provider_key: str,
    custom_base_url: Optional[str] = None,
    force_refresh: bool = False,
) -> DiscoveryResult:
    """Return the live (or cached) model list for a provider.

    Falls back to the hard-coded list in ``PROVIDER_REGISTRY`` if no
    cache and no endpoint are available. Always returns a
    ``DiscoveryResult``; check ``.source`` to know where it came from.
    """
    from brokus.ai.client import PROVIDER_REGISTRY

    cfg = PROVIDER_REGISTRY.get(provider_key)
    fallback = list(cfg.models) if cfg else []

    if not cfg:
        return DiscoveryResult(models=fallback, source="fallback", error="unknown provider")

    discovery = get_discovery()

    if not discovery.is_eligible(provider_key, cfg.library):
        return DiscoveryResult(models=fallback, source="fallback")

    base_url = (custom_base_url or cfg.base_url or "").strip()
    if not base_url:
        return DiscoveryResult(models=fallback, source="fallback", error="no base_url")

    result = await discovery.discover(
        provider_key=provider_key,
        base_url=base_url,
        api_key=cfg.api_key_value,
        force=force_refresh,
        library=cfg.library,
    )

    if not result.models:
        # Discovery succeeded but returned nothing – use fallback
        result.models = fallback
        result.source = "fallback"
    return result


def get_provider_models_sync(
    provider_key: str,
    custom_base_url: Optional[str] = None,
    force_refresh: bool = False,
) -> DiscoveryResult:
    """Sync wrapper for ``get_provider_models_async``.

    Use this from non-async contexts (e.g. the CLI). Raises ``RuntimeError``
    if called from inside a running event loop.
    """
    try:
        asyncio.get_running_loop()
        raise RuntimeError(
            "get_provider_models_sync cannot be called from a running event loop; "
            "use 'await get_provider_models_async' instead."
        )
    except RuntimeError as e:
        if "cannot be called" in str(e):
            raise
        # No running loop → fine
    return asyncio.run(
        get_provider_models_async(provider_key, custom_base_url, force_refresh)
    )
