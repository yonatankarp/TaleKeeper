"""Memory management and cleanup between ML pipeline phases."""

import gc
import logging

from talekeeper.services import transcription, diarization, image_generation, llm_client

logger = logging.getLogger(__name__)


def cleanup_transcription() -> None:
    """Unload transcription model and clear MLX cache."""
    logger.info("Cleaning up transcription resources")
    transcription.unload_model()
    try:
        import mlx.core
        mlx.core.metal.clear_cache()
    except Exception:
        pass
    gc.collect()


def cleanup_diarization() -> None:
    """Unload diarization models and clear MPS cache."""
    logger.info("Cleaning up diarization resources")
    diarization.unload_models()
    gc.collect()


async def cleanup_llm(base_url: str, api_key: str | None, model: str) -> None:
    """Unload LLM from Ollama (no-op for non-Ollama providers)."""
    logger.info("Cleaning up LLM resources")
    await llm_client.unload_model(base_url, api_key, model)
    gc.collect()


def cleanup_image_generation() -> None:
    """Unload image generation model and clear MLX cache."""
    logger.info("Cleaning up image generation resources")
    image_generation.unload_model()
    try:
        import mlx.core
        mlx.core.metal.clear_cache()
    except Exception:
        pass
    gc.collect()


async def cleanup_all(
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
) -> None:
    """Run all cleanup functions."""
    cleanup_transcription()
    cleanup_diarization()
    if llm_base_url and llm_model:
        await cleanup_llm(llm_base_url, llm_api_key, llm_model)
    cleanup_image_generation()
