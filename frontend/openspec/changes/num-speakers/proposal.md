## Why

The recent clustering parameter tuning (cosine distance threshold 0.7 → 1.0) causes diarization to collapse all speakers into a single cluster. The fundamental issue is that unsupervised clustering guesses the speaker count — it either over-segments (10+ phantom speakers) or under-segments (everyone merged into one). Adding an explicit "number of speakers" setting eliminates this guessing by telling the clustering algorithm exactly how many speakers to find.

## What Changes

- Add a `num_speakers` field to campaigns with a default value (e.g., 4), so each campaign knows how many people are typically at the table
- Pass `num_speakers` through to the diarization clustering algorithm, which already supports it but never receives it
- Add the field to campaign creation and editing forms in the frontend
- No new dependencies — the clustering function (`_cluster_embeddings`) already accepts a `num_speakers` parameter that switches from threshold-based to fixed-count clustering

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `campaign-management`: Add `num_speakers` as a required campaign field with a default value, exposed in create/edit forms
- `speaker-diarization`: Use the campaign's `num_speakers` setting to control clustering instead of relying on the distance threshold for automatic speaker count detection

## Impact

- **Database**: New `num_speakers` column on `campaigns` table + migration for existing databases
- **Backend**: `services/diarization.py` (`run_final_diarization` fetches and passes `num_speakers`), `routers/campaigns.py` (create/update models)
- **Frontend**: `CampaignList.svelte` (create/edit forms), `CampaignDashboard.svelte` (type update)
- **No changes needed**: The three callers of `run_final_diarization` (recording.py x2, transcripts.py x1) remain unchanged — `num_speakers` is fetched internally from the campaign
