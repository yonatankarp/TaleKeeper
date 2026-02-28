## ADDED Requirements

### Requirement: Full session narrative summary
The system SHALL generate a narrative summary of a completed session's transcript using a local LLM via Ollama. The summary MUST capture key plot events, NPC interactions, combat encounters, player decisions, and notable moments.

#### Scenario: Generate session summary
- **WHEN** the DM clicks "Generate Summary" on a completed session with a transcript
- **THEN** the system sends the transcript to the local LLM and produces a narrative summary covering the session's key events, displayed in the session view

#### Scenario: Summary for a session without transcript
- **WHEN** the DM attempts to generate a summary for a session with no transcript
- **THEN** the system displays an error explaining that a transcript is required before generating a summary

### Requirement: Per-player POV summaries
The system SHALL generate individual summaries from each player character's perspective. Each POV summary MUST focus on what that character experienced, learned, decided, and how they interacted with other characters and the world. The system MUST generate one POV summary per speaker who has been assigned a character name.

#### Scenario: Generate POV summaries
- **WHEN** the DM clicks "Generate POV Summaries" on a session with 4 assigned character speakers
- **THEN** the system generates 4 separate summaries, each written from the perspective of one character, highlighting that character's personal experience of the session

#### Scenario: POV requires speaker assignment
- **WHEN** the DM attempts to generate POV summaries but no speakers have been assigned character names
- **THEN** the system prompts the DM to assign character names to speakers first

### Requirement: Ollama connectivity
The system SHALL communicate with Ollama via its local REST API (default: `http://localhost:11434`). The system MUST verify Ollama is running and the selected model is available before attempting summary generation.

#### Scenario: Ollama is running and model available
- **WHEN** the DM triggers summary generation and Ollama is running with the configured model loaded
- **THEN** summary generation proceeds normally

#### Scenario: Ollama is not running
- **WHEN** the DM triggers summary generation but Ollama is not running
- **THEN** the system displays an error with instructions on how to start Ollama (e.g., `ollama serve`)

#### Scenario: Model not available
- **WHEN** Ollama is running but the configured model has not been pulled
- **THEN** the system displays an error naming the missing model and the command to pull it (e.g., `ollama pull llama3.1:8b`)

### Requirement: LLM model configuration
The system SHALL allow the DM to configure which Ollama model to use for summary generation. The system MUST provide a sensible default model recommendation.

#### Scenario: Default model
- **WHEN** the DM has not configured a model preference
- **THEN** the system defaults to `llama3.1:8b` for summary generation

#### Scenario: Change model
- **WHEN** the DM selects a different model (e.g., `mistral:7b`) in settings
- **THEN** subsequent summary generations use the newly selected model

### Requirement: Long transcript chunking
The system SHALL handle transcripts that exceed the LLM's context window by splitting the transcript into chunks, summarizing each chunk, and then producing a combined summary from the chunk summaries.

#### Scenario: Transcript exceeds context window
- **WHEN** a session transcript is 50,000 words (exceeding the model's context window)
- **THEN** the system splits the transcript into overlapping chunks, generates a summary per chunk, and combines the chunk summaries into a single coherent session summary

#### Scenario: Short transcript fits context window
- **WHEN** a session transcript is 3,000 words (within the model's context window)
- **THEN** the system processes the transcript in a single pass without chunking

### Requirement: Summary regeneration
The system SHALL allow the DM to regenerate summaries for a session, replacing the previous summaries. The system MUST confirm before overwriting existing summaries.

#### Scenario: Regenerate with different model
- **WHEN** the DM changes the LLM model and clicks "Regenerate Summary" on a session that already has summaries
- **THEN** the system confirms the DM wants to replace existing summaries, then generates new ones using the current model

### Requirement: Summary editing
The system SHALL allow the DM to manually edit generated summaries before exporting or sharing. Edits MUST be saved and persist across application restarts.

#### Scenario: Edit a generated summary
- **WHEN** the DM edits the text of a generated session summary
- **THEN** the changes are saved to the database and displayed on subsequent views

### Requirement: Summary metadata
The system SHALL record which LLM model was used and when each summary was generated. This metadata MUST be visible to the DM in the summary view.

#### Scenario: View summary metadata
- **WHEN** the DM views a generated summary
- **THEN** the summary displays the model name (e.g., "llama3.1:8b") and generation timestamp
