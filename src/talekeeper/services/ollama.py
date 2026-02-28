"""Ollama client service for local LLM communication."""

import os

import httpx

OLLAMA_BASE = os.environ.get("OLLAMA_URL", "http://localhost:11434")


async def health_check() -> dict:
    """Check if Ollama is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            resp.raise_for_status()
            return {"status": "ok", "models": resp.json().get("models", [])}
    except httpx.ConnectError:
        return {"status": "error", "message": "Ollama is not running. Start it with: ollama serve"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def list_models() -> list[str]:
    """List available Ollama models."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{OLLAMA_BASE}/api/tags")
        resp.raise_for_status()
        models = resp.json().get("models", [])
    return [m["name"] for m in models]


async def check_model_available(model_name: str) -> bool:
    """Check if a specific model is available."""
    models = await list_models()
    return any(model_name in m for m in models)


async def generate(model: str, prompt: str, system: str = "") -> str:
    """Generate a completion from Ollama."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{OLLAMA_BASE}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": system,
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json()["response"]
