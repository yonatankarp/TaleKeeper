"""Roster CRUD API endpoints."""

import re

import fitz  # PyMuPDF
import httpx

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from talekeeper.db import get_db
from talekeeper.services import llm_client

router = APIRouter(tags=["roster"])

EXTRACT_DESCRIPTION_SYSTEM = """You are reading a tabletop RPG character sheet.
Extract a concise visual description of the character suitable for illustrating them.
Output ONLY the description, nothing else. No preamble, no commentary.
Include: species/race, class, notable physical features, equipment, clothing, and overall appearance.
Keep it to 2-3 sentences maximum."""

EXTRACT_DESCRIPTION_PROMPT = """From the following character sheet text, extract a concise visual description
of the character. Focus on what they look like, their race/species, class, gear, and any distinctive features.

CHARACTER SHEET:
{text}

Visual description:"""


class RosterEntryCreate(BaseModel):
    player_name: str
    character_name: str
    description: str = ""


class RosterEntryUpdate(BaseModel):
    player_name: str | None = None
    character_name: str | None = None
    description: str | None = None
    is_active: bool | None = None


@router.post("/api/campaigns/{campaign_id}/roster")
async def create_roster_entry(campaign_id: int, body: RosterEntryCreate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT id FROM campaigns WHERE id = ?", (campaign_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Campaign not found")

        cursor = await db.execute(
            "INSERT INTO roster_entries (campaign_id, player_name, character_name, description) VALUES (?, ?, ?, ?)",
            (campaign_id, body.player_name, body.character_name, body.description),
        )
        entry_id = cursor.lastrowid
        rows = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
    return dict(rows[0])


@router.get("/api/campaigns/{campaign_id}/roster")
async def list_roster(campaign_id: int) -> list[dict]:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE campaign_id = ? ORDER BY player_name",
            (campaign_id,),
        )
    return [dict(r) for r in rows]


@router.put("/api/roster/{entry_id}")
async def update_roster_entry(entry_id: int, body: RosterEntryUpdate) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Roster entry not found")

        fields = []
        values = []
        if body.player_name is not None:
            fields.append("player_name = ?")
            values.append(body.player_name)
        if body.character_name is not None:
            fields.append("character_name = ?")
            values.append(body.character_name)
        if body.description is not None:
            fields.append("description = ?")
            values.append(body.description)
        if body.is_active is not None:
            fields.append("is_active = ?")
            values.append(int(body.is_active))

        if fields:
            values.append(entry_id)
            await db.execute(
                f"UPDATE roster_entries SET {', '.join(fields)} WHERE id = ?",
                values,
            )

        rows = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
    return dict(rows[0])


@router.post("/api/roster/{entry_id}/upload-sheet")
async def upload_character_sheet(entry_id: int, file: UploadFile) -> dict:
    """Upload a PDF character sheet and extract a visual description via LLM."""
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
    if not existing:
        raise HTTPException(status_code=404, detail="Roster entry not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read PDF and extract text
    pdf_bytes = await file.read()
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read PDF file")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text found in PDF. The character sheet may be image-based.")

    description = await _extract_description(text)

    # Save to roster entry (store raw sheet data for later refresh)
    async with get_db() as db:
        await db.execute(
            "UPDATE roster_entries SET description = ?, sheet_url = '', sheet_data = ? WHERE id = ?",
            (description.strip(), text[:16000], entry_id),
        )
        rows = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
    return dict(rows[0])


class ImportUrlRequest(BaseModel):
    url: str


_DNDBEYOND_PATTERN = re.compile(
    r"dndbeyond\.com/characters/(\d+)"
)
_DNDBEYOND_JSON_URL = "https://character-service.dndbeyond.com/character/v5/character/{char_id}"


