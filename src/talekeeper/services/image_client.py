"""OpenAI-compatible image generation client."""

import base64
import logging
import os

from openai import AsyncOpenAI, APIConnectionError, AuthenticationError, NotFoundError

from talekeeper.db import get_db

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "x/flux2-klein:9b"


async def resolve_config() -> dict:
    """Resolve image provider configuration: settings table > env vars > defaults."""
    settings: dict[str, str] = {}
    try:
        async with get_db() as db:
            rows = await db.execute_fetchall(
                "SELECT key, value FROM settings WHERE key IN ('image_base_url', 'image_api_key', 'image_model')"
            )
            for r in rows:
                if r["value"]:
                    settings[r["key"]] = r["value"]
    except Exception:
        pass

    base_url = settings.get("image_base_url") or os.environ.get("IMAGE_BASE_URL") or DEFAULT_BASE_URL
    api_key = settings.get("image_api_key") or os.environ.get("IMAGE_API_KEY") or None
    model = settings.get("image_model") or os.environ.get("IMAGE_MODEL") or DEFAULT_MODEL

    return {"base_url": base_url, "api_key": api_key, "model": model}


def _make_client(base_url: str, api_key: str | None) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key or "not-needed",
        timeout=300.0,
    )


async def health_check(base_url: str, api_key: str | None, model: str) -> dict:
    """Verify connectivity to the image generation provider."""
    try:
        client = _make_client(base_url, api_key)
        await client.models.list()
        return {"status": "ok"}
    except APIConnectionError:
        return {"status": "error", "message": f"Cannot reach image provider at {base_url}"}
    except AuthenticationError:
        return {"status": "error", "message": "Authentication failed — check your API key"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def generate_image(base_url: str, api_key: str | None, model: str, prompt: str) -> bytes:
    """Generate an image and return the raw PNG bytes."""
    client = _make_client(base_url, api_key)
    response = await client.images.generate(
        model=model,
        prompt=prompt,
        n=1,
        response_format="b64_json",
    )
    b64_data = response.data[0].b64_json
    return base64.b64decode(b64_data)
