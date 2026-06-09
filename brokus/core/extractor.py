"""Core element extractor – Stage 0 of the pipeline.

Extracts hard facts from the user's book idea as structured JSON.
These elements are embedded into EVERY subsequent prompt to prevent drift.
"""

import re

from brokus.ai.client import AIClient, LLMResponseError
from brokus.ai.schemas import CoreElementsResponse
from brokus.ai.prompts import PromptLoader
from brokus.ai.models import CoreElements, Setting, Protagonist, Character, MandatoryElement
from brokus.utils.logger import log


# ── Modell-Fallback-Kette (Provider: openrouter) ──
# Alle Modelle müssen von OpenRouter unterstützt werden.
# Siehe config/settings.yaml → openrouter.models für die vollständige Liste.
CORE_ELEMENTS_MODEL_CHAIN: list[str] = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "moonshotai/kimi-k2.6:free",
    "deepseek/deepseek-chat",
    "mistralai/mistral-7b-instruct:free",
]


class CoreElementExtractor:
    """Extracts immutable core elements from a book idea."""

    def __init__(self, client: AIClient, prompts: PromptLoader):
        self.client = client
        self.prompts = prompts

    async def extract(self, book_idea: str, model: Optional[str] = None,
                       disable_fallback_chains: bool = False) -> CoreElements:
        """Extract core elements from the user's book idea.

        Probiert nacheinander mehrere Modelle aus (Modell-Fallback-Kette),
        falls das konfigurierte Modell kein gültiges JSON liefert.

        Args:
            book_idea: The user's detailed book description.
            model: Optional model override for multi-model setups.
            disable_fallback_chains: If True, only use the configured model.

        Returns:
            CoreElements with all extracted immutable story facts.
        """
        log.info("Extracting core elements from book idea...", stage="Kernelemente")

        prompt = self.prompts.format(
            "core_elements_prompt",
            book_idea=book_idea,
        )

        # Modell-Fallback-Kette aufbauen
        # 1. Das explizite Stage-Modell (z.B. aus UI ausgewählt)
        # 2. Primäres Modell des Clients
        # 3. Alle Modelle aus CORE_ELEMENTS_MODEL_CHAIN (nur wenn nicht deaktiviert)
        models_to_try: list[str] = []
        if model:
            models_to_try.append(model)
        default = self.client.model if self.client else ""
        if default and default not in models_to_try:
            models_to_try.append(default)
        if not disable_fallback_chains:
            for m in CORE_ELEMENTS_MODEL_CHAIN:
                if m not in models_to_try:
                    models_to_try.append(m)

        last_exc: Optional[Exception] = None
        for m in models_to_try:
            try:
                if m != models_to_try[0]:
                    log.info(f"Retrying core elements with fallback model: {m}", stage="Kernelemente")

                response = await self.client.generate_model(
                    system_prompt=self.prompts.get("system_prompt"),
                    user_prompt=prompt,
                    schema=CoreElementsResponse,
                    temperature=0.3,
                    model=m,
                )
                elements = self._parse_response(response)
                log.info(f"Core elements extracted successfully with {m}: "
                         f"{len(elements.mandatory_elements)} mandatory elements, "
                         f"{len(elements.characters)} characters",
                         stage="Kernelemente")
                return elements
            except LLMResponseError as e:
                log.warning(f"Model {m} failed: {e}", stage="Kernelemente")
                last_exc = e
            except Exception as e:
                log.warning(f"Model {m} unexpected error: {type(e).__name__}: {e}", stage="Kernelemente")
                last_exc = e

        # Alle Modelle fehlgeschlagen → Fallback
        log.error(f"All models failed for core elements. Last error: {last_exc}", stage="Kernelemente")
        log.warning("Using sentence-based fallback", stage="Kernelemente")
        return self._fallback(book_idea)

    def _parse_response(self, response: CoreElementsResponse) -> CoreElements:
        """Convert typed CoreElementsResponse into internal CoreElements model."""
        setting = Setting(**response.setting.model_dump())
        protagonist = Protagonist(**response.protagonist.model_dump())

        characters = [Character(**c.model_dump()) for c in response.characters]

        mandatory_elements = [
            MandatoryElement(id=e.id or f"elem_{i+1}", description=e.description)
            for i, e in enumerate(response.mandatory_elements)
        ]

        return CoreElements(
            setting=setting,
            protagonist=protagonist,
            characters=characters,
            core_conflict=response.core_conflict,
            mandatory_elements=mandatory_elements,
            themes=response.themes,
            tone=response.tone,
            constraints=response.constraints,
        )

    def _fallback(self, book_idea: str) -> CoreElements:
        """Create minimal core elements as fallback.

        Sentence-basiert und sprach-agnostisch (keine Keyword-Listen).
        Extrahiert den ersten Satz als core_conflict.
        """
        text = book_idea.strip()

        # Sätze splitten (funktioniert für Deutsch und Englisch)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

        # Erste 1–2 Sätze als Kernkonflikt (max. ~300 Zeichen)
        core_conflict = ""
        for s in sentences:
            if core_conflict and len(core_conflict) + len(s) > 300:
                break
            core_conflict = (core_conflict + " " + s).strip() if core_conflict else s
        if not core_conflict:
            core_conflict = text[:300]

        return CoreElements(
            core_conflict=core_conflict,
            themes=["Hauptthema aus Buchidee"],
            tone="neutral",
            constraints=[],
            setting=Setting(),
            protagonist=Protagonist(),
            characters=[],
            mandatory_elements=[
                MandatoryElement(id="elem_1", description="Grundidee umsetzen")
            ],
        )

    def format_for_prompt(self, elements: CoreElements) -> str:
        """Format CoreElements as a condensed string for prompts."""
        lines = [
            "KERNELEMENTE (MÜSSEN beachtet werden):",
            "",
            f"Setting: {elements.setting.world} – {elements.setting.location} – {elements.setting.time_period}",
            f"Atmosphäre: {elements.setting.atmosphere}",
            f"Ton: {elements.tone}",
            "",
            f"Protagonist: {elements.protagonist.name} ({elements.protagonist.age})",
            f"Eigenschaften: {', '.join(elements.protagonist.traits)}",
            f"Motivation: {elements.protagonist.motivation}",
            f"Interner Konflikt: {elements.protagonist.internal_conflict}",
            "",
            "Figuren:",
        ]
        for c in elements.characters:
            lines.append(f"  - {c.name}: {c.role} [{', '.join(c.traits)}]")

        lines.extend([
            "",
            f"Zentraler Konflikt: {elements.core_conflict}",
            f"Themen: {', '.join(elements.themes)}",
            "",
            "Pflichtelemente:",
        ])
        for e in elements.mandatory_elements:
            status = "✓" if e.used else "○"
            lines.append(f"  [{status}] {e.id}: {e.description}")

        if elements.constraints:
            lines.extend([
                "",
                "Constraints (darf NICHT passieren):",
            ])
            for c in elements.constraints:
                lines.append(f"  - {c}")

        return "\n".join(lines)

    def get_pending_elements(self, elements: CoreElements) -> list[MandatoryElement]:
        """Get elements that haven't been used yet."""
        return [e for e in elements.mandatory_elements if not e.used]

    def mark_element_used(self, elements: CoreElements, element_id: str):
        """Mark a mandatory element as used."""
        for e in elements.mandatory_elements:
            if e.id == element_id:
                e.used = True
                break

    def to_dict(self, elements: CoreElements) -> dict:
        """Convert CoreElements to a JSON-serializable dict."""
        return elements.model_dump()

    def from_dict(self, data: dict) -> CoreElements:
        """Reconstruct CoreElements from a dict."""
        return CoreElements(**data)
