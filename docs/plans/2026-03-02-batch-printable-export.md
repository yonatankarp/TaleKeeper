# Batch Printable Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing `export/pov-all` endpoint to export all session summaries (full + POV) as printable PDFs in a ZIP.

**Architecture:** Rename and extend the `export_all_pov` endpoint to `export_all_summaries`, removing the POV-only filter and adding a `printable` query parameter. Update the frontend button to use the new endpoint with `printable=true`.

**Tech Stack:** FastAPI, WeasyPrint, Svelte 5

---

### Task 1: Backend — Extend the export endpoint

**Files:**
- Modify: `src/talekeeper/routers/exports.py:308-344`

**Step 1: Rename and extend the endpoint**

Replace the `export_all_pov` function (lines 308-344) with:

```python
@router.get("/api/sessions/{session_id}/export/summaries-all")
async def export_all_summaries(session_id: int, printable: bool = False) -> StreamingResponse:
    from weasyprint import HTML

    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT su.*, s.name as session_name, s.date as session_date,
                      c.name as campaign_name, sp.character_name, sp.player_name
               FROM summaries su
               JOIN sessions s ON s.id = su.session_id
               JOIN campaigns c ON c.id = s.campaign_id
               LEFT JOIN speakers sp ON sp.id = su.speaker_id
               WHERE su.session_id = ?""",
            (session_id,),
        )

    if not rows:
        raise HTTPException(status_code=404, detail="No summaries found")

    image_bytes = None if printable else await _get_latest_session_image(session_id)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            summary = dict(row)
            content_html = _content_to_html(summary["content"])
            html = _build_pdf_html(summary, content_html, image_bytes, printable=printable)
            pdf_bytes = HTML(string=html).write_pdf()
            if summary["type"] == "pov":
                char_name = (summary.get("character_name") or "unknown").lower().replace(" ", "-")
                zf.writestr(f"{char_name}-pov.pdf", pdf_bytes)
            else:
                zf.writestr("session-chronicle.pdf", pdf_bytes)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="summaries.zip"'},
    )
```

Key differences from original:
- Route path changed from `export/pov-all` to `export/summaries-all`
- Function renamed from `export_all_pov` to `export_all_summaries`
- Added `printable: bool = False` parameter
- Removed `AND su.type = 'pov'` from SQL query
- `image_bytes` is `None` when `printable=True` (consistent with single-PDF behavior)
- Passes `printable=printable` to `_build_pdf_html`
- File naming: full summaries → `session-chronicle.pdf`, POV → `{char}-pov.pdf`
- ZIP filename changed to `summaries.zip`
- Error message changed to "No summaries found"

**Step 2: Run existing tests to verify nothing else broke**

Run: `cd /Users/yonatankarp-rudin/Projects/TaleKeeper && python -m pytest tests/routers/test_exports.py -v`
Expected: All existing tests PASS (none test the `pov-all` endpoint directly)

**Step 3: Commit**

```bash
git add src/talekeeper/routers/exports.py
git commit -m "feat: extend pov-all export to all summaries with printable option"
```

---

### Task 2: Backend — Add test for the new endpoint

**Files:**
- Modify: `tests/routers/test_exports.py`

**Step 1: Write tests for the new endpoint**

Add to the end of `tests/routers/test_exports.py`:

```python
@pytest.mark.asyncio
@patch("weasyprint.HTML")
async def test_export_summaries_all(mock_html_cls, client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/summaries-all returns ZIP with all summary PDFs."""
    mock_html_cls.return_value.write_pdf.return_value = b"fake-pdf-bytes"

    async with get_db() as db:
        ids = await _seed(db)
        # Add a POV summary
        await db.execute(
            "INSERT INTO summaries (session_id, type, speaker_id, content, model_used) "
            "VALUES (?, 'pov', ?, 'Gandalf saw the battle.', 'test-model')",
            (ids["session_id"], ids["speaker_id"]),
        )
        await db.commit()

    resp = await client.get(f"/api/sessions/{ids['session_id']}/export/summaries-all")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    import zipfile as zf
    buf = __import__("io").BytesIO(resp.content)
    with zf.ZipFile(buf) as z:
        names = z.namelist()
        assert "session-chronicle.pdf" in names
        assert "gandalf-pov.pdf" in names
        assert len(names) == 2


@pytest.mark.asyncio
@patch("weasyprint.HTML")
async def test_export_summaries_all_printable(mock_html_cls, client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/summaries-all?printable=true uses printable styling."""
    mock_html_cls.return_value.write_pdf.return_value = b"fake-pdf-bytes"

    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/sessions/{ids['session_id']}/export/summaries-all?printable=true")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    # Verify the HTML passed to weasyprint contains printable styling
    call_args = mock_html_cls.call_args
    html_string = call_args[1]["string"] if "string" in call_args[1] else call_args[0][0]
    assert "background: #fff;" in html_string


@pytest.mark.asyncio
async def test_export_summaries_all_empty(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/summaries-all returns 404 when no summaries exist."""
    async with get_db() as db:
        cursor = await db.execute("INSERT INTO campaigns (name) VALUES ('C')")
        cid = cursor.lastrowid
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'S', '2025-01-01')",
            (cid,),
        )
        sid = cursor.lastrowid
        await db.commit()

    resp = await client.get(f"/api/sessions/{sid}/export/summaries-all")
    assert resp.status_code == 404
```

**Step 2: Run new tests**

Run: `cd /Users/yonatankarp-rudin/Projects/TaleKeeper && python -m pytest tests/routers/test_exports.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/routers/test_exports.py
git commit -m "test: add tests for summaries-all export endpoint"
```

---

### Task 3: Frontend — Update export button

**Files:**
- Modify: `frontend/src/components/ExportSection.svelte`

**Step 1: Move batch export button and update URL**

In `ExportSection.svelte`, the current "Export All POV Summaries (ZIP)" button (lines 102-104) is inside the `{#if povSummaries.length > 0}` block. Changes:

1. Add a new top-level batch export button right after the transcript export section (after line 85), before the fullSummaries section:

```svelte
  {#if summaries.length > 0}
    <h3>Batch Export</h3>
    <button class="btn" onclick={() => downloadFile(`/api/sessions/${sessionId}/export/summaries-all?printable=true`)}>
      Export All Printable (ZIP)
    </button>
  {/if}
```

2. Remove the old "Export All POV Summaries (ZIP)" button (lines 102-104):

```svelte
    <button class="btn" onclick={() => downloadFile(`/api/sessions/${sessionId}/export/pov-all`)}>
      Export All POV Summaries (ZIP)
    </button>
```

**Step 2: Verify frontend builds**

Run: `cd /Users/yonatankarp-rudin/Projects/TaleKeeper/frontend && npm run build`
Expected: Build succeeds with no errors

**Step 3: Commit**

```bash
git add frontend/src/components/ExportSection.svelte
git commit -m "feat: update export button for batch printable download"
```
