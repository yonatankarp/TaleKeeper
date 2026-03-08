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
| Base URL | Your AI service's address | `http://localhost:11434/v1` |
| API Key | Access key (not needed for Ollama) | — |
| Model | Which model to use | `llama3.1:8b` |

!!! info "Supported Providers"
    TaleKeeper works with a range of AI services:

    - **Ollama** (runs on your computer, free) — recommended for most users
    - **OpenAI** — use your API key with models like `gpt-4o`
    - **Other services** — LM Studio and similar tools also work

!!! info "Image Generation"
    Scene illustrations are generated directly on your Mac — no additional setup required. The wizard checks that everything needed is installed and shows a ✓ when ready.

### Finishing Up

- Click **Re-check** to test your connections (status indicators update)
- Click **Get Started** when the LLM shows connected
- Or click **Continue Anyway** to skip AI features for now

!!! tip "Hidden Feature"
    You can re-run the setup wizard at any time from the **Settings** page — look for the "Run Setup Wizard" button at the bottom.

Next: [Create Your First Campaign →](../campaigns/index.md)
