"""Database schema, migration, cascade, lifecycle, and default-value tests.

Covers tasks 2.1-2.5 from the test plan:
  2.1 - Schema tests (all 9 tables + column verification)
  2.2 - Migration idempotency
  2.3 - Foreign-key cascade behaviour
  2.4 - get_db() lifecycle
  2.5 - Default values for campaigns and sessions
"""

from pathlib import Path
from unittest.mock import patch

import aiosqlite
import pytest

from talekeeper.db.connection import (
    init_db,
    get_db,
    _migrate_add_language_columns,
    _migrate_add_num_speakers_column,
    _migrate_add_voice_signatures_table,
    _migrate_add_session_images_table,
)
from conftest import create_campaign, create_session, create_speaker, create_segment

# ---------------------------------------------------------------------------
# Expected DDL: table name -> ordered list of (column_name, column_type)
# ---------------------------------------------------------------------------

EXPECTED_TABLES: dict[str, list[tuple[str, str]]] = {
    "campaigns": [
        ("id", "INTEGER"),
        ("name", "TEXT"),
        ("description", "TEXT"),
        ("language", "TEXT"),
        ("num_speakers", "INTEGER"),
        ("session_start_number", "INTEGER"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT"),
    ],
    "sessions": [
        ("id", "INTEGER"),
        ("campaign_id", "INTEGER"),
        ("name", "TEXT"),
        ("date", "TEXT"),
        ("status", "TEXT"),
        ("language", "TEXT"),
        ("session_number", "INTEGER"),
        ("audio_path", "TEXT"),
        ("created_at", "TEXT"),
        ("updated_at", "TEXT"),
    ],
    "speakers": [
        ("id", "INTEGER"),
        ("session_id", "INTEGER"),
        ("diarization_label", "TEXT"),
        ("player_name", "TEXT"),
        ("character_name", "TEXT"),
    ],
    "transcript_segments": [
        ("id", "INTEGER"),
        ("session_id", "INTEGER"),
        ("speaker_id", "INTEGER"),
        ("text", "TEXT"),
        ("start_time", "REAL"),
        ("end_time", "REAL"),
    ],
    "summaries": [
        ("id", "INTEGER"),
        ("session_id", "INTEGER"),
        ("type", "TEXT"),
        ("speaker_id", "INTEGER"),
        ("content", "TEXT"),
        ("model_used", "TEXT"),
        ("generated_at", "TEXT"),
    ],
    "roster_entries": [
        ("id", "INTEGER"),
        ("campaign_id", "INTEGER"),
        ("player_name", "TEXT"),
        ("character_name", "TEXT"),
        ("description", "TEXT"),
        ("sheet_url", "TEXT"),
        ("sheet_data", "TEXT"),
        ("is_active", "INTEGER"),
        ("created_at", "TEXT"),
    ],
    "voice_signatures": [
        ("id", "INTEGER"),
        ("campaign_id", "INTEGER"),
        ("roster_entry_id", "INTEGER"),
        ("embedding", "TEXT"),
        ("source_session_id", "INTEGER"),
        ("num_samples", "INTEGER"),
        ("created_at", "TEXT"),
    ],
    "session_images": [
        ("id", "INTEGER"),
        ("session_id", "INTEGER"),
        ("file_path", "TEXT"),
        ("prompt", "TEXT"),
        ("scene_description", "TEXT"),
        ("model_used", "TEXT"),
        ("generated_at", "TEXT"),
    ],
    "settings": [
        ("key", "TEXT"),
        ("value", "TEXT"),
    ],
}


# ===================================================================
# 2.1 -- Schema tests: all 9 tables exist with correct columns
# ===================================================================


class TestSchema:
    """Verify that init_db() produces exactly the expected tables and columns."""

    @pytest.mark.asyncio
    async def test_all_nine_tables_exist(self, db: aiosqlite.Connection):
        """After init_db(), all 9 application tables must be present."""
        rows = await db.execute_fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = {row["name"] for row in rows}

        for expected in EXPECTED_TABLES:
            assert expected in table_names, f"Table '{expected}' missing from schema"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("table_name", list(EXPECTED_TABLES.keys()))
    async def test_table_columns_match_expected(
        self, db: aiosqlite.Connection, table_name: str
    ):
        """Each table's column names and types must match the DDL spec."""
        rows = await db.execute_fetchall(f"PRAGMA table_info({table_name})")
        actual_columns = [(row["name"], row["type"]) for row in rows]
        assert actual_columns == EXPECTED_TABLES[table_name], (
            f"Column mismatch for '{table_name}': "
            f"expected {EXPECTED_TABLES[table_name]}, got {actual_columns}"
        )


# ===================================================================
# 2.2 -- Migration idempotency
# ===================================================================


class TestMigrationIdempotency:
    """Calling init_db() or individual migrations twice must not fail."""

    @pytest.mark.asyncio
    async def test_double_init_db_succeeds(self, tmp_path: Path):
        """Running init_db() twice on the same database must not raise."""
        db_path = tmp_path / "idempotent.db"
        with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
            await init_db()
            await init_db()  # second call must be harmless

        # Quick sanity check: tables still exist
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            rows = await conn.execute_fetchall(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            table_names = {row["name"] for row in rows}
            for expected in EXPECTED_TABLES:
                assert expected in table_names

    @pytest.mark.asyncio
    async def test_migrate_add_language_columns_idempotent(
        self, db: aiosqlite.Connection
    ):
        """_migrate_add_language_columns can run multiple times safely."""
        await _migrate_add_language_columns(db)
        await _migrate_add_language_columns(db)

        # Verify columns still present exactly once in each table
        for table in ("campaigns", "sessions"):
            cols = await db.execute_fetchall(f"PRAGMA table_info({table})")
            lang_cols = [c for c in cols if c["name"] == "language"]
            assert len(lang_cols) == 1, (
                f"Expected exactly 1 'language' column in {table}, "
                f"found {len(lang_cols)}"
            )

    @pytest.mark.asyncio
    async def test_migrate_add_num_speakers_column_idempotent(
        self, db: aiosqlite.Connection
    ):
        """_migrate_add_num_speakers_column can run multiple times safely."""
        await _migrate_add_num_speakers_column(db)
        await _migrate_add_num_speakers_column(db)

        cols = await db.execute_fetchall("PRAGMA table_info(campaigns)")
        ns_cols = [c for c in cols if c["name"] == "num_speakers"]
        assert len(ns_cols) == 1

    @pytest.mark.asyncio
    async def test_migrate_add_voice_signatures_table_idempotent(
        self, db: aiosqlite.Connection
    ):
        """_migrate_add_voice_signatures_table can run multiple times safely."""
        await _migrate_add_voice_signatures_table(db)
        await _migrate_add_voice_signatures_table(db)

        tables = await db.execute_fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='voice_signatures'"
        )
        assert len(tables) == 1

    @pytest.mark.asyncio
    async def test_migrate_add_session_images_table_idempotent(
        self, db: aiosqlite.Connection
    ):
        """_migrate_add_session_images_table can run multiple times safely."""
        await _migrate_add_session_images_table(db)
        await _migrate_add_session_images_table(db)

        tables = await db.execute_fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='session_images'"
        )
        assert len(tables) == 1


