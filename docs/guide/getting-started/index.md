# Installation

## Preparing Your Keep

Before TaleKeeper can chronicle your adventures, you'll need a few things in place.

### Prerequisites

- **Apple Silicon Mac (M1+)** — Recommended for ML features (transcription, diarization, image generation)
- **Python 3.12+** — [python.org](https://www.python.org/downloads/)
- **ffmpeg** — Required for audio processing
- **Ollama** *(optional)* — For AI-powered text summaries and session naming

=== "macOS"

    ```bash
    brew install ffmpeg
    brew install ollama  # optional, for AI text features
    ```

=== "Linux"

    ```bash
    sudo apt install ffmpeg
    # For Ollama, see https://ollama.ai
    ```

### Install TaleKeeper

```bash
pip install talekeeper
```

### Launch

```bash
talekeeper serve
```

This starts the server at `http://localhost:8000` and opens your browser automatically.

!!! info "Command Options"
    | Flag | Description |
    |------|-------------|
    | `--host <address>` | Bind to a specific address (default: `127.0.0.1`) |
    | `--port <number>` | Use a different port (default: `8000`) |
    | `--reload` | Auto-reload on code changes (development) |
    | `--no-browser` | Don't open the browser on startup |

### Optional: Set Up Ollama

If you want AI-powered summaries, character journals, and session naming:

```bash
ollama serve
ollama pull llama3.1:8b        # For text generation
```

!!! note "No Ollama? No Problem"
    Recording, transcription, speaker identification, and image generation all work without Ollama. You only need an LLM provider for summaries, session naming, and scene description crafting.

### Optional: HuggingFace Token for Speaker Diarization

Speaker diarization (identifying who spoke when) uses pyannote.audio, which requires a free HuggingFace token:

1. Create an account at [huggingface.co](https://huggingface.co)
2. Accept the pyannote model license at [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
3. Add your token in TaleKeeper's Settings under **Providers → HuggingFace**

Without a token, transcription still works but all speech will be attributed to a single speaker.

![TaleKeeper home screen showing the Campaigns list with a campaign card, sidebar navigation, and New Campaign button](../images/home-screen.png)

Next: [Run the Setup Wizard →](setup-wizard.md)
