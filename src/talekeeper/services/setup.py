"""First-run detection and setup checks."""

from pathlib import Path

from talekeeper.services import ollama


async def check_first_run() -> dict:
    """Check the state of all required services and return setup status."""
    checks = {
        "data_dir_exists": Path("data/db").exists(),
        "has_recordings": any(Path("data/audio").rglob("*.webm")) if Path("data/audio").exists() else False,
    }

    # Check Ollama
    try:
        health = await ollama.health_check()
        checks["ollama_running"] = health["status"] == "ok"
        checks["ollama_models"] = [m["name"] for m in health.get("models", [])] if health["status"] == "ok" else []
    except Exception:
        checks["ollama_running"] = False
        checks["ollama_models"] = []

    checks["is_first_run"] = not checks["data_dir_exists"] or not checks["has_recordings"]

    return checks
