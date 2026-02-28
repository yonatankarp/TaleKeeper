"""Export and sharing API endpoints."""

import io
import smtplib
import zipfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from talekeeper.db import get_db

router = APIRouter(tags=["exports"])

PDF_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: Georgia, serif; max-width: 700px; margin: 2rem auto; color: #222; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 2rem; }}
  .content {{ line-height: 1.8; white-space: pre-wrap; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">{meta}</div>
  <div class="content">{content}</div>
</body>
</html>
"""


async def _get_summary_with_meta(summary_id: int) -> dict:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT su.*, s.name as session_name, s.date as session_date,
                      c.name as campaign_name, sp.character_name, sp.player_name
               FROM summaries su
               JOIN sessions s ON s.id = su.session_id
               JOIN campaigns c ON c.id = s.campaign_id
               LEFT JOIN speakers sp ON sp.id = su.speaker_id
               WHERE su.id = ?""",
            (summary_id,),
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Summary not found")
    return dict(rows[0])


def _build_title(summary: dict) -> str:
    if summary["type"] == "pov" and summary.get("character_name"):
        return f"{summary['character_name']}'s Recap — {summary['session_name']}"
    return f"Session Summary — {summary['session_name']}"


def _build_meta(summary: dict) -> str:
    parts = [summary["campaign_name"], summary["session_date"]]
    if summary.get("player_name"):
        parts.append(f"Player: {summary['player_name']}")
    parts.append(f"Model: {summary['model_used']}")
    return " | ".join(parts)


@router.get("/api/summaries/{summary_id}/export/pdf")
async def export_pdf(summary_id: int) -> Response:
    from weasyprint import HTML

    summary = await _get_summary_with_meta(summary_id)

    title = _build_title(summary)
    meta = _build_meta(summary)
    html = PDF_TEMPLATE.format(title=title, meta=meta, content=summary["content"])

    pdf_bytes = HTML(string=html).write_pdf()

    filename = f"{title.replace(' ', '-').lower()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/summaries/{summary_id}/export/text")
async def export_text(summary_id: int) -> Response:
    summary = await _get_summary_with_meta(summary_id)

    title = _build_title(summary)
    meta = _build_meta(summary)
    text = f"{title}\n{'=' * len(title)}\n{meta}\n\n{summary['content']}"

    filename = f"{title.replace(' ', '-').lower()}.txt"
    return Response(
        content=text,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/sessions/{session_id}/export/pov-all")
async def export_all_pov(session_id: int) -> StreamingResponse:
    from weasyprint import HTML

    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT su.*, s.name as session_name, s.date as session_date,
                      c.name as campaign_name, sp.character_name, sp.player_name
               FROM summaries su
               JOIN sessions s ON s.id = su.session_id
               JOIN campaigns c ON c.id = s.campaign_id
               LEFT JOIN speakers sp ON sp.id = su.speaker_id
               WHERE su.session_id = ? AND su.type = 'pov'""",
            (session_id,),
        )

    if not rows:
        raise HTTPException(status_code=404, detail="No POV summaries found")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            summary = dict(row)
            title = _build_title(summary)
            meta = _build_meta(summary)
            html = PDF_TEMPLATE.format(title=title, meta=meta, content=summary["content"])
            pdf_bytes = HTML(string=html).write_pdf()
            char_name = (summary.get("character_name") or "unknown").lower().replace(" ", "-")
            zf.writestr(f"{char_name}-pov.pdf", pdf_bytes)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="pov-summaries.zip"'},
    )


@router.get("/api/sessions/{session_id}/export/transcript")
async def export_transcript(session_id: int) -> Response:
    async with get_db() as db:
        session_rows = await db.execute_fetchall(
            """SELECT s.name, s.date, c.name as campaign_name
               FROM sessions s JOIN campaigns c ON c.id = s.campaign_id
               WHERE s.id = ?""",
            (session_id,),
        )
        if not session_rows:
            raise HTTPException(status_code=404, detail="Session not found")

        seg_rows = await db.execute_fetchall(
            """SELECT ts.text, ts.start_time, ts.end_time,
                      sp.player_name, sp.character_name
               FROM transcript_segments ts
               LEFT JOIN speakers sp ON sp.id = ts.speaker_id
               WHERE ts.session_id = ?
               ORDER BY ts.start_time""",
            (session_id,),
        )

    session = dict(session_rows[0])
    lines = [f"Transcript: {session['name']}", f"Campaign: {session['campaign_name']}", f"Date: {session['date']}", ""]

    for seg in seg_rows:
        s = dict(seg)
        h = int(s["start_time"] // 3600)
        m = int((s["start_time"] % 3600) // 60)
        sec = int(s["start_time"] % 60)
        time_str = f"{h:02d}:{m:02d}:{sec:02d}"

        speaker = ""
        if s.get("character_name") and s.get("player_name"):
            speaker = f" {s['character_name']} ({s['player_name']}):"
        elif s.get("character_name"):
            speaker = f" {s['character_name']}:"

        lines.append(f"[{time_str}]{speaker} {s['text']}")

    text = "\n".join(lines)
    return Response(
        content=text,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="transcript-{session_id}.txt"'},
    )


@router.get("/api/summaries/{summary_id}/email-content")
async def email_content(summary_id: int) -> dict:
    summary = await _get_summary_with_meta(summary_id)
    title = _build_title(summary)

    return {
        "subject": title,
        "body": summary["content"],
        "meta": _build_meta(summary),
    }


class SendEmailRequest(BaseModel):
    to: str


@router.post("/api/summaries/{summary_id}/send-email")
async def send_email(summary_id: int, body: SendEmailRequest) -> dict:
    summary = await _get_summary_with_meta(summary_id)
    title = _build_title(summary)

    # Get SMTP settings
    async with get_db() as db:
        settings_rows = await db.execute_fetchall("SELECT key, value FROM settings")
        settings = {r["key"]: r["value"] for r in settings_rows}

    smtp_host = settings.get("smtp_host")
    smtp_port = int(settings.get("smtp_port", "587"))
    smtp_user = settings.get("smtp_username")
    smtp_pass = settings.get("smtp_password")
    sender = settings.get("smtp_sender")

    if not all([smtp_host, smtp_user, smtp_pass, sender]):
        raise HTTPException(
            status_code=400,
            detail="Email not configured. Set SMTP settings in the Settings page.",
        )

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = body.to
    msg["Subject"] = title
    msg.attach(MIMEText(summary["content"], "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")

    return {"sent": True}
