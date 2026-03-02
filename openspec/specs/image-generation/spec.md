# Image Generation

## Purpose

Provide AI-powered image generation from session content using an OpenAI-compatible image API, with independent provider configuration and a two-step pipeline (LLM scene description then image generation).

## Requirements

### Requirement: Independent image provider settings
The system SHALL store image generation provider configuration separately from the text LLM settings. The settings keys SHALL be `image_base_url`, `image_api_key`, and `image_model`. The `image_api_key` SHALL be encrypted at rest using the same mechanism as `llm_api_key`. The system SHALL resolve configuration in order: settings table, environment variables (`IMAGE_BASE_URL`, `IMAGE_API_KEY`, `IMAGE_MODEL`), then defaults (`http://localhost:7860/v1`, no key, `flux1-schnell`).

#### Scenario: Image settings are stored independently from LLM settings
- **WHEN** user updates `image_base_url` to a new value
- **THEN** the `llm_base_url` setting SHALL remain unchanged

#### Scenario: Image API key is encrypted at rest
- **WHEN** user saves an `image_api_key` value
- **THEN** the stored value in the database SHALL be encrypted with the `ENC:` prefix

#### Scenario: Environment variable overrides default
- **WHEN** the `IMAGE_BASE_URL` environment variable is set and no `image_base_url` exists in the settings table
- **THEN** the system SHALL use the environment variable value

### Requirement: Image provider health check
The system SHALL provide a health check endpoint at `GET /api/settings/image-health` that verifies connectivity to the configured image generation provider. The health check SHALL return a status of `ok` or `error` with a descriptive message.

#### Scenario: Image provider is reachable
- **WHEN** the image generation API is running and accessible
- **THEN** the health check SHALL return `{"status": "ok"}`

#### Scenario: Image provider is unreachable
- **WHEN** the image generation API is not running
- **THEN** the health check SHALL return `{"status": "error", "message": "Cannot reach image provider at <url>"}`

### Requirement: Scene description generation via text LLM
The system SHALL use the configured text LLM to generate an image prompt from session content. The system SHALL prefer the existing full summary if available; otherwise it SHALL use the raw transcript. The LLM SHALL be instructed to produce a concise, vivid scene description optimized for image generation (fantasy art style, visual details, composition). The system SHALL handle long transcripts by using the existing chunking strategy to produce a summary first.

#### Scenario: Scene description from existing summary
- **WHEN** user requests image generation and a full session summary exists
- **THEN** the system SHALL send the summary to the text LLM to craft an image prompt

#### Scenario: Scene description from raw transcript
- **WHEN** user requests image generation and no full summary exists
- **THEN** the system SHALL send the transcript to the text LLM to craft an image prompt

#### Scenario: Text LLM is unavailable
- **WHEN** the text LLM is not configured or unreachable and the user provides a manual prompt
- **THEN** the system SHALL skip the LLM step and use the manual prompt directly for image generation

### Requirement: Image generation via OpenAI-compatible API
The system SHALL generate images by calling `POST /v1/images/generations` on the configured image provider using the `openai` Python SDK. The request SHALL include the prompt and model name. The system SHALL save the returned image to disk at `data/images/{session_id}/{uuid}.png`.

#### Scenario: Successful image generation
- **WHEN** the image provider returns a successful response with image data
- **THEN** the system SHALL save the image file to disk and create a database record with the prompt, model name, file path, and generation timestamp

#### Scenario: Image provider returns an error
- **WHEN** the image provider returns an error response
- **THEN** the system SHALL return an error to the caller with the provider's error message without creating any file or database record

### Requirement: Image metadata storage
The system SHALL store image metadata in a `session_images` database table with columns: `id`, `session_id`, `file_path`, `prompt`, `scene_description`, `model_used`, `generated_at`. The `session_id` SHALL reference the `sessions` table.

#### Scenario: Image metadata is persisted
- **WHEN** an image is successfully generated
- **THEN** a row SHALL be inserted into `session_images` with all metadata fields populated

#### Scenario: Image deletion removes file and metadata
- **WHEN** user deletes an image via `DELETE /api/images/{image_id}`
- **THEN** the system SHALL delete both the image file from disk and the metadata row from the database

### Requirement: Image API endpoints
The system SHALL provide the following API endpoints:
- `POST /api/sessions/{session_id}/generate-image` — accepts optional `prompt` field; triggers the two-step pipeline (LLM prompt crafting then image generation) or uses the provided prompt directly
- `GET /api/sessions/{session_id}/images` — returns all image metadata for a session, ordered by `generated_at` descending
- `GET /api/images/{image_id}/file` — serves the image file with appropriate content type
- `DELETE /api/images/{image_id}` — deletes the image file and metadata

#### Scenario: Generate image with automatic prompt
- **WHEN** `POST /api/sessions/{session_id}/generate-image` is called without a `prompt` field
- **THEN** the system SHALL use the text LLM to craft a scene description, then generate the image

#### Scenario: Generate image with manual prompt
- **WHEN** `POST /api/sessions/{session_id}/generate-image` is called with a `prompt` field
- **THEN** the system SHALL use the provided prompt directly for image generation, skipping LLM prompt crafting

#### Scenario: List session images
- **WHEN** `GET /api/sessions/{session_id}/images` is called
- **THEN** the system SHALL return all image metadata for that session ordered by most recent first

#### Scenario: Serve image file
- **WHEN** `GET /api/images/{image_id}/file` is called for an existing image
- **THEN** the system SHALL return the image file with `Content-Type: image/png`

#### Scenario: Delete image
- **WHEN** `DELETE /api/images/{image_id}` is called
- **THEN** the system SHALL delete the file from disk and remove the database record, returning `204 No Content`

### Requirement: Docker Compose image generation service
The Docker Compose configuration SHALL include an `image-gen` service using an OpenAI-compatible image generation container. The service SHALL expose port 7860, use a named volume for model persistence, and declare GPU resource reservations. The `talekeeper` service SHALL receive an `IMAGE_BASE_URL` environment variable pointing to the image service. The image data directory SHALL be bind-mounted from `./data/images`.

#### Scenario: Image service starts with Docker Compose
- **WHEN** `docker compose up` is run
- **THEN** the `image-gen` service SHALL start and expose the `/v1/images/generations` endpoint

#### Scenario: Model files persist across restarts
- **WHEN** the `image-gen` container is recreated
- **THEN** previously downloaded model files SHALL be available from the named volume

#### Scenario: TaleKeeper connects to image service
- **WHEN** the `talekeeper` service starts
- **THEN** it SHALL be configured with `IMAGE_BASE_URL` pointing to `http://image-gen:7860/v1`

### Requirement: README documents image generation setup
The README SHALL include a section documenting image generation setup covering: Docker Compose usage (included by default), hardware requirements (GPU recommended, disk space for models), macOS limitations (no GPU passthrough in Docker, suggest native mflux as alternative), and how to configure a custom image provider via settings.

#### Scenario: User reads README for image setup
- **WHEN** a new user reads the README
- **THEN** they SHALL find clear instructions for enabling image generation with hardware requirements and platform-specific guidance
