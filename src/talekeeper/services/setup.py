"""First-run detection and setup checks."""

from talekeeper.db import get_db
from talekeeper.paths import get_user_data_dir, get_db_dir
from talekeeper.services import llm_client, image_client


async def check_first_run() -> dict:
    """Check the state of all required services and return setup status."""
    user_data_dir = get_user_data_dir()
    checks = {
        "data_dir_exists": get_db_dir().exists(),
        "has_recordings": any(user_data_dir.rglob("*.webm")) if user_data_dir.exists() else False,
        "data_dir": str(user_data_dir),
    }

    # Check LLM provider
    try:
        config = await llm_client.resolve_config()
        health = await llm_client.health_check(config["base_url"], config["api_key"], config["model"])
        checks["llm_connected"] = health["status"] == "ok"
    except Exception:
        checks["llm_connected"] = False

    # Check image provider
    try:
        img_config = await image_client.resolve_config()
        img_health = await image_client.health_check(img_config["base_url"], img_config["api_key"], img_config["model"])
        checks["image_connected"] = img_health["status"] == "ok"
    except Exception:
        checks["image_connected"] = False

    # Only show wizard automatically if user has never dismissed it
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT value FROM settings WHERE key = 'setup_dismissed'"
        )
        dismissed = rows[0]["value"] == "true" if rows else False

    checks["is_first_run"] = not dismissed

    return checks
