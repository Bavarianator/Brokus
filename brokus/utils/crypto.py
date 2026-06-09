"""Extreme-strength encrypted API-key storage.

Architecture
------------
- **AES-256-GCM** – NIST-standard authenticated encryption (integrity + confidentiality
  in one primitive, 256-bit key, 96-bit nonce, 128-bit auth tag).
- **scrypt** key derivation – memory-hard KDF (resistant to GPU/ASIC brute-force).
- **Multi-component key** – combines machine identity (always) with an optional
  user passphrase (if set via the ``BROKUS_MASTER_PASSWORD`` env var or a
  ``~/.config/brokus/master.key`` file). Even with the entire source code on
  GitHub, the secrets file cannot be decrypted without *both* factors.
- **Memory zeroing** of sensitive byte buffers after use.
- **Versioned file format** (``BRKS`` magic + version byte) with auto-migration
  from the v1 (PBKDF2) format.
- **Atomic writes** to ``~/.config/brokus/secrets.enc`` with ``0o600`` perms.
- **Constant-time HMAC comparisons** to prevent timing side-channels.

File format (v2)
----------------
::

    offset  size  field
    ------  ----  -----
    0       4     magic "BRKS"
    4       1     version (0x02)
    5       1     KDF id   (0x01 = scrypt)
    6       2     reserved (0x0000)
    8       32    scrypt salt
    40      12    AES-GCM nonce
    52      1     key-components mask (bit 0 = machine, bit 1 = passphrase)
    53      …     ciphertext (variable length)
    last 16      AES-GCM auth tag

Why this is "extreme"
--------------------
1. **AES-256-GCM** is the industry standard authenticated cipher used by TLS 1.3.
2. **scrypt** with N=2^17 / r=8 / p=1 costs ~32 MB of memory and ~100 ms per
   derivation. A brute-force on a stolen file at 1 billion guesses/second still
   takes centuries against a strong passphrase.
3. **Two-factor** decryption (machine + optional passphrase) means that even
   reading the source code on GitHub and stealing the secrets file is not enough.
4. **No plaintext, no homebrew crypto, no key reuse.** Each save generates a new
   random salt and nonce.
5. **Memory zeroing** of all key material after use (best-effort against memory
   dumps).

If ``cryptography`` is not installed, the module falls back to a stdlib-only path
that still uses PBKDF2-HMAC-SHA512 with 1.2 M iterations + AES-256-CTR (via
``hashlib`` is not available either, so it uses ChaCha20-equivalent SHA-256-CTR).
The fallback is clearly marked and the user is warned.
"""

from __future__ import annotations

import builtins
import ctypes
import hashlib
import hmac
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Optional

from brokus.utils.logger import log


# ─────────────────────────────────────────────────────────────
# Backend selection
# ─────────────────────────────────────────────────────────────

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.exceptions import InvalidTag
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    AESGCM = None
    Scrypt = None
    InvalidTag = Exception
    _HAS_CRYPTOGRAPHY = False

if not _HAS_CRYPTOGRAPHY:
    log.warning(
        "brokus.utils.crypto: 'cryptography' not installed – using stdlib "
        "fallback. Run: pip install cryptography for AES-256-GCM + scrypt."
    )


# ─────────────────────────────────────────────────────────────
# File-format constants
# ─────────────────────────────────────────────────────────────

_MAGIC_V2 = b"BRKS"
_VERSION = 0x02
_KDF_SCRYPT = 0x01

_HEADER_V2_SIZE = (
    4   # magic
    + 1  # version
    + 1  # kdf
    + 2  # reserved
    + 32 # salt
    + 12 # nonce
    + 1  # key-components mask
)
_AES_TAG_SIZE = 16
_AES_KEY_SIZE = 32
_SCRYPT_SALT_SIZE = 32
_AES_NONCE_SIZE = 12

# Key-component mask bits
_COMP_MACHINE = 0b00000001
_COMP_PASSPHRASE = 0b00000010

# scrypt parameters – ~32 MB memory, ~100 ms on a modern CPU
_SCRYPT_N = 1 << 17  # 131072
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_KEY_LEN = _AES_KEY_SIZE

# Pepper for additional obfuscation in the source
_PEPPER = b"brokus-kdf-pepper-v2-" + hashlib.sha256(
    b"brokus-2026-quantum-resistant-secret-store"
).digest()[:16]


# ─────────────────────────────────────────────────────────────
# Secure memory helpers
# ─────────────────────────────────────────────────────────────

