"""Core element extractor – Stage 0 of the pipeline.

Extracts hard facts from the user's book idea as structured JSON.
These elements are embedded into EVERY subsequent prompt to prevent drift.
"""

from brokus.ai.client import AIClient, LLMResponseError
from brokus.ai.prompts import PromptLoader
from brokus.ai.models import CoreElements, Setting, Protagonist, Character, MandatoryElement
from brokus.ai.schemas import CoreElementsResponse
from brokus.utils.logger import log


class CoreElementExtractor:
    """Extracts immutable core elements from a book idea."""

    def __init__(self, client: AIClient, prompts: PromptLoader):
        self.client = client
        self.prompts = prompts

    async def extract(self, book_idea: str) -> CoreElements:
        """Extract core elements from the user's book idea.

        Args:
            book_idea: The user's detailed book description.

        Returns:
            CoreElements with all extracted immutable story facts.
        """
        log.info("Extracting core elements from book idea...", stage="Kernelemente")

        prompt = self.prompts.format(
            "core_elements_prompt",
            book_idea=book_idea,
        )

        try:
            response = await self.client.generate_model(
                system_prompt=self.prompts.get("system_prompt"),
                user_prompt=prompt,
                schema=CoreElementsResponse,
                temperature=0.3,
            )
            elements = self._parse_response(response)
            log.info(f"Extracted {len(elements.mandatory_elements)} mandatory elements, "
                     f"{len(elements.characters)} characters",
                     stage="Kernelemente")
            return elements
        except (LLMResponseError, Exception) as e:
            log.error(f"Failed to parse core elements: {e}", stage="Kernelemente")
            log.warning("Using fallback with minimal elements", stage="Kernelemente")
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
        """Create minimal core elements as fallback."""
        words = book_idea.split()
        first_50 = " ".join(words[:50]) + "..."
        return CoreElements(
            core_conflict=first_50,
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
