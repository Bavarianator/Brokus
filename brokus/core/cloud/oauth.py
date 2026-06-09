"""Keycloak OAuth2 / OIDC Authorization Code Flow for Nextcloud.

Provides a :class:`KeycloakAuth` helper that opens the user's browser,
completes the OAuth2 Authorization Code flow, and manages token refresh
automatically without any user interaction after the first login.

Typical flow::

    auth = KeycloakAuth(
        keycloak_url="https://auth.example.com",
        realm="nextcloud",
        client_id="brokus",
        client_secret="...",
    )
    token = auth.get_valid_token()   # ← browser opens on first call
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

# Where the OAuth token cache is stored (chmod 0o600)
_TOKEN_PATH = os.path.expanduser("~/.brokus/nextcloud_token.json")


# ── Local OAuth callback server ──


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server that catches the Keycloak redirect.

    The ``auth_code`` and ``state_received`` class attributes are set
    when the browser redirects back to ``http://localhost:<port>/callback``.
    """

    auth_code: str | None = None
    state_received: str | None = None

    def do_GET(self):  # noqa: N802
        params = parse_qs(urlparse(self.path).query)

        OAuthCallbackHandler.auth_code = params.get("code", [None])[0]
        OAuthCallbackHandler.state_received = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>brokus – Login successful</title>
<style>
  body { font-family: sans-serif; display: flex; justify-content: center;
         align-items: center; height: 100vh; margin: 0; background: #1a1a2e; color: #fff; }
  .box { text-align: center; padding: 2rem; border-radius: 12px;
         background: #16213e; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
  h1 { color: #4cc9f0; } p { color: #aaa; }
</style></head>
<body><div class="box">
  <h1>\u2705 Login successful!</h1>
  <p>You may close this window and return to <strong>brokus</strong>.</p>
</div></body></html>"""
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: N802
        pass  # Suppress HTTP server log output


# ── Keycloak OAuth2 client ──


class KeycloakAuth:
    """Keycloak OAuth2 / OIDC Authorization Code flow.

    Args:
        keycloak_url: Base URL of the Keycloak server (e.g. ``https://auth.example.com``).
        realm: Keycloak realm name (e.g. ``nextcloud``).
        client_id: OAuth2 client ID (e.g. ``brokus``).
        client_secret: OAuth2 client secret (confidential client).
        redirect_port: Local TCP port for the OAuth callback listener.
    """

    OIDC_CONFIG_PATH = "/realms/{realm}/.well-known/openid-configuration"

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        redirect_port: int = 8371,
    ):
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_port = redirect_port
        self.redirect_uri = f"http://localhost:{redirect_port}/callback"

        # OIDC endpoints (discovered dynamically for forward-compat)
        oidc_base = (
            f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect"
        )
        self.auth_endpoint = f"{oidc_base}/auth"
        self.token_endpoint = f"{oidc_base}/token"
        self.logout_endpoint = f"{oidc_base}/logout"
        self.userinfo_endpoint = f"{oidc_base}/userinfo"

    # ── Public API ──

    def get_valid_token(self) -> Optional[str]:
        """Return a valid access token.

        Tries, in order:
        1. Cached token (still valid).
        2. Refresh-token rotation (no browser).
        3. Fresh browser-based login.

        Returns ``None`` if all three methods fail.
        """
        token_data = self._load_token()

        if token_data:
            # Still valid? (30s safety margin)
            expires_at = token_data.get("expires_at", 0)
            if expires_at > time.time() + 30:
                token = token_data.get("access_token")
                if token:
                    return token

            # Try refresh
            refresh = token_data.get("refresh_token")
            if refresh:
                refreshed = self._refresh(refresh)
                if refreshed:
                    return refreshed

        # Fresh browser login
        return self._browser_login()

    def logout(self):
        """Clear the cached token (forces fresh login on next upload)."""
        if os.path.exists(_TOKEN_PATH):
            os.remove(_TOKEN_PATH)

    def revoke(self, token: Optional[str] = None) -> bool:
        """Revoke token on the Keycloak server (optional clean-up)."""
        if not token:
            token_data = self._load_token()
            if token_data:
                token = token_data.get("access_token")
        if token:
            try:
                revoke_url = (
                    f"{self.keycloak_url}/realms/{self.realm}"
                    f"/protocol/openid-connect/revoke"
                )
                requests.post(
                    revoke_url,
                    data={"token": token, "client_id": self.client_id},
                    timeout=10,
                )
            except Exception:
                pass
        self.logout()
        return True

    # ── Internal helpers ──

    def _browser_login(self) -> Optional[str]:
        """Open the browser for user login and wait for the callback."""
        from rich.console import Console

        console_ = Console()

        state = secrets.token_urlsafe(16)
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.state_received = None

        # Start local HTTP server (single request)
        server = HTTPServer(("127.0.0.1", self.redirect_port), OAuthCallbackHandler)
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()

        # Build auth URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
        }
        auth_url = f"{self.auth_endpoint}?{urlencode(params)}"

        console_.print()
        console_.print("[bold cyan]\U00002601 Nextcloud Login (Keycloak)[/bold cyan]")
        console_.print(
            "  [dim]\U0001f310 Browser opens for authentication...[/dim]"
        )
        console_.print()

        webbrowser.open(auth_url)

        # Wait for callback (max 120 seconds)
        timeout = 120.0
        waited = 0.0
        while OAuthCallbackHandler.auth_code is None and waited < timeout:
            time.sleep(0.5)
            waited += 0.5

        server.server_close()

        if not OAuthCallbackHandler.auth_code:
            console_.print("  [red]\u2716 Login timed out. Try again.[/red]")
            return None

        if OAuthCallbackHandler.state_received != state:
            console_.print(
                "  [red]\u2716 Security error: state mismatch.[/red]"
            )
            return None

        # Exchange auth code for tokens
        token = self._exchange(OAuthCallbackHandler.auth_code)
        if token:
            console_.print("  [green]\u2713 Login successful. Token cached.[/green]")
        return token

    def _exchange(self, code: str) -> Optional[str]:
        """Exchange an authorization code for an access token."""
        r = requests.post(
            self.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code": code,
            },
            timeout=30,
        )

        if r.status_code == 200:
            data = r.json()
            self._save_token(data)
            return data.get("access_token")

        print(f"  Token exchange failed: {r.text}")
        return None

    def _refresh(self, refresh_token: str) -> Optional[str]:
        """Refresh an access token without user interaction."""
        try:
            r = requests.post(
                self.token_endpoint,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                },
                timeout=30,
            )

            if r.status_code == 200:
                data = r.json()
                self._save_token(data)
                return data.get("access_token")
        except requests.RequestException:
            pass
        return None

    def _save_token(self, token_data: dict):
        """Persist the token to disk with restricted permissions."""
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 300)
        os.makedirs(os.path.dirname(_TOKEN_PATH), exist_ok=True)
        try:
            with open(_TOKEN_PATH, "w") as f:
                json.dump(token_data, f, indent=2)
            os.chmod(_TOKEN_PATH, 0o600)
        except OSError:
            pass

    def _load_token(self) -> Optional[dict]:
        """Read persisted token from disk."""
        if os.path.exists(_TOKEN_PATH):
            try:
                with open(_TOKEN_PATH) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return None
