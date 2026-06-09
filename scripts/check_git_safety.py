#!/usr/bin/env python3
"""brokus – Git safety check (pre-commit / pre-push / CI).

Refuses to allow sensitive files (books, database, logs, API keys, .env,
encrypted secrets) to be added, committed, or pushed to Git.

Usage:
    python scripts/check_git_safety.py                # default: scan staged files
    python scripts/check_git_safety.py --staged       # only staged files
    python scripts/check_git_safety.py --all          # all tracked files
    python scripts/check_git_safety.py --working-tree # all files in working tree
    python scripts/check_git_safety.py --ci           # CI mode (no fix hints)

Exit codes:
    0  clean – safe to commit
    1  sensitive files detected – DO NOT commit
    2  not a git repository
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

# Patterns that should NEVER be committed. Match is done on the path
# (relative to the repo root, using forward slashes).
SENSITIVE_PATTERNS: list[Tuple[str, str]] = [
    # (regex, human-readable reason)
    (r"^data/books/.+",             "user-generated book (md/epub/pdf/docx/json/txt)"),
    (r"^data/.*\.db$",              "SQLite database"),
    (r"^data/.*\.sqlite",           "SQLite database"),
    (r"^data/projects\.db-?.*",     "SQLite database or journal"),
    (r"^data/backups/.+",           "DB backup"),
    (r"^data/cache/.+",             "model discovery cache"),
    (r"^data/logs/.+",              "log files"),
    (r"^data/exports/.+",           "exported books"),
    (r"^data/drafts/.+",            "drafts"),
    (r"^data/.+\.epub$",            "EPUB book"),
    (r"^data/.+\.pdf$",             "PDF book"),
    (r"^data/.+\.docx$",            "Word book"),
    (r"^data/.+\.md$",              "Markdown book"),
    (r"^data/.+\.txt$",             "plain-text book"),
    (r"^.+\.enc$",                  "encrypted secrets file"),
    (r"^.+/secrets\.enc$",          "encrypted secrets file"),
    (r"^.+/master\.key$",           "master passphrase file"),
    (r"^\.env$",                    ".env with secrets"),
    (r"^\.env\..+",                 ".env variant with secrets"),
    (r"^config/local\.ya?ml",       "local config with secrets"),
    (r"^config/.+\.local\.ya?ml",   "local config variant"),
    (r"^.+_history$",               "shell history"),
    (r"^.*\.pem$",                  "private key"),
    (r"^.*\.key$",                  "private key"),
    (r"^.*\.p12$",                  "PKCS12 bundle"),
    (r"^.*\.pfx$",                  "PKCS12 bundle"),
]

# Pre-compile
_SENSITIVE = [(re.compile(p), desc) for p, desc in SENSITIVE_PATTERNS]

# ANSI colors (auto-disabled)
class C:
    _enabled = sys.stdout.isatty()
    @classmethod
    def _wrap(cls, code, t):
        return f"\033[{code}m{t}\033[0m" if cls._enabled else t
    @classmethod
    def red(cls, t): return cls._wrap("31", t)
    @classmethod
    def green(cls, t): return cls._wrap("32", t)
    @classmethod
    def yellow(cls, t): return cls._wrap("33", t)
    @classmethod
    def bold(cls, t): return cls._wrap("1", t)


def _is_git_repo() -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        return True
    except Exception:
        return False


def _git_files(args: list[str]) -> List[str]:
    """Run ``git <args>`` and return the file list."""
    try:
        result = subprocess.run(
            ["git", *args],
            check=True, capture_output=True, text=True, timeout=30,
        )
        # Treat CRLF newlines + strip empties
        return [ln.strip().replace("\\", "/") for ln in result.stdout.splitlines() if ln.strip()]
    except subprocess.CalledProcessError as e:
        print(C.red(f"git command failed: {e}"), file=sys.stderr)
        return []


def _scan(files: Iterable[str]) -> List[Tuple[str, str]]:
    """Return (path, reason) for every file that matches a sensitive pattern."""
    hits: list[Tuple[str, str]] = []
    for f in files:
        for rx, desc in _SENSITIVE:
            if rx.search(f):
                hits.append((f, desc))
                break
    return hits


def _format_report(hits: List[Tuple[str, str]], mode: str) -> str:
    if not hits:
        return ""
    lines = [
        "",
        C.red(C.bold(f"✗ {len(hits)} sensitive file(s) detected ({mode}):")),
        "",
    ]
    for path, reason in hits:
        lines.append(f"  {C.red('✗')} {C.bold(path)}")
        lines.append(f"      {C.yellow('reason:')} {reason}")
    lines.append("")
    lines.append(C.bold("Fix:"))
    lines.append("  1. Add the patterns to .gitignore (already done).")
    lines.append("  2. Untrack already-committed files:  git rm --cached <path>")
    lines.append("  3. Then commit the .gitignore change.")
    lines.append("  4. NEVER commit the actual files. They are user data / secrets.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="brokus git safety check – blocks sensitive files from being committed."
    )
    ap.add_argument("--staged", action="store_true", help="Check staged files only (default).")
    ap.add_argument("--all", dest="all_tracked", action="store_true", help="Check all tracked files.")
    ap.add_argument(
        "--working-tree", action="store_true",
        help="Check every file in the working tree (recursively).",
    )
    ap.add_argument("--ci", action="store_true", help="CI mode – minimal output.")
    args = ap.parse_args()

    if not _is_git_repo():
        if not args.ci:
            print(C.yellow("⚠ Not a git repository – nothing to check."))
        return 2

    # Determine file set to scan
    if args.working_tree:
        # All non-ignored files in the working tree
        files = _git_files(["ls-files", "--others", "--exclude-standard"])
        files += _git_files(["ls-files"])
        files = sorted(set(files))
        mode = "working tree"
    elif args.all_tracked:
        files = _git_files(["ls-files"])
        mode = "all tracked files"
    else:
        # Default: staged files (for pre-commit hook)
        # Only scan files that are actually being *added* or *modified* in the
        # commit. Deletions (D) do not bring sensitive content into the repo –
        # they remove it – so we intentionally ignore them.
        files = _git_files(["diff", "--cached", "--name-only", "--diff-filter=ACMRT"])
        mode = "staged files"

    hits = _scan(files)

    if args.ci:
        # Machine-readable
        import json
        print(json.dumps({
            "mode": mode,
            "ok": not hits,
            "count": len(hits),
            "hits": [{"path": p, "reason": r} for p, r in hits],
        }, indent=2))
    else:
        if not hits:
            print(C.green(f"✓ {mode}: clean – safe to commit"))
        else:
            print(_format_report(hits, mode))

    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
