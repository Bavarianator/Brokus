"""Data models for brokus using Pydantic."""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ChapterStatus(str, Enum):
    PLANNED = "planned"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Setting(BaseModel):
    world: str = ""
    location: str = ""
    time_period: str = ""
    atmosphere: str = ""

    def __init__(self, **data):
        # Coerce None values to empty strings (AI sometimes returns null)
        for k, v in data.items():
            if v is None:
                data[k] = ""
        super().__init__(**data)


class Protagonist(BaseModel):
    name: str = ""
    age: str = ""
    traits: list[str] = Field(default_factory=list)
    motivation: str = ""
    internal_conflict: str = ""

    def __init__(self, **data):
        for k, v in data.items():
            if v is None:
                data[k] = "" if k != "traits" else []
            if k == "age" and not isinstance(v, str):
                data[k] = str(v) if v is not None else ""
        super().__init__(**data)


class Character(BaseModel):
    name: str = ""
    role: str = ""
    traits: list[str] = Field(default_factory=list)

    def __init__(self, **data):
        for k, v in data.items():
            if v is None:
                data[k] = "" if k != "traits" else []
        super().__init__(**data)


class MandatoryElement(BaseModel):
    id: str
    description: str
    used: bool = False


class CoreElements(BaseModel):
    setting: Setting = Field(default_factory=Setting)
    protagonist: Protagonist = Field(default_factory=Protagonist)
    characters: list[Character] = Field(default_factory=list)
    core_conflict: str = ""
    mandatory_elements: list[MandatoryElement] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    tone: str = ""
    constraints: list[str] = Field(default_factory=list)


class ChapterPlanEntry(BaseModel):
    number: int
    title: str
    summary: str = ""
    elements: list[str] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    setting: str = ""
    mood: str = ""
    estimated_words: int = 2000


class CharacterProfile(BaseModel):
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


class ComplianceResult(BaseModel):
    compliance_score: int = 0
    element_checks: list[dict] = Field(default_factory=list)
    tone_match: bool = True
    setting_consistent: bool = True
    character_consistent: bool = True
    constraint_violations: list[str] = Field(default_factory=list)
    style_quality: int = 0
    correction_instructions: str = ""
    summary: str = ""


class ProjectConfig(BaseModel):
    project_id: int
    title: str
    genre: str
    idea: str
    total_chapters: int = 20
    model: str = "claude-sonnet-4-20250514"
    core_elements: Optional[CoreElements] = None
    synopsis: str = ""
    characters: list[CharacterProfile] = Field(default_factory=list)
    chapter_plan: list[ChapterPlanEntry] = Field(default_factory=list)
    status: ProjectStatus = ProjectStatus.DRAFT