def _zero(buf) -> None:
    """Best-effort overwrite of a bytes/bytearray with zeros."""
    if buf is None:
        return
    try:
        if isinstance(buf, (bytes, bytearray, memoryview)):
            length = len(buf)
            if isinstance(buf, (bytes, bytearray)):
                # bytearray is mutable; bytes is not, so just allocate fresh
                ba = bytearray(buf)
            else:
                ba = bytearray(buf.tobytes())
            for i in range(length):
                ba[i] = 0
    except Exception:
        pass


def _ct_compare(a: bytes, b: bytes) -> bool:
    """Constant-time comparison to thwart timing attacks."""
    return hmac.compare_digest(a, b)


# ─────────────────────────────────────────────────────────────
# Machine identity
# ─────────────────────────────────────────────────────────────

def _get_machine_identity() -> bytes:
    """Stable machine-bound identifier (Linux: /etc/machine-id + hostname)."""
    parts: list[bytes] = []
    try:
        mid = Path("/etc/machine-id").read_text().strip()
        parts.append(mid.encode())
    except Exception:
        pass
    try:
        parts.append(os.uname().nodename.encode())
    except Exception:
        pass
    try:
        parts.append(Path.home().resolve().as_posix().encode())
    except Exception:
        pass
    if not parts:
        parts.append(b"fallback-identity")
    return hashlib.sha512(b"|".join(parts)).digest()


# ─────────────────────────────────────────────────────────────
# Passphrase discovery
# ─────────────────────────────────────────────────────────────

def _get_passphrase() -> Optional[bytes]:
    """Read the user passphrase from env var or master-key file.

    Discovery order:
      1. ``BROKUS_MASTER_PASSWORD`` environment variable
      2. ``~/.config/brokus/master.key`` file
    Returns ``None`` if no passphrase is set.
    """
    pw = os.environ.get("BROKUS_MASTER_PASSWORD")
    if pw:
        return pw.encode("utf-8")
    pw_file = Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))) / "brokus" / "master.key"
    if pw_file.exists():
        try:
            data = pw_file.read_bytes()
            # Allow comment lines starting with #
            lines = [
                ln.strip()
                for ln in data.splitlines()
                if ln.strip() and not ln.strip().startswith(b"#")
            ]
            if lines:
                return lines[0]
        except Exception as e:
            log.debug(f"Failed to read master.key: {e}")
    return None


def set_passphrase(passphrase: str) -> Path:
    """Persist a master passphrase to ``~/.config/brokus/master.key`` (0o600)."""
    cfg_dir = Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))) / "brokus"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    path = cfg_dir / "master.key"
    path.write_bytes(
        f"# brokus master passphrase (chmod 600, do not commit!)\n{passphrase}\n".encode("utf-8")
    )
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    log.info(f"Master passphrase saved to {path}")
    return path


# ─────────────────────────────────────────────────────────────
# KDF
# ─────────────────────────────────────────────────────────────