# ===================================================================
# 2.3 -- Foreign-key cascade tests
# ===================================================================


class TestForeignKeyCascades:
    """Verify ON DELETE CASCADE and ON DELETE SET NULL behaviour."""

    @pytest.mark.asyncio
    async def test_delete_campaign_cascades_to_sessions(
        self, db: aiosqlite.Connection
    ):
        """Deleting a campaign must delete all its sessions."""
        cid = await create_campaign(db, name="Cascade Campaign")
        sid1 = await create_session(db, cid, name="S1")
        sid2 = await create_session(db, cid, name="S2")

        # Confirm sessions exist
        rows = await db.execute_fetchall(
            "SELECT id FROM sessions WHERE campaign_id = ?", (cid,)
        )
        assert len(rows) == 2

        # Delete campaign
        await db.execute("DELETE FROM campaigns WHERE id = ?", (cid,))
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id FROM sessions WHERE campaign_id = ?", (cid,)
        )
        assert len(rows) == 0, "Sessions should be cascade-deleted with campaign"

    @pytest.mark.asyncio
    async def test_delete_session_cascades_to_speakers(
        self, db: aiosqlite.Connection
    ):
        """Deleting a session must delete all its speakers."""
        cid = await create_campaign(db)
        sid = await create_session(db, cid)
        spk = await create_speaker(db, sid, diarization_label="SPEAKER_00")

        await db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id FROM speakers WHERE session_id = ?", (sid,)
        )
        assert len(rows) == 0, "Speakers should be cascade-deleted with session"

    @pytest.mark.asyncio
    async def test_delete_session_cascades_to_segments(
        self, db: aiosqlite.Connection
    ):
        """Deleting a session must delete all its transcript segments."""
        cid = await create_campaign(db)
        sid = await create_session(db, cid)
        seg = await create_segment(db, sid, text="Some text", start_time=0.0, end_time=1.0)

        await db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id FROM transcript_segments WHERE session_id = ?", (sid,)
        )
        assert len(rows) == 0, "Segments should be cascade-deleted with session"

    @pytest.mark.asyncio
    async def test_delete_speaker_sets_segment_speaker_id_to_null(
        self, db: aiosqlite.Connection
    ):
        """Deleting a speaker must SET NULL on segment.speaker_id (not delete the segment)."""
        cid = await create_campaign(db)
        sid = await create_session(db, cid)
        spk = await create_speaker(db, sid, diarization_label="SPEAKER_00")
        seg_id = await create_segment(
            db, sid, spk, text="Attributed text", start_time=0.0, end_time=2.0
        )

        # Confirm speaker_id is set
        row = await db.execute_fetchall(
            "SELECT speaker_id FROM transcript_segments WHERE id = ?", (seg_id,)
        )
        assert row[0]["speaker_id"] == spk

        # Delete the speaker
        await db.execute("DELETE FROM speakers WHERE id = ?", (spk,))
        await db.commit()

        row = await db.execute_fetchall(
            "SELECT speaker_id FROM transcript_segments WHERE id = ?", (seg_id,)
        )
        assert len(row) == 1, "Segment must still exist after speaker deletion"
        assert row[0]["speaker_id"] is None, (
            "speaker_id should be NULL after speaker deletion"
        )

    @pytest.mark.asyncio
    async def test_delete_campaign_cascades_through_sessions_to_segments(
        self, db: aiosqlite.Connection
    ):
        """Deleting a campaign should cascade through sessions to segments."""
        cid = await create_campaign(db)
        sid = await create_session(db, cid)
        seg_id = await create_segment(db, sid, text="Deep cascade")

        await db.execute("DELETE FROM campaigns WHERE id = ?", (cid,))
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id FROM transcript_segments WHERE id = ?", (seg_id,)
        )
        assert len(rows) == 0, "Segments should be gone after campaign cascade"

    @pytest.mark.asyncio
    async def test_delete_session_cascades_to_summaries(
        self, db: aiosqlite.Connection
    ):
        """Deleting a session must delete all its summaries."""
        cid = await create_campaign(db)
        sid = await create_session(db, cid)
        await db.execute(
            "INSERT INTO summaries (session_id, type, content) VALUES (?, ?, ?)",
            (sid, "full", "A grand summary"),
        )
        await db.commit()

        await db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id FROM summaries WHERE session_id = ?", (sid,)
        )
        assert len(rows) == 0, "Summaries should be cascade-deleted with session"

    @pytest.mark.asyncio
    async def test_delete_session_cascades_to_session_images(
        self, db: aiosqlite.Connection
    ):
        """Deleting a session must delete all its session images."""
        cid = await create_campaign(db)
        sid = await create_session(db, cid)
        await db.execute(
            "INSERT INTO session_images (session_id, file_path, prompt) VALUES (?, ?, ?)",
            (sid, "/images/test.png", "A dramatic scene"),
        )
        await db.commit()

        await db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id FROM session_images WHERE session_id = ?", (sid,)
        )
        assert len(rows) == 0, "Session images should be cascade-deleted with session"

    @pytest.mark.asyncio
    async def test_delete_campaign_cascades_to_roster_entries(
        self, db: aiosqlite.Connection
    ):
        """Deleting a campaign must delete all its roster entries."""
        cid = await create_campaign(db)
        await db.execute(
            "INSERT INTO roster_entries (campaign_id, player_name, character_name) VALUES (?, ?, ?)",
            (cid, "Alice", "Gandalf"),
        )
        await db.commit()

        await db.execute("DELETE FROM campaigns WHERE id = ?", (cid,))
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id FROM roster_entries WHERE campaign_id = ?", (cid,)
        )
        assert len(rows) == 0, "Roster entries should be cascade-deleted with campaign"

    @pytest.mark.asyncio
    async def test_delete_roster_entry_cascades_to_voice_signatures(
        self, db: aiosqlite.Connection
    ):
        """Deleting a roster entry must cascade-delete its voice signatures."""
        cid = await create_campaign(db)
        cursor = await db.execute(
            "INSERT INTO roster_entries (campaign_id, player_name, character_name) VALUES (?, ?, ?)",
            (cid, "Bob", "Frodo"),
        )
        await db.commit()
        re_id = cursor.lastrowid

        await db.execute(
            "INSERT INTO voice_signatures (campaign_id, roster_entry_id, embedding) VALUES (?, ?, ?)",
            (cid, re_id, "[0.1, 0.2, 0.3]"),
        )
        await db.commit()

        await db.execute("DELETE FROM roster_entries WHERE id = ?", (re_id,))
        await db.commit()

        rows = await db.execute_fetchall(
            "SELECT id FROM voice_signatures WHERE roster_entry_id = ?", (re_id,)
        )
        assert len(rows) == 0, (
            "Voice signatures should be cascade-deleted with roster entry"
        )


