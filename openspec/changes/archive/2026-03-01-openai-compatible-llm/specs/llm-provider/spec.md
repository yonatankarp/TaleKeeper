## ADDED Requirements

### Requirement: LLM provider configuration
The system SHALL allow the DM to configure an LLM provider via three settings: base URL, API key, and model name. The base URL MUST point to any OpenAI-compatible `/v1/chat/completions` endpoint. The API key MUST be optional (local providers like Ollama do not require one). The system MUST default to `http://localhost:11434/v1` (Ollama's OpenAI-compatible endpoint) with model `llama3.1:8b` when no configuration is provided.

#### Scenario: Default configuration
- **WHEN** the DM has not configured any LLM provider settings
- **THEN** the system uses base URL `http://localhost:11434/v1`, no API key, and model `llama3.1:8b`

#### Scenario: Configure cloud provider
- **WHEN** the DM enters base URL `https://api.openai.com/v1`, an API key, and model `gpt-4o-mini` in settings
- **THEN** subsequent LLM operations use the configured cloud provider

#### Scenario: Configure local alternative
- **WHEN** the DM enters base URL `http://localhost:1234/v1` (LM Studio) with no API key and model `local-model`
- **THEN** subsequent LLM operations use the local alternative provider

### Requirement: Settings precedence
The system SHALL resolve LLM configuration with settings table values taking precedence over environment variables. Environment variables (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) MUST serve as fallback defaults. The system SHALL also accept `OLLAMA_URL` as a fallback for `LLM_BASE_URL` (appending `/v1` if needed) and log a deprecation warning when it is used.

#### Scenario: Settings override environment
- **WHEN** `LLM_BASE_URL` env var is set to `http://env-host:11434/v1` and the settings table has `llm_base_url` set to `http://settings-host:11434/v1`
- **THEN** the system uses `http://settings-host:11434/v1`

#### Scenario: Environment variable fallback
- **WHEN** no `llm_base_url` is stored in the settings table and `LLM_BASE_URL` env var is set to `http://env-host:11434/v1`
- **THEN** the system uses `http://env-host:11434/v1`

#### Scenario: Legacy OLLAMA_URL fallback
- **WHEN** neither `LLM_BASE_URL` nor `llm_base_url` in settings is configured, but `OLLAMA_URL` is set to `http://ollama:11434`
- **THEN** the system uses `http://ollama:11434/v1` as the base URL and logs a deprecation warning recommending `LLM_BASE_URL`

### Requirement: LLM health check
The system SHALL provide a health check endpoint at `/api/llm/status` that verifies connectivity to the configured LLM provider. The health check MUST send a minimal chat completion request (`max_tokens: 1`) to confirm the full pipeline works (URL reachable, auth valid, model exists). The health check MUST only be triggered by explicit user action (Test Connection button), never automatically.

#### Scenario: Provider reachable and model valid
- **WHEN** the DM clicks "Test Connection" and the configured provider responds successfully
- **THEN** the system displays a success status indicating the LLM provider is connected

#### Scenario: Provider unreachable
- **WHEN** the DM clicks "Test Connection" and the configured base URL is not reachable
- **THEN** the system displays an error indicating the LLM provider cannot be reached at the configured URL

#### Scenario: Authentication failure
- **WHEN** the DM clicks "Test Connection" and the API key is invalid or missing for a provider that requires one
- **THEN** the system displays an error indicating authentication failed

#### Scenario: Model not found
- **WHEN** the DM clicks "Test Connection" and the configured model does not exist on the provider
- **THEN** the system displays an error indicating the model was not found

### Requirement: Text generation via Chat Completions
The system SHALL generate text using the OpenAI Chat Completions API (`/v1/chat/completions`). The system MUST map system prompts to `{role: "system"}` messages and user prompts to `{role: "user"}` messages. The `openai` Python SDK MUST be used as the HTTP client with the configured `base_url` and `api_key`.

#### Scenario: Generate with system and user prompt
- **WHEN** the system requests text generation with a system prompt and user prompt
- **THEN** the system sends a chat completion request with `messages: [{role: "system", content: <system>}, {role: "user", content: <prompt>}]` and returns the assistant's response content

#### Scenario: Generate without system prompt
- **WHEN** the system requests text generation with only a user prompt (no system prompt)
- **THEN** the system sends a chat completion request with `messages: [{role: "user", content: <prompt>}]` and returns the assistant's response content

### Requirement: LLM settings UI
The system SHALL display an "LLM Provider" section in the Settings page with fields for base URL, API key (masked input), and model name. The section MUST include a "Test Connection" button that calls the health check endpoint and displays the result.

#### Scenario: View LLM settings
- **WHEN** the DM opens the Settings page
- **THEN** the LLM Provider section displays fields for base URL, API key (password input), and model name, pre-filled with current values or defaults

#### Scenario: Save LLM settings
- **WHEN** the DM enters a new base URL, API key, and model name and clicks Save
- **THEN** the settings are persisted and used for subsequent LLM operations

#### Scenario: Test connection from settings
- **WHEN** the DM clicks "Test Connection" in the LLM Provider section
- **THEN** the system calls `/api/llm/status` and displays the result (success or error message)

### Requirement: Setup wizard LLM guidance
The system SHALL display provider-agnostic LLM status in the setup wizard. The wizard MUST check if the configured LLM provider is reachable and display appropriate guidance. The wizard MUST NOT reference Ollama-specific commands unless Ollama is the configured provider.

#### Scenario: Default Ollama provider is reachable
- **WHEN** the setup wizard runs with default configuration and Ollama is running locally
- **THEN** the wizard shows LLM status as connected

#### Scenario: LLM provider not reachable
- **WHEN** the setup wizard runs and the configured LLM provider is not reachable
- **THEN** the wizard shows LLM status as not connected and suggests checking the base URL in Settings

#### Scenario: Continue without LLM
- **WHEN** the LLM provider is not reachable
- **THEN** the wizard allows the DM to continue, noting that LLM features (summaries) require a connected provider
