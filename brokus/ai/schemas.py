"""Pydantic response schemas for LLM API responses.

Every generate_model() call validates against one of these schemas.
This guarantees that internal code never sees raw dicts from the AI.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────
# DNA Extraction (dna_extractor.py)
# ─────────────────────────────────────────────────────────────

class ProtagonistData(BaseModel):
    """Protagonist extracted from the book idea (German field names from AI)."""
    name: str = ""
    alter_start: int = 16
    geschlecht: str = ""
    rolle: str = ""

    @field_validator("name")
    @classmethod
    def not_none(cls, v):
        return v or ""


class SettingData(BaseModel):
    """Setting extracted from the book idea."""
    ort: str = ""
    ausgangssituation: str = ""


class Handlungselement(BaseModel):
    """A mandatory plot element – can be a string or dict from the AI."""
    name: str = ""
    description: str = ""
    done: bool = False

    @field_validator("done", mode="before")
    @classmethod
    def coerce_done(cls, v):
        """AI may return done as string ('true'), None, or omit it."""
        return bool(v) if v else False

    @field_validator("description", mode="before")
    @classmethod
    def coerce_description(cls, v, info):
        """If the AI returns {'name': '...'} without description, use name."""
        if not v and info.data.get("name"):
            return info.data["name"]
        return v or ""

    @classmethod
    def coerce(cls, v):
        """Accept both strings and dicts."""
        if isinstance(v, str):
            return cls(name=v, description=v)
        if isinstance(v, dict):
            # Ensure description is set from name if absent
            if "description" not in v and "name" in v:
                v = dict(v)
                v["description"] = v["name"]
            return cls(**v)
        return cls(description=str(v))


class DNAResponse(BaseModel):
    """Full DNA response from the LLM."""
    protagonistin: ProtagonistData = Field(default_factory=ProtagonistData)
    protagonist: ProtagonistData = Field(default_factory=ProtagonistData)
    setting: SettingData = Field(default_factory=SettingData)
    gruppe: dict = Field(default_factory=lambda: {"anzahl": 0, "typ": ""})
    zeitspanne: str = ""
    perspektive: str = ""
    pflicht_handlungselemente: list[Handlungselement] = Field(default_factory=list)
    verbotene_abweichungen: list[str] = Field(default_factory=list)
    themen_pflicht: list[str] = Field(default_factory=list)
    required_themes: list[str] = Field(default_factory=list)
    ton: str = ""
    tone: str = ""

    @field_validator("pflicht_handlungselemente", mode="before")
    @classmethod
    def normalize_elements(cls, v):
        """Normalize strings → Handlungselement instances."""
        if not isinstance(v, list):
            return []
        return [Handlungselement.coerce(x) for x in v]

    def to_prompt_block(self) -> str:
        """Format as DNA block for chapter prompts."""
        prot = self.protagonistin if self.protagonistin.name else self.protagonist
        lines = [
            "🧬 BUCH-DNA (UNVERÄNDERLICH)",
            f"PROTAGONIST: {prot.name}, {prot.alter_start} Jahre",
            f"SETTING: {self.setting.ort} – {self.setting.ausgangssituation}",
            f"PERSPEKTIVE: {self.perspektive}",
            "",
        ]
        if self.verbotene_abweichungen:
            lines.append("🚫 VERBOTEN:")
            for item in self.verbotene_abweichungen:
                lines.append(f"  ❌ {item}")
            lines.append("")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Core Elements Extraction (extractor.py)
# ─────────────────────────────────────────────────────────────

class SettingResponse(BaseModel):
    world: str = ""
    location: str = ""
    time_period: str = ""
    atmosphere: str = ""


class ProtagonistResponse(BaseModel):
    name: str = ""
    age: str = ""
    traits: list[str] = Field(default_factory=list)
    motivation: str = ""
    internal_conflict: str = ""


class CharacterResponse(BaseModel):
    name: str = ""
    role: str = ""
    traits: list[str] = Field(default_factory=list)


class MandatoryElementResponse(BaseModel):
    id: str = ""
    description: str = ""

    @classmethod
    def coerce(cls, v):
        if isinstance(v, str):
            return cls(description=v)
        if isinstance(v, dict):
            return cls(**v)
        return cls(description=str(v))


class CoreElementsResponse(BaseModel):
    """Raw response from the core_elements_prompt."""
    setting: SettingResponse = Field(default_factory=SettingResponse)
    protagonist: ProtagonistResponse = Field(default_factory=ProtagonistResponse)
    characters: list[CharacterResponse] = Field(default_factory=list)
    core_conflict: str = ""
    mandatory_elements: list[MandatoryElementResponse] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    tone: str = ""
    constraints: list[str] = Field(default_factory=list)

    @field_validator("mandatory_elements", mode="before")
    @classmethod
    def normalize_elements(cls, v):
        if not isinstance(v, list):
            return []
        return [MandatoryElementResponse.coerce(x) for x in v]

    @field_validator("characters", mode="before")
    @classmethod
    def normalize_characters(cls, v):
        if not isinstance(v, list):
            return []
        result = []
        for c in v:
            if isinstance(c, str):
                result.append(CharacterResponse(name=c))
            elif isinstance(c, dict):
                result.append(CharacterResponse(**c))
        return result


# ─────────────────────────────────────────────────────────────
# Character Profiles (pipeline.py _generate_characters)
# ─────────────────────────────────────────────────────────────

class CharacterProfileResponse(BaseModel):
    """A single character profile – may be a dict or string from the AI."""
    name: str
    age: int = 0
    appearance: str = ""
    personality: str = ""
    background: str = ""
    motivation: str = ""
    internal_conflict: str = ""
    external_conflict: str = ""
    relationships: str = ""
    speech_patterns: str = ""
    arc: str = ""


# ─────────────────────────────────────────────────────────────
# Chapter Plan (pipeline.py _generate_chapter_plan)
# ─────────────────────────────────────────────────────────────

class ChapterPlanResponse(BaseModel):
    """A single chapter plan entry from the AI."""
    number: int
    title: str = ""
    summary: str = ""
    elements: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    setting: str = ""
    mood: str = ""
    estimated_words: int = 2000


# ─────────────────────────────────────────────────────────────
# Compliance Check (validator.py)
# ─────────────────────────────────────────────────────────────

class ComplianceCheckItem(BaseModel):
    """A single compliance check result."""
    name: str
    passed: bool = False
    severity: str = "warning"
    note: str = ""


class CharacterProfileListResponse(BaseModel):
    """Wrapper for AI response returning a list of character profiles."""
    characters: list[CharacterProfileResponse] = Field(default_factory=list)


class ChapterPlanListResponse(BaseModel):
    """Wrapper for AI response returning a list of chapter plans."""
    chapters: list[ChapterPlanResponse] = Field(default_factory=list)


class ComplianceCheckResponse(BaseModel):
    """Raw response from the compliance_check_enhanced_prompt."""
    score: int = 0
    compliance_score: int = 0
    perspektive_korrekt: bool = True
    setting_korrekt: bool = True
    protagonist_alter_korrekt: bool = True
    pflicht_erfüllt: list[str] = Field(default_factory=list)
    pflicht_fehlt: list[str] = Field(default_factory=list)
    verbote_verletzt: list[str] = Field(default_factory=list)
    probleme: list[str] = Field(default_factory=list)
    style_quality: int = 7
    empfehlung: str = "ok"
    korrektur_anweisungen: str = ""
    summary: str = ""
    zusammenfassung: str = ""

    @property
    def effective_score(self) -> int:
        return self.score or self.compliance_score

    @property
    def effective_summary(self) -> str:
        return self.summary or self.zusammenfassung or ""