# ===================================================================
# 2.4 -- get_db() lifecycle tests
# ===================================================================


class TestGetDbLifecycle:
    """Verify that get_db() provides a working connection and commits on exit."""

    @pytest.mark.asyncio
    async def test_get_db_connection_is_usable(self, tmp_path: Path):
        """The connection yielded by get_db() must support queries."""
        db_path = tmp_path / "lifecycle.db"
        with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
            await init_db()

            async with get_db() as conn:
                # Simple query: list tables
                rows = await conn.execute_fetchall(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                table_names = {row["name"] for row in rows}
                assert "campaigns" in table_names
                assert "sessions" in table_names

    @pytest.mark.asyncio
    async def test_get_db_commits_on_exit(self, tmp_path: Path):
        """Writes inside get_db() context must be committed after exit."""
        db_path = tmp_path / "lifecycle_commit.db"
        with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
            await init_db()

            async with get_db() as conn:
                await conn.execute(
                    "INSERT INTO campaigns (name) VALUES (?)", ("Persisted",)
                )

        # Open a fresh connection to verify the row was committed
        with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
            async with get_db() as conn2:
                rows = await conn2.execute_fetchall(
                    "SELECT name FROM campaigns WHERE name = 'Persisted'"
                )
                assert len(rows) == 1
                assert rows[0]["name"] == "Persisted"

    @pytest.mark.asyncio
    async def test_get_db_connection_closed_after_exit(self, tmp_path: Path):
        """After exiting the get_db() context, the underlying connection must be closed."""
        db_path = tmp_path / "lifecycle_close.db"
        with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
            await init_db()

            async with get_db() as conn:
                # Connection should work inside the context
                await conn.execute("SELECT 1")

            # After exiting, the connection's internal _connection should be None
            # (aiosqlite sets this when closed).  We verify by checking the
            # underlying attribute that aiosqlite exposes.
            assert conn._connection is None, (
                "Connection should be closed after exiting get_db() context"
            )

    @pytest.mark.asyncio
    async def test_get_db_enables_foreign_keys(self, tmp_path: Path):
        """get_db() must enable PRAGMA foreign_keys on every connection."""
        db_path = tmp_path / "lifecycle_fk.db"
        with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
            await init_db()

            async with get_db() as conn:
                rows = await conn.execute_fetchall("PRAGMA foreign_keys")
                assert rows[0][0] == 1, "foreign_keys should be ON"

    @pytest.mark.asyncio
    async def test_get_db_sets_row_factory(self, tmp_path: Path):
        """get_db() must set row_factory to aiosqlite.Row for dict-style access."""
        db_path = tmp_path / "lifecycle_row.db"
        with patch("talekeeper.db.connection.get_db_path", return_value=db_path):
            await init_db()

            async with get_db() as conn:
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    ("test_key", "test_value"),
                )
                rows = await conn.execute_fetchall(
                    "SELECT key, value FROM settings WHERE key = 'test_key'"
                )
                assert rows[0]["key"] == "test_key"
                assert rows[0]["value"] == "test_value"


