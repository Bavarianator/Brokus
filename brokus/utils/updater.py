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

from brokus import __version__ as current_version
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


# ─────────────────────────────────────────────────────────────
# GitHub API
# ─────────────────────────────────────────────────────────────

GITHUB_REPO = "Bavarianator/Brokus"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_TAGS_API = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
REQUEST_TIMEOUT = 10  # seconds


def _fetch_latest_from_github() -> tuple[str, str, str]:
    """Fetch the latest version from GitHub.

    Tries releases/latest first, then falls back to tags.

    Returns:
        Tuple of (version_str, release_url, release_notes).
        On error, returns ("", "", error_message).
    """
    # Try releases API first
    try:
        req = urlopen(GITHUB_API, timeout=REQUEST_TIMEOUT)
        data = json.loads(req.read().decode())
        tag = data.get("tag_name", "").lstrip("v")
        url = data.get("html_url", "")
        notes = data.get("body", "") or ""
        if tag and _parse_semver(tag) != (0, 0, 0):
            return tag, url, notes
    except URLError as e:
        return ("", "", f"Network error: {e.reason}")
    except (json.JSONDecodeError, KeyError) as e:
        log.debug(f"GitHub releases API parse failed: {e}")
    except Exception as e:
        log.debug(f"GitHub releases API failed: {e}")

    # Fallback: tags API
    try:
        req = urlopen(GITHUB_TAGS_API, timeout=REQUEST_TIMEOUT)
        data = json.loads(req.read().decode())
        if data and isinstance(data, list):
            tag = data[0].get("name", "").lstrip("v")
            url = f"https://github.com/{GITHUB_REPO}/releases/tag/{data[0].get('name', '')}"
            if tag and _parse_semver(tag) != (0, 0, 0):
                return tag, url, ""
    except URLError as e:
        return ("", "", f"Network error: {e.reason}")
    except Exception as e:
        log.debug(f"GitHub tags API failed: {e}")

    return ("", "", "Could not fetch version from GitHub")


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

async def check_for_updates() -> UpdateStatus:
    """Check if a newer version of brokus is available on GitHub.

    Returns:
        UpdateStatus with current_version, latest_version,
        is_update_available flag, and optional error.
    """
    result = UpdateStatus(current_version=current_version)

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

    current_semver = _parse_semver(current_version)
    latest_semver = _parse_semver(latest_ver)

    if current_semver == (0, 0, 0):
        result.error = f"Could not parse current version: {current_version!r}"
        return result
    if latest_semver == (0, 0, 0):
        result.error = f"Could not parse latest version: {latest_ver!r}"
        return result

    result.is_update_available = _semver_greater(latest_semver, current_semver)
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

    # Step 2: pip install -e .
    try:
        log.info("Updating: pip install -e .", stage="Update")
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "-e", ".",
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            err_msg = stderr.decode().strip() or stdout.decode().strip()[:200]
            return False, f"pip install failed: {err_msg}"
        log.info(f"pip install OK", stage="Update")
    except asyncio.TimeoutError:
        return False, "pip install timed out (120s)"
    except Exception as e:
        return False, f"pip install error: {e}"

    return True, f"Update to v{status.latest_version} erfolgreich! Bitte neustarten."
