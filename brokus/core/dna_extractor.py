"""DNA Extractor – Schicht 1: Pre-Generation Lock.

Extrahiert die unveränderliche Buch-DNA aus der User-Idee.
Diese DNA wird in JEDEN Prompt eingebettet und verhindert Drift.
"""

from brokus.ai.client import AIClient, LLMResponseError
from brokus.ai.prompts import PromptLoader
from brokus.ai.schemas import DNAResponse, Handlungselement
from brokus.utils.logger import log


class DNAExtractor:
    """Extracts immutable DNA from a book idea (Schicht 1)."""

    def __init__(self, client: AIClient, prompts: PromptLoader):
        self.client = client
        self.prompts = prompts

    async def extract(self, user_idea: str, model: Optional[str] = None) -> DNAResponse:
        """Extract the unchangeable book DNA.

        Args:
            user_idea: The user's book description.
            model: Optional model override for multi-model setups.

        Returns a typed DNAResponse with Pydantic-validated fields.
        """
        log.info("Extracting book DNA...", stage="DNA")

        prompt = self.prompts.format("dna_extraction_prompt", user_idea=user_idea)

        try:
            dna = await self.client.generate_model(
                system_prompt=self.prompts.get("system_prompt"),
                user_prompt=prompt,
                schema=DNAResponse,
                temperature=0.2,
                model=model,
            )
            log.info(
                f"DNA extracted: {len(dna.pflicht_handlungselemente)} "
                f"mandatory elements, {len(dna.verbotene_abweichungen)} "
                f"forbidden deviations",
                stage="DNA",
            )
            return dna
        except LLMResponseError as e:
            log.warning(f"DNA extraction failed: {e}, using fallback", stage="DNA")
            return self._fallback_dna(user_idea)

    def _fallback_dna(self, user_idea: str) -> DNAResponse:
        """Minimal DNA as fallback."""
        return DNAResponse(
            setting={"ort": "Unbekannt", "ausgangssituation": user_idea[:200]},
            pflicht_handlungselemente=[
                Handlungselement(name="Die Grundidee umsetzen", description="Die Grundidee des Buches umsetzen")
            ],
            verbotene_abweichungen=[],
            themen_pflicht=[],
            ton="neutral",
        )

    def format_for_prompt(self, dna: DNAResponse, extra: dict | None = None) -> str:
        """Format DNA as a prominent prompt block.

        Args:
            dna: The extracted DNAResponse.
            extra: Optional extra context (e.g., protagonist age).
        """
        prot = dna.protagonistin if dna.protagonistin.name else dna.protagonist
        lines = [
            "════════════════════════════════════════════",
            "🧬 BUCH-DNA (UNVERÄNDERLICH – LIES ZUERST)",
            "════════════════════════════════════════════",
            "",
        ]

        if prot.name:
            age = extra.get("protagonist_age", prot.alter_start) if extra else prot.alter_start
            lines.append(f"PROTAGONIST: {prot.name}, {age} Jahre, {prot.geschlecht}")
            lines.append(f"Rolle: {prot.rolle}")
            lines.append("")

        lines.append(f"SETTING: {dna.setting.ort} – {dna.setting.ausgangssituation}")
        if dna.perspektive:
            lines.append(f"PERSPEKTIVE: {dna.perspektive}")
        lines.append("")

        if dna.verbotene_abweichungen:
            lines.append("🚫 ABSOLUT VERBOTEN:")
            for item in dna.verbotene_abweichungen:
                lines.append(f"  ❌ {item}")
            lines.append("")

        mandatory = dna.pflicht_handlungselemente
        lines.append(f"✅ PFLICHT-ELEMENTE GESAMT ({len(mandatory)}):")
        for item in mandatory:
            marker = "✅" if item.done else "⏳"
            lines.append(f"  {marker} {item.description or item.name}")
        lines.append("")

        themes = dna.themen_pflicht or dna.required_themes
        if themes:
            lines.append(f"THEMEN PFLICHT: {', '.join(themes)}")

        tone = dna.ton or dna.tone
        if tone:
            lines.append(f"TON: {tone}")

        lines.append("")
        return "\n".join(lines)

    def get_mandatory_elements(self, dna: DNAResponse) -> list[str]:
        """Get list of mandatory element descriptions."""
        return [e.description or e.name for e in dna.pflicht_handlungselemente]

    def get_forbidden_deviations(self, dna: DNAResponse) -> list[str]:
        """Get list of forbidden deviations."""
        return dna.verbotene_abweichungen
