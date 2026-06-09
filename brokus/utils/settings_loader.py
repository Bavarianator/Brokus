"""Centralized settings loader for brokus.

Loads the full settings.yaml from config/ and exposes a single
``load_settings()`` function that returns a typed dict with all sections.

The CLI and TUI both use this to keep the configuration surface in sync.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from brokus.utils.logger import log


_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_SETTINGS_PATH = _CONFIG_DIR / "settings.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into ``base`` (override wins)."""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings(path: Path | None = None) -> dict[str, Any]:
    """Load the full settings.yaml and return it as a nested dict.

    Returns a deep-merged config of on-disk settings and sensible defaults,
    so callers can rely on every key existing.
    """
    p = path or _SETTINGS_PATH
    defaults: dict[str, Any] = {
        "ai": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "temperature": 0.7,
            "max_tokens": 4000,
            "top_p": None,
            "frequency_penalty": None,
            "presence_penalty": None,
            "max_retries": 3,
            "retry_delay": 1.0,
            "custom_base_url": None,
        },
        "generation": {
            "min_chapter_words": 1500,
            "max_chapter_words": 3000,
            "compliance_threshold": 80,
            "auto_retry": True,
            "max_retries": 3,
            "default_chapters": 20,
            "max_chapters": 50,
            "min_chapters": 5,
            "chapter_delay": 2.0,
            "default_language": "Deutsch",
            "default_genre": "drama",
            "story_pace": "balanced",
            "detail_level": "standard",
            "auto_export": False,
            "auto_open_after_export": True,
            "export_formats": ["md", "epub"],
            "backup_enabled": True,
            "backup_count": 5,
            "save_drafts": True,
        },
        "ui": {
            "theme": "dark",
            "animations": True,
            "log_level": "INFO",
            "show_token_count": True,
            "show_cost_estimate": True,
            "progress_style": "bar",
            "confirm_quit": True,
        },
        "storage": {
            "database_path": "data/projects.db",
            "books_path": "data/books",
            "backups_path": "data/backups",
            "max_projects": 0,
        },
        "advanced": {
            "use_extended_thinking": False,
            "parallel_chapters": 1,
            "request_timeout": 300,
            "streaming": False,
            "cache_responses": True,
            "max_cache_size_mb": 500,
        },
    }
    if not p.exists():
        log.debug(f"Settings file not found: {p}; using defaults")
        return defaults
    try:
        with open(p, "r", encoding="utf-8") as f:
            on_disk = yaml.safe_load(f) or {}
        return _deep_merge(defaults, on_disk)
    except Exception as e:
        log.warning(f"Failed to load settings from {p}: {e}")
        return defaults


def save_settings(settings: dict[str, Any], path: Path | None = None) -> bool:
    """Persist the full settings dict back to YAML."""
    p = path or _SETTINGS_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(settings, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        log.error(f"Failed to save settings to {p}: {e}")
        return False


def get_ai_config() -> dict[str, Any]:
    """Convenience: return just the ``ai`` section."""
    return load_settings().get("ai", {})


def get_generation_config() -> dict[str, Any]:
    """Convenience: return just the ``generation`` section."""
    return load_settings().get("generation", {})


def get_advanced_config() -> dict[str, Any]:
    """Convenience: return just the ``advanced`` section."""
    return load_settings().get("advanced", {})
