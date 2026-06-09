"""Nextcloud upload via WebDAV + OCS Share API.

Supports two authentication methods:

1. **Basic Auth** (legacy) – username + app-password
2. **Login Flow v2** – browser-based OAuth (Nextcloud built-in, no Keycloak)

The Login Flow v2 is the recommended approach. The user enters their
Nextcloud URL, the browser opens, they log in and click "Allow", and
brokus receives the credentials automatically.
"""

from __future__ import annotations

import json
import os
import time
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

from .base import CloudUploader, UploadResult

# Where the Login Flow v2 token cache is stored
_TOKEN_PATH = os.path.expanduser("~/.brokus/nextcloud_token.json")


class NextcloudUploader(CloudUploader):
    """Upload files to a Nextcloud instance via WebDAV.

    Supports two setup methods:

    * **Basic Auth** – pass ``username`` + ``app_password``
    * **Login Flow v2** – pass only ``base_url``, then call :meth:`login_v2`
      (or it auto-runs on first :meth:`upload`)

    The Login Flow v2 uses Nextcloud's built-in browser-based app-password
    generation. No Keycloak, no client secrets required.

    Args:
        base_url: Nextcloud server URL (e.g. ``https://cloud.example.com``).
        username: Nextcloud username (required for Basic Auth).
        app_password: App-password for Basic Auth.
        auto_login: If ``True`` and no credentials given, automatically
            start the Login Flow v2 on first upload (default: ``True``).
    """

    name = "Nextcloud"

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Prepend ``https://`` if no protocol is specified.

        ``cloud.besener.de`` → ``https://cloud.besener.de``
        ``https://cloud.besener.de`` → ``https://cloud.besener.de``
        ``http://192.168.1.100`` → ``http://192.168.1.100``
        """
        url = url.strip()
        if not url.startswith("http"):
            url = "https://" + url
        return url.rstrip("/")

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        app_password: str | None = None,
        auto_login: bool = True,
    ):
        self.base_url = self._normalize_url(base_url)
        self.username = username
        self._app_password = app_password
        self._auto_login = auto_login

        if username and app_password:
            self._auth_type = "basic"
            self._basic_auth = HTTPBasicAuth(username, app_password)
        else:
            self._auth_type = "v2"
            self._basic_auth = None
            self._try_load_cached_token()

    # ── Auth helpers ──

    @property
    def auth_type(self) -> str:
        """Return ``"basic"`` or ``"v2"`` depending on setup."""
        return self._auth_type

    @property
    def has_credentials(self) -> bool:
        """Return ``True`` if we have valid credentials for WebDAV."""
        return self._basic_auth is not None

    def _try_load_cached_token(self):
        """Restore credentials from a previous Login Flow v2 session."""
        if os.path.exists(_TOKEN_PATH):
            try:
                with open(_TOKEN_PATH) as f:
                    data = json.load(f)
                server = self._normalize_url(data.get("server", ""))
                if server == self.base_url:
                    user = data["loginName"]
                    pw = data["appPassword"]
                    self.username = user
                    self._app_password = pw
                    self._basic_auth = HTTPBasicAuth(user, pw)
            except (json.JSONDecodeError, OSError, KeyError):
                pass

    def _cache_token(self, data: dict):
        """Persist the credentials from Login Flow v2."""
        os.makedirs(os.path.dirname(_TOKEN_PATH), exist_ok=True)
        try:
            with open(_TOKEN_PATH, "w") as f:
                json.dump(data, f, indent=2)
            os.chmod(_TOKEN_PATH, 0o600)
        except OSError:
            pass

    # ── Nextcloud Login Flow v2 ──

    def login_v2(self) -> bool:
        """Execute Nextcloud Login Flow v2.

        Opens the user's browser to authenticate with Nextcloud and
        automatically receive an app password. Polls the server until
        the user approves or the request times out (120s).

        Returns:
            ``True`` if login succeeded, ``False`` on timeout or error.
        """
        from rich.console import Console

        console_ = Console()

        # Step 1: Request login flow from server
        try:
            r = requests.post(
                f"{self.base_url}/index.php/login/v2", timeout=10
            )
            if r.status_code != 200:
                console_.print(
                    f"  [red]✗ Login v2 nicht verfügbar (HTTP {r.status_code}).[/red]"
                )
                return False
            data = r.json()
        except requests.RequestException as e:
            console_.print(f"  [red]✗ Could not reach Nextcloud: {e}[/red]")
            return False
        except (ValueError, KeyError) as e:
            console_.print(f"  [red]✗ Invalid server response: {e}[/red]")
            return False

        login_url = data["login"]
        poll_token = data["poll"]["token"]
        poll_url = data["poll"]["endpoint"]

        # Step 2: Open browser
        console_.print()
        console_.print(
            "  [cyan]🌐 Browser opened for Nextcloud login...[/cyan]"
        )
        console_.print(
            "  [dim]Waiting for confirmation in browser (120s timeout)...[/dim]"
        )
        console_.print()
        webbrowser.open(login_url)

        # Step 3: Poll until user approves
        timeout = 120.0
        waited = 0.0
        while waited < timeout:
            time.sleep(2)
            waited += 2.0
            try:
                r = requests.post(
                    poll_url, data={"token": poll_token}, timeout=10
                )
                if r.status_code == 200:
                    creds = r.json()
                    server = creds.get("server", self.base_url).rstrip("/")
                    self.username = creds["loginName"]
                    self._app_password = creds["appPassword"]
                    self._basic_auth = HTTPBasicAuth(
                        self.username, self._app_password
                    )
                    self._cache_token(creds)
                    console_.print(
                        "  [green]✅ Nextcloud verbunden!"
                        f" Server: {server}[/green]"
                    )
                    return True
            except requests.RequestException:
                pass  # Keep polling

        console_.print("  [red]✗ Login timeout. Bitte erneut versuchen.[/red]")
        return False

    def _ensure_auth(self):
        """Ensure we have valid auth credentials before making requests.

        If auth type is ``"v2"`` and no cached credentials exist,
        automatically starts the Login Flow v2.
        """
        if self._basic_auth is None and self._auto_login:
            self.login_v2()

    def _do_request(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """Issue an HTTP request with the configured auth method.

        If using Login Flow v2 and no credentials are loaded yet,
        automatically starts the browser login flow.
        """
        self._ensure_auth()
        kwargs.setdefault("timeout", 10)

        if self._basic_auth is not None:
            kwargs["auth"] = self._basic_auth
        else:
            # No credentials available after attempted login
            resp = requests.Response()
            resp.status_code = 401
            resp.reason = "Nextcloud nicht authentifiziert (Login erforderlich)"
            return resp

        return requests.request(method, url, **kwargs)

    # ── WebDAV helpers ──

    def _dav_url(self, remote_path: str) -> str:
        return f"{self.base_url}/remote.php/dav/files/{self.username}/{remote_path}"

    def _ensure_folder(self, folder: str) -> bool:
        """Create a remote folder tree via MKCOL (recursive parent creation)."""
        parts = folder.strip("/").split("/")
        for i in range(1, len(parts) + 1):
            sub = "/".join(parts[:i])
            url = self._dav_url(sub)
            r = self._do_request("MKCOL", url)
            # 201 = created, 405 = already exists — both OK
            if r.status_code not in (201, 405):
                return False
        return True

    # ── OCS Share-API ──

    def _create_share_link(self, remote_path: str) -> Optional[str]:
        """Create a public share link for the given remote path.

        Returns the share URL or ``None`` on failure.
        """
        try:
            url = f"{self.base_url}/ocs/v2.php/apps/files_sharing/api/v1/shares"
            data = {
                "path": remote_path,
                "shareType": 3,  # 3 = public link
                "permissions": 1,  # 1 = read-only
            }
            headers = {"OCS-APIRequest": "true"}
            r = self._do_request("POST", url, data=data, headers=headers, timeout=10)

            if r.status_code == 200:
                root = ET.fromstring(r.text)
                url_elem = root.find(".//url")
                if url_elem is not None and url_elem.text:
                    return url_elem.text
        except Exception:
            pass
        return None

    # ── Public API ──

    def upload(self, local_path: Path, remote_folder: str = "brokus/") -> UploadResult:
        """Upload *local_path* to the remote folder.

        Auto-creates the folder tree if it doesn't exist and attempts to
        generate a public share link after a successful upload.
        """
        try:
            remote_folder = remote_folder.strip("/")
            if remote_folder:
                remote_folder += "/"

            if not self._ensure_folder(remote_folder):
                return UploadResult(
                    success=False,
                    provider=self.name,
                    remote_path="",
                    error="Could not create remote folder",
                )

            remote_path = f"{remote_folder}{local_path.name}"
            url = self._dav_url(remote_path)

            with open(local_path, "rb") as f:
                r = self._do_request("PUT", url, data=f, timeout=300)

            if r.status_code in (201, 204):
                share_link = self._create_share_link(remote_path)
                return UploadResult(
                    success=True,
                    provider=self.name,
                    remote_path=remote_path,
                    share_link=share_link,
                )
            return UploadResult(
                success=False,
                provider=self.name,
                remote_path=remote_path,
                error=f"HTTP {r.status_code}",
            )
        except requests.RequestException as e:
            return UploadResult(
                success=False, provider=self.name, remote_path="", error=str(e)
            )
        except OSError as e:
            return UploadResult(
                success=False, provider=self.name, remote_path="", error=str(e)
            )

    def test_connection(self) -> bool:
        """Verify connectivity by issuing a PROPFIND on the root DAV folder."""
        try:
            url = self._dav_url("")
            r = self._do_request("PROPFIND", url)
            return r.status_code == 207
        except requests.RequestException:
            return False
