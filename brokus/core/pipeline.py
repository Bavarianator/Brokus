"""5-Stage book generation pipeline.

Orchestrates: DNA → Core Elements → Synopsis → Characters → Chapter Plan → Chapter Loop.
"""

import asyncio
import json
from typing import Optional, Callable

from brokus.ai.client import AIClient, LLMResponseError
from brokus.ai.prompts import PromptLoader, GenreLoader
from brokus.ai.models import CoreElements
from brokus.ai.schemas import CharacterProfileListResponse, ChapterPlanListResponse, DNAResponse
from brokus.core.extractor import CoreElementExtractor
from brokus.core.dna_extractor import DNAExtractor
from brokus.core.context import StoryContextBuilder
from brokus.core.tracker import StoryTracker
from brokus.utils.logger import log


ProgressCallback = Callable[[str, float, str], None]


class BookPipeline:
    """Orchestrates book generation."""

    def __init__(
        self,
        client: AIClient,
        prompts: PromptLoader,
        genres: GenreLoader,
        min_chapter_words: int = 1500,
        max_chapter_words: int = 3000,
        temperature: float = 0.7,
        chapter_delay: float = 2.0,
        default_language: str = "Deutsch",
        detail_level: str = "standard",
        story_pace: str = "balanced",
        use_extended_thinking: bool = False,
        auto_export: bool = False,
        auto_open_after_export: bool = True,
        backup_enabled: bool = True,
    ):
        self.client = client
        self.prompts = prompts
        self.genres = genres
        self.extractor = CoreElementExtractor(client, prompts)
        self.dna_extractor = DNAExtractor(client, prompts)
        self.context_builder = StoryContextBuilder()
        self.tracker: Optional[StoryTracker] = None

        self.min_chapter_words = min_chapter_words
        self.max_chapter_words = max_chapter_words
        self._temperature = temperature
        self._chapter_delay = chapter_delay
        self._default_language = default_language
        self._detail_level = detail_level
        self._story_pace = story_pace
        self._use_extended_thinking = use_extended_thinking
        self._auto_export = auto_export
        self._auto_open_after_export = auto_open_after_export
        self._backup_enabled = backup_enabled

        self._progress_callback: Optional[ProgressCallback] = None
        self._paused = False
        self._stopped = False

    def set_progress_callback(self, callback: ProgressCallback):
        self._progress_callback = callback

    def pause(self):
        self._paused = True
        log.info("Pipeline paused")

    def resume(self):
        self._paused = False
        log.info("Pipeline resumed")

    def stop(self):
        self._stopped = True
        log.info("Pipeline stopped")

    async def _report(self, stage: str, progress: float, message: str):
        if self._progress_callback:
            self._progress_callback(stage, progress, message)

    def set_compliance_callback(self, callback):
        """No-op – compliance wurde entfernt."""
        pass

    async def _sleep_check(self, seconds: float = 0.1):
        for _ in range(int(seconds * 10)):
            if self._stopped:
                raise asyncio.CancelledError("Pipeline stopped")
            while self._paused and not self._stopped:
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.1)

    async def run(
        self,
        book_idea: str,
        genre_key: str,
        num_chapters: int,
        save_chapter_cb: Callable,
        log_event_cb: Callable,
        language: str = "Deutsch",
    ) -> dict:
        self._paused = False
        self._stopped = False

        self._language = language

        genre = self.genres.get_genre(genre_key) or {}
        style_hints = genre.get("style_hint", "")
        genre_name = genre.get("name", genre_key)

        # ── Schicht 1: DNA Extraction ──
        await self._report("DNA", 0.02, "Extrahiere Buch-DNA...")
        dna: DNAResponse = await self.dna_extractor.extract(book_idea)
        await self._sleep_check()

        # ── Stage 0: Core Elements ──
        await self._report("Kernelemente", 0.05, "Extrahiere Kernelemente...")
        core_elements = await self.extractor.extract(book_idea)
        await self._sleep_check()

        # ── Stage 1: Synopsis ──
        await self._report("Synopsis", 0.12, "Generiere Synopsis...")
        synopsis = await self._generate_synopsis(book_idea, core_elements, genre_name, style_hints, language)
        await self._sleep_check()

        # ── Stage 2: Characters ──
        await self._report("Charaktere", 0.20, "Erstelle Charakterprofile...")
        characters = await self._generate_characters(book_idea, synopsis, core_elements)
        await self._sleep_check()

        # ── Stage 3: Chapter Plan ──
        await self._report("Kapitelplan", 0.28, f"Plane {num_chapters} Kapitel...")
        chapter_plan = await self._generate_chapter_plan(
            book_idea, synopsis, characters, core_elements, num_chapters
        )
        await self._sleep_check()

        # ── Initialize Tracker (Schicht 4) ──
        self.tracker = StoryTracker(dna)

        # ── Stage 4: Chapter Loop ──
        chapter_context_extra = ""  # Wird nach jedem Kapitel mit Tracker-Status aktualisiert
        for i, plan in enumerate(chapter_plan):
            if self._stopped:
                break

            chapter_num = plan.get("number", i + 1) if isinstance(plan, dict) else plan.number
            chapter_title = plan.get("title", f"Kapitel {chapter_num}") if isinstance(plan, dict) else plan.title
            progress_base = 0.30 + (i / num_chapters) * 0.65

            await self._report(
                f"Kapitel {chapter_num}/{num_chapters}",
                progress_base,
                f"Schreibe: {chapter_title}",
            )

            # Build context (mit total_chapters für Phasen-Berechnung)
            story_context = self.context_builder.get_context_for_chapter(chapter_num, total_chapters=num_chapters)

            # Chapter elements
            chapter_elements = plan.get("elements", []) if isinstance(plan, dict) else plan.elements
            chapter_elements_descriptions = []
            for e in core_elements.mandatory_elements:
                if e.id in chapter_elements:
                    chapter_elements_descriptions.append(f"{e.id}: {e.description}")

            chapter_char_names = plan.get("characters", []) if isinstance(plan, dict) else plan.characters
            chapter_characters = "\n".join(
                f"  - {c.name}: {c.role}" for c in core_elements.characters
                if c.name in chapter_char_names
            ) if chapter_char_names else "Alle bisherigen Charaktere"

            target_words = plan.get("estimated_words", 2000) if isinstance(plan, dict) else plan.estimated_words

            # Build DNA block
            dna_block = self.dna_extractor.format_for_prompt(dna, extra={
                "protagonist_age": self.tracker.facts["protagonist_age"] if self.tracker else None,
            })

            # Generate chapter (ein Versuch, kein Compliance-Check)
            await self._report(
                f"Kapitel {chapter_num}/{num_chapters}",
                progress_base,
                f"Schreibe '{chapter_title}'...",
            )

            # Story-Phase berechnen (Pace-abhängig: langsam/ausgewogen/schnell)
            phase_ratio = chapter_num / num_chapters if num_chapters > 0 else 0.5
            # Pace passt die Phasen-Grenzen an
            if self._story_pace == "slow":
                # Langsam = längere Einleitung, kürzere Auflösung
                p_intro, p_rise, p_turn, p_escalate, p_climax = 0.20, 0.45, 0.60, 0.78, 0.90
            elif self._story_pace == "fast":
                # Schnell = kurze Einleitung, längerer Mittelteil, spätere Auflösung
                p_intro, p_rise, p_turn, p_escalate, p_climax = 0.10, 0.30, 0.45, 0.65, 0.82
            else:
                # Ausgewogen (Standard)
                p_intro, p_rise, p_turn, p_escalate, p_climax = 0.15, 0.35, 0.50, 0.70, 0.85

            if phase_ratio <= p_intro:
                story_phase = "Einführung – Status Quo und Figuren etablieren"
            elif phase_ratio <= p_rise:
                story_phase = "Steigende Handlung – Konflikte und Herausforderungen"
            elif phase_ratio <= p_turn:
                story_phase = "Erster Wendepunkt – Die Handlung nimmt eine neue Richtung"
            elif phase_ratio <= p_escalate:
                story_phase = "Eskalation – Die Spannung steigt, Konsequenzen zeigen sich"
            elif phase_ratio <= p_climax:
                story_phase = "Höhepunkt – Der finale Konflikt bahnt sich an"
            else:
                story_phase = "Auflösung – Die Geschichte findet ihren Abschluss"

            chapter_text = await self._generate_chapter_with_dna(
                dna_block=dna_block,
                book_idea=book_idea,
                story_phase=story_phase,
                chapter_number=chapter_num,
                chapter_title=chapter_title,
                synopsis=synopsis,
                story_context=story_context,
                chapter_elements="\n".join(chapter_elements_descriptions),
                chapter_characters=chapter_characters,
                genre=genre_name,
                target_words=target_words,
                chapter_context_extra=chapter_context_extra,
            )
            await self._sleep_check()

            # Kurzer Delay zwischen Kapiteln (verhindert Rate-Limits)
            await asyncio.sleep(self._chapter_delay)

            words = len(chapter_text.split())

            # Mark elements as used
            for elem_id in chapter_elements:
                self.extractor.mark_element_used(core_elements, elem_id)

            # Update context
            self.context_builder.add_chapter(
                chapter_number=chapter_num,
                title=chapter_title,
                text=chapter_text,
                characters_present=chapter_char_names,
                elements_covered=chapter_elements,
            )

            # Update tracker – nutze pure descriptions (ohne ID-Präfix) für korrektes Matching
            if self.tracker:
                tracker_elements = [e.description for e in core_elements.mandatory_elements
                                    if e.id in chapter_elements]
                self.tracker.update_after_chapter(
                    chapter_num=chapter_num,
                    chapter_text=chapter_text,
                    elements_covered=tracker_elements,
                )

            # Tracker-Status für nächste Kapitel abrufen
            pending_block = self.tracker.get_pending_prompt_block() if self.tracker else ""
            characters_block = self.tracker.get_characters_prompt_block() if self.tracker else ""

            # Beim nächsten Kapitel die offenen Elemente und bekannten Charaktere mitgeben
            chapter_context_extra = ""
            if pending_block:
                chapter_context_extra += "\n\n" + pending_block
            if characters_block:
                chapter_context_extra += "\n\n" + characters_block

            # Save chapter
            await save_chapter_cb(
                chapter_num, chapter_title, chapter_text,
                word_count=words,
                compliance_score=0,
                status="completed",
                elements_covered=chapter_elements,
            )
            await log_event_cb(
                f"Kapitel {chapter_num} abgeschlossen ({words} Wörter)",
                level="INFO",
                chapter_number=chapter_num,
                details={"words": words},
            )

        # ── Done ──
        await self._report("Fertig", 1.0, "Buchgenerierung abgeschlossen!")
        await log_event_cb("Buchgenerierung abgeschlossen", level="INFO")

        return {
            "status": "completed" if not self._stopped else "stopped",
            "total_chapters": self.context_builder.total_chapters,
            "total_words": self.context_builder.total_words,
            "dna": dna.model_dump(),
            "core_elements": self.extractor.to_dict(core_elements),
            "synopsis": synopsis,
            "characters": characters,
            "chapter_plan": chapter_plan,
            "tracker": self.tracker.get_compact_status() if self.tracker else {},
        }

    # ── Generation Methods ──

    async def _generate_synopsis(self, book_idea, core_elements, genre, style_hints, language="Deutsch"):
        prompt = self.prompts.format(
            "synopsis_prompt",
            book_idea=book_idea,
            core_elements=self.extractor.format_for_prompt(core_elements),
            genre=genre,
            style_hints=style_hints,
        )
        prompt = prompt.replace("{language}", language)

        response = await self.client.generate(
            system_prompt=self.prompts.get("system_prompt"),
            user_prompt=prompt,
            temperature=self._temperature,
            max_tokens=2000,
        )
        return response.text

    async def _generate_characters(self, book_idea, synopsis, core_elements):
        prompt = self.prompts.format(
            "character_prompt",
            book_idea=book_idea,
            synopsis=synopsis,
            core_elements=self.extractor.format_for_prompt(core_elements),
        )
        try:
            result = await self.client.generate_model(
                system_prompt=self.prompts.get("system_prompt"),
                user_prompt=prompt,
                schema=CharacterProfileListResponse,
                temperature=self._temperature,
            )
            return [c.model_dump() for c in result.characters]
        except LLMResponseError as e:
            log.warning(f"Character generation failed: {e}", stage="Charaktere")
            return []

    async def _generate_chapter_plan(self, book_idea, synopsis, characters, core_elements, num_chapters):
        pending = self.extractor.get_pending_elements(core_elements)
        pending_str = "\n".join(f"  {e.id}: {e.description}" for e in pending)
        prompt = self.prompts.format(
            "chapter_plan_prompt",
            book_idea=book_idea,
            synopsis=synopsis,
            characters=json.dumps(characters, ensure_ascii=False, indent=2),
            core_elements=self.extractor.format_for_prompt(core_elements),
            pending_elements=pending_str,
            num_chapters=num_chapters,
        )
        try:
            result = await self.client.generate_model(
                system_prompt=self.prompts.get("system_prompt"),
                user_prompt=prompt,
                schema=ChapterPlanListResponse,
                temperature=0.5,
                max_tokens=16000,
            )
            return [c.model_dump() for c in result.chapters]
        except LLMResponseError as e:
            log.warning(f"Chapter plan generation failed: {e}", stage="Kapitelplan")
            return []

    async def _generate_chapter_with_dna(
        self, dna_block, book_idea, story_phase, chapter_number, chapter_title,
        synopsis, story_context, chapter_elements, chapter_characters,
        genre, target_words, chapter_context_extra="",
    ):
        # Detailgrad als zusätzliche Anweisung an die KI einbetten
        detail_hint = ""
        if self._detail_level == "loose":
            detail_hint = "\n\n🔓 DETAILGRAD (LOCKER): Du hast künstlerische Freiheit. Halte dich an die Grundidee, erfinde ruhig Details, Szenen und Wendungen, die zur Atmosphäre passen. Strenge 1:1-Übersetzung ist NICHT nötig."
        elif self._detail_level == "detailed":
            detail_hint = "\n\n🎯 DETAILGRAD (DETAILIERT): Setze die Idee präzise um. Wichtige Details, Namen, Orte und Ereignisse aus der Idee sollen erhalten bleiben."
        elif self._detail_level == "strict":
            detail_hint = "\n\n🔒 DETAILGRAD (STRENG): Maximale Treue zur Originalidee. Keine Abweichungen, keine erfundenen Elemente, keine zusätzlichen Charaktere, die nicht in der Idee vorkommen. Nur minimale Ausschmückung."
        # "standard" → kein zusätzlicher Hinweis

        # Extended Thinking: Hinweis an die KI, dass sie ausführlich planen soll
        thinking_hint = ""
        if self._use_extended_thinking:
            thinking_hint = "\n\n🧠 EXTENDED THINKING: Plane vor dem Schreiben ausführlich: Welche Wendungen passieren? Wie entwickeln sich Charaktere? Welche symbolischen Ebenen gibt es? Liefere besonders durchdachte Prosa."

        # Sprache aus den Settings (überschreibt evtl. übergebene _language)
        language = getattr(self, '_language', None) or self._default_language

        full_context_extra = (chapter_context_extra or "") + detail_hint + thinking_hint

        prompt = self.prompts.format(
            "chapter_prompt_with_dna",
            dna_block=dna_block,
            book_idea=book_idea,
            story_phase=story_phase,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            synopsis=synopsis,
            characters=chapter_characters,
            story_context=story_context,
            chapter_elements=chapter_elements,
            target_words=target_words,
            genre=genre,
            chapter_context_extra=full_context_extra,
            correction_instructions="",
        )
        prompt = prompt.replace("{language}", language)

        response = await self.client.generate(
            system_prompt=self.prompts.get("system_prompt"),
            user_prompt=prompt,
            temperature=0.8,
            max_tokens=self.max_chapter_words * 3,
        )
        return response.text
