## Context

TaleKeeper currently uses Ollama's proprietary REST API (`/api/generate`, `/api/tags`) for all LLM interactions (summary generation). The integration is spread across:

- `src/talekeeper/services/ollama.py` — HTTP client for Ollama's proprietary endpoints
- `src/talekeeper/services/summarization.py` — calls `ollama.generate()` for summaries
- `src/talekeeper/services/setup.py` — Ollama health check on first run
- `src/talekeeper/routers/summaries.py` — `/api/ollama/status` endpoint + Ollama-specific model checks before generation
- `frontend/src/routes/SettingsPage.svelte` — "Summary Generation (Ollama)" settings section
- `frontend/src/components/SetupWizard.svelte` — Ollama status and install instructions
- `docker-compose.yml` — `OLLAMA_URL` env var and Ollama service

The OpenAI Chat Completions API (`/v1/chat/completions`) has become the de facto standard. Ollama, LM Studio, vLLM, llama.cpp, and all major cloud providers support it. By switching to this standard, we support all providers with one code path.

## Goals / Non-Goals

**Goals:**
- Replace Ollama-specific client with a generic OpenAI-compatible client using the `openai` Python SDK
- Allow users to configure any OpenAI-compatible LLM provider via base URL + API key + model name
- Keep Ollama as the default zero-config experience (via its `/v1/` endpoint)
- Update all UI to reflect the provider-agnostic approach

**Non-Goals:**
- Provider-specific presets or auto-discovery (users enter the URL manually)
- Streaming responses (current non-streaming approach is kept)
- Model listing/browsing from the provider (user types the model name)
- Switching the chat API format (we use `/v1/chat/completions` only, not `/v1/completions`)

## Decisions

### Decision 1: Use the `openai` Python SDK as the HTTP client

**Choice:** Use `openai` package with custom `base_url` rather than raw `httpx`.

**Alternatives considered:**
- **Raw httpx**: Consistent with current codebase style, no new dependency. But requires manual handling of auth headers, error parsing, response typing. More code to maintain.
- **litellm**: Supports 100+ providers with model routing. Overkill for our use case, large dependency, adds complexity.

**Rationale:** The `openai` SDK is lightweight, well-maintained, handles auth/retries/errors, and is the canonical client for the API format we're targeting. Setting `base_url` to any compatible endpoint is a first-class feature.

### Decision 2: Unify on `/v1/chat/completions` (not `/v1/completions`)

**Choice:** Use the Chat Completions endpoint exclusively, mapping the current `system` + `prompt` pattern to `messages: [{role: "system", ...}, {role: "user", ...}]`.

**Rationale:** The legacy completions endpoint is deprecated by OpenAI and not supported by all compatible providers. Chat completions is universally supported.

### Decision 3: Configuration via settings table (not just env vars)

**Choice:** Store `llm_base_url`, `llm_api_key`, and `llm_model` in the settings table, with env vars (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) as fallback defaults.

**Rationale:** Users configure settings through the UI. Env vars provide defaults for Docker deployments. Settings table takes precedence so users can override without restarting the container.

### Decision 4: Health check via a lightweight completions call

**Choice:** Replace the Ollama-specific `/api/tags` health check with a minimal chat completion request (e.g., `messages: [{role: "user", content: "hi"}]`, `max_tokens: 1`).

**Alternatives considered:**
- **GET on base URL**: Not standardized across providers. Ollama returns HTML, OpenAI returns a JSON object, others vary.
- **List models endpoint** (`/v1/models`): Not supported by all providers (some local servers skip it).

**Rationale:** A tiny completion request is the most reliable way to verify the full pipeline works (URL reachable, auth valid, model exists). The cost is negligible (1 token).

### Decision 5: New `llm_client.py` replaces `ollama.py`

**Choice:** Create `src/talekeeper/services/llm_client.py` exposing:
- `async def health_check(base_url, api_key, model) -> dict` — verify connectivity
- `async def generate(base_url, api_key, model, prompt, system) -> str` — generate text

The functions accept explicit config params. Callers load settings and pass them in.

**Rationale:** Keeps the service stateless and testable. The same interface shape as the current `ollama.py` minimizes changes in `summarization.py`.

### Decision 6: API endpoint rename

**Choice:** Replace `/api/ollama/status` with `/api/llm/status`.

**Rationale:** Reflects the provider-agnostic nature. The frontend already calls this URL from a single place (SettingsPage + SetupWizard), so the change surface is small.

## Risks / Trade-offs

- **[Breaking change for existing users]** Users with `OLLAMA_URL` in their environment will need to switch to `LLM_BASE_URL`. → Mitigation: Fall back to `OLLAMA_URL` if `LLM_BASE_URL` is not set, with a deprecation warning in logs.
- **[API key stored in settings DB]** The API key for cloud providers will be stored in plaintext in SQLite. → Mitigation: Acceptable for a local-first self-hosted app. Document that users should secure the data directory. Environment variable fallback avoids storing the key in DB if preferred.
- **[Health check cost with cloud providers]** The 1-token completion health check costs a tiny amount when using paid APIs. → Mitigation: Only triggered on explicit "Test Connection" button click, not automatically.
- **[No model validation]** Without a model list endpoint, we can't verify the model name before attempting generation. → Mitigation: Clear error messages from the SDK on invalid model names are sufficient. The health check will catch this.
