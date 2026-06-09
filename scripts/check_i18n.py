#!/usr/bin/env python3
"""CI-friendly i18n validator for brokus.

Loads all ``data/i18n/*.json`` files and reports:
  * missing keys (present in some languages but not in others)
  * empty values (key exists but maps to "" or whitespace)
  * placeholder mismatches (e.g. ``{name}`` exists in the reference language
    but is missing in another translation → would raise ``KeyError`` at runtime)

Designed to run in CI:
  * Exit code 0 → everything is fine
  * Exit code 1 → missing keys
  * Exit code 2 → empty values
  * Exit code 3 → placeholder mismatches
  * Exit codes are OR-able (e.g. ``3`` means both 1 and 2 were triggered)

Usage
-----
    python scripts/check_i18n.py                # human-readable, exit non-zero on issues
    python scripts/check_i18n.py --json        # machine-readable JSON report
    python scripts/check_i18n.py --strict      # also flag empty / placeholder issues
    python scripts/check_i18n.py --reference en  # use English as the reference
    python scripts/check_i18n.py --quiet       # only print errors (still exits non-zero)
    python scripts/check_i18n.py --check-only  # alias of --strict (CI mode)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# ────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────

I18N_DIR = Path("data/i18n")
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
EXIT_OK = 0
EXIT_MISSING = 1
EXIT_EMPTY = 2
EXIT_PLACEHOLDER = 4
LANG_NAMES = {
    "de": "Deutsch",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "nl": "Nederlands",
}


# ────────────────────────────────────────────────────────────────────
# ANSI colors (auto-disabled when stdout is not a tty)
# ────────────────────────────────────────────────────────────────────


class C:
    """ANSI color helpers. Detects tty automatically."""

    _enabled = sys.stdout.isatty()

    @classmethod
    def _wrap(cls, code: str, text: str) -> str:
        if not cls._enabled:
            return text
        return f"\033[{code}m{text}\033[0m"

    @classmethod
    def red(cls, t: str) -> str:
        return cls._wrap("31", t)

    @classmethod
    def green(cls, t: str) -> str:
        return cls._wrap("32", t)

    @classmethod
    def yellow(cls, t: str) -> str:
        return cls._wrap("33", t)

    @classmethod
    def blue(cls, t: str) -> str:
        return cls._wrap("34", t)

    @classmethod
    def bold(cls, t: str) -> str:
        return cls._wrap("1", t)

    @classmethod
    def dim(cls, t: str) -> str:
        return cls._wrap("2", t)


# ────────────────────────────────────────────────────────────────────
# Data classes
# ────────────────────────────────────────────────────────────────────


@dataclass
class LangData:
    """A single language file's content + metadata."""

    code: str
    path: Path
    data: Dict[str, str]
    error: Optional[str] = None  # set if file could not be loaded

    @property
    def name(self) -> str:
        return LANG_NAMES.get(self.code, self.code)

    @property
    def key_count(self) -> int:
        return len(self.data) if not self.error else 0


@dataclass
class CheckReport:
    """Complete validation report for a single run."""

    reference: str
    languages: List[LangData] = field(default_factory=list)

    # Set of all keys across all languages
    all_keys: Set[str] = field(default_factory=set)

    # Per-language missing keys (relative to the reference)
    missing: Dict[str, Set[str]] = field(default_factory=dict)

    # Per-language extra keys (not in the reference)
    extra: Dict[str, Set[str]] = field(default_factory=dict)

    # Per-language empty values
    empty: Dict[str, Set[str]] = field(default_factory=dict)

    # Per-language placeholder mismatches
    placeholders: Dict[str, Set[str]] = field(default_factory=dict)

    # File-level errors (unloadable files)
    file_errors: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.empty or self.placeholders or self.file_errors)

    def exit_code(self, strict: bool = False) -> int:
        """Compute a CI-friendly exit code (OR of all triggered bits)."""
        code = EXIT_OK
        if self.file_errors:
            code |= EXIT_MISSING
        if self.missing:
            code |= EXIT_MISSING
        if strict and self.empty:
            code |= EXIT_EMPTY
        if strict and self.placeholders:
            code |= EXIT_PLACEHOLDER
        return code


# ────────────────────────────────────────────────────────────────────
# Core logic
# ────────────────────────────────────────────────────────────────────


def _placeholder_keys(text: str) -> Set[str]:
    """Extract ``{var}`` placeholder names from a translation string."""
    return set(PLACEHOLDER_RE.findall(text))


def load_languages(i18n_dir: Path) -> List[LangData]:
    """Load every ``*.json`` in ``i18n_dir`` (sorted by code)."""
    if not i18n_dir.exists():
        return []
    out: List[LangData] = []
    for path in sorted(i18n_dir.glob("*.json")):
        code = path.stem
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError(f"top-level must be an object, got {type(raw).__name__}")
            # Coerce all values to str (in case some are numbers / bools)
            data: Dict[str, str] = {str(k): "" if v is None else str(v) for k, v in raw.items()}
            out.append(LangData(code=code, path=path, data=data))
        except Exception as exc:  # noqa: BLE001 – we want to surface the message
            out.append(LangData(code=code, path=path, data={}, error=str(exc)))
    return out


