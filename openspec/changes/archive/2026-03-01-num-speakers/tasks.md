## 1. Database schema

- [x] 1.1 Add `num_speakers INTEGER NOT NULL DEFAULT 4` column to the `campaigns` CREATE TABLE statement in `src/talekeeper/db/connection.py`
- [x] 1.2 Add ALTER TABLE migration (`ALTER TABLE campaigns ADD COLUMN num_speakers INTEGER NOT NULL DEFAULT 4`) with try/except in `ensure_tables()` for existing databases
- [x] 1.3 Update default from 4 to 5 and range from 1-20 to 1-10 in the CREATE TABLE statement and ALTER TABLE migration in `src/talekeeper/db/connection.py`

## 2. Backend models and validation

- [x] 2.1 Add `num_speakers: int = 4` with `Field(ge=1, le=20)` to `CampaignCreate` in `src/talekeeper/routers/campaigns.py`
- [x] 2.2 Add `num_speakers: int | None = None` with `Field(ge=1, le=20)` to `CampaignUpdate` in `src/talekeeper/routers/campaigns.py`
- [x] 2.3 Update default from 4 to 5 and validation range from `le=20` to `le=10` in `CampaignCreate` and `CampaignUpdate` Pydantic models
- [x] 2.4 Add `num_speakers: int | None = None` with `Field(ge=1, le=10)` to `RetranscribeRequest` in `src/talekeeper/routers/transcripts.py`, pass to diarization

## 3. Diarization integration

- [x] 3.1 In `run_final_diarization` (`src/talekeeper/services/diarization.py`), fetch the campaign's `num_speakers` from the DB using the session's `campaign_id`
- [x] 3.2 Pass the fetched `num_speakers` value through to `_cluster_embeddings` in the final diarization call chain
- [x] 3.3 Add optional `num_speakers_override` parameter to `run_final_diarization`; when provided, use it instead of the campaign's value

## 4. Frontend — campaign forms

- [x] 4.1 Add `num_speakers` number input (min 1, max 20, default 4) to the campaign create form in `frontend/src/routes/CampaignList.svelte`
- [x] 4.2 Add `num_speakers` number input to the campaign edit form in `frontend/src/routes/CampaignList.svelte`
- [x] 4.3 Add `num_speakers: number` to the `Campaign` type in `frontend/src/routes/CampaignDashboard.svelte`
- [x] 4.4 Update default from 4 to 5 and max from 20 to 10 in campaign create/edit forms in `frontend/src/routes/CampaignList.svelte`

## 5. Frontend — session-level override

- [x] 5.1 Add `num_speakers` number input to the retranscribe bar in `frontend/src/components/TranscriptView.svelte`, pre-filled with the campaign's `num_speakers`; pass `campaignId` from `SessionDetail`
- [x] 5.2 Add `num_speakers` number input to `RecordingControls.svelte`, pre-filled with the campaign's `num_speakers`; send in WS stop message and process-audio call

## 6. Backend — session-level override

- [x] 6.1 Read `num_speakers` from WS stop message and `process-audio` request in `routers/recording.py`, pass to `run_final_diarization`
- [x] 6.2 Read `num_speakers` from retranscribe request in `routers/transcripts.py`, pass to `run_final_diarization`

## 7. Verification

- [x] 7.1 Verify campaign create/edit round-trips `num_speakers` correctly via the API
- [x] 7.2 Verify `run_final_diarization` passes `num_speakers` to `_cluster_embeddings`
- [x] 7.3 Verify existing database migration applies default value of 4
- [x] 7.4 Verify default is 5 and range is 1-10 end-to-end (DB, API, frontend)
- [x] 7.5 Verify retranscribe with `num_speakers` override clusters into the overridden count
- [x] 7.6 Verify recording with `num_speakers` override uses the overridden count for final diarization
