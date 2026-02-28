"""Settings API endpoints."""

import base64
import hashlib
import os

from fastapi import APIRouter
from pydantic import BaseModel

from talekeeper.db import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    settings: dict[str, str]


# Simple encryption for SMTP password at rest
_ENCRYPT_KEY = os.environ.get("TALEKEEPER_SECRET", "talekeeper-default-key-change-me")


def _encrypt(value: str) -> str:
    """Simple obfuscation for password storage at rest."""
    key_bytes = hashlib.sha256(_ENCRYPT_KEY.encode()).digest()
    value_bytes = value.encode()
    encrypted = bytes(a ^ b for a, b in zip(value_bytes, key_bytes * (len(value_bytes) // len(key_bytes) + 1)))
    return "ENC:" + base64.b64encode(encrypted).decode()


def _decrypt(value: str) -> str:
    """Decrypt an obfuscated password."""
    if not value.startswith("ENC:"):
        return value
    encrypted = base64.b64decode(value[4:])
    key_bytes = hashlib.sha256(_ENCRYPT_KEY.encode()).digest()
    decrypted = bytes(a ^ b for a, b in zip(encrypted, key_bytes * (len(encrypted) // len(key_bytes) + 1)))
    return decrypted.decode()


SENSITIVE_KEYS = {"smtp_password"}


@router.get("")
async def get_settings() -> dict[str, str]:
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT key, value FROM settings")

    result = {}
    for r in rows:
        key = r["key"]
        value = r["value"]
        if key in SENSITIVE_KEYS and value:
            # Don't expose actual password, just indicate it's set
            result[key] = "********"
        else:
            result[key] = value or ""
    return result


@router.put("")
async def update_settings(body: SettingsUpdate) -> dict:
    async with get_db() as db:
        for key, value in body.settings.items():
            # Encrypt sensitive values
            store_value = value
            if key in SENSITIVE_KEYS and value and value != "********":
                store_value = _encrypt(value)

            # Skip if trying to set password to the masked value
            if key in SENSITIVE_KEYS and value == "********":
                continue

            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
                (key, store_value, store_value),
            )
    return {"updated": True}