def check(report: CheckReport) -> None:
    """Populate ``report`` with all findings in-place."""
    # 1) Collect all keys
    for lang in report.languages:
        report.all_keys.update(lang.data.keys())

    # 2) Reference key set
    ref_lang = next((l for l in report.languages if l.code == report.reference), None)
    ref_keys: Set[str] = set()
    if ref_lang and not ref_lang.error:
        ref_keys = set(ref_lang.data.keys())

    # 3) Per-language diffs
    for lang in report.languages:
        if lang.error:
            report.file_errors.append((lang.code, lang.error))
            continue

        keys = set(lang.data.keys())
        # Missing = in reference but not in this language
        if ref_keys:
            miss = ref_keys - keys
            if miss:
                report.missing[lang.code] = miss
            # Extra = in this language but not in reference
            extra = keys - ref_keys
            if extra:
                report.extra[lang.code] = extra

        # Empty values
        empty_here = {k for k, v in lang.data.items() if not v.strip()}
        if empty_here:
            report.empty[lang.code] = empty_here

        # Placeholder mismatches (only when reference is loadable)
        if ref_lang and not ref_lang.error and ref_lang is not lang:
            ph_mismatches: Set[str] = set()
            for k in keys & ref_keys:
                ref_ph = _placeholder_keys(ref_lang.data.get(k, ""))
                lang_ph = _placeholder_keys(lang.data.get(k, ""))
                if ref_ph != lang_ph:
                    ph_mismatches.add(k)
            if ph_mismatches:
                report.placeholders[lang.code] = ph_mismatches


# ────────────────────────────────────────────────────────────────────
# Rendering
# ────────────────────────────────────────────────────────────────────


def _print_human(report: CheckReport, strict: bool, quiet: bool, max_per_section: int) -> None:
    print(C.bold("─" * 60))
    print(C.bold("  brokus i18n check"))
    print(C.bold("─" * 60))
    print(f"  Reference language: {C.blue(report.reference)}")
    print(f"  Files checked:      {len(report.languages)}")
    print(f"  Total keys:         {len(report.all_keys)}")
    print(f"  Mode:               {'strict' if strict else 'lenient'}")
    print()

    # Per-language summary table
    print(C.bold("Languages:"))
    for lang in report.languages:
        if lang.error:
            print(f"  {C.red('✗')} {lang.code:<4} {C.red(lang.error)}")
        else:
            mark = C.green("✓")
            print(f"  {mark} {lang.code:<4} ({lang.name:<12}) – {lang.key_count} keys")
    print()

    if report.ok:
        print(C.green("✓ All good – no missing keys."))
        if strict:
            print(C.green("✓ No empty values."))
            print(C.green("✓ No placeholder mismatches."))
        return

    # File errors
    if report.file_errors:
        print(C.red(C.bold("File errors:")))
        for code, err in report.file_errors:
            print(f"  {C.red('✗')} {code}: {err}")
        print()

    # Missing keys
    if report.missing:
        print(C.red(C.bold("Missing keys (in reference, not in this language):")))
        for code in sorted(report.missing):
            keys = sorted(report.missing[code])
            shown = keys[:max_per_section]
            extra = len(keys) - len(shown)
            head = f"  {C.red('✗')} {code}: {len(keys)} missing"
            print(head)
            for k in shown:
                print(f"      {C.dim(k)}")
            if extra > 0:
                print(f"      {C.dim(f'… and {extra} more')}")
        print()

    # Extra keys
    if report.extra:
        print(C.yellow(C.bold("Extra keys (in this language, not in reference):")))
        for code in sorted(report.extra):
            keys = sorted(report.extra[code])
            print(f"  {C.yellow('!')} {code}: {len(keys)} extra")
            for k in keys[:max_per_section]:
                print(f"      {C.dim(k)}")
            if len(keys) > max_per_section:
                print(f"      {C.dim(f'… and {len(keys) - max_per_section} more')}")
        print()

    # Empty values (strict only)
    if report.empty and strict:
        print(C.yellow(C.bold("Empty values:")))
        for code in sorted(report.empty):
            keys = sorted(report.empty[code])
            print(f"  {C.yellow('!')} {code}: {len(keys)} empty")
            for k in keys[:max_per_section]:
                print(f"      {C.dim(k)}")
            if len(keys) > max_per_section:
                print(f"      {C.dim(f'… and {len(keys) - max_per_section} more')}")
        print()

    # Placeholder mismatches (strict only)
    if report.placeholders and strict:
        print(C.yellow(C.bold("Placeholder mismatches (e.g. '{n}' in ref, missing here):")))
        # Get reference data for context
        ref_lang = next((l for l in report.languages if l.code == report.reference), None)
        for code in sorted(report.placeholders):
            keys = sorted(report.placeholders[code])
            print(f"  {C.yellow('!')} {code}: {len(keys)} mismatches")
            for k in keys[:max_per_section]:
                if ref_lang and not ref_lang.error:
                    ref_text = ref_lang.data.get(k, "")
                    lang_text = (
                        next((l for l in report.languages if l.code == code), None).data.get(k, "")
                        if False
                        else ""
                    )
                    print(f"      {C.dim(k)}")
                    print(f"        ref : {C.green(ref_text)}")
                    lang_obj = next((l for l in report.languages if l.code == code), None)
                    if lang_obj:
                        print(f"        {code}   : {C.yellow(lang_obj.data.get(k, ''))}")
            if len(keys) > max_per_section:
                print(f"      {C.dim(f'… and {len(keys) - max_per_section} more')}")
        print()

    # Final verdict
    code = report.exit_code(strict=strict)
    if code == EXIT_OK:
        print(C.green(C.bold("✓ PASS")))
    else:
        bits = []
        if code & EXIT_MISSING:
            bits.append("missing-keys")
        if code & EXIT_EMPTY:
            bits.append("empty-values")
        if code & EXIT_PLACEHOLDER:
            bits.append("placeholder-mismatches")
        print(C.red(C.bold(f"✗ FAIL ({', '.join(bits)}) – exit code {code}")))


