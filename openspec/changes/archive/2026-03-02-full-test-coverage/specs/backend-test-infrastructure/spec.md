## ADDED Requirements

### Requirement: Pytest configuration in pyproject.toml
The project SHALL include a `[tool.pytest.ini_options]` section in `pyproject.toml` that configures asyncio mode as `auto`, sets the test paths to `tests/`, and enables coverage reporting for the `talekeeper` package.

#### Scenario: Running pytest discovers all backend tests
- **WHEN** a developer runs `pytest` from the project root
- **THEN** pytest discovers and runs all test files under `tests/`

#### Scenario: Coverage report is generated
- **WHEN** a developer runs `pytest --cov`
- **THEN** a coverage report is printed showing line coverage for every module under `src/talekeeper/`

### Requirement: Dev dependency group
The project SHALL declare test dependencies in a `[project.optional-dependencies]` section under a `dev` key, including: `pytest`, `pytest-asyncio`, `pytest-cov`, and `httpx`.

#### Scenario: Installing dev dependencies
- **WHEN** a developer runs `pip install -e ".[dev]"`
- **THEN** all test dependencies are installed and `pytest` is available on the PATH

### Requirement: Campaign fixture factory
The test suite SHALL provide a shared async helper `create_campaign()` in `tests/conftest.py` that inserts a campaign row with configurable name, description, language, and num_speakers, returning the campaign ID.

#### Scenario: Creating a campaign with defaults
- **WHEN** a test calls `await create_campaign(db)` without arguments
- **THEN** a campaign row is inserted with sensible defaults and the campaign ID is returned

#### Scenario: Creating a campaign with custom values
- **WHEN** a test calls `await create_campaign(db, name="My Campaign", language="de")`
- **THEN** a campaign row is inserted with the specified name and language

### Requirement: Session fixture factory
The test suite SHALL provide a shared async helper `create_session()` in `tests/conftest.py` that inserts a session row for a given campaign ID with configurable name, date, status, and language, returning the session ID.

#### Scenario: Creating a session for a campaign
- **WHEN** a test calls `await create_session(db, campaign_id=1)`
- **THEN** a session row is inserted linked to campaign 1 and the session ID is returned

### Requirement: Speaker fixture factory
The test suite SHALL provide a shared async helper `create_speaker()` in `tests/conftest.py` that inserts a speaker row for a given session ID with configurable diarization_label, player_name, and character_name, returning the speaker ID.

#### Scenario: Creating a speaker for a session
- **WHEN** a test calls `await create_speaker(db, session_id=1, player_name="Alice")`
- **THEN** a speaker row is inserted linked to session 1 with player_name "Alice"

### Requirement: Segment fixture factory
The test suite SHALL provide a shared async helper `create_segment()` in `tests/conftest.py` that inserts a transcript_segment row for a given session ID and speaker ID with configurable text, start_time, and end_time, returning the segment ID.

#### Scenario: Creating a transcript segment
- **WHEN** a test calls `await create_segment(db, session_id=1, speaker_id=2, text="Hello")`
- **THEN** a transcript_segment row is inserted with the given values

### Requirement: Database fixture provides connection
The test suite SHALL provide a `db` fixture that yields an initialized aiosqlite connection to a temporary database, usable by factory functions.

#### Scenario: Using the db fixture
- **WHEN** a test declares a `db` parameter
- **THEN** it receives an aiosqlite connection with all tables created, isolated per test
