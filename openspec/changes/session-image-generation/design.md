## Context

TaleKeeper is an offline-first D&D session recorder with a FastAPI backend, Svelte frontend, and Docker Compose deployment. It already integrates with a text LLM via an OpenAI-compatible API (configurable base URL, API key, model) for generating session summaries. The Docker Compose stack currently runs two services: `talekeeper` and `ollama`.

There is no image generation capability today. The goal is to add scene illustration generation using a local image model, keeping it fully decoupled from the text LLM configuration.

## Goals / Non-Goals

**Goals:**
- Allow users to generate scene illustrations from their session content
- Use the text LLM to craft an optimized image prompt from session transcript/summary
- Call a separate OpenAI-compatible image generation API to produce the image
- Provide independent settings for the image generation provider (not coupled with text LLM)
- Include the image generation model as a Docker Compose service
- Document setup in the README

**Non-Goals:**
- Image editing, inpainting, or img2img workflows
- Multiple image styles or model switching per image
- Batch generation of images for an entire session
- Gallery/album organization across sessions
- Image export to PDF (can be added later)

## Decisions

### 1. Two-step generation pipeline: LLM prompt crafting → image generation

The user clicks "Generate" and the backend:
1. Sends the session transcript (or existing full summary) to the **text LLM** with a system prompt asking it to write a vivid, concise scene description optimized for image generation (e.g., "a dramatic fantasy scene of...")
2. Sends that scene description to the **image generation API** via `POST /v1/images/generations`

**Why:** Raw transcripts make poor image prompts. The text LLM can distill a multi-hour session into a focused visual description. This also means the user doesn't need to write prompts manually.

**Alternative considered:** Let users write prompts manually. Rejected as the primary flow because it breaks the "one-click" experience, but users should be able to edit the generated prompt before submitting to the image model.

### 2. OpenAI-compatible `/v1/images/generations` endpoint

The image service client will use the same `openai` Python SDK already in the project, calling `client.images.generate()`. This means any backend that implements the OpenAI images API works: openedai-images-flux, LocalAI, AUTOMATIC1111 with API mode, or even OpenAI itself.

**Why:** Maximum flexibility with zero new dependencies. Users can swap image backends without code changes.

### 3. Separate settings keys for image generation

New settings keys, completely independent from the text LLM:
- `image_base_url` — base URL of the image generation API
- `image_api_key` — API key (encrypted at rest, same as `llm_api_key`)
- `image_model` — model name (e.g., `flux1-schnell`)

Default values when running via Docker Compose:
- `image_base_url`: `http://image-gen:7860/v1` (points to the Docker service)
- `image_model`: `flux1-schnell`

**Why:** The text LLM and image model are fundamentally different services, possibly on different machines. Coupling them would be limiting. The settings UI will show them as separate sections.

### 4. Docker Compose: `openedai-images-flux` as the image service

Add a third service to `docker-compose.yml`:
```yaml
image-gen:
  image: ghcr.io/matatonic/openedai-images-flux:latest
  ports:
    - "7860:7860"
  volumes:
    - image_models:/app/models
  deploy:
    resources:
      reservations:
        devices:
          - capabilities: [gpu]
```

The `talekeeper` service gets an additional environment variable: `IMAGE_BASE_URL=http://image-gen:7860/v1`.

**Why:** openedai-images-flux provides an OpenAI-compatible images endpoint out of the box with FLUX support. It's purpose-built for this use case.

**Alternative considered:** ComfyUI — more powerful but requires workflow JSON configuration, much more complex to set up and integrate. AUTOMATIC1111 — also viable but heavier container. LocalAI — supports images but is a larger all-in-one project.

**Note:** GPU passthrough in Docker requires Linux + NVIDIA. On macOS, the image service won't have GPU access in Docker. The README will document this limitation and suggest native alternatives (mflux) for Mac users.

### 5. Image storage on disk with DB metadata

Images stored as files in `data/images/{session_id}/{uuid}.png`. Database table stores metadata:

```sql
CREATE TABLE IF NOT EXISTS session_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    file_path TEXT NOT NULL,
    prompt TEXT NOT NULL,
    scene_description TEXT,
    model_used TEXT,
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

**Why:** Images are large binary blobs — storing them in SQLite would bloat the database and slow backups. The existing pattern (audio files on disk, metadata in DB) is proven.

### 6. Backend API design

New router `images.py` with endpoints:
- `POST /api/sessions/{session_id}/generate-image` — triggers the two-step pipeline. Accepts optional `prompt` override. Returns image metadata.
- `GET /api/sessions/{session_id}/images` — list all images for a session
- `GET /api/images/{image_id}/file` — serve the image file
- `DELETE /api/images/{image_id}` — delete image and file
- `GET /api/settings/image-health` — health check for image provider connectivity

### 7. Frontend: new "Illustrations" tab

Add a 5th tab to `SessionDetail.svelte` with key `illustrations` and D&D-themed label "Visions". Keyboard shortcut: `5`.

The `IllustrationsSection.svelte` component will:
- Show a "Generate Scene" button (disabled if no transcript/summary exists)
- Display a loading state with elapsed time during generation (same pattern as summaries)
- Show the generated prompt (editable before submitting)
- Display generated images in a simple grid/list with the prompt used
- Allow deleting individual images
- Show a health check warning if the image provider is unreachable

### 8. New service: `image_client.py`

Mirrors the pattern of `llm_client.py` but for image generation:
- `resolve_config()` — reads `image_base_url`, `image_api_key`, `image_model` from settings/env/defaults
- `health_check()` — verifies connectivity to the image provider
- `generate_image()` — calls `client.images.generate()` and saves the result to disk

### 9. Scene description generation via text LLM

New function in `image_generation.py` service (not in `summarization.py` — keeps concerns separate):
- Takes the session transcript (or existing full summary if available)
- Sends to the text LLM with a system prompt tuned for generating image prompts
- Returns a concise scene description suitable for image generation
- The user can edit this description before it goes to the image model

## Risks / Trade-offs

- **GPU required for reasonable speed** → Docker GPU passthrough only works on Linux/NVIDIA. macOS Docker users will get CPU-only performance (minutes per image). Mitigation: document this clearly, suggest native mflux for Mac users.
- **Large Docker image** → The image generation container includes model weights (~8-12GB). Mitigation: use a named volume for models so they persist across container rebuilds. Document the disk space requirement.
- **First-run model download** → Similar to Ollama, the image model needs to be pulled on first run. Mitigation: add an entrypoint script that downloads the model, same pattern as the existing Ollama service.
- **Image quality varies** → Smaller/quantized models produce lower quality. Mitigation: the scene description step helps produce better prompts, and users can edit prompts before generation.
- **Text LLM dependency for prompt crafting** → If the text LLM is not configured/running, prompt crafting fails. Mitigation: allow users to type a manual prompt directly, bypassing the LLM step.
