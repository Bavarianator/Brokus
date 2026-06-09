"""rclone-based cloud uploader.

Wraps the ``rclone`` CLI tool as a :class:`CloudUploader`, giving access to
**40+ cloud providers** (Google Drive, Nextcloud, OneDrive, Dropbox, S3, …)
through a single, consistent interface.

Requires ``rclone`` to be installed on the system (``brew install rclone``,
``apt install rclone``, or from https://rclone.org/install/).

The user configures remotes via ``rclone config`` — brokus just calls
``rclone copy`` for the actual upload.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from .base import CloudUploader, UploadResult


class RcloneUploader(CloudUploader):
    """Upload files to any rclone-supported cloud provider.

    Uses the ``rclone copy`` command internally. The user must have already
    configured at least one remote via ``rclone config``.

    Args:
        remote: rclone remote name (e.g. ``\"gdrive:\"``, ``\"nextcloud:\"``).
            If omitted you must call :meth:`pick_remote` before first upload.
    """

    name = "rclone"

    def __init__(self, remote: str = ""):
        self._remote = remote
        self._available: Optional[bool] = None

    # ── Helpers ──

    @property
    def remote(self) -> str:
        """The configured rclone remote name (with trailing colon)."""
        return self._remote

    @remote.setter
    def remote(self, value: str):
        r = value.strip()
        if r and not r.endswith(":"):
            r += ":"
        self._remote = r

    def is_installed(self) -> bool:
        """Return ``True`` if the ``rclone`` binary is found on ``$PATH``."""
        if self._available is None:
            self._available = shutil.which("rclone") is not None
        return self._available

    def list_remotes(self) -> List[str]:
        """Return all configured rclone remotes (e.g. ``[\"gdrive:\", \"nextcloud:\"]``)."""
        if not self.is_installed():
            return []
        try:
            result = subprocess.run(
                ["rclone", "listremotes"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                return [r.strip() for r in result.stdout.splitlines() if r.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return []

    def pick_remote(self) -> Optional[str]:
        """Show an interactive menu of configured remotes for the user to pick.

        If no remotes exist, offers to run ``rclone config``.
        """
        from rich.console import Console

        console_ = Console()

        if not self.is_installed():
            console_.print("  [red]✗ rclone is not installed.[/red]")
            console_.print(
                "  [dim]Install: brew install rclone  |  "
                "apt install rclone  |  https://rclone.org/install/[/dim]"
            )
            return None

        remotes = self.list_remotes()

        if not remotes:
            console_.print(
                "  [yellow]⚠ No rclone remotes configured.[/yellow]"
            )
            if input("  Open rclone config now? (j/n): ").strip().lower() in (
                "j",
                "ja",
                "y",
                "yes",
                "",
            ):
                console_.print(
                    "\n  [dim]Running: rclone config[/dim]"
                )
                console_.print(
                    "  [dim]Choose your provider and complete the OAuth "
                    "flow in the terminal.[/dim]\n"
                )
                subprocess.run(["rclone", "config"])
                remotes = self.list_remotes()

        if not remotes:
            console_.print("  [red]✗ No remotes configured. Aborting.[/red]")
            return None

        console_.print("\n  Available remotes:")
        for i, r in enumerate(remotes, 1):
            console_.print(f"  [cyan]{i}[/cyan]. {r}")

        try:
            raw = input(f"\n  Choose remote (1-{len(remotes)}): ").strip()
            idx = int(raw) - 1
            if 0 <= idx < len(remotes):
                self._remote = remotes[idx]
                return self._remote
        except (ValueError, IndexError):
            pass

        console_.print("  [red]Invalid choice.[/red]")
        return None

    # ── Public API ──

    def upload(self, local_path: Path, remote_folder: str = "brokus/") -> UploadResult:
        """Upload *local_path* via ``rclone copy``.

        Args:
            local_path: The local file to upload.
            remote_folder: Destination folder on the remote.

        Returns:
            An :class:`UploadResult`.
        """
        if not self.is_installed():
            return UploadResult(
                success=False,
                provider=self.name,
                remote_path="",
                error="rclone not installed",
            )

        if not self._remote:
            return UploadResult(
                success=False,
                provider=self.name,
                remote_path="",
                error="No remote configured. Run cloud setup first.",
            )

        # Normalise remote path
        dest = f"{self._remote}{remote_folder.strip('/')}/"

        try:
            result = subprocess.run(
                ["rclone", "copy", str(local_path), dest],
                capture_output=True, text=True, timeout=300,
            )

            if result.returncode == 0:
                return UploadResult(
                    success=True,
                    provider=f"rclone ({self._remote})",
                    remote_path=f"{remote_folder}{local_path.name}",
                )
            else:
                err = result.stderr.strip() or f"exit code {result.returncode}"
                return UploadResult(
                    success=False,
                    provider=self.name,
                    remote_path="",
                    error=err,
                )

        except subprocess.TimeoutExpired:
            return UploadResult(
                success=False,
                provider=self.name,
                remote_path="",
                error="Upload timed out (300s)",
            )
        except FileNotFoundError:
            return UploadResult(
                success=False,
                provider=self.name,
                remote_path="",
                error="rclone not found",
            )
        except OSError as e:
            return UploadResult(
                success=False, provider=self.name, remote_path="", error=str(e)
            )

    def test_connection(self) -> bool:
        """Verify that rclone is installed and the remote is accessible."""
        if not self.is_installed():
            return False

        if not self._remote:
            # Just check that rclone itself works
            try:
                result = subprocess.run(
                    ["rclone", "version"],
                    capture_output=True, text=True, timeout=10,
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return False

        # Check that the remote is reachable
        try:
            result = subprocess.run(
                ["rclone", "lsf", self._remote, "--max-depth=1", "--limit=1"],
                capture_output=True, text=True, timeout=15,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
