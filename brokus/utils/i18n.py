"""Lightweight JSON-based i18n for brokus.

Design:
- Translation files live in ``data/i18n/{lang}.json``
- ``t("key")`` looks up the key in the active language, falling back
  to the default language (German) and finally returning the key itself
  so missing translations are immediately visible in the UI.
- ``{var}`` placeholders are substituted using ``str.format(**kwargs)``.
- Languages can be switched at runtime via ``set_language()``.
- The current language is persisted in ``Settings.ui_language`` so it
  survives restarts.

Quick start:
    from brokus.utils.i18n import t, set_language, get_language
    set_language("en")
    print(t("main.title"))           # "What do you want to do?"
    print(t("models.discovered", n=42))  # "42 models discovered"
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

_I18N_DIR = Path("data/i18n")
_DEFAULT_LANG = "de"
_AVAILABLE = ("de", "en", "fr", "es", "it", "nl")

# In-memory cache: { lang: { key: value } }
_TRANSLATIONS: dict[str, dict[str, str]] = {}
# Currently active language code
_CURRENT_LANG: str = _DEFAULT_LANG
_LANGUAGE_LOADED: set[str] = set()


# ─────────────────────────────────────────────────────────────
# File loading
# ─────────────────────────────────────────────────────────────

def _load(lang: str) -> dict[str, str]:
    """Load translations for ``lang`` from disk (cached)."""
    if lang in _LANGUAGE_LOADED:
        return _TRANSLATIONS.get(lang, {})

    path = _I18N_DIR / f"{lang}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                _TRANSLATIONS[lang] = {str(k): str(v) for k, v in data.items()}
            else:
                _TRANSLATIONS[lang] = {}
        except Exception:
            _TRANSLATIONS[lang] = {}
    else:
        _TRANSLATIONS[lang] = {}

    _LANGUAGE_LOADED.add(lang)
    return _TRANSLATIONS[lang]


def reload_language(lang: Optional[str] = None) -> None:
    """Drop the cache for ``lang`` (or all languages) so files are re-read."""
    global _LANGUAGE_LOADED
    if lang is None:
        _LANGUAGE_LOADED.clear()
        _TRANSLATIONS.clear()
    else:
        _LANGUAGE_LOADED.discard(lang)
        _TRANSLATIONS.pop(lang, None)


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def set_language(lang: str) -> bool:
    """Switch the active language. Returns True on success.

    Falls back to the default language if the requested one is unknown
    or has no translation file.
    """
    global _CURRENT_LANG
    if lang not in _AVAILABLE:
        return False
    # Pre-load to fail fast if the file is missing
    _load(lang)
    _CURRENT_LANG = lang
    return True


def get_language() -> str:
    """Return the currently active language code."""
    return _CURRENT_LANG


def available_languages() -> tuple[str, ...]:
    """Return the tuple of supported language codes."""
    return _AVAILABLE


def language_name(code: str) -> str:
    """Return the human-readable name of a language code (always localized)."""
    names = {
        "de": "Deutsch",
        "en": "English",
        "fr": "Français",
        "es": "Español",
        "it": "Italiano",
        "nl": "Nederlands",
    }
    return names.get(code, code)


def t_label(category: str, key: str, default: Optional[str] = None) -> str:
    """Look up a translated label for a YAML/config entry by category.

    Convenience wrapper for keys like ``"genre.drama.name"`` or
    ``"provider.anthropic.note"``. Falls back through the same chain
    as :func:`t` (active language → default → default value → key).

    Parameters
    ----------
    category : str
        Top-level namespace, e.g. ``"genre"`` or ``"provider"``.
    key : str
        Entry key, e.g. ``"drama"`` or ``"anthropic"``.
    default : str, optional
        Value to return when neither the active language nor the
        default language has a translation. Defaults to the key itself.

    Examples
    --------
    >>> t_label("genre", "drama")  # current language's "Drama"
    >>> t_label("provider", "anthropic", default="Anthropic")
    """
    full = f"{category}.{key}"
    text = _load(_CURRENT_LANG).get(full)
    if text is None and _CURRENT_LANG != _DEFAULT_LANG:
        text = _load(_DEFAULT_LANG).get(full)
    if text is None:
        return default if default is not None else full
    return text


def t(key: str, **kwargs) -> str:
    """Translate ``key`` using the active language.

    - Falls back to the default language if the key is missing.
    - Falls back to the key itself if still missing (helps spot gaps).
    - Substitutes ``{name}`` placeholders from ``kwargs``.

    Example:
        t("models.discovered", n=42)  # → "42 Modelle entdeckt"
    """
    if not key:
        return ""

    # 1) Try active language
    text = _load(_CURRENT_LANG).get(key)
    # 2) Try default language
    if text is None and _CURRENT_LANG != _DEFAULT_LANG:
        text = _load(_DEFAULT_LANG).get(key)
    # 3) Last resort: the key itself
    if text is None:
        return key

    # Substitute placeholders if any kwargs were passed
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


# ─────────────────────────────────────────────────────────────
# Bootstrap: detect language from env / LANG on first import
# ─────────────────────────────────────────────────────────────

def detect_system_language() -> Optional[str]:
    """Detect the user's preferred language from common env vars.

    Checks ``BROKUS_LANG``, then ``LANG`` and ``LANGUAGE``.
    Returns the first supported language code, or None.
    """
    candidates = []
    env_lang = os.environ.get("BROKUS_LANG")
    if env_lang:
        candidates.append(env_lang)
    for var in ("LANGUAGE", "LANG", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(var, "")
        if val:
            candidates.append(val)

    for cand in candidates:
        # Try exact match first
        if cand in _AVAILABLE:
            return cand
        # Try first part before "_" or "."
        primary = cand.split("_")[0].split(".")[0].lower()
        if primary in _AVAILABLE:
            return primary
    return None


# Auto-detect on import (only if user hasn't set explicitly)
_detected = detect_system_language()
if _detected:
    _CURRENT_LANG = _detected
