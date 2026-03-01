## Why

The LLM integration is currently hardcoded to Ollama's proprietary REST API (`/api/generate`, `/api/tags`). This limits users to running Ollama locally and prevents use of cloud providers (OpenAI, Together.ai, Groq), local alternatives (LM Studio, vLLM, llama.cpp), or any other service exposing an OpenAI-compatible `/v1/chat/completions` endpoint. Since Ollama itself supports the OpenAI-compatible API at `/v1/`, we can unify all LLM access under a single code path.

## What Changes

- **BREAKING**: Remove `ollama.py` service and its proprietary API calls (`/api/generate`, `/api/tags`)
- Replace with a generic LLM client using the `openai` Python SDK, targeting `/v1/chat/completions`
- Add `openai` Python package as a new dependency
- Update Settings UI: replace "Summary Generation (Ollama)" section with "LLM Provider" section containing base URL, optional API key, and model name fields
- Update the `/api/ollama/status` endpoint to a generic `/api/llm/status` health check
- Update `summarization.py` to call the new generic LLM client instead of `ollama.generate()`
- Update `summaries.py` router to use generic health/model checks instead of Ollama-specific ones
- Update `docker-compose.yml` environment variables: replace `OLLAMA_URL` with generic `LLM_BASE_URL` defaulting to Ollama's OpenAI-compatible endpoint (`http://ollama:11434/v1`)
- Keep Ollama as the default bundled provider in docker-compose for zero-config local experience

## Capabilities

### New Capabilities
- `llm-provider`: Generic OpenAI-compatible LLM client configuration covering base URL, API key, model selection, health checking, and text generation via the `openai` Python SDK

### Modified Capabilities
- `summary-generation`: Requirements change from Ollama-specific connectivity (proprietary `/api/generate` and `/api/tags` endpoints) to generic OpenAI-compatible LLM provider (base URL + API key + model). Error messages and health check behavior must reflect the provider-agnostic approach.

## Impact

- **Backend services**: `ollama.py` removed, new `llm_client.py` created; `summarization.py` updated to use new client
- **API routes**: `/api/ollama/status` replaced with `/api/llm/status`; summary generation endpoints use generic health checks
- **Frontend**: Settings page LLM section updated (base URL, API key, model fields replace Ollama-specific UI)
- **Dependencies**: `openai` Python package added to `pyproject.toml` / `requirements.txt`
- **Docker**: `OLLAMA_URL` env var replaced with `LLM_BASE_URL`; Ollama service remains as default provider
- **Database**: `settings` table gains `llm_base_url` and `llm_api_key` keys (alongside existing `ollama_model` renamed to `llm_model`)
