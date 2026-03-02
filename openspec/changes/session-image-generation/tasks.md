## 1. Database & Storage

- [x] 1.1 Add `session_images` table to the database schema in `connection.py`
- [x] 1.2 Create `data/images/` directory handling in the paths module (ensure it exists on startup, respects `data_dir` setting)

## 2. Image Provider Settings

- [x] 2.1 Add `image_api_key` to `SENSITIVE_KEYS` in `settings.py` for encryption at rest
- [x] 2.2 Create `image_client.py` service with `resolve_config()` (reads `image_base_url`, `image_api_key`, `image_model` from settings/env/defaults), `health_check()`, and `generate_image()` using the `openai` SDK `client.images.generate()`

## 3. Scene Description & Image Generation Service

- [x] 3.1 Create `image_generation.py` service with scene description prompt crafting — takes transcript or existing summary, sends to text LLM with image-prompt-optimized system prompt, returns scene description
- [x] 3.2 Add the two-step pipeline function: craft scene description via LLM, then call `image_client.generate_image()`, save file to `data/images/{session_id}/{uuid}.png`, insert metadata into `session_images`

## 4. Backend API Router

- [x] 4.1 Create `images.py` router with `POST /api/sessions/{session_id}/generate-image` endpoint (accepts optional `prompt` field, triggers pipeline or uses manual prompt)
- [x] 4.2 Add `GET /api/sessions/{session_id}/images` endpoint (returns image metadata list, ordered by `generated_at` desc)
- [x] 4.3 Add `GET /api/images/{image_id}/file` endpoint (serves image file with `Content-Type: image/png`)
- [x] 4.4 Add `DELETE /api/images/{image_id}` endpoint (deletes file from disk and metadata from DB)
- [x] 4.5 Add `GET /api/settings/image-health` endpoint (calls `image_client.health_check()`)
- [x] 4.6 Register the images router in `app.py`

## 5. Frontend — Settings Page

- [x] 5.1 Add "Image Generation" section to the settings page with fields for image base URL, image API key (masked), and image model name — separate from the LLM Provider section
- [x] 5.2 Add "Test Connection" button in the Image Generation settings section that calls `/api/settings/image-health` and displays success/error feedback

## 6. Frontend — Illustrations Tab

- [x] 6.1 Create `IllustrationsSection.svelte` component with image list display (image, prompt, model, timestamp per entry), empty state message, and image provider health check warning on mount
- [x] 6.2 Add "Generate Scene" button that calls the backend to craft a scene description, displays the result in an editable text area, and a "Generate Image" button to submit the final prompt
- [x] 6.3 Add manual prompt input — allow typing directly into the prompt text area and submitting without LLM crafting
- [x] 6.4 Add generation loading state with elapsed time counter and disabled buttons during generation
- [x] 6.5 Add delete button per image with confirmation dialog

## 7. Frontend — Session Detail Tab Integration

- [x] 7.1 Add `illustrations` to the `tabs` array and `tabLabels` map (label: "Visions", shortcut: `5`) in `SessionDetail.svelte`
- [x] 7.2 Add an SVG icon for the Visions tab consistent with the existing tab icon style
- [x] 7.3 Add the `IllustrationsSection` component in a hidden div following the existing tab mounting pattern
- [x] 7.4 Add API client methods for image endpoints in `frontend/src/lib/api.ts`

## 8. Docker Compose & Documentation

- [x] 8.1 Add `image-gen` service to `docker-compose.yml` with OpenAI-compatible image generation container, port 7860, named volume for models, and GPU resource reservation
- [x] 8.2 Add `IMAGE_BASE_URL=http://image-gen:7860/v1` environment variable to the `talekeeper` service and bind-mount `./data/images:/app/data/images`
- [x] 8.3 Add "Image Generation" section to README covering: Docker Compose setup (included by default), hardware requirements, macOS limitations and native alternatives, custom provider configuration
