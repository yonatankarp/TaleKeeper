"""Generic OpenAI-compatible LLM client."""

import logging
import os

import httpx
from openai import AsyncOpenAI, APIConnectionError, AuthenticationError, NotFoundError

from talekeeper.db import get_db

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.1:8b"

# Cache Ollama detection results per base_url
_ollama_cache: dict[str, bool] = {}


async def resolve_config() -> dict:
    """Resolve LLM configuration: settings table > env vars > defaults."""
    settings: dict[str, str] = {}
    try:
        async with get_db() as db:
            rows = await db.execute_fetchall(
                "SELECT key, value FROM settings WHERE key IN ('llm_base_url', 'llm_api_key', 'llm_model')"
            )
            for r in rows:
                if r["value"]:
                    settings[r["key"]] = r["value"]
    except Exception:
        pass

    # Base URL: settings > LLM_BASE_URL env > legacy OLLAMA_URL env > default
    base_url = settings.get("llm_base_url") or os.environ.get("LLM_BASE_URL")
    if not base_url:
        ollama_url = os.environ.get("OLLAMA_URL")
        if ollama_url:
            logger.warning(
                "OLLAMA_URL is deprecated — use LLM_BASE_URL instead. "
                "Appending /v1 to %s.",
                ollama_url,
            )
            base_url = ollama_url.rstrip("/") + "/v1"
    if not base_url:
        base_url = DEFAULT_BASE_URL

    api_key = settings.get("llm_api_key") or os.environ.get("LLM_API_KEY") or None
    model = settings.get("llm_model") or os.environ.get("LLM_MODEL") or DEFAULT_MODEL

    return {"base_url": base_url, "api_key": api_key, "model": model}


def _make_client(base_url: str, api_key: str | None) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key or "not-needed",
        timeout=10.0,
    )


async def health_check(base_url: str, api_key: str | None, model: str) -> dict:
    """Verify connectivity to the LLM provider with a minimal completion request."""
    try:
        client = _make_client(base_url, api_key)
        await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        return {"status": "ok"}
    except APIConnectionError:
        return {"status": "error", "message": f"Cannot reach LLM provider at {base_url}"}
    except AuthenticationError:
        return {"status": "error", "message": "Authentication failed — check your API key"}
    except NotFoundError:
        return {"status": "error", "message": f"Model '{model}' not found on the provider"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _is_ollama(base_url: str) -> bool:
    """Detect if the given base_url points to an Ollama server.

    Strips '/v1' suffix and probes '/api/tags'. Results are cached per base_url.
    """
    if base_url in _ollama_cache:
        return _ollama_cache[base_url]

    # Strip /v1 suffix to get the Ollama root
    ollama_root = base_url.rstrip("/")
    if ollama_root.endswith("/v1"):
        ollama_root = ollama_root[:-3]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ollama_root}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                is_ollama = isinstance(data.get("models"), list)
                _ollama_cache[base_url] = is_ollama
                return is_ollama
    except Exception:
        pass

    _ollama_cache[base_url] = False
    return False


async def generate(base_url: str, api_key: str | None, model: str, prompt: str, system: str = "") -> str:
    """Generate text using the OpenAI Chat Completions API."""
    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key or "not-needed",
        timeout=300.0,
    )
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict = {}
    if await _is_ollama(base_url):
        kwargs["extra_body"] = {"options": {"num_ctx": 32768}}

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,
    )
    return response.choices[0].message.content or ""


async def unload_model(base_url: str, api_key: str | None, model: str) -> None:
    """Unload a model from Ollama by sending keep_alive: 0. No-op for non-Ollama providers."""
    if not await _is_ollama(base_url):
        return

    ollama_root = base_url.rstrip("/")
    if ollama_root.endswith("/v1"):
        ollama_root = ollama_root[:-3]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{ollama_root}/api/generate",
                json={"model": model, "keep_alive": "0"},
            )
        logger.info("Sent keep_alive=0 to Ollama for model %s", model)
    except Exception as e:
        logger.warning("Failed to unload Ollama model %s: %s", model, e)
