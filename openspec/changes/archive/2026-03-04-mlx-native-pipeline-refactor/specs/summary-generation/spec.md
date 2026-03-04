# Summary Generation

## MODIFIED Requirements

### Requirement: LLM model configuration
The system SHALL allow the DM to configure which model to use for summary generation via the LLM Provider settings (base URL, API key, model name). The system MUST provide a sensible default model recommendation. The settings UI SHALL show recommended models with performance notes.

#### Scenario: Default model
- **WHEN** the DM has not configured a model preference
- **THEN** the system defaults to `llama3.1:8b` for summary generation

#### Scenario: Change model
- **WHEN** the DM selects a different model (e.g., `mistral-small:24b`) in LLM Provider settings
- **THEN** subsequent summary generations use the newly selected model

#### Scenario: Model recommendations shown in UI
- **WHEN** the DM opens the LLM model selection in settings
- **THEN** the UI shows recommended models with annotations (e.g., "llama4:8b — fast, good for most sessions", "mistral-small:24b — slower, higher quality for complex narratives")

### Requirement: Long transcript chunking
The system SHALL handle transcripts that exceed the LLM's context window by splitting the transcript into chunks, summarizing each chunk, and then producing a combined summary from the chunk summaries. When the LLM provider is detected as Ollama, the system SHALL request a 32768-token context window via the `num_ctx` option to minimize chunking and improve summary coherence.

#### Scenario: Transcript exceeds context window
- **WHEN** a session transcript is 50,000 words (exceeding the model's context window)
- **THEN** the system splits the transcript into overlapping chunks, generates a summary per chunk, and combines the chunk summaries into a single coherent session summary

#### Scenario: Short transcript fits context window
- **WHEN** a session transcript is 3,000 words (within the model's context window)
- **THEN** the system processes the transcript in a single pass without chunking

#### Scenario: Ollama extended context window
- **WHEN** the LLM provider is detected as Ollama and a transcript is 20,000 words
- **THEN** the system requests `num_ctx: 32768` from Ollama, allowing the full transcript to be processed in a single pass instead of being chunked
