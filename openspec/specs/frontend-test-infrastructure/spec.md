# Frontend Test Infrastructure

## Purpose

Provide Vitest configuration, test dependencies, and unit tests for the frontend API client and streaming functions.

## Requirements

### Requirement: Vitest configuration
The frontend SHALL include a `vitest.config.ts` that configures vitest with the Svelte plugin, jsdom environment, and resolves the `$lib` alias to `src/lib`.

#### Scenario: Running vitest discovers frontend tests
- **WHEN** a developer runs `npm test` from the `frontend/` directory
- **THEN** vitest discovers and runs all `*.test.ts` files under `src/`

### Requirement: Frontend test dependencies
The `frontend/package.json` SHALL include dev dependencies for `vitest`, `@testing-library/svelte`, `jsdom`, and `@testing-library/jest-dom`.

#### Scenario: Installing frontend dev dependencies
- **WHEN** a developer runs `npm install` in the `frontend/` directory
- **THEN** vitest and testing-library are available for import in test files

### Requirement: API client unit tests
The test suite SHALL include unit tests for `src/lib/api.ts` covering the core HTTP methods (`get`, `post`, `put`, `del`) and error handling with mocked `fetch`.

#### Scenario: api.get sends GET request to correct URL
- **WHEN** `api.get("/campaigns")` is called with fetch mocked to return JSON
- **THEN** fetch is called with `GET` method to `/api/campaigns` and the parsed JSON is returned

#### Scenario: api.post sends POST with JSON body
- **WHEN** `api.post("/campaigns", { name: "Test" })` is called with fetch mocked
- **THEN** fetch is called with `POST` method, `Content-Type: application/json` header, and the serialized body

#### Scenario: api.del sends DELETE request
- **WHEN** `api.del("/campaigns/1")` is called with fetch mocked
- **THEN** fetch is called with `DELETE` method to `/api/campaigns/1`

#### Scenario: API error throws with message
- **WHEN** any API method is called and fetch returns a non-ok response with a JSON error body
- **THEN** an error is thrown containing the error message from the response

### Requirement: mergeSpeakers function test
The test suite SHALL include a unit test for the `mergeSpeakers()` exported function.

#### Scenario: mergeSpeakers sends correct payload
- **WHEN** `mergeSpeakers(1, 10, 20)` is called with fetch mocked
- **THEN** fetch is called with POST to `/api/sessions/1/merge-speakers` with body `{"source_speaker_id": 10, "target_speaker_id": 20}`

### Requirement: uploadAudio function test
The test suite SHALL include a unit test for the `uploadAudio()` exported function.

#### Scenario: uploadAudio sends multipart form data
- **WHEN** `uploadAudio(1, file)` is called with a mock File object and fetch mocked
- **THEN** fetch is called with POST to `/api/sessions/1/upload-audio` with a FormData body containing the file

### Requirement: SSE streaming function tests
The test suite SHALL include unit tests for `generateImageStream()`, `reDiarize()`, and `processAudio()` verifying they parse SSE events and call the correct callbacks.

#### Scenario: generateImageStream calls onPhase and onDone
- **WHEN** `generateImageStream()` is called and the mocked EventSource emits phase and done events
- **THEN** `onPhase` is called with the phase string and `onDone` is called with the image metadata

#### Scenario: reDiarize calls onError on error event
- **WHEN** `reDiarize()` is called and the mocked EventSource emits an error event
- **THEN** `onError` is called with the error message

#### Scenario: processAudio calls onProgress for chunk events
- **WHEN** `processAudio()` is called and the mocked EventSource emits progress events
- **THEN** `onProgress` is called with chunk and total values

### Requirement: npm test script
The `frontend/package.json` SHALL include a `"test"` script that runs `vitest run`.

#### Scenario: npm test runs all frontend tests
- **WHEN** a developer runs `npm test` in the `frontend/` directory
- **THEN** vitest executes all test files and reports results
