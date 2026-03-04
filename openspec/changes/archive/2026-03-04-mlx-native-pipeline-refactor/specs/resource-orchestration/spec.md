# Resource Orchestration

## Purpose

Provide memory management and cleanup between ML pipeline phases, ensuring that transcription, diarization, LLM summarization, and image generation can run sequentially within a 32GB unified memory budget on Apple Silicon without triggering system swap.

## ADDED Requirements

### Requirement: MLX memory cache clearing
The system SHALL clear the MLX Metal GPU cache using `mlx.core.metal.clear_cache()` after any MLX-based model (transcription, image generation) finishes processing. The system SHALL also run `gc.collect()` to release Python-level references.

#### Scenario: Cache cleared after transcription
- **WHEN** the transcription phase completes (success or error)
- **THEN** the system calls `mlx.core.metal.clear_cache()` followed by `gc.collect()` to free GPU memory

#### Scenario: Cache cleared after image generation
- **WHEN** the image generation phase completes (success or error)
- **THEN** the system calls `mlx.core.metal.clear_cache()` followed by `gc.collect()` to free GPU memory

### Requirement: PyTorch MPS cache clearing
The system SHALL clear the PyTorch MPS device cache using `torch.mps.empty_cache()` after the diarization phase finishes processing. The system SHALL also run `gc.collect()` to release Python-level references.

#### Scenario: MPS cache cleared after diarization
- **WHEN** the diarization phase completes (success or error)
- **THEN** the system calls `torch.mps.empty_cache()` followed by `gc.collect()` to free GPU memory

### Requirement: Ollama model unloading
The system SHALL unload the LLM model from Ollama's memory after summary generation completes, when the configured LLM provider is detected as Ollama. The system SHALL call Ollama's native API with `keep_alive: "0"` to force immediate model eviction.

#### Scenario: Ollama model unloaded after summaries
- **WHEN** summary generation completes and the LLM provider is Ollama
- **THEN** the system sends a request to Ollama's `/api/generate` endpoint with `keep_alive: "0"` to unload the model from memory

#### Scenario: Non-Ollama provider skips unloading
- **WHEN** summary generation completes and the LLM provider is not Ollama
- **THEN** the system skips the model unloading step (no-op)

### Requirement: Phase transition cleanup
The system SHALL provide a cleanup function for each ML phase that unloads models, clears framework-specific caches, and runs garbage collection. Each cleanup function SHALL be callable independently from any router or pipeline orchestrator.

#### Scenario: Cleanup functions are independently callable
- **WHEN** a router endpoint finishes a single phase (e.g., process-audio completes transcription + diarization)
- **THEN** the appropriate cleanup functions are called to free memory before the response completes

#### Scenario: Cleanup runs in pipeline transitions
- **WHEN** the session pipeline transitions from one phase to the next
- **THEN** the cleanup function for the completed phase runs before the next phase begins loading its models
