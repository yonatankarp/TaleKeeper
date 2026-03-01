"""Centralized path resolution for TaleKeeper.

Internal paths (hardcoded, not user-configurable):
  - DB:     ``data/db/talekeeper.db``
  - Models: ``data/models/``

User data directory (configurable) — stores recordings, transcripts,
exports, and any other user-facing artifacts:
  1. DB setting ``data_dir`` (set via :func:`set_user_data_dir`)
  2. Environment variable ``TALEKEEPER_DATA_DIR``
  3. Default ``data``

Sub-directories under the user data root (``audio/``, etc.) are created
as needed.
"""

import os
from pathlib import Path

# --- Internal (hardcoded) paths -------------------------------------------

_INTERNAL_DIR = Path("data")


def get_db_dir() -> Path:
    return _INTERNAL_DIR / "db"


def get_db_path() -> Path:
    return get_db_dir() / "talekeeper.db"


def get_models_dir() -> Path:
    return _INTERNAL_DIR / "models"


# --- User data (configurable) paths --------------------------------------

_DEFAULT_USER_DATA_DIR = Path("data")

_user_data_dir_override: str | None = None


def set_user_data_dir(value: str | None) -> None:
    """Set the user data directory override (called during app startup)."""
    global _user_data_dir_override
    _user_data_dir_override = value


def get_user_data_dir() -> Path:
    """Return the resolved user data root directory."""
    if _user_data_dir_override:
        return Path(_user_data_dir_override)
    env = os.environ.get("TALEKEEPER_DATA_DIR")
    if env:
        return Path(env)
    return _DEFAULT_USER_DATA_DIR


def get_audio_dir() -> Path:
    return get_user_data_dir() / "audio"


def get_campaign_audio_dir(campaign_id: int) -> Path:
    return get_audio_dir() / str(campaign_id)