async def _fetch_dndbeyond_character(char_id: str) -> str:
    """Fetch character data from D&D Beyond's JSON API and format key fields as text."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(
            _DNDBEYOND_JSON_URL.format(char_id=char_id),
            headers={"User-Agent": "Mozilla/5.0 (compatible; TaleKeeper/1.0)"},
        )
        resp.raise_for_status()

    data = resp.json().get("data", resp.json())

    # Build a concise text summary from the JSON
    parts = []
    name = data.get("name", "Unknown")
    parts.append(f"Name: {name}")

    # Race / species
    race = data.get("race", {})
    if isinstance(race, dict):
        race_name = race.get("fullName") or race.get("baseName") or ""
    else:
        race_name = str(race) if race else ""
    if race_name:
        parts.append(f"Race: {race_name}")

    # Classes
    classes = data.get("classes", [])
    if classes:
        class_strs = []
        for c in classes:
            cls_name = c.get("definition", {}).get("name", "") if isinstance(c.get("definition"), dict) else ""
            level = c.get("level", "")
            subclass = c.get("subclassDefinition")
            sub_name = subclass.get("name", "") if isinstance(subclass, dict) else ""
            entry = f"{cls_name} {level}".strip()
            if sub_name:
                entry += f" ({sub_name})"
            class_strs.append(entry)
        parts.append(f"Class: {', '.join(class_strs)}")

    # Appearance / traits
    traits = data.get("traits", {})
    if isinstance(traits, dict):
        for key in ("appearance", "personalityTraits", "ideals", "bonds", "flaws"):
            val = traits.get(key)
            if val:
                parts.append(f"{key}: {val}")

    notes = data.get("notes", {})
    if isinstance(notes, dict):
        for key in ("personalityTraits", "ideals", "bonds", "flaws", "backstory", "appearance"):
            val = notes.get(key)
            if val:
                parts.append(f"{key}: {val}")

    # Physical characteristics
    for field in ("gender", "hair", "eyes", "skin", "height", "weight", "faith"):
        val = data.get(field)
        if val:
            parts.append(f"{field}: {val}")

    # Equipment (brief)
    inventory = data.get("inventory", [])
    if inventory:
        equipped = [
            item.get("definition", {}).get("name", "")
            for item in inventory
            if item.get("equipped") and isinstance(item.get("definition"), dict)
        ]
        equipped = [e for e in equipped if e]
        if equipped:
            parts.append(f"Equipped: {', '.join(equipped[:15])}")

    return "\n".join(parts)


async def _fetch_generic_page(url: str) -> str:
    """Fetch a generic web page and strip HTML to text."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; TaleKeeper/1.0)",
        })
        resp.raise_for_status()

    html = resp.text
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@router.post("/api/roster/{entry_id}/import-url")
async def import_character_url(entry_id: int, body: ImportUrlRequest) -> dict:
    """Fetch a D&D Beyond (or similar) character page and extract a visual description via LLM."""
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
    if not existing:
        raise HTTPException(status_code=404, detail="Roster entry not found")

    # Fetch character data
    match = _DNDBEYOND_PATTERN.search(body.url)
    try:
        if match:
            text = await _fetch_dndbeyond_character(match.group(1))
        else:
            text = await _fetch_generic_page(body.url)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: HTTP {e.response.status_code}")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not fetch URL. Check the link and try again.")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No character data found at the URL.")

    description = await _extract_description(text)

    # Save to roster entry (store URL and raw data for later refresh)
    async with get_db() as db:
        await db.execute(
            "UPDATE roster_entries SET description = ?, sheet_url = ?, sheet_data = ? WHERE id = ?",
            (description.strip(), body.url, text[:16000], entry_id),
        )
        rows = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
    return dict(rows[0])


async def _extract_description(text: str) -> str:
    """Run the LLM to extract a visual character description from sheet text."""
    config = await llm_client.resolve_config()
    health = await llm_client.health_check(config["base_url"], config["api_key"], config["model"])
    if health["status"] != "ok":
        raise HTTPException(status_code=503, detail=health["message"])

    prompt = EXTRACT_DESCRIPTION_PROMPT.format(text=text[:8000])
    return await llm_client.generate(
        config["base_url"], config["api_key"], config["model"],
        prompt, system=EXTRACT_DESCRIPTION_SYSTEM,
    )


@router.post("/api/roster/{entry_id}/refresh-sheet")
async def refresh_character_sheet(entry_id: int) -> dict:
    """Re-fetch (if URL) and re-extract the character description from the stored sheet."""
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
    if not existing:
        raise HTTPException(status_code=404, detail="Roster entry not found")

    entry = dict(existing[0])
    sheet_url = entry.get("sheet_url") or ""
    sheet_data = entry.get("sheet_data") or ""

    # If we have a URL, re-fetch fresh data
    if sheet_url:
        match = _DNDBEYOND_PATTERN.search(sheet_url)
        try:
            if match:
                text = await _fetch_dndbeyond_character(match.group(1))
            else:
                text = await _fetch_generic_page(sheet_url)
        except Exception:
            raise HTTPException(status_code=400, detail="Could not re-fetch URL. Using stored data is not possible.")
    elif sheet_data:
        text = sheet_data
    else:
        raise HTTPException(status_code=400, detail="No character sheet stored. Upload a PDF or import a URL first.")

    description = await _extract_description(text)

    async with get_db() as db:
        await db.execute(
            "UPDATE roster_entries SET description = ?, sheet_data = ? WHERE id = ?",
            (description.strip(), text[:16000], entry_id),
        )
        rows = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
    return dict(rows[0])


@router.delete("/api/roster/{entry_id}")
async def delete_roster_entry(entry_id: int) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM roster_entries WHERE id = ?", (entry_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Roster entry not found")

        await db.execute("DELETE FROM roster_entries WHERE id = ?", (entry_id,))
    return {"deleted": True}
