## Why

Single-channel recordings of D&D sessions with players at uneven distances from the mic cause distant players' speech to be completely absorbed by louder nearby players during overlap — their words disappear from the transcript entirely. Post-clustering overlap detection (separate change) flags these segments but cannot recover them; source separation can actually split the mixed audio into individual speaker streams before diarization runs, giving every player a fair chance at attribution.

## What Changes

- Add an optional pre-diarization source separation stage using SpeechBrain's SepFormer model (local, offline, CPU-capable) that decomposes the single-channel recording into N speaker streams
- Run diarization on the separated streams individually rather than the mixed audio, then merge results back to original timestamps
- Expose source separation as an opt-in toggle in campaign settings (off by default — it adds significant processing time)
- Report source separation progress via SSE alongside existing diarization progress events
- Store separated streams as temp files only; do not persist them

## Capabilities

### New Capabilities
- `speech-source-separation`: Opt-in pre-diarization stage that uses SpeechBrain SepFormer to decompose single-channel audio into per-speaker streams. Controlled by a campaign-level setting. Integrated into the diarization pipeline before VAD.

### Modified Capabilities
- `speaker-diarization`: Pipeline gains an optional first stage (source separation) before VAD. When enabled, VAD and embedding extraction run per separated stream rather than on the original mix. SSE progress events gain a `separation_start` / `separation_done` stage pair.
- `campaign-management`: Campaign settings gain a `source_separation_enabled` boolean (default false).
- `session-re-diarization`: Re-diarization must respect the campaign's `source_separation_enabled` setting.

## Impact

- **Dependencies**: Add `speechbrain` (Apache 2.0, CPU-capable, ~500MB model download on first use). Model cached locally under `~/.cache/speechbrain/`.
- **Database**: New `source_separation_enabled` boolean column on `campaigns` table. Migration required.
- **Backend**: New `src/talekeeper/services/separation.py` service. `diarization.py` calls it as stage 0 when enabled. `recording.py` and `transcripts.py` routers unchanged — SSE event vocabulary gains two new stage names only.
- **Frontend**: Campaign settings form gains a toggle for source separation with a warning about processing time. No changes to transcript or speaker panel views.
- **Processing time**: SepFormer on CPU adds roughly 0.5–1x real-time per session (a 30-minute session takes ~15–30 min extra). Acceptable for offline post-session processing.
- **No cloud services** — model runs entirely locally.
