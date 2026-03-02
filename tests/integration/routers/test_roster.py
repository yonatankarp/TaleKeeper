"""Integration tests for roster API endpoints."""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


async def _create_campaign(client: AsyncClient) -> int:
    """Helper to create a campaign and return its ID."""
    resp = await client.post("/api/campaigns", json={"name": "Test Campaign"})
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_roster_entry(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    resp = await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["player_name"] == "Alice"
    assert data["character_name"] == "Gandalf"
    assert data["campaign_id"] == campaign_id
    assert "id" in data


@pytest.mark.asyncio
async def test_list_roster(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Bob", "character_name": "Aragorn"},
    )

    resp = await client.get(f"/api/campaigns/{campaign_id}/roster")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    player_names = [e["player_name"] for e in data]
    assert "Alice" in player_names
    assert "Bob" in player_names


@pytest.mark.asyncio
async def test_update_roster_entry(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    create_resp = await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    entry_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/roster/{entry_id}",
        json={"character_name": "Gandalf the White"},
    )
    assert resp.status_code == 200
    assert resp.json()["character_name"] == "Gandalf the White"
    # Player name should remain unchanged
    assert resp.json()["player_name"] == "Alice"


@pytest.mark.asyncio
async def test_delete_roster_entry(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    create_resp = await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    entry_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/roster/{entry_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


@pytest.mark.asyncio
async def test_delete_roster_entry_not_found(client: AsyncClient) -> None:
    resp = await client.delete("/api/roster/99999")
    assert resp.status_code == 404


# --- helpers for sheet / import tests ---


async def _create_roster_entry(client: AsyncClient) -> tuple[int, int]:
    """Create a campaign + roster entry. Returns (campaign_id, entry_id)."""
    campaign_id = await _create_campaign(client)
    resp = await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    assert resp.status_code == 200
    return campaign_id, resp.json()["id"]


def _mock_llm():
    """Return patch context-managers for llm_client resolve_config, health_check, generate."""
    resolve = patch(
        "talekeeper.routers.roster.llm_client.resolve_config",
        new_callable=AsyncMock,
        return_value={"base_url": "http://test", "api_key": None, "model": "m"},
    )
    health = patch(
        "talekeeper.routers.roster.llm_client.health_check",
        new_callable=AsyncMock,
        return_value={"status": "ok"},
    )
    generate = patch(
        "talekeeper.routers.roster.llm_client.generate",
        new_callable=AsyncMock,
        return_value="A tall elven ranger",
    )
    return resolve, health, generate


# --- upload-sheet tests ---


@pytest.mark.asyncio
async def test_upload_sheet_pdf(client: AsyncClient) -> None:
    """Upload a PDF sheet, mock fitz + LLM, expect description extracted."""
    _, entry_id = await _create_roster_entry(client)

    # Build a mock fitz document that yields pages with get_text()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Elf Ranger level 5, green cloak"
    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

    resolve, health, generate = _mock_llm()

    with (
        patch("talekeeper.routers.roster.fitz.open", return_value=mock_doc) as _fitz,
        resolve,
        health,
        generate,
    ):
        resp = await client.post(
            f"/api/roster/{entry_id}/upload-sheet",
            files={"file": ("sheet.pdf", BytesIO(b"fake-pdf"), "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "A tall elven ranger"


@pytest.mark.asyncio
async def test_upload_sheet_non_pdf(client: AsyncClient) -> None:
    """Uploading a non-PDF file should return 400."""
    _, entry_id = await _create_roster_entry(client)

    resp = await client.post(
        f"/api/roster/{entry_id}/upload-sheet",
        files={"file": ("notes.txt", BytesIO(b"plain text"), "text/plain")},
    )
    assert resp.status_code == 400


# --- import-url test ---


@pytest.mark.asyncio
async def test_import_url(client: AsyncClient) -> None:
    """Import a character from a URL, mock httpx + LLM, expect description extracted."""
    _, entry_id = await _create_roster_entry(client)

    # Build a mock httpx response
    mock_response = MagicMock()
    mock_response.text = "<html><body>Elf Ranger level 5</body></html>"
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.get.return_value = mock_response

    # AsyncClient is used as an async context-manager
    mock_http_cls = MagicMock()
    mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    resolve, health, generate = _mock_llm()

    with (
        patch("talekeeper.routers.roster.httpx.AsyncClient", mock_http_cls),
        resolve,
        health,
        generate,
    ):
        resp = await client.post(
            f"/api/roster/{entry_id}/import-url",
            json={"url": "https://example.com/char"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "A tall elven ranger"


# --- refresh-sheet tests ---


@pytest.mark.asyncio
async def test_refresh_sheet_no_data(client: AsyncClient) -> None:
    """Refreshing when no sheet data is stored should return 400."""
    _, entry_id = await _create_roster_entry(client)

    resp = await client.post(f"/api/roster/{entry_id}/refresh-sheet")
    assert resp.status_code == 400
