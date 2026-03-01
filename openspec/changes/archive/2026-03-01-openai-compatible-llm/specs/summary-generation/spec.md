## MODIFIED Requirements

### Requirement: Full session narrative summary
The system SHALL generate a narrative summary of a completed session's transcript using the configured LLM provider via the OpenAI Chat Completions API. The summary MUST capture key plot events, NPC interactions, combat encounters, player decisions, and notable moments.

#### Scenario: Generate session summary
- **WHEN** the DM clicks "Generate Summary" on a completed session with a transcript
- **THEN** the system sends the transcript to the configured LLM provider and produces a narrative summary covering the session's key events, displayed in the session view

#### Scenario: Summary for a session without transcript
- **WHEN** the DM attempts to generate a summary for a session with no transcript
- **THEN** the system displays an error explaining that a transcript is required before generating a summary

### Requirement: Per-player POV summaries
The system SHALL generate individual summaries from each player character's perspective using the configured LLM provider via the OpenAI Chat Completions API. Each POV summary MUST focus on what that character experienced, learned, decided, and how they interacted with other characters and the world. The system MUST generate one POV summary per speaker who has been assigned a character name.

#### Scenario: Generate POV summaries
- **WHEN** the DM clicks "Generate POV Summaries" on a session with 4 assigned character speakers
- **THEN** the system generates 4 separate summaries, each written from the perspective of one character, highlighting that character's personal experience of the session

#### Scenario: POV requires speaker assignment
- **WHEN** the DM attempts to generate POV summaries but no speakers have been assigned character names
- **THEN** the system prompts the DM to assign character names to speakers first

### Requirement: LLM model configuration
The system SHALL allow the DM to configure which model to use for summary generation via the LLM Provider settings (base URL, API key, model name). The system MUST provide a sensible default model recommendation.

#### Scenario: Default model
- **WHEN** the DM has not configured a model preference
- **THEN** the system defaults to `llama3.1:8b` for summary generation

#### Scenario: Change model
- **WHEN** the DM selects a different model (e.g., `gpt-4o-mini`) in LLM Provider settings
- **THEN** subsequent summary generations use the newly selected model

## REMOVED Requirements

### Requirement: Ollama connectivity
**Reason**: Replaced by the generic `llm-provider` capability which handles connectivity to any OpenAI-compatible LLM provider, including Ollama via its `/v1/` endpoint.
**Migration**: LLM connectivity checks are now handled by the `/api/llm/status` endpoint and the `llm-provider` capability's health check requirement. Ollama-specific error messages (e.g., `ollama serve`, `ollama pull`) are replaced by generic provider error messages.
