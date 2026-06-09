"""Updater – check for and install brokus updates from GitHub.

Uses the GitHub Releases API to discover newer versions, compares
semver, and offers to update via ``git pull && pip install -e .``.

Usage:
    from brokus.utils.updater import check_for_updates, perform_update
    status = await check_for_updates()           # returns UpdateStatus
    ok, msg = await perform_update(status)       # runs git pull + pip install
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.request import urlopen
from urllib.error import URLError

from brokus import __version__ as _fallback_version
from brokus.utils.logger import log


# ─────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────

@dataclass
class UpdateStatus:
    """Result of an update check."""
    current_version: str = ""
    latest_version: str = ""
    is_update_available: bool = False
    release_url: str = ""
    release_notes: str = ""
    error: str = ""

    @property
    def up_to_date(self) -> bool:
        return not self.is_update_available and not self.error


# ─────────────────────────────────────────────────────────────
# Project paths
# ─────────────────────────────────────────────────────────────

def _get_project_root() -> Path:
    """Return the project root directory (where pyproject.toml lives)."""
    return Path(__file__).resolve().parent.parent.parent


# ─────────────────────────────────────────────────────────────
# Version helpers
# ─────────────────────────────────────────────────────────────

def _parse_semver(version_str: str) -> tuple[int, int, int]:
    """Parse '1.2.3' → (1, 2, 3). Returns (0,0,0) on failure."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version_str.strip())
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return (0, 0, 0)


