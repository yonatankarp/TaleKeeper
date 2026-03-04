# Image Generation

## MODIFIED Requirements

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

### Requirement: README documents image generation setup
The README SHALL include a section documenting image generation setup covering: mflux installation as part of TaleKeeper dependencies, model download behavior (first-use automatic download), Apple Silicon requirements (M1 or later), disk space for model files, and how to configure model and generation parameters via settings.

#### Scenario: User reads README for image setup
- **WHEN** a new user reads the README
- **THEN** they SHALL find clear instructions for image generation including hardware requirements and model download information

## REMOVED Requirements

### Requirement: Image generation via OpenAI-compatible API
**Reason**: Replaced by in-process mflux generation. Image generation no longer requires an external API server.
**Migration**: Remove image_client.py. Image generation uses the mflux library directly in-process.

### Requirement: Docker Compose image generation service
**Reason**: In-process mflux eliminates the need for a separate image generation container. The FLUX model runs directly within the TaleKeeper process.
**Migration**: Remove the `image-gen` service from Docker Compose. Image generation works out of the box with mflux installed as a Python dependency.
