"""AES-256-GCM authenticated encryption for data at rest.

Every secret Meshy Studio persists (the fal.ai API key, cached job
history) is sealed with AES-256-GCM before it ever touches the disk. The
master key is either derived from a user passphrase (``MESHY_MASTER_KEY``)
using scrypt, or generated once and stored in a ``0600`` key file.

Token layout (all binary, then base64url for text storage)::

    MAGIC(4) | VERSION(1) | NONCE(12) | CIPHERTEXT+TAG

The GCM tag authenticates both the ciphertext and the associated data, so
tampering is detected on decrypt.
"""
from __future__ import annotations

import base64
import hmac
import os
import stat
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"MSAE"  # Meshy Studio AES Envelope
VERSION = 1
NONCE_SIZE = 12  # 96-bit nonce recommended for GCM
KEY_SIZE = 32  # 256-bit key => AES-256
_SCRYPT_SALT_MARKER = b"meshy-studio.scrypt.v1"


class CryptoError(Exception):
    """Raised when encryption or decryption fails."""


def _derive_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=KEY_SIZE, n=2**15, r=8, p=1)
    return kdf.derive(passphrase.encode("utf-8"))


def load_or_create_master_key(key_path: Path, passphrase: str | None = None) -> bytes:
    """Return a 32-byte master key.

    If ``passphrase`` is provided it is stretched with scrypt (deterministic,
    so the same passphrase always unlocks existing data). Otherwise a random
    key is generated once and persisted to ``key_path`` with ``0600``
    permissions.
    """
    if passphrase:
        # Deterministic key from the operator-supplied passphrase.
        salt = _SCRYPT_SALT_MARKER.ljust(16, b"\0")[:16]
        return _derive_from_passphrase(passphrase, salt)

    key_path = Path(key_path)
    if key_path.exists():
        data = key_path.read_bytes()
        if len(data) != KEY_SIZE:
            raise CryptoError(
                f"Master key file {key_path} is corrupt (expected {KEY_SIZE} bytes)."
            )
        return data

    key = AESGCM.generate_key(bit_length=256)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    # Write atomically with restrictive permissions from the start.
    fd = os.open(
        key_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        stat.S_IRUSR | stat.S_IWUSR,  # 0600
    )
    try:
        os.write(fd, key)
    finally:
        os.close(fd)
    try:
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return key


class Cryptor:
    """AES-256-GCM sealer/unsealer bound to a single master key."""

    def __init__(self, key: bytes):
        if len(key) != KEY_SIZE:
            raise CryptoError("Master key must be exactly 32 bytes (AES-256).")
        self._aead = AESGCM(key)

    def encrypt(self, plaintext: bytes, associated_data: bytes | None = None) -> bytes:
        if not isinstance(plaintext, (bytes, bytearray)):
            raise CryptoError("plaintext must be bytes")
        nonce = os.urandom(NONCE_SIZE)
        ct = self._aead.encrypt(nonce, bytes(plaintext), associated_data)
        return MAGIC + bytes([VERSION]) + nonce + ct

    def decrypt(self, token: bytes, associated_data: bytes | None = None) -> bytes:
        if len(token) < len(MAGIC) + 1 + NONCE_SIZE + 16:
            raise CryptoError("Ciphertext token is too short / malformed.")
        if not hmac.compare_digest(token[: len(MAGIC)], MAGIC):
            raise CryptoError("Unrecognized ciphertext format (bad magic).")
        version = token[len(MAGIC)]
        if version != VERSION:
            raise CryptoError(f"Unsupported ciphertext version: {version}.")
        offset = len(MAGIC) + 1
        nonce = token[offset : offset + NONCE_SIZE]
        ct = token[offset + NONCE_SIZE :]
        try:
            return self._aead.decrypt(nonce, ct, associated_data)
        except InvalidTag as exc:  # pragma: no cover - defensive
            raise CryptoError(
                "Decryption failed: data was tampered with or the master key changed."
            ) from exc

    # --- text helpers (base64url) -------------------------------------
    def encrypt_str(self, text: str, associated_data: bytes | None = None) -> str:
        token = self.encrypt(text.encode("utf-8"), associated_data)
        return base64.urlsafe_b64encode(token).decode("ascii")

    def decrypt_str(self, token_b64: str, associated_data: bytes | None = None) -> str:
        try:
            token = base64.urlsafe_b64decode(token_b64.encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise CryptoError("Ciphertext is not valid base64.") from exc
        return self.decrypt(token, associated_data).decode("utf-8")
