"""Roster CRUD API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from talekeeper.db import get_db

router = APIRouter(tags=["roster"])


class RosterEntryCreate(BaseModel):
    player_name: str
    character_name: str


class RosterEntryUpdate(BaseModel):
    player_name: str | None = None
    character_name: str | None = None
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
            "INSERT INTO roster_entries (campaign_id, player_name, character_name) VALUES (?, ?, ?)",
            (campaign_id, body.player_name, body.character_name),
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
