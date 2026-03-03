"""SQLite async connection management via aiosqlite."""

import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncIterator

from talekeeper.paths import get_db_path

_connection: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Initialize the database: create tables and run migrations."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await _apply_schema(db)
        await db.commit()


async def _apply_schema(db: aiosqlite.Connection) -> None:
    """Create all tables if they don't exist."""
    await db.executescript(_SCHEMA)
    await _migrate_add_language_columns(db)
    await _migrate_add_num_speakers_column(db)
    await _migrate_add_voice_signatures_table(db)
    await _migrate_add_session_images_table(db)
    await _migrate_add_roster_description(db)
    await _migrate_add_session_number_column(db)
    await _migrate_add_session_start_number_column(db)
    await _migrate_backfill_session_numbers(db)
    await _migrate_invalidate_voice_signatures(db)
    await _migrate_add_similarity_threshold(db)
    await _migrate_add_mlx_settings(db)


async def _migrate_add_session_number_column(db: aiosqlite.Connection) -> None:
    """Add session_number column to sessions if missing."""
    cols = await db.execute_fetchall("PRAGMA table_info(sessions)")
    col_names = [c["name"] for c in cols]
    if "session_number" not in col_names:
        await db.execute(
            "ALTER TABLE sessions ADD COLUMN session_number INTEGER"
        )


async def _migrate_backfill_session_numbers(db: aiosqlite.Connection) -> None:
    """Backfill session_number for existing sessions and update generic names."""
    # Check if any sessions lack a session_number
    rows = await db.execute_fetchall(
        "SELECT id FROM sessions WHERE session_number IS NULL LIMIT 1"
    )
    if not rows:
        return

    # Get all campaigns
    campaigns = await db.execute_fetchall("SELECT id, session_start_number FROM campaigns")
    for campaign in campaigns:
        campaign_id = campaign["id"]
        start_number = campaign["session_start_number"]

        # Get sessions for this campaign ordered by creation
        sessions = await db.execute_fetchall(
            "SELECT id, name FROM sessions WHERE campaign_id = ? AND session_number IS NULL "
            "ORDER BY created_at ASC, id ASC",
            (campaign_id,),
        )
        for i, session in enumerate(sessions):
            num = start_number + i
            await db.execute(
                "UPDATE sessions SET session_number = ? WHERE id = ?",
                (num, session["id"]),
            )
            # Update generic names (empty or default-looking) to "Session N"
            name = session["name"] or ""
            if not name.strip() or name.strip().lower().startswith("session"):
                await db.execute(
                    "UPDATE sessions SET name = ? WHERE id = ?",
                    (f"Session {num}", session["id"]),
                )


async def _migrate_add_session_start_number_column(db: aiosqlite.Connection) -> None:
    """Add session_start_number column to campaigns if missing."""
    cols = await db.execute_fetchall("PRAGMA table_info(campaigns)")
    col_names = [c["name"] for c in cols]
    if "session_start_number" not in col_names:
        await db.execute(
            "ALTER TABLE campaigns ADD COLUMN session_start_number INTEGER NOT NULL DEFAULT 0"
        )


