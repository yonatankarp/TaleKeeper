# Image Generation

## Purpose

Provide AI-powered image generation from session content using mflux running in-process on Apple Silicon, with independent provider configuration and a two-step pipeline (LLM scene description then image generation).

## Requirements

### Requirement: Independent image provider settings
The system SHALL store image generation configuration in the settings table. The settings keys SHALL be `image_model`, `image_steps`, and `image_guidance_scale`. The system SHALL resolve configuration in order: settings table, environment variables (`IMAGE_MODEL`, `IMAGE_STEPS`, `IMAGE_GUIDANCE_SCALE`), then defaults (`FLUX.2-Klein-4B-Distilled`, `4`, `0`). The settings UI SHALL show recommended models with performance notes.

#### Scenario: Image settings are stored independently from LLM settings
- **WHEN** user updates `image_model` to a new value
- **THEN** the `llm_model` setting SHALL remain unchanged

#### Scenario: Default settings for fast generation
- **WHEN** no image settings have been configured
- **THEN** the system uses model `FLUX.2-Klein-4B-Distilled`, 4 inference steps, and guidance scale 0

#### Scenario: Environment variable overrides default
- **WHEN** the `IMAGE_MODEL` environment variable is set and no `image_model` exists in the settings table
- **THEN** the system SHALL use the environment variable value

### Requirement: Image provider health check
The system SHALL provide a health check endpoint at `GET /api/settings/image-health` that verifies the mflux library is importable and the configured model is available. The health check SHALL return a status of `ok` or `error` with a descriptive message.

#### Scenario: mflux available and model present
- **WHEN** the mflux library is installed and the configured model files are downloaded
- **THEN** the health check SHALL return `{"status": "ok"}`

#### Scenario: mflux not installed
- **WHEN** the mflux library is not importable
- **THEN** the health check SHALL return `{"status": "error", "message": "mflux library is not installed"}`

#### Scenario: Model not downloaded
- **WHEN** the mflux library is installed but the configured model files are not present
- **THEN** the health check SHALL return `{"status": "error", "message": "Model '<model>' not found. It will be downloaded on first use."}`

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

### Requirement: In-process image generation via mflux
The system SHALL generate images using the mflux library running in-process on the Apple Silicon GPU via MLX. The system SHALL load the FLUX model lazily on first use and cache it globally. Image output SHALL be saved to disk at `data/images/{session_id}/{uuid}.png`. The model SHALL be unloadable via the resource orchestration module.

#### Scenario: Successful image generation
- **WHEN** the system generates an image with a prompt
- **THEN** the mflux library produces a PNG image using the configured model, steps, and guidance scale, and the system saves it to disk and creates a database record with the prompt, model name, file path, and generation timestamp

#### Scenario: First generation downloads model
- **WHEN** image generation is triggered for the first time and the model has not been downloaded
- **THEN** the mflux library downloads the model files before generating the image (this first run will be slower)

#### Scenario: Model cached for subsequent generations
- **WHEN** a second image is generated in the same process lifetime
- **THEN** the cached model is reused without reloading

#### Scenario: Image generation error
- **WHEN** an error occurs during mflux image generation
- **THEN** the system returns an error to the caller with the error message without creating any file or database record

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

### Requirement: README documents image generation setup
The README SHALL include a section documenting image generation setup covering: mflux installation as part of TaleKeeper dependencies, model download behavior (first-use automatic download), Apple Silicon requirements (M1 or later), disk space for model files, and how to configure model and generation parameters via settings.

#### Scenario: User reads README for image setup
- **WHEN** a new user reads the README
- **THEN** they SHALL find clear instructions for image generation including hardware requirements and model download information
