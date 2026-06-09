"""Google Drive uploader via the REST API (no google-api-python-client needed).

Uses a simple OAuth 2.0 flow with a local HTTP callback server (same pattern
as the Nextcloud Login Flow v2). On first use the user enters their Google
Client ID + Secret, then authenticates in the browser. The token is cached to
``~/.brokus/gdrive_token.json`` for subsequent runs.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from .base import CloudUploader, UploadResult

# ── Constants ──

SCOPES = "https://www.googleapis.com/auth/drive.file"
REDIRECT_URI = "http://localhost:8372/callback"
TOKEN_PATH = os.path.expanduser("~/.brokus/gdrive_token.json")
API_BASE = "https://www.googleapis.com"


# ── OAuth callback handler ──


class _GDriveCallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server that catches the Google OAuth redirect."""

    auth_code: str | None = None
    state_received: str | None = None

    def do_GET(self):  # noqa: N802
        params = parse_qs(urlparse(self.path).query)

        _GDriveCallbackHandler.auth_code = params.get("code", [None])[0]
        _GDriveCallbackHandler.state_received = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>brokus – Google Drive verbunden</title>
<style>
  body { font-family: sans-serif; display: flex; justify-content: center;
         align-items: center; height: 100vh; margin: 0; background: #1a1a2e; color: #fff; }
  .box { text-align: center; padding: 2rem; border-radius: 12px;
         background: #16213e; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
  h1 { color: #4cc9f0; } p { color: #aaa; }
</style></head>
<body><div class="box">
  <h1>\u2705 Google Drive verbunden!</h1>
  <p>You may close this window and return to <strong>brokus</strong>.</p>
</div></body></html>"""
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: N802
        pass


# ── Google Drive Uploader ──


class GoogleDriveUploader(CloudUploader):
    """Upload files to Google Drive via the REST API.

    Uses a simple OAuth 2.0 flow with Client ID + Secret (no
    ``credentials.json`` needed). The token is cached automatically.

    Args:
        client_id: Google OAuth2 client ID.
        client_secret: Google OAuth2 client secret.
        token_file: Path to persist the OAuth token.
    """

    name = "Google Drive"

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        token_file: str = TOKEN_PATH,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = token_file
        self._token_data: Optional[dict] = None

        # Try to load cached token
        self._load_token()

    # ── Auth ──

    @property
    def has_credentials(self) -> bool:
        """Return ``True`` if we have a usable OAuth token."""
        return self._token_data is not None

    def is_configured(self) -> bool:
        """Return ``True`` if client ID and secret are set."""
        return bool(self.client_id) and bool(self.client_secret)

    def login(self, client_id: str, client_secret: str) -> bool:
        """Run the OAuth 2.0 flow: open browser, catch callback, get token.

        Args:
            client_id: Google OAuth2 client ID.
            client_secret: Google OAuth2 client secret.

        Returns:
            ``True`` on success.
        """
        from rich.console import Console

        console_ = Console()

        self.client_id = client_id
        self.client_secret = client_secret

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(16)

        # Reset callback holder
        _GDriveCallbackHandler.auth_code = None
        _GDriveCallbackHandler.state_received = None

        # Start local HTTP server
        server = HTTPServer(
            ("127.0.0.1", 8372), _GDriveCallbackHandler
        )
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        # Build auth URL
        params = {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "state": state,
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        console_.print()
        console_.print("  [cyan]\U0001f310 Browser opens for Google authentication...[/cyan]")
        console_.print("  [dim]Waiting for confirmation in browser (120s timeout)...[/dim]")
        console_.print()

        webbrowser.open(auth_url)

        # Wait for callback
        timeout = 120.0
        waited = 0.0
        while _GDriveCallbackHandler.auth_code is None and waited < timeout:
            time.sleep(0.5)
            waited += 0.5

        server.server_close()

        if not _GDriveCallbackHandler.auth_code:
            console_.print("  [red]\u2716 Login timed out. Try again.[/red]")
            return False

        if _GDriveCallbackHandler.state_received != state:
            console_.print("  [red]\u2716 Security error: state mismatch.[/red]")
            return False

        # Exchange code for tokens
        r = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": _GDriveCallbackHandler.auth_code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )

        if r.status_code == 200:
            self._token_data = r.json()
            self._save_token()
            console_.print("  [green]\u2713 Google Drive authenticated! Token cached.[/green]")
            return True

        console_.print(f"  [red]\u2716 Token exchange failed: {r.text}[/red]")
        return False

    def get_access_token(self) -> Optional[str]:
        """Return a valid access token, refreshing if necessary."""
        if not self._token_data:
            return None

        access = self._token_data.get("access_token")
        expires_at = self._token_data.get("expires_at", 0)

        # Still valid? (60s safety margin)
        if access and expires_at > time.time() + 60:
            return access

        # Try refresh
        refresh = self._token_data.get("refresh_token")
        if refresh:
            try:
                r = requests.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "refresh_token": refresh,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "refresh_token",
                    },
                    timeout=30,
                )
                if r.status_code == 200:
                    new_data = r.json()
                    # Preserve refresh_token (Google only sends it on first auth)
                    if "refresh_token" not in new_data:
                        new_data["refresh_token"] = refresh
                    new_data["expires_at"] = time.time() + new_data.get(
                        "expires_in", 3600
                    )
                    self._token_data = new_data
                    self._save_token()
                    return new_data.get("access_token")
            except requests.RequestException:
                pass

        return None

    def _headers(self) -> dict:
        """Return authorization headers for API calls."""
        token = self.get_access_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _api_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Issue an authenticated request to the Google API."""
        kwargs.setdefault("timeout", 30)
        headers = kwargs.pop("headers", {})
        headers.update(self._headers())
        kwargs["headers"] = headers
        return requests.request(method, url, **kwargs)

    # ── Token persistence ──

    def _save_token(self):
        """Persist the token to disk with restricted permissions."""
        if not self._token_data:
            return
        # Store expiry time
        if "expires_at" not in self._token_data and "expires_in" in self._token_data:
            self._token_data["expires_at"] = time.time() + self._token_data["expires_in"]
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        try:
            with open(self.token_file, "w") as f:
                json.dump(self._token_data, f, indent=2)
            os.chmod(self.token_file, 0o600)
        except OSError:
            pass

    def _load_token(self):
        """Restore token from disk."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file) as f:
                    self._token_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

    # ── Drive API helpers ──

    def _get_or_create_folder(self, folder_name: str) -> Optional[str]:
        """Return the Drive folder ID, creating it if missing."""
        # Search for existing folder
        query = (
            f"name='{folder_name}' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        )
        r = self._api_request(
            "GET",
            f"{API_BASE}/drive/v3/files",
            params={"q": query, "fields": "files(id)"},
        )
        if r.status_code == 200:
            files = r.json().get("files", [])
            if files:
                return files[0]["id"]

        # Create folder
        r = self._api_request(
            "POST",
            f"{API_BASE}/drive/v3/files",
            json={
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            },
            params={"fields": "id"},
        )
        if r.status_code == 200:
            return r.json().get("id")

        return None

    # ── Public API ──

    def upload(self, local_path: Path, remote_folder: str = "brokus") -> UploadResult:
        """Upload *local_path* into a Google Drive folder.

        Args:
            local_path: The local file to upload.
            remote_folder: Folder name under ``My Drive``.

        Returns:
            An :class:`UploadResult`.
        """
        try:
            # Ensure we have a valid token
            token = self.get_access_token()
            if not token:
                return UploadResult(
                    success=False,
                    provider=self.name,
                    remote_path="",
                    error="Not authenticated. Run setup first.",
                )

            folder_id = self._get_or_create_folder(remote_folder.strip("/"))
            if not folder_id:
                return UploadResult(
                    success=False,
                    provider=self.name,
                    remote_path="",
                    error="Could not create or find Drive folder",
                )

            # Upload file via multipart POST to the Drive API
            # We use the simpler upload URL without media upload endpoint
            metadata = json.dumps({
                "name": local_path.name,
                "parents": [folder_id],
            })

            with open(local_path, "rb") as f:
                r = requests.post(
                    f"{API_BASE}/upload/drive/v3/files",
                    params={"uploadType": "multipart", "fields": "id, webViewLink"},
                    headers=self._headers(),
                    data={
                        "metadata": ("metadata.json", metadata, "application/json"),
                        "file": (local_path.name, f, "application/octet-stream"),
                    },
                    timeout=300,
                )

            if r.status_code == 200:
                result = r.json()
                return UploadResult(
                    success=True,
                    provider=self.name,
                    remote_path=f"{remote_folder}/{local_path.name}",
                    share_link=result.get("webViewLink"),
                )

            return UploadResult(
                success=False,
                provider=self.name,
                remote_path="",
                error=f"HTTP {r.status_code}: {r.text[:200]}",
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
        """Verify the Drive API is reachable and the token is valid."""
        try:
            r = self._api_request(
                "GET", f"{API_BASE}/drive/v3/files", params={"pageSize": 1}
            )
            return r.status_code == 200
        except requests.RequestException:
            return False
