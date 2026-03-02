## Why

TaleKeeper captures rich narrative content from D&D sessions through transcription and summarization, but has no visual component. Players would benefit from AI-generated scene illustrations that bring their session recaps to life — produced entirely offline using a local image generation model, consistent with TaleKeeper's offline-first philosophy.

## What Changes

- Add a new "Illustrations" tab to the session detail page for generating and viewing scene images
- Use the existing LLM to craft an image generation prompt from the session transcript/summary (a "scene description")
- Call an OpenAI-compatible image generation API (separate from the text LLM) to produce the image
- Add a new Docker Compose service for the image generation model (using [openedai-images-flux](https://github.com/matatonic/openedai-images-flux) or similar OpenAI-compatible image server)
- Add independent settings for the image generation provider (base URL, API key, model) — fully decoupled from the text LLM settings
- Store generated images on disk and metadata in the database
- Update the README with setup instructions for the image generation service

## Capabilities

### New Capabilities
- `image-generation`: Backend service for generating images via an OpenAI-compatible `/v1/images/generations` endpoint, with independent provider settings, image storage, and database metadata
- `session-illustrations-tab`: New "Illustrations" tab in session detail — UI for generating scene images from session content, viewing/deleting generated images, and configuring the image provider in settings

### Modified Capabilities
- `session-tabs`: Add a 5th tab ("Illustrations") to the tab navigation and keyboard shortcuts

## Impact

- **Backend**: New `image_generation.py` service, new `images.py` router, new DB table for image metadata, settings router extended for image provider config
- **Frontend**: New `IllustrationsSection.svelte` component, `SessionDetail.svelte` updated with 5th tab, settings page extended with image provider section
- **Docker**: New service in `docker-compose.yml` for the image generation model
- **Dependencies**: No new Python dependencies — reuses the `openai` SDK already in use for text LLM
- **Storage**: New `data/images/` directory for generated image files
- **README**: New section documenting image generation setup and hardware requirements
