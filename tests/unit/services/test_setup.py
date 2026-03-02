"""Tests for the first-run setup check service."""

import pytest
from unittest.mock import patch, AsyncMock
from pathlib import Path

from talekeeper.services.setup import check_first_run


@patch(
    "talekeeper.services.setup.llm_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://test", "api_key": None, "model": "test"},
)
@patch(
    "talekeeper.services.setup.llm_client.health_check",
    new_callable=AsyncMock,
    return_value={"status": "error", "message": "no"},
)
@patch(
    "talekeeper.services.setup.image_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://test", "api_key": None, "model": "test"},
)
@patch(
    "talekeeper.services.setup.image_client.health_check",
    new_callable=AsyncMock,
    return_value={"status": "error", "message": "no"},
)
@patch("talekeeper.services.setup.get_db_dir")
@patch("talekeeper.services.setup.get_user_data_dir")
async def test_check_first_run(
    mock_user_dir,
    mock_db_dir,
    mock_img_health,
    mock_img_config,
    mock_llm_health,
    mock_llm_config,
    db,
    tmp_path,
):
    """check_first_run returns status dict with connectivity and path checks."""
    mock_db_dir.return_value = tmp_path / "db"
    (tmp_path / "db").mkdir()

    user_data = tmp_path / "user_data"
    user_data.mkdir()
    mock_user_dir.return_value = user_data

    result = await check_first_run()

    assert result["data_dir_exists"] is True
    assert result["llm_connected"] is False
    assert result["image_connected"] is False
    assert result["is_first_run"] is True
    assert result["has_recordings"] is False
    assert result["data_dir"] == str(user_data)
