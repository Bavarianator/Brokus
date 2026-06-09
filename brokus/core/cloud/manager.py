"""Central manager for cloud upload configuration and orchestration.

Provider credentials are stored **encrypted** inside the same
:class:`brokus.utils.crypto.SecretStore` that protects API keys — no
plain-text ``cloud_config.json`` is written to disk.

Credentials are stored as a single JSON blob under the ``cloud_config`` key
inside ``secrets.enc`` (AES-256-GCM). If the user has configured a master
passphrase, the cloud config is additionally protected by it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from .base import CloudUploader, UploadResult
from .nextcloud import NextcloudUploader

console = Console()

# Sentinel key used inside SecretStore for the cloud-config JSON blob
_CLOUD_CONFIG_KEY = "cloud_config"


# ── Config helpers (encrypted via SecretStore) ──


def _load_cloud_config() -> dict:
    """Load the cloud-config blob from the encrypted SecretStore.

    Falls back to the old plain-text ``cloud_config.json`` and migrates it
    silently into the encrypted store.
    """
    from brokus.utils.crypto import SecretStore

    # 1) Try encrypted store first
    store = SecretStore.instance()
    if not store.is_loaded:
        store.load()

    raw = store.get(_CLOUD_CONFIG_KEY)
    if raw is not None:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass

    # 2) Fallback: migrate from legacy plain-text file
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    legacy = Path(xdg) / "brokus" / "cloud_config.json"
    if legacy.exists():
        try:
            with open(legacy) as f:
                config = json.load(f)
            # Write into encrypted store immediately
            store.set(_CLOUD_CONFIG_KEY, json.dumps(config))
            store.save()
            # Remove the plain-text file
            try:
                legacy.unlink(missing_ok=True)
            except Exception:
                pass
            console.print(
                "[dim]☁ Migrated cloud credentials to encrypted storage.[/dim]"
            )
            return config
        except Exception:
            pass

    return {}


def _save_cloud_config(config: dict):
    """Persist the cloud config dict into the encrypted SecretStore."""
    from brokus.utils.crypto import SecretStore

    store = SecretStore.instance()
    if not store.is_loaded:
        store.load()

    store.set(_CLOUD_CONFIG_KEY, json.dumps(config))
    store.save()


# ── CloudManager ──


class CloudManager:
    """Manages configured cloud uploaders, persistent config, and batch uploads.

    Typical usage::

        cloud = CloudManager()
        if cloud.uploaders:
            results = cloud.upload_book(exported_files, "My Book Title")
    """

    def __init__(self):
        self.uploaders: List[CloudUploader] = []
        self._load_config()

    # ── Config persistence (encrypted via SecretStore) ──

    def _load_config(self):
        """Load and instantiate all enabled uploaders from encrypted storage."""
        config = _load_cloud_config()

        for provider, settings in config.items():
            if not settings.get("enabled", False):
                continue
            try:
                if provider == "nextcloud":
                    auth_type = settings.get("auth_type", "basic")

                    if auth_type == "v2":
                        # Login Flow v2 – credentials cached in nextcloud_token.json
                        self.uploaders.append(
                            NextcloudUploader(
                                settings["url"],
                                auto_login=False,  # don't re-open browser
                            )
                        )
                    else:
                        self.uploaders.append(
                            NextcloudUploader(
                                settings["url"],
                                settings["username"],
                                app_password=settings.get("app_password", ""),
                            )
                        )
                elif provider == "gdrive":
                    from .gdrive import GoogleDriveUploader

                    up = GoogleDriveUploader(
                        client_id=settings.get("client_id", ""),
                        client_secret=settings.get("client_secret", ""),
                    )
                    if up.has_credentials or up.is_configured():
                        self.uploaders.append(up)
                elif provider == "rclone":
                    from .rclone import RcloneUploader

                    self.uploaders.append(
                        RcloneUploader(remote=settings.get("remote", ""))
                    )
            except Exception as e:
                console.print(
                    f"[yellow]⚠ {provider} could not be loaded: {e}[/yellow]"
                )

    def save_config(self, provider: str, settings: dict):
        """Persist (or update) the configuration for *provider* (encrypted)."""
        config = _load_cloud_config()
        config[provider] = settings
        _save_cloud_config(config)

    # ── Upload orchestration ──

    def upload_book(
        self, export_files: List[Path], book_title: str
    ) -> List[UploadResult]:
        """Upload a set of exported book files to all configured providers.

        Args:
            export_files: List of local ``Path`` objects to upload.
            book_title: Human-readable book title (used for the remote folder name).

        Returns:
            List of :class:`UploadResult` (one per file × provider).
        """
        if not self.uploaders:
            return []

        results: List[UploadResult] = []
        remote_folder = f"brokus/{self._sanitize(book_title)}"

        console.print(f"\n[bold cyan]☁ Cloud-Upload: {book_title}[/bold cyan]")

        for uploader in self.uploaders:
            for file in export_files:
                console.print(f"  → {uploader.name}: {file.name}...", end=" ")
                result = uploader.upload(file, remote_folder)
                console.print(
                    "[green]✓[/green]"
                    if result.success
                    else f"[red]✗ {result.error}[/red]"
                )
                results.append(result)

        return results

    # ── Interactive Setup Wizard ──

    def setup_wizard(self):
        """Walk the user through configuring cloud providers."""
        console.print("\n[bold cyan]☁ Cloud-Upload Setup[/bold cyan]\n")

        options = [
            ("1", "Nextcloud"),
            ("2", "Google Drive"),
            ("3", "rclone (40+ Anbieter)"),
            ("4", "Fertig"),
        ]
        for key, label in options:
            console.print(f"  [{key}] {label}")
        console.print()

        choice = input("  Provider wählen: ").strip()

        if choice == "1":
            self._setup_nextcloud()
        elif choice == "2":
            self._setup_gdrive()
        elif choice == "3":
            self._setup_rclone()
        else:
            console.print("  [dim]Done.[/dim]")

    def _setup_rclone(self):
        """Setup via rclone (universal cloud upload tool)."""
        from .rclone import RcloneUploader

        uploader = RcloneUploader()

        if not uploader.is_installed():
            console.print("\n  [yellow]⚠ rclone is not installed.[/yellow]")
            console.print("  rclone automatisch installieren? (j/n): ", end="")
            try:
                raw = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                raw = ""
            if raw in ("j", "ja", "y", "yes", ""):
                os_name = os.uname().sysname if hasattr(os, 'uname') else ""
                try:
                    if os_name == "Darwin" and shutil.which("brew"):
                        subprocess.run(["brew", "install", "rclone"], check=True)
                    elif shutil.which("apt"):
                        subprocess.run(["sudo", "apt", "install", "-y", "rclone"], check=True)
                    elif shutil.which("pacman"):
                        subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "rclone"], check=True)
                    elif shutil.which("dnf"):
                        subprocess.run(["sudo", "dnf", "install", "-y", "rclone"], check=True)
                    else:
                        console.print(
                            "  [red]✗ Could not detect package manager.[/red]"
                        )
                        console.print(
                            "  [dim]Install manually: "
                            "https://rclone.org/install/[/dim]"
                        )
                        return
                    console.print("  [green]✓ rclone installed![/green]")
                except subprocess.CalledProcessError:
                    console.print(
                        "  [red]✗ Installation failed. "
                        "Install manually: https://rclone.org/install/[/red]"
                    )
                    return
            else:
                return

        remote = uploader.pick_remote()
        if remote:
            self.save_config("rclone", {
                "enabled": True,
                "remote": remote,
            })
            self.uploaders.append(uploader)
            console.print(
                f"[green]✅ rclone remote '{remote}' konfiguriert![/green]"
            )

    def _setup_nextcloud(self):
        """Interactive Nextcloud setup.

        Supports two methods:
        1. **Login Flow v2** (recommended) – browser login, zero config
        2. **App-Password** (Basic Auth) – manual, needs admin config
        """
        console.print("\n[bold]Nextcloud Setup[/bold]\n")
        console.print("  Choose setup method:\n")
        console.print(
            "  [cyan]1[/cyan]. Browser-Login (empfohlen)"
        )
        console.print(
            "    [dim]Nur URL eingeben, Browser öffnet sich → "
            "Einloggen + Erlauben ✅[/dim]"
        )
        console.print(
            "  [cyan]2[/cyan]. App-Password (Basic Auth – manuell)"
        )
        console.print(
            "    [dim]Benötigt: Nextcloud → Einstellungen → Sicherheit[/dim]"
        )
        console.print()

        auth_choice = input("  Your choice (1/2): ").strip()

        if auth_choice == "2":
            self._setup_nextcloud_basic()
        else:
            self._setup_nextcloud_v2()

    def _setup_nextcloud_v2(self):
        """Setup via Nextcloud Login Flow v2 (browser-based, recommended)."""
        url = input(
            "  Nextcloud URL (e.g. https://cloud.example.com): "
        ).strip()
        if not url:
            console.print("  [red]Aborted.[/red]")
            return

        uploader = NextcloudUploader(url, auto_login=False)

        # Run the login flow
        if uploader.login_v2():
            self.save_config("nextcloud", {
                "enabled": True,
                "url": url,
                "auth_type": "v2",
            })
            self.uploaders.append(uploader)
            console.print(
                "[green]✅ Nextcloud via Browser-Login konfiguriert![/green]"
            )
        else:
            console.print("[red]✗ Login fehlgeschlagen.[/red]")

    def _setup_nextcloud_basic(self):
        """Setup via Basic Auth (username + app-password)."""
        console.print(
            "[dim]Generate an app-password at: "
            "Nextcloud → Settings → Security[/dim]\n"
        )
        url = input("  Server-URL (e.g. https://cloud.example.com): ").strip()
        if not url:
            console.print("  [red]Aborted.[/red]")
            return
        user = input("  Username: ").strip()
        pw = input("  App-Password: ").strip()

        if not user or not pw:
            console.print("  [red]Username and password required.[/red]")
            return

        uploader = NextcloudUploader(url, user, app_password=pw)
        console.print("  Testing connection...", end=" ")

        if uploader.test_connection():
            console.print("[green]✓[/green]")
            self.save_config("nextcloud", {
                "enabled": True,
                "url": url,
                "username": user,
                "app_password": pw,
                "auth_type": "basic",
            })
            self.uploaders.append(uploader)
            console.print("[green]Nextcloud configured successfully![/green]")
        else:
            console.print("[red]✗[/red]")
            console.print(
                "[red]Connection failed. Please check your credentials.[/red]"
            )

    def _setup_gdrive(self):
        """Interactive Google Drive setup with OAuth flow.

        Prompts for Client ID + Secret (one-time, from Google Cloud Console),
        then opens the browser for OAuth authentication.
        """
        console.print("\n[bold]Google Drive Setup[/bold]\n")
        console.print(
            "  [dim]You need a Google Client ID + Secret.\n"
            "  Guide: https://console.cloud.google.com/apis/credentials[/dim]\n"
        )

        client_id = input("  Client ID: ").strip()
        if not client_id:
            console.print("  [red]Aborted.[/red]")
            return

        client_secret = input("  Client Secret: ").strip()
        if not client_secret:
            console.print("  [red]Aborted.[/red]")
            return

        from .gdrive import GoogleDriveUploader

        uploader = GoogleDriveUploader(client_id, client_secret)
        console.print()

        if uploader.login(client_id, client_secret):
            self.save_config("gdrive", {
                "enabled": True,
                "client_id": client_id,
                "client_secret": client_secret,
            })
            self.uploaders.append(uploader)
            console.print(
                "[green]✅ Google Drive configured successfully![/green]"
            )
        else:
            console.print("[red]✗ Authentication failed.[/red]")

    # ── Status ──

    def show_status(self):
        """Print a table of all configured cloud providers with connection status."""
        console.print()
        if not self.uploaders:
            console.print("  [dim]No cloud providers configured.[/dim]")
            console.print(
                "  Configure at: [cyan]Settings → Cloud-Upload[/cyan]\n"
            )
            return

        table = Table(title="☁ Cloud-Provider", box=None, padding=(0, 1))
        table.add_column("Provider", style="cyan", width=20)
        table.add_column("Status", width=40)

        for up in self.uploaders:
            ok = up.test_connection()
            status = "[green]✓ Active[/green]" if ok else "[red]✗ Error[/red]"
            table.add_row(up.name, status)

        console.print(table)
        console.print()

    @property
    def is_configured(self) -> bool:
        """Return ``True`` if at least one uploader is active."""
        return len(self.uploaders) > 0

    # ── Helpers ──

    @staticmethod
    def _sanitize(name: str) -> str:
        """Make *name* safe for use as a remote folder name."""
        return "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip()
