"""Audio merging service: concatenate multiple audio parts into a single file."""

import asyncio
import shutil
import subprocess
from pathlib import Path

from talekeeper.db import get_db


async def merge_audio_parts(session_id: int, output_path: Path) -> Path:
    """Fetch ordered audio parts from DB, merge via ffmpeg concat, return output path.

    Single-part case: copy file directly without invoking ffmpeg.
    Multi-part case: use ffmpeg concat demuxer with re-encoding to WAV.

    Raises ValueError if session has no audio parts.
    Raises RuntimeError if ffmpeg fails.
    """
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT file_path FROM session_audio_files WHERE session_id = ? ORDER BY sort_order",
            (session_id,),
        )

    if not rows:
        raise ValueError("No audio parts for this session")

    parts = [Path(row["file_path"]) for row in rows]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Single-part fast path: copy directly without invoking ffmpeg concat
    if len(parts) == 1:
        shutil.copy2(parts[0], output_path)
        return output_path

    # Multi-part: use ffmpeg concat demuxer
    filelist_path = output_path.parent / f"_concat_{session_id}.txt"
    try:
        with open(filelist_path, "w") as f:
            for p in parts:
                f.write(f"file '{str(p.resolve())}'\n")

        def _run_ffmpeg() -> None:
            import subprocess as _subprocess
            result = _subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(filelist_path),
                    "-ar", "44100",
                    "-ac", "1",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr}")

        await asyncio.to_thread(_run_ffmpeg)
    finally:
        if filelist_path.exists():
            filelist_path.unlink()

    return output_path
