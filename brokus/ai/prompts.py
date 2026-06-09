"""Prompt loader from YAML configuration."""

import yaml
from pathlib import Path
from typing import Optional

from brokus.utils.logger import log
from brokus.utils.i18n import t_label

# Default config directory: <project_root>/config
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

class PromptLoader:
    """Loads and formats prompts from config/prompts.yaml."""

    def __init__(self, prompts_path: Path = _CONFIG_DIR / "prompts.yaml"):
        self.prompts_path = prompts_path
        self._prompts: dict = {}
        self.load()

    def load(self):
        """Load prompts from YAML file."""
        if self.prompts_path.exists():
            with open(self.prompts_path, "r", encoding="utf-8") as f:
                self._prompts = yaml.safe_load(f) or {}
                log.debug(f"Loaded {len(self._prompts)} prompts from {self.prompts_path}")
        else:
            log.warning(f"Prompts file not found: {self.prompts_path}")

    def get(self, name: str) -> str:
        """Get a prompt template by name."""
        return self._prompts.get(name, "")

    def format(
        self,
        name: str,
        **kwargs,
    ) -> str:
        """Get and format a prompt template with keyword arguments."""
        template = self.get(name)
        if not template:
            log.error(f"Prompt '{name}' not found")
            return ""

        try:
            # Use {placeholder} format, escape any unmatched
            formatted = template
            for key, value in kwargs.items():
                placeholder = "{" + key + "}"
                formatted = formatted.replace(placeholder, str(value))
            return formatted
        except Exception as e:
            log.error(f"Failed to format prompt '{name}': {e}")
            return template


class GenreLoader:
    """Loads genre definitions from config/genres.yaml."""

    def __init__(self, genres_path: Path = _CONFIG_DIR / "genres.yaml"):
        self.genres_path = genres_path
        self._genres: dict = {}
        self.load()

    def load(self):
        """Load genres from YAML file."""
        if self.genres_path.exists():
            with open(self.genres_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self._genres = data.get("genres", {})
                log.debug(f"Loaded {len(self._genres)} genres from {self.genres_path}")
        else:
            log.warning(f"Genres file not found: {self.genres_path}")

    def get_genre(self, genre_key: str) -> Optional[dict]:
        """Get a genre by its key."""
        return self._genres.get(genre_key)

    def get_style_hint(self, genre_key: str) -> str:
        """Get the style hint for a genre (falls back to YAML value)."""
        genre = self.get_genre(genre_key)
        if not genre:
            return ""
        # The style_hint is a technical instruction; only override if i18n has one.
        translated = t_label("genre", f"{genre_key}.style_hint", default="")
        return translated or genre.get("style_hint", "")

    def get_name(self, genre_key: str) -> str:
        """Get the display name for a genre (i18n-aware)."""
        genre = self.get_genre(genre_key)
        fallback = genre.get("name", genre_key) if genre else genre_key
        return t_label("genre", f"{genre_key}.name", default=fallback)

    @property
    def genre_keys(self) -> list[str]:
        """List all available genre keys."""
        return list(self._genres.keys())

    @property
    def genre_names(self) -> dict[str, str]:
        """Mapping of genre keys to display names."""
        return {k: self.get_name(k) for k in self._genres}