def _print_json(report: CheckReport, strict: bool) -> None:
    """Machine-readable output (for CI artifacts)."""
    payload = {
        "reference": report.reference,
        "strict": strict,
        "ok": report.ok,
        "exit_code": report.exit_code(strict=strict),
        "total_keys": len(report.all_keys),
        "languages": [
            {
                "code": l.code,
                "name": l.name,
                "path": str(l.path),
                "key_count": l.key_count,
                "error": l.error,
            }
            for l in report.languages
        ],
        "file_errors": [{"code": c, "error": e} for c, e in report.file_errors],
        "missing": {c: sorted(s) for c, s in report.missing.items()},
        "extra": {c: sorted(s) for c, s in report.extra.items()},
        "empty": {c: sorted(s) for c, s in report.empty.items()},
        "placeholder_mismatches": {c: sorted(s) for c, s in report.placeholders.items()},
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Validate brokus i18n JSON files (CI-friendly).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exit codes:\n"
            "  0  ok\n"
            "  1  missing keys (always reported)\n"
            "  2  empty values (only with --strict / --check-only)\n"
            "  4  placeholder mismatches (only with --strict / --check-only)\n"
            "\n"
            "Examples:\n"
            "  python scripts/check_i18n.py                 # human-readable\n"
            "  python scripts/check_i18n.py --json         # JSON for CI\n"
            "  python scripts/check_i18n.py --strict       # also fail on empty / placeholders\n"
            "  python scripts/check_i18n.py --reference en  # use English as reference\n"
        ),
    )
    p.add_argument(
        "--dir",
        default=str(I18N_DIR),
        help=f"i18n directory (default: {I18N_DIR})",
    )
    p.add_argument(
        "--reference",
        "-r",
        default="de",
        help="reference language code (default: de)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON report instead of human output",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="also fail on empty values and placeholder mismatches",
    )
    p.add_argument(
        "--check-only",
        action="store_true",
        help="alias of --strict (CI mode: fail on any issue)",
    )
    p.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="only print errors and the final verdict",
    )
    p.add_argument(
        "--max-per-section",
        type=int,
        default=10,
        help="max number of keys to list per section before summarising (default: 10)",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colors",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.no_color:
        C._enabled = False

    strict = args.strict or args.check_only

    i18n_dir = Path(args.dir)
    languages = load_languages(i18n_dir)

    if not languages:
        print(
            f"{C.red('✗')} No language files found in {i18n_dir}",
            file=sys.stderr,
        )
        return EXIT_MISSING

    report = CheckReport(reference=args.reference, languages=languages)
    check(report)

    if args.json:
        _print_json(report, strict=strict)
    elif not args.quiet:
        _print_human(report, strict=strict, quiet=args.quiet, max_per_section=args.max_per_section)
    else:
        # Quiet: only print the final verdict
        if report.ok:
            print(C.green("✓ i18n OK"))
        else:
            code = report.exit_code(strict=strict)
            summary_bits = []
            if report.missing:
                summary_bits.append(f"missing={sum(len(s) for s in report.missing.values())}")
            if report.empty and strict:
                summary_bits.append(f"empty={sum(len(s) for s in report.empty.values())}")
            if report.placeholders and strict:
                summary_bits.append(
                    f"placeholder-mismatches={sum(len(s) for s in report.placeholders.values())}"
                )
            print(f"{C.red('✗')} i18n FAIL ({', '.join(summary_bits)}) – exit {code}")

    return report.exit_code(strict=strict)


if __name__ == "__main__":
    sys.exit(main())
