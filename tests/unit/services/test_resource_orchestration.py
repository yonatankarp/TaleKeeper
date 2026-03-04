"""Tests for resource orchestration cleanup functions."""

from unittest.mock import patch, AsyncMock, MagicMock

from talekeeper.services.resource_orchestration import (
    cleanup_transcription,
    cleanup_diarization,
    cleanup_llm,
    cleanup_image_generation,
    cleanup_all,
)


@patch("talekeeper.services.resource_orchestration.gc")
@patch("talekeeper.services.resource_orchestration.transcription")
def test_cleanup_transcription(mock_transcription, mock_gc):
    """cleanup_transcription unloads model, clears MLX cache, runs gc."""
    mock_mlx_core = MagicMock()
    with patch.dict("sys.modules", {"mlx": MagicMock(), "mlx.core": mock_mlx_core}):
        cleanup_transcription()

    mock_transcription.unload_model.assert_called_once()
    mock_gc.collect.assert_called_once()


@patch("talekeeper.services.resource_orchestration.gc")
def test_cleanup_diarization(mock_gc):
    """cleanup_diarization runs gc (no models to unload with diarize library)."""
    cleanup_diarization()

    mock_gc.collect.assert_called_once()


@patch("talekeeper.services.resource_orchestration.gc")
@patch("talekeeper.services.resource_orchestration.llm_client")
async def test_cleanup_llm(mock_llm_client, mock_gc):
    """cleanup_llm calls llm_client.unload_model and runs gc."""
    mock_llm_client.unload_model = AsyncMock()

    await cleanup_llm("http://localhost:11434/v1", None, "llama3")

    mock_llm_client.unload_model.assert_awaited_once_with(
        "http://localhost:11434/v1", None, "llama3"
    )
    mock_gc.collect.assert_called_once()


@patch("talekeeper.services.resource_orchestration.gc")
@patch("talekeeper.services.resource_orchestration.image_generation")
def test_cleanup_image_generation(mock_image_gen, mock_gc):
    """cleanup_image_generation unloads model, clears MLX cache, runs gc."""
    mock_mlx_core = MagicMock()
    with patch.dict("sys.modules", {"mlx": MagicMock(), "mlx.core": mock_mlx_core}):
        cleanup_image_generation()

    mock_image_gen.unload_model.assert_called_once()
    mock_gc.collect.assert_called_once()


@patch("talekeeper.services.resource_orchestration.cleanup_image_generation")
@patch("talekeeper.services.resource_orchestration.cleanup_llm", new_callable=AsyncMock)
@patch("talekeeper.services.resource_orchestration.cleanup_diarization")
@patch("talekeeper.services.resource_orchestration.cleanup_transcription")
async def test_cleanup_all_with_llm(mock_trans, mock_diar, mock_llm, mock_img):
    """cleanup_all calls all cleanup functions when LLM config is provided."""
    await cleanup_all("http://localhost:11434/v1", None, "llama3")

    mock_trans.assert_called_once()
    mock_diar.assert_called_once()
    mock_llm.assert_awaited_once_with("http://localhost:11434/v1", None, "llama3")
    mock_img.assert_called_once()


@patch("talekeeper.services.resource_orchestration.cleanup_image_generation")
@patch("talekeeper.services.resource_orchestration.cleanup_llm", new_callable=AsyncMock)
@patch("talekeeper.services.resource_orchestration.cleanup_diarization")
@patch("talekeeper.services.resource_orchestration.cleanup_transcription")
async def test_cleanup_all_without_llm(mock_trans, mock_diar, mock_llm, mock_img):
    """cleanup_all skips LLM cleanup when no config provided."""
    await cleanup_all()

    mock_trans.assert_called_once()
    mock_diar.assert_called_once()
    mock_llm.assert_not_awaited()
    mock_img.assert_called_once()
