from __future__ import annotations

import base64
import json
import os
from typing import Dict

from cryptography.fernet import Fernet


# Generate encryption key from environment variable
# ENCRYPTION_KEY must be set in .env (32-byte base64 encoded)

def get_encryption_key() -> bytes:
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        new_key = Fernet.generate_key()
        print(f"Add to .env: ENCRYPTION_KEY={new_key.decode()}")
        raise ValueError("ENCRYPTION_KEY not set")
    return key.encode()


def encrypt_credentials(credentials: Dict) -> str:
    """Encrypt credentials dict to base64 string."""
    fernet = Fernet(get_encryption_key())
    plaintext = json.dumps(credentials)
    encrypted = fernet.encrypt(plaintext.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_credentials(encrypted: str) -> Dict:
    """Decrypt base64 string to credentials dict."""
    fernet = Fernet(get_encryption_key())
    encrypted_bytes = base64.b64decode(encrypted.encode())
    decrypted = fernet.decrypt(encrypted_bytes)
    return json.loads(decrypted.decode())
