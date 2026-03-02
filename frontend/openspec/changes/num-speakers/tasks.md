## 1. Database

- [ ] 1.1 Add `num_speakers INTEGER NOT NULL DEFAULT 5` to campaigns table in `_SCHEMA` in `db/connection.py`
- [ ] 1.2 Add `_migrate_add_num_speakers_column` migration function and register it in `_apply_schema`

## 2. Campaign API

- [ ] 2.1 Add `num_speakers: int = 5` to `CampaignCreate` model with validator (2-10) in `routers/campaigns.py`
- [ ] 2.2 Add `num_speakers: int | None = None` to `CampaignUpdate` model with validator (2-10)
- [ ] 2.3 Include `num_speakers` in the INSERT SQL in `create_campaign` endpoint
- [ ] 2.4 Include `num_speakers` in the dynamic UPDATE logic in `update_campaign` endpoint

## 3. Diarization

- [ ] 3.1 Update `diarize()` function signature to accept optional `num_speakers` parameter and forward to `_run_pipeline`
- [ ] 3.2 In `run_final_diarization`, fetch `num_speakers` from the campaigns table and pass it to `diarize()` in the clustering fallback branch

## 4. Frontend

- [ ] 4.1 Add `num_speakers` number input (min=2, max=10, default=5) to campaign create form in `CampaignList.svelte`
- [ ] 4.2 Add `num_speakers` number input to campaign edit form in `CampaignList.svelte`
- [ ] 4.3 Include `num_speakers` in create and edit API calls
- [ ] 4.4 Update `Campaign` type in `CampaignDashboard.svelte` to include `num_speakers`
