# Installation

## Preparing Your Keep

Before TaleKeeper can chronicle your adventures, you'll need a few things in place.

### Prerequisites

- **Python 3.12+** — [python.org](https://www.python.org/downloads/)
- **ffmpeg** — Required for audio processing
- **Ollama** *(optional)* — For AI summaries and image generation

=== "macOS"

    ```bash
    brew install ffmpeg
    brew install ollama  # optional, for AI features
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

If you want AI-powered summaries, character journals, and scene illustrations:

```bash
ollama serve
ollama pull llama3.1:8b        # For text generation
ollama pull x/flux2-klein:9b   # For image generation (macOS only)
```

!!! note "No Ollama? No Problem"
    Recording, transcription, and speaker identification work entirely without Ollama or any LLM. You only need an AI provider for summaries, session naming, and illustration generation.

![TaleKeeper home screen showing the Campaigns list with a campaign card, sidebar navigation, and New Campaign button](../images/home-screen.png)

Next: [Run the Setup Wizard →](setup-wizard.md)
