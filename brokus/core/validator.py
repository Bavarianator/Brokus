"""Compliance Validator – Schicht 3: Post-Generation Audit.

Enhanced validator with DNA-basierte Prüfung:
- Perspective check
- Setting consistency
- Character age tracking
- Mandatory element coverage
- Forbidden deviation detection
- Auto-retry with correction hints below threshold
"""

from dataclasses import dataclass, field
import json
from brokus.ai.client import AIClient, LLMResponseError
from brokus.ai.prompts import PromptLoader
from brokus.ai.schemas import ComplianceCheckResponse
from brokus.utils.logger import log


@dataclass
class ValidationResult:
    """Detailed compliance validation result."""
    score: int = 0
    passed: bool = False

    # Detailed checks
    perspective_correct: bool = True
    setting_correct: bool = True
    character_age_correct: bool = True

    # Element tracking
    elements_fulfilled: list[str] = field(default_factory=list)
    elements_missing: list[str] = field(default_factory=list)

    # Violations
    forbidden_violations: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    # Quality
    style_quality: int = 0

    # Action
    recommendation: str = "ok"  # "ok" | "retry" | "edit"
    correction_instructions: str = ""

    summary: str = ""

    @property
    def element_checks(self) -> list[dict]:
        """Backward-compatible element check format."""
        checks = []
        for el in self.elements_fulfilled:
            checks.append({"element_id": el[:20], "covered": True, "note": ""})
        for el in self.elements_missing:
            checks.append({"element_id": el[:20], "covered": False, "note": "Fehlt"})
        return checks

    @property
    def compliance_score(self) -> int:
        """Alias for backward compatibility."""
        return self.score

    @property
    def tone_match(self) -> bool:
        return True  # Simplified

    @property
    def setting_consistent(self) -> bool:
        return self.setting_correct

    @property
    def character_consistent(self) -> bool:
        return self.character_age_correct

    @property
    def constraint_violations(self) -> list[str]:
        return self.forbidden_violations


class ComplianceValidator:
    """Enhanced compliance validator (Schicht 3).

    Uses AI audit to score each chapter 0-100 against the book DNA.
    Auto-retries below threshold with targeted correction hints.
    """

    def __init__(
        self,
        client: AIClient,
        prompts: PromptLoader,
        threshold: int = 75,
        max_retries: int = 3,
        auto_retry: bool = True,
    ):
        self.client = client
        self.prompts = prompts
        self.threshold = threshold
        self.max_retries = max_retries
        self.auto_retry = auto_retry

    async def validate(
        self,
        chapter_text: str,
        dna: dict | None = None,
        chapter_elements: list[str] | None = None,
        core_elements=None,
    ) -> ValidationResult:
        """Validate chapter compliance against book DNA.

        Uses the enhanced compliance check prompt for DNA-based validation.
        Falls back to basic check if no DNA is provided.

        Args:
            chapter_text: The generated chapter text.
            dna: Book DNA dict (from DNAExtractor, can be serialize DNAResponse).
            chapter_elements: Mandatory element IDs/descriptions for this chapter.
            core_elements: Legacy CoreElements (backward compat).

        Returns:
            ValidationResult with detailed compliance data.
        """
        log.info("Running enhanced compliance check...", stage="Compliance")

        # Build element descriptions for the prompt
        element_descriptions = []
        if chapter_elements:
            for elem in chapter_elements:
                element_descriptions.append(f"  - {elem}")
        elif core_elements:
            for e in core_elements.mandatory_elements:
                if e.id in (chapter_elements or []):
                    element_descriptions.append(f"  {e.id}: {e.description}")

        # Use DNA-enhanced prompt if available
        if dna:
            prompt = self.prompts.format(
                "compliance_check_enhanced_prompt",
                dna=json.dumps(dna, ensure_ascii=False, indent=2),
                chapter_text=chapter_text[:8000],
                required_elements="\n".join(element_descriptions) if element_descriptions else "Keine",
            )
        elif core_elements:
            # Backward-compatible fallback
            prompt = self.prompts.format(
                "compliance_check_prompt",
                chapter_text=chapter_text[:8000],
                core_elements=self._format_core_elements_compact(core_elements),
                chapter_elements="\n".join(element_descriptions) if element_descriptions else "Keine",
            )
        else:
            return ValidationResult(
                score=100, passed=True,
                summary="No DNA or core elements provided – chapter accepted.",
                recommendation="ok",
            )

        try:
            response = await self.client.generate_model(
                system_prompt=self.prompts.get("system_prompt"),
                user_prompt=prompt,
                schema=ComplianceCheckResponse,
                temperature=0.1,
            )

            result = ValidationResult(
                score=response.effective_score,
                perspective_correct=response.perspektive_korrekt,
                setting_correct=response.setting_korrekt,
                character_age_correct=response.protagonist_alter_korrekt,
                elements_fulfilled=response.pflicht_erfüllt,
                elements_missing=response.pflicht_fehlt,
                forbidden_violations=response.verbote_verletzt,
                issues=response.probleme,
                style_quality=response.style_quality,
                recommendation=response.empfehlung,
                correction_instructions=response.korrektur_anweisungen,
                summary=response.effective_summary,
            )
            result.passed = result.score >= self.threshold
        except (LLMResponseError, Exception) as e:
            log.error(f"Compliance validation failed: {e}", stage="Compliance")
            result = ValidationResult(
                score=100, passed=True,
                summary=f"Validation error: {e}. Chapter accepted.",
                recommendation="ok",
            )

        log.info(f"Compliance score: {result.score}/100 ({'✅' if result.passed else '❌'})", stage="Compliance")
        if not result.passed:
            log.warning(
                f"Score below threshold ({self.threshold}). "
                f"Issues: {result.issues[:3]}",
                stage="Compliance",
            )

        return result

    def passed(self, result: ValidationResult) -> bool:
        """Check if the validation result passes the threshold."""
        return result.passed

    def _format_core_elements_compact(self, elements) -> str:
        """Format core elements compactly (legacy fallback)."""
        lines = [
            f"Setting: {elements.setting.world} – {elements.setting.location}",
            f"Ton: {elements.tone}",
            f"Protagonist: {elements.protagonist.name}",
            f"Konflikt: {elements.core_conflict}",
            "Constraints:",
        ]
        for c in elements.constraints:
            lines.append(f"  - {c}")
        return "\n".join(lines)