# ===================================================================
# 2.5 -- Default value tests
# ===================================================================


class TestDefaultValues:
    """Verify SQL DEFAULT clauses for campaigns and sessions."""

    @pytest.mark.asyncio
    async def test_campaign_default_language(self, db: aiosqlite.Connection):
        """Campaign language defaults to 'en'."""
        cursor = await db.execute(
            "INSERT INTO campaigns (name) VALUES (?)", ("Lang Test",)
        )
        await db.commit()
        cid = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT language FROM campaigns WHERE id = ?", (cid,)
        )
        assert rows[0]["language"] == "en"

    @pytest.mark.asyncio
    async def test_campaign_default_num_speakers(self, db: aiosqlite.Connection):
        """Campaign num_speakers defaults to 5."""
        cursor = await db.execute(
            "INSERT INTO campaigns (name) VALUES (?)", ("Speakers Test",)
        )
        await db.commit()
        cid = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT num_speakers FROM campaigns WHERE id = ?", (cid,)
        )
        assert rows[0]["num_speakers"] == 5

    @pytest.mark.asyncio
    async def test_campaign_default_description(self, db: aiosqlite.Connection):
        """Campaign description defaults to empty string."""
        cursor = await db.execute(
            "INSERT INTO campaigns (name) VALUES (?)", ("Desc Test",)
        )
        await db.commit()
        cid = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT description FROM campaigns WHERE id = ?", (cid,)
        )
        assert rows[0]["description"] == ""

    @pytest.mark.asyncio
    async def test_campaign_defaults_all_at_once(self, db: aiosqlite.Connection):
        """Inserting a campaign with only 'name' must populate all defaults correctly."""
        cursor = await db.execute(
            "INSERT INTO campaigns (name) VALUES (?)", ("All Defaults",)
        )
        await db.commit()
        cid = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT language, num_speakers, description, created_at, updated_at "
            "FROM campaigns WHERE id = ?",
            (cid,),
        )
        row = rows[0]
        assert row["language"] == "en"
        assert row["num_speakers"] == 5
        assert row["description"] == ""
        assert row["created_at"] is not None, "created_at should be auto-populated"
        assert row["updated_at"] is not None, "updated_at should be auto-populated"

    @pytest.mark.asyncio
    async def test_session_default_status(self, db: aiosqlite.Connection):
        """Session status defaults to 'draft'."""
        cid = await create_campaign(db)
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, ?, ?)",
            (cid, "Status Test", "2025-06-01"),
        )
        await db.commit()
        sid = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT status FROM sessions WHERE id = ?", (sid,)
        )
        assert rows[0]["status"] == "draft"

    @pytest.mark.asyncio
    async def test_session_default_language(self, db: aiosqlite.Connection):
        """Session language defaults to 'en'."""
        cid = await create_campaign(db)
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, ?, ?)",
            (cid, "Lang Test Session", "2025-06-01"),
        )
        await db.commit()
        sid = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT language FROM sessions WHERE id = ?", (sid,)
        )
        assert rows[0]["language"] == "en"

    @pytest.mark.asyncio
    async def test_session_defaults_all_at_once(self, db: aiosqlite.Connection):
        """Inserting a session with minimal fields must populate all defaults correctly."""
        cid = await create_campaign(db)
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, ?, ?)",
            (cid, "All Defaults Session", "2025-06-01"),
        )
        await db.commit()
        sid = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT status, language, audio_path, created_at, updated_at "
            "FROM sessions WHERE id = ?",
            (sid,),
        )
        row = rows[0]
        assert row["status"] == "draft"
        assert row["language"] == "en"
        assert row["audio_path"] is None, "audio_path should default to NULL"
        assert row["created_at"] is not None, "created_at should be auto-populated"
        assert row["updated_at"] is not None, "updated_at should be auto-populated"

    @pytest.mark.asyncio
    async def test_roster_entry_default_is_active(self, db: aiosqlite.Connection):
        """Roster entry is_active defaults to 1 (true)."""
        cid = await create_campaign(db)
        cursor = await db.execute(
            "INSERT INTO roster_entries (campaign_id, player_name, character_name) VALUES (?, ?, ?)",
            (cid, "TestPlayer", "TestCharacter"),
        )
        await db.commit()
        re_id = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT is_active FROM roster_entries WHERE id = ?", (re_id,)
        )
        assert rows[0]["is_active"] == 1

    @pytest.mark.asyncio
    async def test_summary_default_content(self, db: aiosqlite.Connection):
        """Summary content defaults to empty string."""
        cid = await create_campaign(db)
        sid = await create_session(db, cid)
        cursor = await db.execute(
            "INSERT INTO summaries (session_id, type) VALUES (?, ?)",
            (sid, "full"),
        )
        await db.commit()
        summ_id = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT content FROM summaries WHERE id = ?", (summ_id,)
        )
        assert rows[0]["content"] == ""

    @pytest.mark.asyncio
    async def test_voice_signature_default_num_samples(
        self, db: aiosqlite.Connection
    ):
        """Voice signature num_samples defaults to 0."""
        cid = await create_campaign(db)
        cursor = await db.execute(
            "INSERT INTO roster_entries (campaign_id, player_name, character_name) VALUES (?, ?, ?)",
            (cid, "Player", "Char"),
        )
        await db.commit()
        re_id = cursor.lastrowid

        cursor = await db.execute(
            "INSERT INTO voice_signatures (campaign_id, roster_entry_id, embedding) VALUES (?, ?, ?)",
            (cid, re_id, "[0.1, 0.2]"),
        )
        await db.commit()
        vs_id = cursor.lastrowid

        rows = await db.execute_fetchall(
            "SELECT num_samples FROM voice_signatures WHERE id = ?", (vs_id,)
        )
        assert rows[0]["num_samples"] == 0
