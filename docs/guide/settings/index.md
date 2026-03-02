# Settings

## The Artificer's Workshop

The Settings page lets you configure TaleKeeper's behavior, AI providers, and integrations.

![Settings page showing Transcription section with Whisper model selector and live transcription toggle, and LLM Provider section with Base URL, API Key, Model fields, and Test Connection button](../images/settings-page.png)

### Transcription

| Setting | Description | Default |
|---------|-------------|---------|
| Whisper Model | Speech recognition model size | `medium` |
| Live Transcription | Show preview segments during recording | Off |

**Model size guide:**

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| `tiny` | ~1 min / 10 min audio | Lower | Quick tests |
| `base` | ~2 min / 10 min audio | Fair | Short sessions |
| `small` | ~4 min / 10 min audio | Good | Casual use |
| `medium` | ~8 min / 10 min audio | Very Good | **Recommended** |
| `large-v3` | ~15 min / 10 min audio | Best | Important recordings |

!!! info "Live Transcription"
    When enabled, preliminary transcript segments appear during recording. These are a preview — the final transcript after processing will be more accurate and include speaker labels.

### LLM Provider

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

Configure the AI that generates scene illustrations.

| Field | Description | Default |
|-------|-------------|---------|
| Base URL | API endpoint | `http://localhost:11434/v1` |
| API Key | Authentication (optional for Ollama) | — |
| Model | Which image model to use | `x/flux2-klein:9b` |

!!! warning "macOS Note for Ollama"
    Ollama image generation currently works only on macOS. For Linux or Windows, use a cloud provider like OpenAI (`dall-e-3`).

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
| `IMAGE_API_KEY` | Image provider API key | — |
| `IMAGE_MODEL` | Image model name | `x/flux2-klein:9b` |

!!! note "Priority"
    Settings saved in the UI take precedence over environment variables.

Next: [Tips & Tricks →](../tips-and-tricks.md)
