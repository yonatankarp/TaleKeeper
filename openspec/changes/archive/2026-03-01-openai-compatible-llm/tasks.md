## 1. Dependencies and Configuration

- [x] 1.1 Add `openai` Python package to project dependencies
- [x] 1.2 Update `docker-compose.yml`: replace `OLLAMA_URL` env var with `LLM_BASE_URL` defaulting to `http://ollama:11434/v1`

## 2. LLM Client Service

- [x] 2.1 Create `src/talekeeper/services/llm_client.py` with config resolution function that reads settings table, falls back to env vars (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`), supports legacy `OLLAMA_URL` with `/v1` append and deprecation warning, and applies defaults (`http://localhost:11434/v1`, no key, `llama3.1:8b`)
- [x] 2.2 Implement `async def health_check(base_url, api_key, model) -> dict` using `openai` SDK — sends minimal chat completion (`max_tokens: 1`), returns `{"status": "ok"}` on success or `{"status": "error", "message": ...}` with specific messages for unreachable, auth failure, and model not found
- [x] 2.3 Implement `async def generate(base_url, api_key, model, prompt, system="") -> str` using `openai` SDK — maps system/user prompts to chat messages, returns assistant response content
- [x] 2.4 Delete `src/talekeeper/services/ollama.py`

## 3. Summarization Service Update

- [x] 3.1 Update `src/talekeeper/services/summarization.py`: replace `ollama.generate()` calls with `llm_client.generate()`, passing config params (base_url, api_key, model) through function signatures

## 4. API Routes Update

- [x] 4.1 Update `src/talekeeper/routers/summaries.py`: replace `/api/ollama/status` with `/api/llm/status` endpoint that loads LLM config from settings and calls `llm_client.health_check()`
- [x] 4.2 Update `generate_summary` endpoint: replace Ollama-specific health check and model availability check with generic `llm_client.health_check()`, update error messages to be provider-agnostic
- [x] 4.3 Update `generate_summary` and `generate_pov_summary` calls to pass LLM config (base_url, api_key, model) loaded from settings

## 5. Setup Service Update

- [x] 5.1 Update `src/talekeeper/services/setup.py`: replace `ollama.health_check()` with `llm_client.health_check()` using resolved config, rename response keys from `ollama_running`/`ollama_models` to `llm_connected`

## 6. Frontend Settings Page

- [x] 6.1 Update `frontend/src/routes/SettingsPage.svelte`: replace "Summary Generation (Ollama)" section with "LLM Provider" section containing base URL input, API key password input, and model name input
- [x] 6.2 Update settings load/save to use `llm_base_url`, `llm_api_key`, `llm_model` keys (with defaults)
- [x] 6.3 Update "Test Connection" button to call `/api/llm/status` instead of `/api/ollama/status`

## 7. Frontend Setup Wizard

- [x] 7.1 Update `frontend/src/components/SetupWizard.svelte`: replace Ollama-specific status display and instructions with provider-agnostic LLM status (connected/not connected), remove `ollama serve`/`ollama pull` commands, suggest checking Settings if not connected

## 8. App Wiring

- [x] 8.1 Update `src/talekeeper/app.py` if it registers the Ollama status route separately — ensure `/api/llm/status` is registered and `/api/ollama/status` is removed
