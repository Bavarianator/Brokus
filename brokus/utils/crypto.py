"""Secure API key storage using machine-bound encryption.

Uses only Python stdlib: PBKDF2-HMAC key derivation + SHA-256 stream cipher + HMAC auth.
Keys are tied to the machine (machine-id + hostname) and cannot be decrypted if copied elsewhere.
"""

import os
import json
import hmac
import hashlib
import secrets
from pathlib import Path
from typing import Optional

from brokus.utils.logger import log


# ─────────────────────────────────────────────────────────────
# Key derivation constants
# ─────────────────────────────────────────────────────────────

_PEPPER = b"brokus-secret-store-v1"
_PBKDF2_ITERATIONS = 600_000
_KEY_LENGTH = 32  # 256 bits


def _get_machine_identity() -> bytes:
    """Get a stable machine-specific identifier.

    Tries /etc/machine-id (Linux) first, falls back to hostname + user.
    """
    try:
        mid = Path("/etc/machine-id").read_text().strip()
        return mid.encode()
    except Exception:
        pass

    try:
        return os.uname().nodename.encode()
    except Exception:
        return b"unknown-machine"


def _derive_key(salt: bytes) -> bytes:
    """Derive an encryption key from machine identity + pepper + salt."""
    machine_id = _get_machine_identity()
    return hashlib.pbkdf2_hmac(
        "sha256",
        _PEPPER + machine_id,
        salt,
        _PBKDF2_ITERATIONS,
        dklen=_KEY_LENGTH,
    )


# ─────────────────────────────────────────────────────────────
# Encryption / Decryption (SHA-256 stream cipher + HMAC)
# ─────────────────────────────────────────────────────────────


def _encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt plaintext using a SHA-256-based stream cipher with HMAC auth.

    Output format: iv (16) || ciphertext || auth_tag (32)
    """
    iv = secrets.token_bytes(16)

    # Generate keystream: for each 32-byte block, SHA-256(key || iv || counter)
    num_blocks = (len(plaintext) + 31) // 32
    keystream = b""
    for i in range(num_blocks):
        keystream += hashlib.sha256(
            key + iv + i.to_bytes(4, "big")
        ).digest()

    # XOR plaintext with keystream
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, keystream))

    # HMAC authentication tag over IV + ciphertext
    auth_tag = hmac.new(key, iv + ciphertext, "sha256").digest()

    return iv + ciphertext + auth_tag


def _decrypt(key: bytes, data: bytes) -> Optional[bytes]:
    """Decrypt data produced by _encrypt. Returns None if auth fails."""
    if len(data) < 16 + 32:  # iv + min auth_tag
        return None

    iv = data[:16]
    auth_tag = data[-32:]
    ciphertext = data[16:-32]

    # Verify HMAC before decrypting (authenticates IV + ciphertext)
    expected_tag = hmac.new(key, iv + ciphertext, "sha256").digest()
    if not hmac.compare_digest(auth_tag, expected_tag):
        log.warning("HMAC verification failed – data may be tampered or from another machine")
        return None

    # Regenerate keystream
    num_blocks = (len(ciphertext) + 31) // 32
    keystream = b""
    for i in range(num_blocks):
        keystream += hashlib.sha256(
            key + iv + i.to_bytes(4, "big")
        ).digest()

    return bytes(p ^ k for p, k in zip(ciphertext, keystream))


# ─────────────────────────────────────────────────────────────
# SecretStore – Persistent encrypted key-value store
# ─────────────────────────────────────────────────────────────


class SecretStore:
    """Machine-bound encrypted storage for API keys.

    Keys are encrypted using a key derived from the machine identity.
    If the secrets file is copied to another machine, decryption will fail
    (HMAC mismatch).

    Usage:
        store = SecretStore()
        store.set("OPENAI_API_KEY", "sk-abc123")
        store.save()

        # Later:
        store = SecretStore()
        store.load()
        key = store.get("OPENAI_API_KEY")  # "sk-abc123"
    """

    _instance: Optional["SecretStore"] = None

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            path = Path(xdg_config) / "brokus" / "secrets.enc"

        self._path = path
        self._secrets: dict[str, str] = {}
        self._loaded = False

    # ── Singleton access ──

    @classmethod
    def instance(cls) -> "SecretStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Public API ──

    def load(self) -> bool:
        """Load and decrypt secrets from disk. Returns False if file missing/corrupt."""
        if not self._path.exists():
            self._loaded = True
            return False

        try:
            raw = self._path.read_bytes()
            if len(raw) < 32:  # salt (16) + iv (16) minimum
                log.warning("Secrets file too short, ignoring")
                self._loaded = True
                return False

            salt = raw[:16]
            encrypted = raw[16:]

            key = _derive_key(salt)
            plaintext = _decrypt(key, encrypted)
            if plaintext is None:
                log.warning("Secrets file decryption failed (wrong machine or tampered)")
                self._loaded = True
                return False

            self._secrets = json.loads(plaintext.decode("utf-8"))
            self._loaded = True
            log.debug(f"Loaded {len(self._secrets)} encrypted secrets")
            return True
        except Exception as e:
            log.warning(f"Failed to load secrets: {e}")
            self._secrets = {}
            self._loaded = True
            return False

    def save(self) -> bool:
        """Encrypt and persist secrets to disk. Creates parent dirs as needed."""
        if not self._secrets:
            # Remove the file if there are no secrets
            if self._path.exists():
                self._path.unlink()
            return True

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)

            plaintext = json.dumps(self._secrets, ensure_ascii=False).encode("utf-8")
            salt = secrets.token_bytes(16)
            key = _derive_key(salt)
            encrypted = _encrypt(key, plaintext)

            # Write atomically: write to temp, then rename
            tmp_path = self._path.with_suffix(".tmp")
            tmp_path.write_bytes(salt + encrypted)
            tmp_path.chmod(0o600)
            tmp_path.rename(self._path)

            log.debug(f"Saved {len(self._secrets)} encrypted secrets")
            return True
        except Exception as e:
            log.error(f"Failed to save secrets: {e}")
            return False

    def get(self, env_var: str) -> Optional[str]:
        """Get a decrypted secret by environment variable name (e.g. 'OPENAI_API_KEY')."""
        if not self._loaded:
            self.load()
        return self._secrets.get(env_var)

    def set(self, env_var: str, value: str):
        """Store a secret for later encryption."""
        self._secrets[env_var] = value

    def delete(self, env_var: str):
        """Remove a stored secret."""
        self._secrets.pop(env_var, None)

    @property
    def is_loaded(self) -> bool:
        return self._loaded


def load_secrets() -> bool:
    """Convenience: load secrets from disk into the singleton store."""
    return SecretStore.instance().load()
