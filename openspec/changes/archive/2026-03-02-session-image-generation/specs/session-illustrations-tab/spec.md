## ADDED Requirements

### Requirement: Illustrations tab displays generated images
The Illustrations tab SHALL display all generated images for the current session in a list, ordered by most recent first. Each image entry SHALL show the image, the prompt used to generate it, the model name, and the generation timestamp.

#### Scenario: Session has generated images
- **WHEN** user navigates to the Illustrations tab and images exist for the session
- **THEN** the tab SHALL display all images in a list with their prompt, model, and timestamp

#### Scenario: Session has no images
- **WHEN** user navigates to the Illustrations tab and no images exist
- **THEN** the tab SHALL display an empty state message indicating no illustrations have been generated yet

### Requirement: Generate scene button
The Illustrations tab SHALL display a "Generate Scene" button. The button SHALL be disabled when the session has no transcript segments and no existing summary. Clicking the button SHALL trigger the two-step generation pipeline (LLM prompt crafting followed by image generation).

#### Scenario: Generate button with transcript available
- **WHEN** the session has transcript segments or a summary
- **THEN** the "Generate Scene" button SHALL be enabled

#### Scenario: Generate button with no content
- **WHEN** the session has no transcript segments and no summary
- **THEN** the "Generate Scene" button SHALL be disabled with a tooltip explaining that a transcript or summary is needed

### Requirement: Editable prompt before image generation
After clicking "Generate Scene", the system SHALL first call the backend to craft a scene description via the text LLM, then display the generated prompt in an editable text area. The user SHALL be able to modify the prompt before confirming image generation. A "Generate Image" button SHALL submit the final prompt to the image generation API.

#### Scenario: User accepts generated prompt as-is
- **WHEN** the LLM returns a scene description and the user clicks "Generate Image" without editing
- **THEN** the system SHALL send the unmodified prompt to the image generation API

#### Scenario: User edits the prompt
- **WHEN** the LLM returns a scene description and the user modifies the text
- **THEN** the system SHALL send the user-modified prompt to the image generation API

#### Scenario: User writes a fully manual prompt
- **WHEN** the user types a prompt directly into the text area without clicking "Generate Scene" first
- **THEN** the system SHALL send the manual prompt to the image generation API, skipping LLM prompt crafting

### Requirement: Generation loading state
The Illustrations tab SHALL display a loading indicator with elapsed time while an image is being generated. The "Generate Scene" and "Generate Image" buttons SHALL be disabled during generation to prevent concurrent requests.

#### Scenario: Image generation in progress
- **WHEN** the image generation API is processing a request
- **THEN** the tab SHALL show a spinner with elapsed time and disable all generation buttons

#### Scenario: Generation completes successfully
- **WHEN** the image generation API returns a result
- **THEN** the loading indicator SHALL disappear and the new image SHALL appear at the top of the image list

### Requirement: Delete individual images
Each image entry in the Illustrations tab SHALL have a delete button. Clicking delete SHALL show a confirmation dialog before removing the image.

#### Scenario: User confirms deletion
- **WHEN** user clicks delete on an image and confirms in the dialog
- **THEN** the system SHALL call `DELETE /api/images/{image_id}` and remove the image from the displayed list

#### Scenario: User cancels deletion
- **WHEN** user clicks delete on an image and cancels in the dialog
- **THEN** the image SHALL remain unchanged

### Requirement: Image provider health check warning
The Illustrations tab SHALL check image provider connectivity on mount. If the provider is unreachable, the tab SHALL display a warning banner indicating the image generation service is not available, with guidance to check settings.

#### Scenario: Image provider is reachable
- **WHEN** the Illustrations tab loads and the image provider health check returns ok
- **THEN** no warning SHALL be displayed

#### Scenario: Image provider is unreachable
- **WHEN** the Illustrations tab loads and the image provider health check returns error
- **THEN** a warning banner SHALL be displayed with the error message and a link to settings

### Requirement: Image provider settings in settings page
The settings page SHALL include an "Image Generation" section separate from the "LLM Provider" section. The section SHALL contain fields for image base URL, image API key (masked), and image model name. The section SHALL include a "Test Connection" button that calls the image health check endpoint.

#### Scenario: User configures image provider
- **WHEN** user enters image provider URL, API key, and model in the Image Generation settings section and saves
- **THEN** the `image_base_url`, `image_api_key`, and `image_model` settings SHALL be persisted independently

#### Scenario: Test connection succeeds
- **WHEN** user clicks "Test Connection" and the image provider is reachable
- **THEN** a success message SHALL be displayed

#### Scenario: Test connection fails
- **WHEN** user clicks "Test Connection" and the image provider is unreachable
- **THEN** an error message SHALL be displayed with details
