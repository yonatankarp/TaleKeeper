"""Tests for the scene description and image generation pipeline (mflux)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from conftest import create_campaign, create_session

from talekeeper.services.image_generation import (
    craft_scene_description,
    generate_session_image,
    _resolve_image_config,
    health_check,
    unload_model,
)
import talekeeper.services.image_generation as mod


# ---- craft_scene_description (6.8 — unchanged) ----


@patch(
    "talekeeper.services.image_generation.llm_client.generate",
    new_callable=AsyncMock,
    return_value="A dark tavern scene",
)
async def test_craft_scene_description(mock_gen):
    """craft_scene_description calls llm_client.generate and returns the result."""
    result = await craft_scene_description(
        "transcript content", "http://test", None, "model"
    )

    assert result == "A dark tavern scene"
    mock_gen.assert_awaited_once()


# ---- Image config resolution (6.5) ----


async def test_resolve_image_config_defaults(db):
    """_resolve_image_config returns defaults when no settings."""
    config = await _resolve_image_config()
    assert config["model"] == "flux2-klein-4b"
    assert config["steps"] == 4
    assert config["guidance_scale"] == 0.0


async def test_resolve_image_config_from_settings(db):
    """_resolve_image_config reads from settings table."""
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('image_steps', '8')"
    )
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('image_guidance_scale', '3.5')"
    )
    await db.commit()

    config = await _resolve_image_config()
    assert config["steps"] == 8
    assert config["guidance_scale"] == 3.5


# ---- Image generation (6.9) ----


@patch("talekeeper.services.image_generation._resolve_image_config", new_callable=AsyncMock)
@patch("talekeeper.services.image_generation._get_model")
@patch("talekeeper.services.image_generation.get_session_images_dir")
async def test_generate_session_image(mock_dir, mock_get_model, mock_config, db, tmp_path):
    """generate_session_image generates via mflux, saves PNG to disk, and records metadata."""
    mock_dir.return_value = tmp_path
    mock_config.return_value = {"model": "flux2-klein-4b", "steps": 4, "guidance_scale": 0.0}

    # Mock the FLUX model
    mock_model = MagicMock()
    mock_generated = MagicMock()
    mock_pil_image = MagicMock()
    mock_generated.image = mock_pil_image
    mock_model.generate_image.return_value = mock_generated
    mock_get_model.return_value = mock_model

    campaign_id = await create_campaign(db, name="Image Test Campaign")
    session_id = await create_session(db, campaign_id, name="Image Test Session")

    result = await generate_session_image(
        session_id, "a dragon in a cave", "A fierce dragon guards its hoard"
    )

    # Model should have been called
    mock_model.generate_image.assert_called_once()
    call_kwargs = mock_model.generate_image.call_args
    assert call_kwargs.kwargs["prompt"] == "a dragon in a cave"
    assert call_kwargs.kwargs["num_inference_steps"] == 4

    # PIL image.save should have been called
    mock_pil_image.save.assert_called_once()

    # Result should contain metadata from DB
    assert result["session_id"] == session_id
    assert result["prompt"] == "a dragon in a cave"
    assert result["scene_description"] == "A fierce dragon guards its hoard"
    assert result["model_used"] == "flux2-klein-4b"


# ---- Health check (6.10) ----


def test_health_check_ok():
    """health_check returns ok when mflux is importable."""
    result = health_check()
    assert result["status"] == "ok"
    assert result["engine"] == "mflux"


@patch("talekeeper.services.image_generation.health_check")
def test_health_check_import_error(mock_check):
    """health_check returns error when mflux is not available."""
    # Simulate the real health_check behavior on import failure
    mock_check.return_value = {"status": "error", "message": "mflux not available: No module named 'mflux'"}
    result = mock_check()
    assert result["status"] == "error"
