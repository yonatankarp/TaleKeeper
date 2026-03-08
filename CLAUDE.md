# TaleKeeper

D&D session recording, transcription, and summarization app. FastAPI backend + Svelte 5 frontend SPA.

## Environment

- **Python**: 3.12 (use project venv, NEVER global Python)
- **Node**: 22+
- **Venv**: `venv/bin/python` — always use this for running Python commands
- **Database**: SQLite (aiosqlite, WAL mode) at `data/db/talekeeper.db`
- **System deps**: ffmpeg, Pango, Cairo
- **Optional**: Ollama for local LLM summaries and image generation

## Commands

### Make targets (primary interface)
- `make help` — show all available targets
- `make install` — install backend and frontend dependencies
- `make serve` — build frontend and start server (`ARGS="--reload"` to pass flags)
- `make dev` — start backend in reload mode (no frontend build)
- `make build` — build the frontend
- `make test` — run all tests (backend + frontend)
- `make test-backend` — run backend tests (pytest)
- `make test-frontend` — run frontend tests (vitest)
- `make coverage` — run backend tests with coverage
- `make check` — run frontend type checking (svelte-check)
- `make docs` — build and serve documentation locally
- `make docs-build` — build documentation with zensical
- `make screenshots` — capture screenshots for the user guide
- `make clean` — remove build artifacts

### Direct commands (secondary reference)
- Run server: `venv/bin/python -m talekeeper serve --reload --no-browser`
- Run all tests: `venv/bin/python -m pytest`
- Run unit tests: `venv/bin/python -m pytest tests/unit`
- Run integration tests: `venv/bin/python -m pytest tests/integration`
- Run tests with coverage: `venv/bin/python -m pytest -v --cov`
- Install deps: `venv/bin/pip install -e ".[dev]"`
- Frontend dev server: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Frontend type check: `cd frontend && npm run check`
- Frontend tests: `cd frontend && npm run test`

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

- **ALWAYS use `venv/bin/python` or `venv/bin/pip`** — never install to or run from global Python
- Run tests before claiming work is complete
- Prefer editing existing files over creating new ones
- Keep routers thin — business logic belongs in `services/`
- Use `async with get_db() as db` for all database operations
- Frontend build output goes to `src/talekeeper/static/` (gitignored, do not commit)
- **Always use OpenSpec** for planning and tracking changes — never use `docs/plans/` directly
- **Archiving an OpenSpec change must commit and push** — after archiving, automatically commit all changes and push to remote
- **Always use a git worktree when developing a new spec** — work in an isolated worktree so multiple agents can work on different specs in parallel without conflicts
- **Document new features in `docs/guide/`** — when adding or changing user-facing functionality, update the relevant guide pages. Write from the **user's perspective** (a D&D player, not a developer): describe what they see and do, not how it's implemented. Avoid internal terms like API endpoints, library names, model architectures, or code concepts. Add new features to the hidden features table in `tips-and-tricks.md`. Run `make docs-build` to verify.
