"""First-run detection and setup checks."""

from pathlib import Path

from talekeeper.services import llm_client


async def check_first_run() -> dict:
    """Check the state of all required services and return setup status."""
    checks = {
        "data_dir_exists": Path("data/db").exists(),
        "has_recordings": any(Path("data/audio").rglob("*.webm")) if Path("data/audio").exists() else False,
    }

    # Check LLM provider
    try:
        config = await llm_client.resolve_config()
        health = await llm_client.health_check(config["base_url"], config["api_key"], config["model"])
        checks["llm_connected"] = health["status"] == "ok"
    except Exception:
        checks["llm_connected"] = False

    checks["is_first_run"] = not checks["data_dir_exists"] or not checks["has_recordings"]

    return checks