def _semver_greater(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    """Return True if a > b (semver comparison)."""
    return a > b


def _get_git_tag() -> Optional[str]:
    """Get the nearest git tag reachable from HEAD (via git describe).

    Returns the tag name (without 'v' prefix), or None if:
    - Git is not installed
    - No tags exist
    - Not a git repository

    Beispiel: Bei Tag "ai" → "ai", bei "v1.0.1" → "1.0.1"
    """
    try:
        root = _get_project_root()
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip().lstrip("v")
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def _detect_current_version() -> str:
    """Detect the current version of brokus.

    Priority:
    1. Git tag (via `git describe --tags --abbrev=0`)
    2. __version__ from brokus/__init__.py (Fallback)

    Returns:
        Version string (e.g. "1.0.0", "ai").
    """
    git_tag = _get_git_tag()
    if git_tag:
        return git_tag
    return _fallback_version


# ─────────────────────────────────────────────────────────────
# GitHub API
# ─────────────────────────────────────────────────────────────

GITHUB_REPO = "Bavarianator/Brokus"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
GITHUB_TAGS_API = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
REQUEST_TIMEOUT = 10  # seconds


def _fetch_json(url: str) -> Optional[dict | list]:
    """Fetch a URL and parse JSON. Returns None on error."""
    try:
        req = urlopen(url, timeout=REQUEST_TIMEOUT)
        return json.loads(req.read().decode())
    except Exception as e:
        log.debug(f"GitHub API fetch failed: {url} — {e}")
        return None


def _fetch_latest_from_github() -> tuple[str, str, str]:
    """Fetch the latest version from GitHub.

    Strategy:
    1. Fetch all releases from GitHub Releases API
    2. Find the first published release that has a tag
    3. The tag can be semver (e.g. v1.0.1) or any string (e.g. "ai")

    Returns:
        Tuple of (version_str, release_url, release_notes).
        On error, returns ("", "", error_message).
    """
    # Strategy 1: Fetch all releases, find first published one
    data = _fetch_json(GITHUB_RELEASES_API)
    if data and isinstance(data, list):
        for release in data:
            tag = release.get("tag_name", "")
            if not tag:
                continue
            # Skip drafts
            if release.get("draft", False):
                continue
            tag_clean = tag.lstrip("v")
            url = release.get("html_url", "") or f"https://github.com/{GITHUB_REPO}/releases/tag/{tag}"
            notes = release.get("body", "") or ""
            return (tag_clean, url, notes)

    # Strategy 2: Fallback — tags API (falls releases leer sind)
    data = _fetch_json(GITHUB_TAGS_API)
    if data and isinstance(data, list) and len(data) > 0:
        tag = data[0].get("name", "").lstrip("v")
        url = f"https://github.com/{GITHUB_REPO}/releases/tag/{data[0].get('name', '')}"
        if tag:
            return (tag, url, "")

    return ("", "", "Could not fetch version from GitHub — kein Release gefunden")


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

async def check_for_updates() -> UpdateStatus:
    """Check if a newer version of brokus is available on GitHub.

    Die aktuelle Version wird zuverlässig via Git-Tag ermittelt
    (git describe --tags --abbrev=0). Nur als Fallback wird die
    __version__ aus brokus/__init__.py verwendet.

    Returns:
        UpdateStatus with current_version, latest_version,
        is_update_available flag, and optional error.
    """
    result = UpdateStatus(current_version=_detect_current_version())

    try:
        latest_ver, release_url, release_notes = await asyncio.to_thread(
            _fetch_latest_from_github
        )
    except Exception as e:
        result.error = f"Update check failed: {e}"
        return result

    if not latest_ver:
        result.error = release_notes or "Could not determine latest version"
        return result

    result.latest_version = latest_ver
    result.release_url = release_url
    result.release_notes = release_notes

    # Versionen vergleichen: erst Semver, dann String
    current_semver = _parse_semver(result.current_version)
    latest_semver = _parse_semver(latest_ver)

    if current_semver == (0, 0, 0):
        current_semver = None
    if latest_semver == (0, 0, 0):
        latest_semver = None

    if current_semver is not None and latest_semver is not None:
        # Beides gültige Semver → normaler Vergleich
        result.is_update_available = _semver_greater(latest_semver, current_semver)
    elif latest_semver is None and current_semver is not None:
        # Release hat keinen Semver-Tag (z.B. "ai"), aber lokale Version schon
        # → nur als Update betrachten, wenn der Tag-Name anders ist
        result.is_update_available = (latest_ver != result.current_version)
    else:
        # Beide kein Semver oder nur latest hat Semver → String-Vergleich
        result.is_update_available = (latest_ver != result.current_version)

    return result


async def perform_update(status: UpdateStatus) -> tuple[bool, str]:
    """Perform the actual update: git pull + pip install -e .

    Args:
        status: UpdateStatus from check_for_updates().

    Returns:
        Tuple of (success: bool, message: str).
    """
    project_root = _get_project_root()

    # Step 1: git pull
    try:
        log.info("Updating: git pull...", stage="Update")
        proc = await asyncio.create_subprocess_exec(
            "git", "pull",
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        if proc.returncode != 0:
            err_msg = stderr.decode().strip() or stdout.decode().strip()[:200]
            return False, f"git pull failed: {err_msg}"
        log.info(f"git pull OK: {stdout.decode().strip()[:100]}", stage="Update")
    except asyncio.TimeoutError:
        return False, "git pull timed out (60s)"
    except FileNotFoundError:
        return False, "git not found — is Git installed?"
    except Exception as e:
        return False, f"git pull error: {e}"

    # Step 2: pip install -e . (mit Live-Output)
    pip_args = [sys.executable, "-m", "pip", "install", "-e", "."]
    pip_args_fallback = pip_args + ["--break-system-packages"]

    for attempt_args, attempt_label in [(pip_args, "pip install"), (pip_args_fallback, "pip install --break-system-packages")]:
        log.info(f"Updating: {attempt_label}", stage="Update")
        try:
            proc = await asyncio.create_subprocess_exec(
                *attempt_args,
                cwd=str(project_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Output live streamen, damit der User Fortschritt sieht
            full_stdout = []
            full_stderr = []
            if proc.stdout is None or proc.stderr is None:
                return False, "pip install: konnte keine Ausgabe-Pipes öffnen"

            async def _read_stream(stream, storage):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace").rstrip()
                    if decoded:
                        log.info(f"  {decoded}", stage="Update")
                    storage.append(decoded)

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        _read_stream(proc.stdout, full_stdout),
                        _read_stream(proc.stderr, full_stderr),
                    ),
                    timeout=300,
                )
            except asyncio.TimeoutError:
                proc.kill()
                if attempt_args is pip_args_fallback:
                    return False, "pip install timed out (300s) — auch mit --break-system-packages"
                log.info(f"pip install timed out — retrying mit --break-system-packages", stage="Update")
                continue

            await proc.wait()

            if proc.returncode == 0:
                log.info(f"{attempt_label} OK", stage="Update")
                return True, f"Update to v{status.latest_version} erfolgreich! Bitte neustarten."

            err_msg = "\n".join(full_stderr or full_stdout)[:500]

            # PEP 668 (externally-managed-environment) → Fallback mit --break-system-packages
            if "externally-managed" in err_msg.lower():
                if attempt_args is pip_args_fallback:
                    return False, f"pip install failed: {err_msg}"
                log.info(f"PEP 668 detected — retrying with --break-system-packages", stage="Update")
                continue

            return False, f"pip install failed: {err_msg}"

        except Exception as e:
            if attempt_args is pip_args_fallback:
                return False, f"pip install error: {e}"
            log.info(f"pip error: {e} — retrying mit --break-system-packages", stage="Update")
            continue

    return False, "pip install fehlgeschlagen – auch mit --break-system-packages"
