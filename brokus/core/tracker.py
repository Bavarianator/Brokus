"""Story Tracker – Schicht 4: Cross-Chapter Consistency.

Tracks facts across all chapters and detects contradictions.
Provides live status display for the TUI compliance dashboard.
"""

from brokus.ai.schemas import DNAResponse
from brokus.utils.logger import log


class StoryTracker:
    """Tracks story state across all chapters to maintain consistency.

    Monitors:
    - Character ages and life events
    - Story timeline
    - Mandatory element completion
    - Character introductions
    - Location changes
    """

    def __init__(self, dna: DNAResponse):
        self.dna = dna

        prot = dna.protagonistin if dna.protagonistin.name else dna.protagonist
        start_age = prot.alter_start
        elements = dna.pflicht_handlungselemente

        # Tracked state
        self.facts: dict = {
            "story_year": 0,
            "protagonist_age": start_age,
            "fulfilled_elements": [],
            "pending_elements": self._get_all_elements(elements),
            "characters": {},
            "locations": [],
            "events_log": [],
        }

        self._chapter_count = 0

    def _get_all_elements(self, elements: list) -> list[str]:
        """Extract all mandatory element descriptions from list."""
        result = []
        for e in elements:
            if isinstance(e, str):
                result.append(e)
            elif hasattr(e, "description"):
                result.append(e.description or e.name or str(e))
            else:
                result.append(str(e))
        return result

    def update_after_chapter(
        self,
        chapter_num: int,
        chapter_text: str,
        report: dict | None = None,
        elements_covered: list[str] | None = None,
    ):
        """Update tracker state after a chapter completes.

        Parses the AI chapter report (---KAPITEL-REPORT---) if present.
        """
        self._chapter_count = chapter_num

        # Update fulfilled/pending elements
        if elements_covered:
            for elem in elements_covered:
                if elem in self.facts["pending_elements"]:
                    self.facts["pending_elements"].remove(elem)
                    self.facts["fulfilled_elements"].append(elem)

        # Extract info from AI chapter report if available
        if report:
            if "LENAS_ALTER" in report:
                self.facts["protagonist_age"] = int(report["LENAS_ALTER"])
            if "STORY_JAHR" in report:
                self.facts["story_year"] = int(report["STORY_JAHR"])
            for char in report.get("NEUE_CHARAKTERE", []):
                if char and char != "keine":
                    self.facts["characters"][char] = {"introduced_in": chapter_num}
        else:
            # Try to parse AI self-report from chapter text
            parsed = self._parse_chapter_report(chapter_text)
            if parsed:
                if "PROTAGONIST_ALTER" in parsed:
                    self.facts["protagonist_age"] = int(parsed["PROTAGONIST_ALTER"])
                if "STORY_JAHR" in parsed:
                    self.facts["story_year"] = int(parsed["STORY_JAHR"])
                for char in parsed.get("NEUE_CHARAKTERE", []):
                    if char and char != "keine":
                        self.facts["characters"][char] = {"introduced_in": chapter_num}

        first_sentence = chapter_text.split("\n")[0][:100] if chapter_text.strip() else ""
        self.facts["events_log"].append((chapter_num, f"Kapitel {chapter_num}: {first_sentence}..."))

        log.debug(
            f"Tracker: Kapitel {chapter_num} | "
            f"{len(self.facts['fulfilled_elements'])} erfuellt, "
            f"{len(self.facts['pending_elements'])} offen"
        )

    def _parse_chapter_report(self, text: str) -> dict | None:
        """Parse the AI's ---KAPITEL-REPORT--- section from chapter text."""
        import re
        match = re.search(r'---KAPITEL-REPORT---\n(.*?)\n---ENDE-REPORT---', text, re.DOTALL)
        if not match:
            return None
        report_text = match.group(1)
        report = {}
        for line in report_text.split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().upper().replace(" ", "_")
                value = value.strip()
                # Parse list values like "[Element 1, Element 2]"
                if value.startswith("[") and value.endswith("]"):
                    items = [i.strip() for i in value[1:-1].split(",") if i.strip()]
                    report[key] = items
                else:
                    report[key] = value
        return report if report else None

    def check_consistency(self) -> list[str]:
        """Check for consistency issues across all chapters.

        Returns:
            List of warning/issue descriptions.
        """
        issues = []

        # Age plausibility
        if self.facts["protagonist_age"] > 90:
            issues.append("⚠️ Protagonist zu alt – Zeitlinie prüfen")

        # Progress vs remaining elements
        total = len(self.facts["fulfilled_elements"]) + len(self.facts["pending_elements"])
        if total > 0:
            progress = len(self.facts["fulfilled_elements"]) / total
            if progress > 0.7 and len(self.facts["pending_elements"]) > total * 0.3:
                issues.append(
                    f"⚠️ {len(self.facts['pending_elements'])} Pflichtelemente "
                    f"noch offen bei {int(progress * 100)}% des Buches!"
                )

        # Story year drift
        if self.facts["story_year"] > 100:
            issues.append("⚠️ Story-Zeitraum sehr lang – Konsistenz prüfen")

        return issues

    def get_status_display(self) -> str:
        """Build a TUI status display string.

        Returns:
            Formatted status for compliance dashboard.
        """
        total = len(self.facts["fulfilled_elements"]) + len(self.facts["pending_elements"])
        if total == 0:
            total = self._count_dna_elements()
        done = len(self.facts["fulfilled_elements"])

        lines = [
            f"📊 PFLICHTELEMENTE: {done}/{total}",
            f"👤 Protagonist: {self.facts['protagonist_age']} Jahre",
            f"📅 Story-Jahr: {self.facts['story_year']}",
            f"📖 Kapitel: {self._chapter_count}",
            "",
        ]

        if self.facts["fulfilled_elements"]:
            lines.append("✅ ERLEDIGT:")
            for el in self.facts["fulfilled_elements"][-5:]:  # Last 5
                lines.append(f"  ✅ {el[:50]}")
            if len(self.facts["fulfilled_elements"]) > 5:
                lines.append(f"  ... +{len(self.facts['fulfilled_elements']) - 5} mehr")

        if self.facts["pending_elements"]:
            lines.append("")
            lines.append("⏳ NOCH OFFEN:")
            for el in self.facts["pending_elements"][:5]:  # First 5
                lines.append(f"  ⏳ {el[:50]}")
            if len(self.facts["pending_elements"]) > 5:
                lines.append(f"  ... +{len(self.facts['pending_elements']) - 5} mehr")

        issues = self.check_consistency()
        if issues:
            lines.append("")
            lines.append("⚠️ WARNUNGEN:")
            for issue in issues:
                lines.append(f"  {issue}")

        return "\n".join(lines)

    def get_compact_status(self) -> dict:
        """Get compact status as dict for TUI updates."""
        total = len(self.facts["fulfilled_elements"]) + len(self.facts["pending_elements"])
        if total == 0:
            total = self._count_dna_elements()
        done = len(self.facts["fulfilled_elements"])

        return {
            "elements_done": done,
            "elements_total": total,
            "protagonist_age": self.facts["protagonist_age"],
            "story_year": self.facts["story_year"],
            "chapters_completed": self._chapter_count,
            "warnings": self.check_consistency(),
        }

    def get_pending_prompt_block(self) -> str:
        """Format pending elements as a prompt block for chapter generation.

        Returns a formatted string showing what's still open, or empty string.
        """
        if not self.facts["pending_elements"]:
            return ""

        lines = [
            "⏳ NOCH OFFENE PFLICHTELEMENTE (GESAMTBILD):",
            "",
        ]
        for el in self.facts["pending_elements"]:
            lines.append(f"  ⏳ {el[:80]}")
        lines.extend([
            "",
            f"→ {len(self.facts['pending_elements'])} Elemente müssen noch in verbleibenden Kapiteln behandelt werden.",
            "→ Verschwende sie NICHT alle auf einmal – verteile sie über die restlichen Kapitel.",
        ])
        return "\n".join(lines)

    def get_characters_prompt_block(self) -> str:
        """Format known characters as a prompt block."""
        if not self.facts["characters"]:
            return ""

        lines = [
            "👤 BEREITS EINGEFÜHRTE CHARAKTERE:",
            "",
        ]
        for name, info in sorted(self.facts["characters"].items(), key=lambda x: x[1].get("introduced_in", 0)):
            chap = info.get("introduced_in", "?")
            lines.append(f"  • {name} (eingeführt in Kapitel {chap})")
        lines.append("")
        lines.append("→ Nutze diese Charaktere weiter. Führe neue nur ein, wenn nötig.")
        return "\n".join(lines)

    def _count_dna_elements(self) -> int:
        """Return the total number of mandatory elements from DNA."""
        return len(self.dna.pflicht_handlungselemente)

    @property
    def total_mandatory(self) -> int:
        total = len(self.facts["fulfilled_elements"]) + len(self.facts["pending_elements"])
        if total == 0:
            total = self._count_dna_elements()
        return total

    @property
    def completed_mandatory(self) -> int:
        return len(self.facts["fulfilled_elements"])
