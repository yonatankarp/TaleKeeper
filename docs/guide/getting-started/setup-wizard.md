# The Setup Wizard

## Charting Your Course

On your first launch, TaleKeeper greets you with a setup wizard to configure the essentials. You can always re-run it later from the Settings page.

![Setup wizard showing Data directory and LLM Provider configuration sections with status checkmarks](../images/setup-wizard-overlay.png)

### Step 1: Data Directory

Choose where TaleKeeper stores your recordings, transcripts, and summaries.

!!! tip "Backup Tip"
    As long as this folder exists, all your data is safe. Back it up regularly to preserve your campaign archives.

- Click **Browse** to open your system's folder picker
- Or type a path directly into the field
- The status indicator shows ✓ when the directory is valid

### Step 2: LLM Provider

Connect an AI provider for summaries and session naming.

| Field | Description | Example |
|-------|-------------|---------|
| Base URL | Your provider's API endpoint | `http://localhost:11434/v1` |
| API Key | Authentication key (optional for Ollama) | — |
| Model | Which model to use | `llama3.1:8b` |

!!! info "Supported Providers"
    TaleKeeper works with any **OpenAI-compatible** API:

    - **Ollama** (local, free) — recommended for getting started
    - **OpenAI** — use your API key with models like `gpt-4o`
    - **Any OpenAI-compatible service** — LM Studio, vLLM, etc.

!!! info "Image Generation"
    Scene illustrations are generated locally using mflux on Apple Silicon — no additional setup required. The wizard checks that mflux is available and shows a ✓ when ready.

### Finishing Up

- Click **Re-check** to test your connections (status indicators update)
- Click **Get Started** when the LLM shows connected
- Or click **Continue Anyway** to skip AI features for now

!!! tip "Hidden Feature"
    You can re-run the setup wizard at any time from the **Settings** page — look for the "Run Setup Wizard" button at the bottom.

Next: [Create Your First Campaign →](../campaigns/index.md)
