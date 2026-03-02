"""Tests for the scene description and image generation pipeline."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from conftest import create_campaign, create_session

from talekeeper.services.image_generation import (
    craft_scene_description,
    generate_session_image,
)


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


@patch(
    "talekeeper.services.image_generation.image_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://test", "api_key": None, "model": "test-model"},
)
@patch(
    "talekeeper.services.image_generation.image_client.generate_image",
    new_callable=AsyncMock,
    return_value=b"PNG-DATA",
)
@patch("talekeeper.services.image_generation.get_session_images_dir")
async def test_generate_session_image(mock_dir, mock_gen_img, mock_config, db, tmp_path):
    """generate_session_image saves image to disk and records metadata in DB."""
    mock_dir.return_value = tmp_path

    # Create campaign and session in the database
    campaign_id = await create_campaign(db, name="Image Test Campaign")
    session_id = await create_session(db, campaign_id, name="Image Test Session")

    result = await generate_session_image(
        session_id, "a dragon in a cave", "A fierce dragon guards its hoard"
    )

    # Image file should be written to tmp_path
    written_files = list(tmp_path.glob("*.png"))
    assert len(written_files) == 1
    assert written_files[0].read_bytes() == b"PNG-DATA"

    # Result should contain metadata from DB
    assert result["session_id"] == session_id
    assert result["prompt"] == "a dragon in a cave"
    assert result["scene_description"] == "A fierce dragon guards its hoard"
    assert result["model_used"] == "test-model"
