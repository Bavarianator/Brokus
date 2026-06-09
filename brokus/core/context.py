"""Story context builder – maintains structured summary of all chapters."""


from brokus.utils.logger import log


class StoryContextBuilder:
    """Builds and maintains a structured summary of the story so far."""

    def __init__(self):
        self._chapter_summaries: list[dict] = []
        self._key_events: list[str] = []
        self._total_words: int = 0
        self._arch_phase_labels = [
            "EINFÜHRUNG – Status Quo & Figurenvorstellung",
            "AUSLÖSENDES EREIGNIS – Die Handlung beginnt",
            "STEIGENDE HANDLUNG – Konflikte bauen sich auf",
            "ERSTER WENDEPUNKT – Neue Richtung / neue Herausforderung",
            "STEIGENDE HANDLUNG II – Eskalation & Konsequenzen",
            "MITTE – Der tiefste Punkt / die größte Enthüllung",
            "STEIGENDE HANDLUNG III – Vorbereitung auf den Höhepunkt",
            "ZWEITER WENDEPUNKT – Die finale Entscheidung naht",
            "HÖHEPUNKT – Der finale Konflikt / die große Konfrontation",
            "FALLENDE HANDLUNG – Nachwirkungen des Höhepunkts",
            "AUFLÖSUNG – Loslösung & neues Gleichgewicht",
            "EPILOG / AUSBLICK – Was bleibt",
        ]

    def add_chapter(
        self,
        chapter_number: int,
        title: str,
        text: str,
        characters_present: list[str],
        elements_covered: list[str],
    ):
        """Add a completed chapter to the context."""
        words = len(text.split())

        # Extrahiere Key Events aus dem Kapiteltext
        key_events = self._extract_key_events(text)

        summary = {
            "number": chapter_number,
            "title": title,
            "word_count": words,
            "characters": characters_present,
            "elements": elements_covered,
            "key_events": key_events,
            "first_sentence": text.split("\n")[0][:200] if text.strip() else "",
            "last_paragraph": self._get_last_paragraph(text),
        }
        self._chapter_summaries.append(summary)
        self._total_words += words

        self._key_events.extend(key_events)

        log.debug(f"Story context updated: {len(self._chapter_summaries)} chapters, {self._total_words} words")

    def _get_last_paragraph(self, text: str) -> str:
        """Get the last meaningful paragraph of a chapter."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return ""
        return paragraphs[-1][:600]

    def _extract_key_events(self, text: str) -> list[str]:
        """Extract key events from chapter text using heuristics.

        Looks for sentences with action verbs, dialogue tags, or
        pivotal descriptions that move the plot forward.
        """
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        events = []
        keywords = [
            "plötzlich", "da", "endlich", "schließlich", "entschied", "erkannte",
            "fand", "entdeckte", "geschah", "passierte", "traf", "sah",
            "hörte", "fühlte", "wusste", "begriff", "öffnete", "schloss",
            "rannte", "lief", "ging", "kam", "fiel", "stand", "setzte",
            "nahm", "gab", "sagte", "rief", "flüsterte", "schrie",
            "lachte", "weinte", "lächelte", "starrte", "blickte",
        ]
        for s in sentences:
            s_lower = s.lower().strip()
            if any(kw in s_lower for kw in keywords) and len(s) > 40:
                events.append(s[:150])
                if len(events) >= 5:
                    break
        return events[:5]

    def _get_story_phase(self, chapter_number: int, total_chapters: int) -> str:
        """Assign a narrative arc phase based on chapter position."""
        if total_chapters <= 0:
            return ""

        ratio = chapter_number / total_chapters
        idx = min(len(self._arch_phase_labels) - 1, int(ratio * len(self._arch_phase_labels)))
        return self._arch_phase_labels[idx]

    def get_context_for_chapter(self, chapter_number: int, total_chapters: int = 0) -> str:
        """Build context string for the AI when writing a new chapter.

        Provides a structured summary that preserves key information
        while keeping token usage manageable.
        """
        if not self._chapter_summaries:
            return "Dies ist das erste Kapitel. Es gibt noch keinen vorherigen Kontext."

        lines = [
            "════════════════════════════════════════════",
            "📚 BISHERIGE HANDLUNG",
            "════════════════════════════════════════════",
            "",
        ]

        # ── Story-Arc Phase ──
        if total_chapters > 0:
            phase = self._get_story_phase(chapter_number, total_chapters)
            lines.append(f"📌 PHASE IM GESAMTEN HANDLUNGSBOGEN: {phase}")
            lines.append(f"📌 AKTUELLER STAND: Kapitel {chapter_number} von {total_chapters}")
            lines.append("")

        # ── Kurze Chronik aller Kapitel ──
        lines.append("📖 KAPITEL-CHRONIK:")
        for ch in self._chapter_summaries:
            events_bullet = ch["key_events"][0] if ch["key_events"] else ""
            lines.append(f"  Kap. {ch['number']}: {ch['title']}")
            if events_bullet:
                lines.append(f"    → {events_bullet}")
        lines.append("")

        # ── Letzte 3 Kapitel detailliert ──
        recent = self._chapter_summaries[-3:]
        if recent:
            lines.append("🔍 LETZTE KAPITEL (DETAIL):")
            for ch in recent:
                lines.append(f"  Kapitel {ch['number']} – {ch['title']} ({ch['word_count']} Wörter)")
                lines.append(f"    Endet mit: {ch['last_paragraph']}")
                if ch["characters"]:
                    lines.append(f"    Figuren: {', '.join(ch['characters'][:5])}")
                lines.append("")

        # ── Offene Handlungsstränge ──
        if self._key_events:
            # Nur die wichtigsten/neuesten Events
            recent_events = self._key_events[-8:]
            lines.append("🔗 WICHTIGE EREIGNISSE (Zusammenfassung):")
            for ev in recent_events:
                lines.append(f"  • {ev}")

        lines.append("")
        lines.append(f"📊 Gesamt: {len(self._chapter_summaries)} Kapitel, {self._total_words} Wörter geschrieben.")
        lines.append("════════════════════════════════════════════")

        return "\n".join(lines)

    @property
    def total_chapters(self) -> int:
        return len(self._chapter_summaries)

    @property
    def total_words(self) -> int:
        return self._total_words
