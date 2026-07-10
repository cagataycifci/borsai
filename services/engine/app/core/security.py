"""Secret management.

Provider API keys are encrypted at rest with Fernet. The Fernet master key is
stored in the OS keychain via ``keyring`` (Windows Credential Manager, macOS
Keychain, Secret Service on Linux). If no keychain backend is available, we fall
back to a file in the app data dir with 0600 permissions and log a warning.

The plaintext secret never leaves the engine process and is never sent to the UI.
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SERVICE = "BorsaAI"
_KEY_NAME = "engine-master-key"


def _load_or_create_master_key() -> bytes:
    """Return the Fernet master key, creating and persisting one if absent."""
    try:
        import keyring

        existing = keyring.get_password(_SERVICE, _KEY_NAME)
        if existing:
            return existing.encode()
        key = Fernet.generate_key()
        keyring.set_password(_SERVICE, _KEY_NAME, key.decode())
        return key
    except Exception as exc:  # keyring backend missing/unavailable
        logger.warning("Keychain unavailable (%s); using file-based master key.", exc)
        return _file_master_key()


def _file_master_key() -> bytes:
    settings = get_settings()
    path: Path = settings.data_dir / ".master.key"
    if path.exists():
        return path.read_bytes()
    key = Fernet.generate_key()
    path.write_bytes(key)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


class SecretBox:
    """Encrypts/decrypts small secrets (API keys) with the master key."""

    def __init__(self) -> None:
        self._fernet = Fernet(_load_or_create_master_key())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str | None:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("Failed to decrypt a stored secret (invalid token).")
            return None


_box: SecretBox | None = None


def get_secret_box() -> SecretBox:
    global _box
    if _box is None:
        _box = SecretBox()
    return _box
