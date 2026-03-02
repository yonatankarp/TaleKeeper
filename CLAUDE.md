# TaleKeeper

D&D session recording, transcription, and summarization app. FastAPI backend + Svelte 5 frontend SPA.

## Environment

- **Python**: 3.14 (use project venv, NEVER global Python)
- **Node**: 22+
- **Venv**: `.venv/bin/python` — always use this for running Python commands
- **Database**: SQLite (aiosqlite, WAL mode) at `data/db/talekeeper.db`
- **System deps**: ffmpeg, Pango, Cairo
- **Optional**: Ollama for local LLM summaries and image generation

## Commands

### Backend
- Run server: `.venv/bin/python -m talekeeper serve --reload --no-browser`
- Run all tests: `.venv/bin/python -m pytest`
- Run unit tests: `.venv/bin/python -m pytest tests/unit`
- Run integration tests: `.venv/bin/python -m pytest tests/integration`
- Run tests with coverage: `.venv/bin/python -m pytest -v --cov`
- Install deps: `.venv/bin/pip install -e ".[dev]"`

### Frontend
- Dev server: `cd frontend && npm run dev`
- Build: `cd frontend && npm run build`
- Type check: `cd frontend && npm run check`
- Run tests: `cd frontend && npm run test`

## Architecture

### Backend (`src/talekeeper/`)
- `app.py` — FastAPI app setup, lifespan, CORS, static serving
- `routers/` — Feature-based API endpoints (campaigns, sessions, recording, etc.)
- `services/` — Business logic and ML pipelines (transcription, diarization, summarization, image generation)
- `db/connection.py` — aiosqlite connection management, schema, migrations
- `paths.py` — Centralized path resolution

### Frontend (`frontend/src/`)
- `routes/` — Page-level Svelte components
- `components/` — Reusable UI components
- `lib/` — Shared utilities (api client, router, theme, wizard)

### Key patterns
- Async throughout: all route handlers and DB operations are `async def`
- Streaming: WebSocket for live recording, SSE for long-running ops (image gen, re-diarization)
- Feature-based organization: routers, services, and tests grouped by feature
- DB access via context manager: `async with get_db() as db`

## Code Conventions

### Python
- Snake_case for variables, functions, files; PascalCase for classes
- Full type annotations on all function signatures
- Relative imports within `talekeeper` package, absolute for external
- Pydantic models for request/response validation
- HTTPException for API errors with status codes
- Prefix internal/private functions with `_`

### Frontend (Svelte/TypeScript)
- Svelte 5 runes: `$state`, `$derived`, `$effect` (NOT legacy `$:` reactive statements)
- PascalCase for `.svelte` component files
- API calls through `lib/api.ts` wrapper (`api.get`, `api.post`, `api.put`, `api.del`)
- Scoped CSS within `<style>` blocks
- TypeScript strict mode

## Testing

- Framework: pytest with asyncio (auto mode)
- Unit tests: `tests/unit/` — mock external dependencies
- Integration tests: `tests/integration/` — real SQLite DB, httpx AsyncClient
- Shared fixtures in `tests/conftest.py`: `client`, `db`, helpers (`create_campaign`, `create_session`, etc.)
- Test naming: `test_<feature_description>()`
- DB isolation: each test gets a fresh temp database via `_tmp_db` fixture
- Frontend tests: Vitest + @testing-library/svelte (jsdom)

## Git Conventions

- Commit format: `<type>: <description>` or `<type>(<scope>): <description>`
- Types: `feat`, `fix`, `refactor`, `chore`, `docs`
- Lowercase, concise descriptions

## Rules

- **ALWAYS use `.venv/bin/python` or `.venv/bin/pip`** — never install to or run from global Python
- Run tests before claiming work is complete
- Prefer editing existing files over creating new ones
- Keep routers thin — business logic belongs in `services/`
- Use `async with get_db() as db` for all database operations
- Frontend build output goes to `src/talekeeper/static/` (gitignored, do not commit)
- **Always use OpenSpec** for planning and tracking changes — never use `docs/plans/` directly
- **Archiving an OpenSpec change must commit and push** — after archiving, automatically commit all changes and push to remote
