# LLM Provider

## MODIFIED Requirements

### Requirement: Text generation via Chat Completions
The system SHALL generate text using the OpenAI Chat Completions API (`/v1/chat/completions`). The system MUST map system prompts to `{role: "system"}` messages and user prompts to `{role: "user"}` messages. The `openai` Python SDK MUST be used as the HTTP client with the configured `base_url` and `api_key`. When the provider is detected as Ollama, the system SHALL include `extra_body` parameters for provider-specific optimizations (e.g., `num_ctx` for context window size).

#### Scenario: Generate with system and user prompt
- **WHEN** the system requests text generation with a system prompt and user prompt
- **THEN** the system sends a chat completion request with `messages: [{role: "system", content: <system>}, {role: "user", content: <prompt>}]` and returns the assistant's response content

#### Scenario: Generate without system prompt
- **WHEN** the system requests text generation with only a user prompt (no system prompt)
- **THEN** the system sends a chat completion request with `messages: [{role: "user", content: <prompt>}]` and returns the assistant's response content

#### Scenario: Ollama-specific parameters injected
- **WHEN** the system requests text generation and the provider is detected as Ollama
- **THEN** the request includes `extra_body={"options": {"num_ctx": 32768}}` to override Ollama's default 4k context window

#### Scenario: Non-Ollama provider unaffected
- **WHEN** the system requests text generation and the provider is not Ollama
- **THEN** no extra_body parameters are injected and the request uses standard OpenAI Chat Completions format

## ADDED Requirements

### Requirement: Ollama endpoint auto-detection
The system SHALL automatically detect whether the configured LLM provider is an Ollama instance by probing the native Ollama API endpoint. The detection result SHALL be cached per base_url for the lifetime of the process. Detection MUST NOT affect non-Ollama providers.

#### Scenario: Ollama detected via API probe
- **WHEN** the configured base URL is `http://localhost:11434/v1` and the endpoint at `http://localhost:11434/api/tags` returns a valid JSON response with a `models` array
- **THEN** the system identifies the provider as Ollama and enables Ollama-specific optimizations

#### Scenario: Non-Ollama provider not misidentified
- **WHEN** the configured base URL points to OpenAI, LM Studio, or another provider that does not respond to `/api/tags`
- **THEN** the system identifies the provider as non-Ollama and uses standard OpenAI-compatible behavior

#### Scenario: Detection result is cached
- **WHEN** Ollama detection is performed for a base URL
- **THEN** the result is cached and subsequent requests to the same base URL do not re-probe the endpoint

### Requirement: Ollama memory management
The system SHALL provide a function to force-unload the active model from Ollama's memory by sending a request with `keep_alive: "0"` to the Ollama native API. This function SHALL be callable by the resource orchestration module after summary generation completes.

#### Scenario: Model unloaded from Ollama
- **WHEN** the resource orchestration module calls the Ollama unload function
- **THEN** the system sends `POST /api/generate` with `{"model": "<configured-model>", "keep_alive": "0"}` to the Ollama endpoint, causing Ollama to immediately evict the model from memory

#### Scenario: Unload skipped for non-Ollama
- **WHEN** the unload function is called but the provider is not Ollama
- **THEN** the function returns without making any requests