async def _migrate_add_session_images_table(db: aiosqlite.Connection) -> None:
    """Create session_images table if it doesn't exist (for pre-existing databases)."""
    tables = await db.execute_fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='session_images'"
    )
    if not tables:
        await db.execute("""
            CREATE TABLE session_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                prompt TEXT NOT NULL,
                scene_description TEXT,
                model_used TEXT,
                generated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)


async def _migrate_add_language_columns(db: aiosqlite.Connection) -> None:
    """Add language column to campaigns and sessions if missing."""
    for table in ("campaigns", "sessions"):
        cols = await db.execute_fetchall(f"PRAGMA table_info({table})")
        col_names = [c["name"] for c in cols]
        if "language" not in col_names:
            await db.execute(
                f"ALTER TABLE {table} ADD COLUMN language TEXT NOT NULL DEFAULT 'en'"
            )


async def _migrate_add_num_speakers_column(db: aiosqlite.Connection) -> None:
    """Add num_speakers column to campaigns if missing."""
    cols = await db.execute_fetchall("PRAGMA table_info(campaigns)")
    col_names = [c["name"] for c in cols]
    if "num_speakers" not in col_names:
        await db.execute(
            "ALTER TABLE campaigns ADD COLUMN num_speakers INTEGER NOT NULL DEFAULT 5"
        )


async def _migrate_add_voice_signatures_table(db: aiosqlite.Connection) -> None:
    """Create voice_signatures table if it doesn't exist (for pre-existing databases)."""
    tables = await db.execute_fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='voice_signatures'"
    )
    if not tables:
        await db.execute("""
            CREATE TABLE voice_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
                roster_entry_id INTEGER NOT NULL REFERENCES roster_entries(id) ON DELETE CASCADE,
                embedding TEXT NOT NULL,
                source_session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
                num_samples INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)


async def _migrate_add_roster_description(db: aiosqlite.Connection) -> None:
    """Add description, sheet_url, and sheet_data columns to roster_entries if missing."""
    cols = await db.execute_fetchall("PRAGMA table_info(roster_entries)")
    col_names = [c["name"] for c in cols]
    if "description" not in col_names:
        await db.execute(
            "ALTER TABLE roster_entries ADD COLUMN description TEXT DEFAULT ''"
        )
    if "sheet_url" not in col_names:
        await db.execute(
            "ALTER TABLE roster_entries ADD COLUMN sheet_url TEXT DEFAULT ''"
        )
    if "sheet_data" not in col_names:
        await db.execute(
            "ALTER TABLE roster_entries ADD COLUMN sheet_data TEXT DEFAULT ''"
        )


async def _migrate_invalidate_voice_signatures(db: aiosqlite.Connection) -> None:
    """Invalidate all voice signatures — pyannote embeddings are incompatible with speechbrain."""
    # Use a settings flag to ensure this only runs once
    row = await db.execute_fetchall(
        "SELECT value FROM settings WHERE key = '_migration_voice_sigs_invalidated'"
    )
    if not row:
        await db.execute("DELETE FROM voice_signatures")
        await db.execute(
            "INSERT INTO settings (key, value) VALUES ('_migration_voice_sigs_invalidated', '1')"
        )


async def _migrate_add_similarity_threshold(db: aiosqlite.Connection) -> None:
    """Add similarity_threshold column to campaigns for configurable voice matching."""
    cols = await db.execute_fetchall("PRAGMA table_info(campaigns)")
    col_names = [c["name"] for c in cols]
    if "similarity_threshold" not in col_names:
        await db.execute(
            "ALTER TABLE campaigns ADD COLUMN similarity_threshold REAL DEFAULT 0.65"
        )


async def _migrate_add_mlx_settings(db: aiosqlite.Connection) -> None:
    """Insert default settings rows for MLX pipeline configuration."""
    defaults = {
        "hf_token": "",
        "whisper_batch_size": "",
        "image_steps": "4",
        "image_guidance_scale": "0",
    }
    for key, value in defaults.items():
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )


@asynccontextmanager
async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Yield an async database connection."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
        finally:
            await db.commit()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    language TEXT NOT NULL DEFAULT 'en',
    num_speakers INTEGER NOT NULL DEFAULT 5,
    session_start_number INTEGER NOT NULL DEFAULT 0,
    similarity_threshold REAL DEFAULT 0.65,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    language TEXT NOT NULL DEFAULT 'en',
    session_number INTEGER,
    audio_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    diarization_label TEXT NOT NULL,
    player_name TEXT,
    character_name TEXT
);

CREATE TABLE IF NOT EXISTS transcript_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    speaker_id INTEGER REFERENCES speakers(id) ON DELETE SET NULL,
    text TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    speaker_id INTEGER REFERENCES speakers(id) ON DELETE SET NULL,
    content TEXT NOT NULL DEFAULT '',
    model_used TEXT,
    generated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS roster_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    character_name TEXT NOT NULL,
    description TEXT DEFAULT '',
    sheet_url TEXT DEFAULT '',
    sheet_data TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS voice_signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    roster_entry_id INTEGER NOT NULL REFERENCES roster_entries(id) ON DELETE CASCADE,
    embedding TEXT NOT NULL,
    source_session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    num_samples INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS session_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    prompt TEXT NOT NULL,
    scene_description TEXT,
    model_used TEXT,
    generated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""
