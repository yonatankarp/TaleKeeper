"""Generic OpenAI-compatible LLM client."""

import logging
import os

from openai import AsyncOpenAI, APIConnectionError, AuthenticationError, NotFoundError

from talekeeper.db import get_db

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.1:8b"


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

    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content or ""
