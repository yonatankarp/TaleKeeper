## ADDED Requirements

### Requirement: Schema creation tests
The test suite SHALL verify that `init_db()` creates all expected tables with correct columns.

#### Scenario: All tables exist after init_db
- **WHEN** `init_db()` is called on a fresh database
- **THEN** all 8 tables exist: `campaigns`, `sessions`, `speakers`, `transcript_segments`, `summaries`, `roster_entries`, `voice_signatures`, `session_images`, `settings`

#### Scenario: Table columns match schema
- **WHEN** `PRAGMA table_info(<table>)` is run for each table after init_db
- **THEN** the columns match the expected names and types defined in the DDL

### Requirement: Migration idempotency tests
The test suite SHALL verify that running `init_db()` multiple times does not fail or corrupt data.

#### Scenario: Double init_db succeeds
- **WHEN** `init_db()` is called twice on the same database
- **THEN** no error is raised and the schema is intact

#### Scenario: Migrations are idempotent
- **WHEN** each migration function (`_migrate_add_language_columns`, `_migrate_add_num_speakers_column`, `_migrate_add_voice_signatures_table`, `_migrate_add_session_images_table`) is called on an already-migrated database
- **THEN** no error is raised and existing data is preserved

### Requirement: Foreign key constraint tests
The test suite SHALL verify that foreign key cascades work as expected.

#### Scenario: Deleting a campaign cascades to sessions
- **WHEN** a campaign with sessions is deleted
- **THEN** all sessions belonging to that campaign are also deleted

#### Scenario: Deleting a session cascades to speakers and segments
- **WHEN** a session with speakers and transcript_segments is deleted
- **THEN** all speakers and segments for that session are also deleted

#### Scenario: Deleting a speaker sets segment speaker_id to NULL
- **WHEN** a speaker with associated transcript_segments is deleted
- **THEN** the segments remain but their speaker_id is set to NULL

### Requirement: Connection lifecycle tests
The test suite SHALL verify that the `get_db()` context manager properly manages connections.

#### Scenario: get_db yields a usable connection
- **WHEN** `async with get_db() as db` is used
- **THEN** the connection can execute queries

#### Scenario: get_db connection is closed after context exit
- **WHEN** the `get_db()` context manager exits
- **THEN** the connection is properly closed (no leaked connections)

### Requirement: Default value tests
The test suite SHALL verify that table defaults are applied correctly on insert.

#### Scenario: Campaign defaults
- **WHEN** a campaign is inserted with only a name
- **THEN** `language` defaults to `"en"`, `num_speakers` defaults to `5`, `description` defaults to `""`, and `created_at`/`updated_at` are set

#### Scenario: Session defaults
- **WHEN** a session is inserted with only campaign_id, name, and date
- **THEN** `status` defaults to `"draft"` and `language` defaults to `"en"`
