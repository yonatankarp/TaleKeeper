# Settings

## The Artificer's Workshop

The Settings page lets you configure TaleKeeper's behavior, AI providers, and integrations.

![Settings page showing Transcription section with Whisper model selector and batch size, HuggingFace token field, LLM Provider section, and Image Generation section with steps and guidance scale](../images/settings-page.png)

### Transcription

| Setting | Description | Default |
|---------|-------------|---------|
| Whisper Model | Speech recognition model | `distil-large-v3` |
| Batch Size | Parallel processing chunks (empty = auto-detected) | Auto |

**Model guide:**

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| `tiny` | ~30 sec / 10 min audio | Lower | Quick tests |
| `base` | ~1 min / 10 min audio | Fair | Short sessions |
| `small` | ~2 min / 10 min audio | Good | Casual use |
| `medium` | ~3 min / 10 min audio | Very Good | Balanced option |
| **`distil-large-v3`** | ~2 min / 10 min audio | **Excellent** | **Recommended** |
| `large-v3` | ~5 min / 10 min audio | Best | Critical recordings, accented speech |

!!! info "MLX-Native Engine"
    TaleKeeper uses lightning-whisper-mlx, an MLX-native transcription engine optimized for Apple Silicon. It includes a VAD (Voice Activity Detection) pre-pass that filters out non-speech audio before transcription, improving both speed and accuracy.

!!! info "Batch Size"
    Batch size controls how many audio segments are processed in parallel. When left empty, TaleKeeper auto-detects the optimal value based on your Apple Silicon performance cores. Only adjust this if you experience memory issues.

### Providers

#### HuggingFace

| Field | Description |
|-------|-------------|
| Token | HuggingFace access token for speaker diarization |

Speaker diarization (identifying who spoke when) uses pyannote.audio, which requires a HuggingFace token. To obtain one:

1. Create a free account at [huggingface.co](https://huggingface.co)
2. Accept the license at [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
3. Generate an access token in your [HuggingFace settings](https://huggingface.co/settings/tokens)
4. Paste it into the HuggingFace Token field

!!! warning "Required for Speaker Detection"
    Without a HuggingFace token, transcription will still work but all speech will be attributed to a single speaker.

#### LLM Provider

Configure the AI that powers summaries, session naming, and scene descriptions.

| Field | Description | Default |
|-------|-------------|---------|
| Base URL | API endpoint | `http://localhost:11434/v1` |
| API Key | Authentication (optional for Ollama) | — |
| Model | Which model to use | `llama3.1:8b` |

Click **Test Connection** to verify. A green checkmark means you're connected.

!!! info "Provider Compatibility"
    Any OpenAI-compatible API works: Ollama, OpenAI, LM Studio, vLLM, Together AI, etc.

### Image Generation

TaleKeeper generates scene illustrations locally using mflux, an MLX-native FLUX image model. No external server or API is required.

| Field | Description | Default |
|-------|-------------|---------|
| Model | Image model identifier | `FLUX.2-Klein-4B-Distilled` |
| Steps | Number of inference steps (1–50) | `4` |
| Guidance Scale | Prompt adherence strength (0–20) | `0` |

Click **Check Availability** to verify that mflux is installed.

!!! info "Apple Silicon Required"
    Image generation uses mflux which runs natively on Apple Silicon (M1 and newer). No external image server, API key, or GPU is needed — everything runs in-process on your Mac.

!!! tip "Tuning Image Quality"
    The defaults (4 steps, 0 guidance) are optimized for the Klein distilled model. Increasing steps produces more detailed images but takes longer. Increasing guidance scale makes the image follow the prompt more closely.

### Email (SMTP)

Configure email for [sharing summaries](../export/email-sharing.md).

| Field | Description | Example |
|-------|-------------|---------|
| SMTP Host | Mail server | `smtp.gmail.com` |
| SMTP Port | Server port | `587` |
| Username | Login | `you@gmail.com` |
| Password | App password | ••••••••  |
| Sender Address | From address | `you@gmail.com` |

!!! info "Password Security"
    Passwords are encrypted at rest in TaleKeeper's database. They're never stored in plaintext.

### Data Directory

Where TaleKeeper stores all recordings, transcripts, images, and the database.

- Click **Browse** to open your system's native folder picker
- Or type a path directly
- Default: `data/` in the TaleKeeper directory

!!! tip "Backup This Folder"
    Your entire TaleKeeper archive lives in this directory. Back it up to preserve your campaign history.

### Re-run Setup Wizard

Click **Run Setup Wizard** at the bottom to walk through initial configuration again.

### Environment Variables

For advanced users, TaleKeeper also respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `TALEKEEPER_CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:5173` |
| `TALEKEEPER_SECRET` | Encryption key for stored passwords | Built-in default |
| `LLM_BASE_URL` | LLM provider URL | `http://localhost:11434/v1` |
| `LLM_API_KEY` | LLM API key | — |
| `LLM_MODEL` | LLM model name | `llama3.1:8b` |
| `HF_TOKEN` | HuggingFace token for diarization | — |
| `IMAGE_MODEL` | Image model name | `FLUX.2-Klein-4B-Distilled` |
| `IMAGE_STEPS` | Image inference steps | `4` |
| `IMAGE_GUIDANCE_SCALE` | Image guidance scale | `0` |

!!! note "Priority"
    Settings saved in the UI take precedence over environment variables.

Next: [Tips & Tricks →](../tips-and-tricks.md)
