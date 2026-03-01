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