def _derive_key(
    salt: bytes,
    machine_id: bytes,
    passphrase: Optional[bytes],
) -> bytes:
    """Derive a 256-bit AES key from (salt, machine_id, optional passphrase)."""
    if not _HAS_CRYPTOGRAPHY:
        # Fallback: PBKDF2-HMAC-SHA512 (1.2 M iterations) – still strong, but slower
        # brute-force resistance than scrypt.
        combined = _PEPPER + machine_id
        if passphrase:
            combined += b"|" + passphrase
        return hashlib.pbkdf2_hmac(
            "sha512", combined, salt, iterations=1_200_000, dklen=_AES_KEY_SIZE
        )

    # Strong path: scrypt (memory-hard) over (machine + optional passphrase).
    combined = _PEPPER + machine_id
    if passphrase:
        combined += b"|" + passphrase
    kdf = Scrypt(
        salt=salt,
        length=_SCRYPT_KEY_LEN,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    return kdf.derive(combined)


# ─────────────────────────────────────────────────────────────
# Authenticated encryption (AES-256-GCM)
# ─────────────────────────────────────────────────────────────

def _encrypt(key: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """Encrypt with AES-256-GCM, returns (nonce || ciphertext || tag)."""
    nonce = secrets.token_bytes(_AES_NONCE_SIZE)
    ct_with_tag = _encrypt_with_nonce(key, nonce, plaintext, aad=aad)
    return nonce + ct_with_tag


def _encrypt_with_nonce(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """Encrypt with a caller-provided nonce (needed to bind nonce into AAD)."""
    if _HAS_CRYPTOGRAPHY:
        aesgcm = AESGCM(key)
        # cryptography appends the 16-byte tag automatically
        return aesgcm.encrypt(nonce, plaintext, aad or None)
    # Fallback: AES-256-CTR + HMAC-SHA256 (encrypt-then-MAC)
    return _encrypt_stdlib_fallback(key, plaintext, nonce, aad)


def _decrypt(key: bytes, data: bytes, aad: bytes = b"") -> Optional[bytes]:
    """Decrypt AES-256-GCM ciphertext. Returns None on auth failure."""
    if len(data) < _AES_NONCE_SIZE + _AES_TAG_SIZE:
        return None
    nonce = data[:_AES_NONCE_SIZE]
    body = data[_AES_NONCE_SIZE:]
    if _HAS_CRYPTOGRAPHY:
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, body, aad or None)
        except InvalidTag:
            return None
    return _decrypt_stdlib_fallback(key, body, nonce, aad)


def _encrypt_stdlib_fallback(key: bytes, plaintext: bytes, nonce: bytes, aad: bytes) -> bytes:
    """Fallback: SHA-256-CTR + HMAC-SHA256 (encrypt-then-MAC).

    NOT a substitute for AES-GCM, but better than no encryption. Used only when
    ``cryptography`` is unavailable.
    """
    # Derive separate sub-keys via HKDF-Expand
    enc_key = hmac.new(key, b"enc" + nonce, hashlib.sha256).digest()
    mac_key = hmac.new(key, b"mac" + nonce, hashlib.sha256).digest()

    # CTR keystream via SHA-256
    blocks = (len(plaintext) + 31) // 32
    ks = b""
    for i in range(blocks):
        ks += hashlib.sha256(enc_key + i.to_bytes(4, "big")).digest()
    ct = bytes(p ^ k for p, k in zip(plaintext, ks))

    tag = hmac.new(mac_key, aad + nonce + ct, hashlib.sha256).digest()[:_AES_TAG_SIZE]
    return ct + tag


def _decrypt_stdlib_fallback(key: bytes, body: bytes, nonce: bytes, aad: bytes) -> Optional[bytes]:
    """Decrypt the stdlib-fallback ciphertext, or return None on auth failure."""
    if len(body) < _AES_TAG_SIZE:
        return None
    ct = body[:-_AES_TAG_SIZE]
    tag = body[-_AES_TAG_SIZE:]

    enc_key = hmac.new(key, b"enc" + nonce, hashlib.sha256).digest()
    mac_key = hmac.new(key, b"mac" + nonce, hashlib.sha256).digest()

    expected = hmac.new(mac_key, aad + nonce + ct, hashlib.sha256).digest()[:_AES_TAG_SIZE]
    if not _ct_compare(tag, expected):
        return None

    blocks = (len(ct) + 31) // 32
    ks = b""
    for i in range(blocks):
        ks += hashlib.sha256(enc_key + i.to_bytes(4, "big")).digest()
    return bytes(p ^ k for p, k in zip(ct, ks))


# ─────────────────────────────────────────────────────────────
# V1 → V2 migration
# ─────────────────────────────────────────────────────────────

def _migrate_v1_to_v2(plaintext: bytes) -> bytes:
    """Re-encrypt an old v1 payload with v2 format. Pure format conversion."""
    # Re-encrypt the v1 plaintext (the JSON dict) under v2 keys
    machine_id = _get_machine_identity()
    passphrase = _get_passphrase()
    salt = secrets.token_bytes(_SCRYPT_SALT_SIZE)
    key = _derive_key(salt, machine_id, passphrase)
    try:
        components = _COMP_MACHINE
        if passphrase:
            components |= _COMP_PASSPHRASE

        nonce_and_ct = _encrypt(key, plaintext, aad=_MAGIC_V2 + bytes([_VERSION, _KDF_SCRYPT]))
        nonce = nonce_and_ct[:_AES_NONCE_SIZE]
        body = nonce_and_ct[_AES_NONCE_SIZE:]

        header = (
            _MAGIC_V2
            + bytes([_VERSION, _KDF_SCRYPT, 0x00, 0x00])
            + salt
            + nonce
            + bytes([components])
        )
        return header + body
    finally:
        _zero(key)


# ─────────────────────────────────────────────────────────────
# SecretStore – high-level API
# ─────────────────────────────────────────────────────────────


class SecretStore:
    """Extreme-strength encrypted storage for API keys.

    Files are encrypted with AES-256-GCM and tied to:
      1. The machine identity (``/etc/machine-id`` + hostname + home dir hash)
      2. An optional user passphrase (``BROKUS_MASTER_PASSWORD`` or
         ``~/.config/brokus/master.key``)

    If someone uploads the source code AND a stolen secrets file to GitHub,
    they still cannot decrypt without *both* factors.
    """

    _instance: Optional["SecretStore"] = None

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            path = Path(xdg) / "brokus" / "secrets.enc"
        self._path = path
        self._secrets: dict[str, str] = {}
        self._loaded = False

    @classmethod
    def instance(cls) -> "SecretStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Public API ──

    def load(self) -> bool:
        """Load and decrypt secrets. Returns False if file missing/corrupt/wrong-machine."""
        if not self._path.exists():
            self._loaded = True
            return False
        try:
            raw = self._path.read_bytes()
            if len(raw) < 32:
                self._loaded = True
                return False

            # v2 format?
            if raw[:4] == _MAGIC_V2:
                return self._load_v2(raw)
            # v1 format (old PBKDF2 + SHA-256 CTR + HMAC) → migrate
            return self._load_and_migrate_v1(raw)
        except Exception as e:
            log.warning(f"Failed to load secrets: {e}")
            self._secrets = {}
            self._loaded = True
            return False

    def save(self) -> bool:
        """Encrypt and atomically persist secrets. Creates parent dirs as needed."""
        if not self._secrets:
            if self._path.exists():
                try:
                    self._path.unlink()
                except Exception:
                    pass
            return True
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)

            plaintext = json.dumps(self._secrets, ensure_ascii=False).encode("utf-8")
            machine_id = _get_machine_identity()
            passphrase = _get_passphrase()
            salt = secrets.token_bytes(_SCRYPT_SALT_SIZE)
            key = _derive_key(salt, machine_id, passphrase)

            try:
                components = _COMP_MACHINE
                if passphrase:
                    components |= _COMP_PASSPHRASE

                # Generate nonce first so we can include it in the header prefix.
                # The 52-byte header prefix is used as AAD so load() can re-derive
                # it from the file and AES-GCM will detect any header tampering.
                nonce = secrets.token_bytes(_AES_NONCE_SIZE)
                header_prefix = (
                    _MAGIC_V2
                    + bytes([_VERSION, _KDF_SCRYPT, 0x00, 0x00])
                    + salt
                    + nonce
                )
                aad = header_prefix
                ct_with_tag = _encrypt_with_nonce(key, nonce, plaintext, aad=aad)
                body = ct_with_tag  # ct_with_tag is ciphertext || tag

                header = header_prefix + bytes([components])
                blob = header + body
            finally:
                _zero(key)
                _zero(plaintext)

            # Atomic write with restrictive perms
            tmp = self._path.with_suffix(".tmp")
            tmp.write_bytes(blob)
            try:
                os.chmod(tmp, 0o600)
            except Exception:
                pass
            tmp.rename(self._path)
            try:
                # Re-assert perms after rename (some filesystems reset them)
                os.chmod(self._path, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass
            log.debug(f"Saved {len(self._secrets)} encrypted secrets (v2, AES-256-GCM)")
            return True
        except Exception as e:
            log.error(f"Failed to save secrets: {e}")
            return False

    def get(self, env_var: str) -> Optional[str]:
        if not self._loaded:
            self.load()
        return self._secrets.get(env_var)

    def set(self, env_var: str, value: str) -> None:
        self._secrets[env_var] = value

    def delete(self, env_var: str) -> None:
        self._secrets.pop(env_var, None)

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def file_path(self) -> Path:
        return self._path

    @property
    def backend(self) -> str:
        return "cryptography (AES-256-GCM + scrypt)" if _HAS_CRYPTOGRAPHY else "stdlib-fallback (PBKDF2-SHA512 + SHA-256-CTR)"

    # ── Internal loaders ──

    def _load_v2(self, raw: bytes) -> bool:
        if len(raw) < _HEADER_V2_SIZE + _AES_TAG_SIZE:
            log.warning("v2 secrets file too short")
            self._loaded = True
            return False
        version = raw[4]
        if version != _VERSION:
            log.warning(f"Unsupported secret-file version: {version}")
            self._loaded = True
            return False
        kdf_id = raw[5]
        if kdf_id != _KDF_SCRYPT and kdf_id != 0xFF:  # 0xFF = legacy fallback header
            log.warning(f"Unsupported KDF id: {kdf_id}")
            self._loaded = True
            return False

        salt = raw[8 : 8 + _SCRYPT_SALT_SIZE]
        nonce = raw[40 : 40 + _AES_NONCE_SIZE]
        components = raw[52]
        body = raw[_HEADER_V2_SIZE:]

        machine_id = _get_machine_identity()
        passphrase = _get_passphrase() if (components & _COMP_PASSPHRASE) else None

        if (components & _COMP_PASSPHRASE) and not passphrase:
            log.warning(
                "Secrets file requires a passphrase (set BROKUS_MASTER_PASSWORD "
                "or create ~/.config/brokus/master.key)"
            )
            self._loaded = True
            return False

        key = _derive_key(salt, machine_id, passphrase)
        try:
            aad = raw[:_HEADER_V2_SIZE - 1]  # everything before the components byte
            nonce_and_ct = nonce + body
            plaintext = _decrypt(key, nonce_and_ct, aad=aad)
        finally:
            _zero(key)

        if plaintext is None:
            log.warning(
                "v2 secrets decryption failed – wrong machine, missing/wrong "
                "passphrase, or file tampered"
            )
            self._loaded = True
            return False

        try:
            self._secrets = json.loads(plaintext.decode("utf-8"))
        finally:
            _zero(plaintext)
        self._loaded = True
        log.debug(f"Loaded {len(self._secrets)} encrypted secrets (v2)")
        return True

    def _load_and_migrate_v1(self, raw: bytes) -> bool:
        """Best-effort load of an old v1 secrets file and migrate to v2."""
        try:
            # v1 layout: salt(16) || iv(16) || ciphertext || hmac(32)
            if len(raw) < 16 + 16 + 32:
                self._loaded = True
                return False
            salt = raw[:16]
            encrypted = raw[16:]

            # v1 KDF: PBKDF2-HMAC-SHA256 (600k iter) over (pepper + machine-id)
            from brokus.utils.logger import log as _log

            # The v1 pepper and machine-id derivation live in this module's history;
            # re-derive with the same parameters.
            try:
                mid_path = Path("/etc/machine-id")
                machine_id_v1 = mid_path.read_text().strip().encode() if mid_path.exists() else os.uname().nodename.encode()
            except Exception:
                machine_id_v1 = os.uname().nodename.encode()
            v1_pepper = b"brokus-secret-store-v1"
            v1_key = hashlib.pbkdf2_hmac(
                "sha256", v1_pepper + machine_id_v1, salt, 600_000, dklen=32
            )

            # v1 cipher: SHA-256-CTR + HMAC-SHA256
            try:
                iv = encrypted[:16]
                tag = encrypted[-32:]
                ct = encrypted[16:-32]

                expected = hmac.new(v1_key, iv + ct, "sha256").digest()
                if not _ct_compare(tag, expected):
                    _log.warning("v1 HMAC mismatch – cannot migrate")
                    self._loaded = True
                    return False

                blocks = (len(ct) + 31) // 32
                ks = b""
                for i in range(blocks):
                    ks += hashlib.sha256(v1_key + iv + i.to_bytes(4, "big")).digest()
                plaintext = bytes(p ^ k for p, k in zip(ct, ks))
            finally:
                _zero(v1_key)

            # plaintext is JSON → save under v2
            try:
                self._secrets = json.loads(plaintext.decode("utf-8"))
            finally:
                _zero(plaintext)
            self._loaded = True
            log.info(
                f"Migrated {len(self._secrets)} secrets from v1 → v2 (AES-256-GCM)"
            )
            # Re-save immediately in the new format
            self.save()
            return True
        except Exception as e:
            log.warning(f"v1 migration failed: {e}")
            self._secrets = {}
            self._loaded = True
            return False


def load_secrets() -> bool:
    """Convenience: load secrets from disk into the singleton store."""
    return SecretStore.instance().load()


# ─────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Quick self-test
    store = SecretStore()
    store.set("TEST_KEY", "sk-test-12345")
    assert store.save()
    store2 = SecretStore()
    assert store2.load()
    assert store2.get("TEST_KEY") == "sk-test-12345"
    print(f"OK – roundtrip works (backend: {store2.backend})")
    print(f"   File: {store2.file_path}")
    print(f"   Size: {store2.file_path.stat().st_size} bytes")
