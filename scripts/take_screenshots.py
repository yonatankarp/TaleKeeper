"""
Auto-capture screenshots for the TaleKeeper user guide.

Seeds a temp database with mock data, starts the server, and uses
Playwright to navigate every page/state and capture screenshots.

Usage:
    .venv/bin/python scripts/take_screenshots.py
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import aiosqlite
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GUIDE_IMG_DIR = PROJECT_ROOT / "docs" / "guide" / "images"
VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python"
SERVER_PORT = 8099
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
APP_URL = f"{SERVER_URL}/#"

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

CAMPAIGN_NAME = "The Dragon's Bane Chronicles"
CAMPAIGN_DESC = "A tale of heroes who dare to challenge the ancient wyrm Pyratheon."
SESSION_1_NAME = "The Siege of Blackmoor"
SESSION_2_NAME = "Betrayal at the Crossroads"
SESSION_3_NAME = "Session 3"  # draft, unnamed

ROSTER = [
    ("Alex", "Theron Ashford", "A broad-shouldered human fighter with a crimson cloak, "
     "scarred jaw, and a greatsword etched with dwarven runes across his back."),
    ("Jordan", "Elara Moonwhisper", "A lithe half-elf ranger with silver-streaked auburn hair, "
     "emerald eyes, and a longbow of pale yew. She wears a cloak of forest green."),
    ("Sarah", "Dungeon Master", ""),
    ("Chris", "Brim Ironforge", "A stout dwarf cleric in polished chainmail bearing the "
     "hammer-and-anvil symbol of Moradin. Bushy red beard braided with silver clasps."),
]

TRANSCRIPT_LINES = [
    ("SPEAKER_00", "Sarah", "Dungeon Master",
     "The rain hammers against the windows of the Prancing Pony. You've been waiting for your contact for nearly an hour.", 0.0, 6.2),
    ("SPEAKER_01", "Alex", "Theron Ashford",
     "I lean back in my chair and scan the room. Anyone look suspicious?", 6.5, 10.1),
    ("SPEAKER_00", "Sarah", "Dungeon Master",
     "Roll perception.", 10.5, 11.8),
    ("SPEAKER_01", "Alex", "Theron Ashford",
     "That's a nineteen.", 12.0, 13.2),
    ("SPEAKER_00", "Sarah", "Dungeon Master",
     "You notice a hooded figure in the far corner, nursing a drink. They've been watching your table.", 13.5, 19.0),
    ("SPEAKER_02", "Jordan", "Elara Moonwhisper",
     "I cast Detect Magic, just in case. You can never be too careful in a place like this.", 19.5, 24.8),
    ("SPEAKER_00", "Sarah", "Dungeon Master",
     "A faint aura of enchantment glows around the figure's ring. Something is definitely not what it seems.", 25.0, 31.2),
    ("SPEAKER_03", "Chris", "Brim Ironforge",
     "By Moradin's beard. I grip my warhammer under the table. If things go south, I'm ready.", 31.5, 37.0),
    ("SPEAKER_01", "Alex", "Theron Ashford",
     "Easy, Brim. Let's not start a tavern brawl. Elara, can you get a closer look without being noticed?", 37.5, 43.2),
    ("SPEAKER_02", "Jordan", "Elara Moonwhisper",
     "I slip through the crowd toward the bar, trying to pass by their table. Stealth check — twenty-two.", 43.5, 50.1),
    ("SPEAKER_00", "Sarah", "Dungeon Master",
     "As you pass, the figure reaches out and catches your wrist. 'Sit down, ranger. I have what you're looking for.'", 50.5, 58.0),
    ("SPEAKER_02", "Jordan", "Elara Moonwhisper",
     "I freeze. How did they know what I am?", 58.5, 61.2),
    ("SPEAKER_00", "Sarah", "Dungeon Master",
     "The figure pushes back their hood. It's a drow — pale lavender skin, white hair. They slide a scroll across the table.", 61.5, 69.0),
]

SUMMARY_TEXT = """\
The party gathered at the Prancing Pony, a rain-soaked tavern on the edge of Blackmoor, \
to meet a mysterious contact who promised information about Pyratheon's lair. After an hour \
of tense waiting, Theron spotted a hooded figure watching them from the corner.

Elara's Detect Magic revealed an enchanted ring on the stranger, raising the party's suspicions. \
When Elara attempted to get a closer look, the figure — revealed to be a drow named Vizera — \
caught her wrist and produced a scroll bearing the seal of the Arcane Brotherhood.

The scroll contained a partial map of the Underdark passages leading to Pyratheon's volcanic \
sanctum, along with a warning: the dragon had acquired a *Staff of Power* from a fallen archmage. \
Vizera demanded payment — not gold, but a favor to be named later. After heated debate, the party \
agreed, though Brim voiced his distrust of making deals with drow.

Armed with the map, the party set out at dawn, following the Blackmoor road toward the \
mountain pass. The session ended as they spotted smoke rising from the village of Thornwall \
ahead — a grim sign that Pyratheon's forces were already on the move."""

POV_JOURNAL_THERON = """\
We arrived at the Prancing Pony as the storm broke. I hate waiting — every minute in that \
tavern felt like a trap closing around us. When I spotted the hooded figure in the corner, \
my hand went straight to my sword.

I should have trusted my instincts. A drow, of all things. Vizera, she called herself. \
Something about her sets my teeth on edge, but the map she provided is genuine — I can \
tell dwarven cartography when I see it. Brim confirmed the Underdark passages match old \
mining records.

A favor to be named later. I don't like open-ended debts, especially to a drow with an \
enchanted ring and connections to the Arcane Brotherhood. But we need that map. Pyratheon \
won't wait for us to find another way in.

The smoke over Thornwall troubles me most. If the dragon's forces have reached this far \
west, we may already be too late for some."""

POV_JOURNAL_ELARA = """\
The rain was a blessing — it covered my approach. Or it should have. The drow caught my \
wrist before I could even see her face clearly. She knew I was a ranger. She knew what we \
were looking for. That kind of foreknowledge is dangerous.

Her ring pulsed with enchantment magic — nothing I recognized. Transmutation, perhaps, or \
divination. I should have studied it more closely, but Theron was giving me the signal to \
stand down.

The map itself is fascinating. I've never seen the Underdark charted with such precision. \
If these passages are accurate, we can reach Pyratheon's sanctum in three days underground \
rather than two weeks over the mountains. But underground means no stars, no wind to guide \
us. I'll need to rely on Brim's stonecunning.

I don't trust Vizera's unnamed favor. In my experience, the price you don't know is always \
the one you can least afford to pay."""


def create_mock_image(path: Path, label: str) -> None:
    """Generate a placeholder fantasy-style image."""
    img = Image.new("RGB", (1024, 1024), color=(45, 30, 50))
    draw = ImageDraw.Draw(img)
    # gradient overlay
    for y in range(1024):
        r = int(45 + (90 - 45) * y / 1024)
        g = int(30 + (50 - 30) * y / 1024)
        b = int(50 + (80 - 50) * y / 1024)
        draw.line([(0, y), (1023, y)], fill=(r, g, b))
    # center text
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((1024 - tw) / 2, (1024 - th) / 2), label, fill=(200, 180, 140), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


async def seed_database(db_path: Path, data_dir: Path) -> dict:
    """Seed the database with rich mock data. Returns IDs for reference."""
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row

        # -- Settings (dismiss wizard for main screenshots, we'll re-enable) --
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('setup_dismissed', 'true')")
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('whisper_model', 'medium')")
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('live_transcription', 'false')")
        await db.execute(f"INSERT OR REPLACE INTO settings (key, value) VALUES ('data_dir', ?)", (str(data_dir),))

        # -- Campaign --
        cur = await db.execute(
            "INSERT INTO campaigns (name, description, language, num_speakers) VALUES (?, ?, ?, ?)",
            (CAMPAIGN_NAME, CAMPAIGN_DESC, "en", 4),
        )
        campaign_id = cur.lastrowid

        # -- Roster --
        roster_ids = {}
        for player, char, desc in ROSTER:
            cur = await db.execute(
                "INSERT INTO roster_entries (campaign_id, player_name, character_name, description, is_active) "
                "VALUES (?, ?, ?, ?, 1)",
                (campaign_id, player, char, desc),
            )
            roster_ids[char] = cur.lastrowid

        # -- Voice Signatures (for Theron and Elara) --
        await db.execute(
            "INSERT INTO voice_signatures (campaign_id, roster_entry_id, embedding, num_samples, created_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (campaign_id, roster_ids["Theron Ashford"], json.dumps([0.1] * 192), 12),
        )
        await db.execute(
            "INSERT INTO voice_signatures (campaign_id, roster_entry_id, embedding, num_samples, created_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (campaign_id, roster_ids["Elara Moonwhisper"], json.dumps([0.2] * 192), 8),
        )

        # -- Session 1 (completed, with everything) --
        cur = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date, status, language, session_number) "
            "VALUES (?, ?, ?, 'completed', 'en', ?)",
            (campaign_id, SESSION_1_NAME, "2026-02-15", 1),
        )
        session1_id = cur.lastrowid

        # Audio path (create a small valid webm later)
        audio_dir = data_dir / "audio" / str(campaign_id)
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"{session1_id}.webm"
        # minimal valid file
        audio_path.write_bytes(b"\x1a\x45\xdf\xa3" + b"\x00" * 100)
        await db.execute("UPDATE sessions SET audio_path = ? WHERE id = ?", (str(audio_path), session1_id))

        # Speakers
        speaker_ids = {}
        for label, player, char, *_ in TRANSCRIPT_LINES:
            if label not in speaker_ids:
                cur = await db.execute(
                    "INSERT INTO speakers (session_id, diarization_label, player_name, character_name) "
                    "VALUES (?, ?, ?, ?)",
                    (session1_id, label, player, char),
                )
                speaker_ids[label] = cur.lastrowid

        # Transcript segments
        for label, _player, _char, text, start, end in TRANSCRIPT_LINES:
            await db.execute(
                "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
                "VALUES (?, ?, ?, ?, ?)",
                (session1_id, speaker_ids[label], text, start, end),
            )

        # Crosstalk segment
        await db.execute(
            "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time, is_overlap) "
            "VALUES (?, NULL, '[crosstalk]', 37.0, 37.5, 1)",
            (session1_id,),
        )

        # Summaries
        await db.execute(
            "INSERT INTO summaries (session_id, type, content, model_used) VALUES (?, 'full', ?, 'llama3.1:8b')",
            (session1_id, SUMMARY_TEXT),
        )
        # POV journals
        theron_speaker = speaker_ids["SPEAKER_01"]
        elara_speaker = speaker_ids["SPEAKER_02"]
        await db.execute(
            "INSERT INTO summaries (session_id, type, speaker_id, content, model_used) "
            "VALUES (?, 'character', ?, ?, 'llama3.1:8b')",
            (session1_id, theron_speaker, POV_JOURNAL_THERON),
        )
        await db.execute(
            "INSERT INTO summaries (session_id, type, speaker_id, content, model_used) "
            "VALUES (?, 'character', ?, ?, 'llama3.1:8b')",
            (session1_id, elara_speaker, POV_JOURNAL_ELARA),
        )

        # Images
        img_dir = data_dir / "images" / str(session1_id)
        img1_name = f"{uuid.uuid4().hex}.png"
        img1_path = img_dir / img1_name
        create_mock_image(img1_path, "The Prancing Pony")
        await db.execute(
            "INSERT INTO session_images (session_id, file_path, prompt, scene_description, model_used) "
            "VALUES (?, ?, ?, ?, ?)",
            (session1_id, str(img1_path),
             "A dark rainy tavern scene with hooded figures",
             "The rain-lashed Prancing Pony tavern, warm light spilling from windows",
             "flux2-klein:9b"),
        )

        img2_name = f"{uuid.uuid4().hex}.png"
        img2_path = img_dir / img2_name
        create_mock_image(img2_path, "The Drow Revealed")
        await db.execute(
            "INSERT INTO session_images (session_id, file_path, prompt, scene_description, model_used) "
            "VALUES (?, ?, ?, ?, ?)",
            (session1_id, str(img2_path),
             "A drow woman revealing a scroll in a dimly lit tavern corner",
             "Vizera the drow pushes back her hood, sliding an ancient scroll across the table",
             "flux2-klein:9b"),
        )

        # -- Session 2 (completed, less data) --
        cur = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date, status, language, session_number) "
            "VALUES (?, ?, ?, 'completed', 'en', ?)",
            (campaign_id, SESSION_2_NAME, "2026-02-22", 2),
        )
        session2_id = cur.lastrowid

        # -- Session 3 (draft) --
        cur = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date, status, language, session_number) "
            "VALUES (?, ?, ?, 'draft', 'en', ?)",
            (campaign_id, SESSION_3_NAME, "2026-03-01", 3),
        )
        session3_id = cur.lastrowid

        await db.commit()

        return {
            "campaign_id": campaign_id,
            "session1_id": session1_id,
            "session2_id": session2_id,
            "session3_id": session3_id,
            "roster_ids": roster_ids,
            "speaker_ids": speaker_ids,
        }


async def init_temp_db(db_path: Path) -> None:
    """Create schema by importing talekeeper's init_db with our path."""
    # We'll set the env var so talekeeper uses our temp dir
    from talekeeper.db.connection import init_db
    await init_db()


def start_server(cwd: Path) -> subprocess.Popen:
    """Start TaleKeeper server on SERVER_PORT with given CWD.

    The CWD determines where ``data/db/talekeeper.db`` resolves to.
    We symlink ``data/`` into the project root's temp dir so the server
    finds the DB while still having access to the installed package.
    """
    env = os.environ.copy()
    # User data dir (audio, images) also lives under data/ in cwd
    env["TALEKEEPER_DATA_DIR"] = str(cwd / "data")
    proc = subprocess.Popen(
        [str(VENV_PYTHON), "-m", "talekeeper", "serve",
         "--port", str(SERVER_PORT), "--no-browser"],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def wait_for_server(timeout: int = 30) -> bool:
    """Poll until the server responds."""
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{SERVER_URL}/api/campaigns", timeout=2)
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------

async def capture_screenshots(ids: dict, db_path: Path) -> None:
    """Navigate the app with Playwright and capture all screenshots."""
    from playwright.async_api import async_playwright

    GUIDE_IMG_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Use dark mode (slate theme) for consistency
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            color_scheme="dark",
        )
        page = await context.new_page()

        campaign_id = ids["campaign_id"]
        session1_id = ids["session1_id"]

        async def screenshot(name: str, delay: float = 0.5) -> None:
            await page.wait_for_timeout(int(delay * 1000))
            path = GUIDE_IMG_DIR / f"{name}.png"
            await page.screenshot(path=str(path))
            print(f"  captured: {name}.png")

        async def screenshot_element(selector: str, name: str, delay: float = 0.5) -> None:
            await page.wait_for_timeout(int(delay * 1000))
            elem = page.locator(selector).first
            path = GUIDE_IMG_DIR / f"{name}.png"
            await elem.screenshot(path=str(path))
            print(f"  captured: {name}.png (element)")

        # ---------------------------------------------------------------
        # 1. Home page (campaign list)
        # ---------------------------------------------------------------
        print("\n--- Home Page ---")
        await page.goto(f"{APP_URL}/")
        await page.wait_for_timeout(1000)
        await screenshot("home-screen")

        # Campaign creation form
        try:
            await page.click('button:has-text("New Campaign")', timeout=3000)
            await page.wait_for_timeout(500)
            await screenshot("campaign-creation-form")
            await page.click('button:has-text("Cancel")', timeout=3000)
        except Exception as e:
            print(f"  skipped campaign creation form: {e}")

        # ---------------------------------------------------------------
        # 3. Campaign Dashboard
        # ---------------------------------------------------------------
        print("\n--- Campaign Dashboard ---")
        await page.goto(f"{APP_URL}/campaigns/{campaign_id}")
        await page.wait_for_timeout(1000)
        await screenshot("campaign-dashboard")

        # ---------------------------------------------------------------
        # 4. Roster page
        # ---------------------------------------------------------------
        print("\n--- Roster ---")
        await page.goto(f"{APP_URL}/campaigns/{campaign_id}/roster")
        await page.wait_for_timeout(1000)
        await screenshot("roster-page")

        # ---------------------------------------------------------------
        # Helper: navigate to session tab using keyboard shortcut
        # Reloads the session page each time for a clean state.
        # ---------------------------------------------------------------
        async def goto_session_tab(session_id: int, tab_key: str, wait: float = 1.5) -> None:
            """Navigate to a session page and switch to a tab via keyboard."""
            await page.goto(f"{APP_URL}/sessions/{session_id}")
            await page.wait_for_timeout(1500)  # let SPA render
            # Use the tab-bar button with exact class to avoid breadcrumb confusion
            tab_bar = page.locator(".tab-bar")
            await tab_bar.wait_for(timeout=5000)
            # Press the keyboard shortcut (1-5) on the body
            await page.press("body", tab_key)
            await page.wait_for_timeout(int(wait * 1000))

        # ---------------------------------------------------------------
        # 5. Session Detail — Recording tab (idle)
        # ---------------------------------------------------------------
        print("\n--- Session Detail ---")
        await goto_session_tab(session1_id, "1")
        await screenshot("recording-tab-idle")

        # ---------------------------------------------------------------
        # 6. Chronicle tab (transcript)
        # ---------------------------------------------------------------
        print("\n--- Chronicle ---")
        await goto_session_tab(session1_id, "2")
        await screenshot("chronicle-tab")

        # Expand the Speakers panel (starts collapsed) then screenshot
        try:
            await page.click('.speaker-panel .panel-header', timeout=3000)
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"  could not expand speakers panel: {e}")
        await screenshot("speaker-panel")

        # ---------------------------------------------------------------
        # 7. Tales tab (summaries)
        # ---------------------------------------------------------------
        print("\n--- Tales ---")
        await goto_session_tab(session1_id, "3")
        await screenshot("tales-tab")

        # Scroll down for POV journals if they're below fold
        await page.evaluate("window.scrollBy(0, 600)")
        await page.wait_for_timeout(500)
        await screenshot("pov-journals")
        await page.evaluate("window.scrollTo(0, 0)")

        # ---------------------------------------------------------------
        # 8. Visions tab (illustrations)
        # ---------------------------------------------------------------
        print("\n--- Visions ---")
        await goto_session_tab(session1_id, "4")
        await screenshot("visions-tab")

        # ---------------------------------------------------------------
        # 9. Export tab
        # ---------------------------------------------------------------
        print("\n--- Export ---")
        await goto_session_tab(session1_id, "5")
        await screenshot("export-tab")

        # ---------------------------------------------------------------
        # 10. Draft session (Recording tab with upload)
        # ---------------------------------------------------------------
        print("\n--- Draft Session ---")
        session3_id = ids["session3_id"]
        await page.goto(f"{APP_URL}/sessions/{session3_id}")
        await page.wait_for_timeout(1000)
        await screenshot("recording-tab-draft")

        # ---------------------------------------------------------------
        # 11. Settings page
        # ---------------------------------------------------------------
        print("\n--- Settings ---")
        # Use a tall viewport so the SPA's scrollable container shows all content
        await page.set_viewport_size({"width": 1440, "height": 2400})
        await page.goto(f"{APP_URL}/settings")
        await page.wait_for_timeout(1000)
        path = GUIDE_IMG_DIR / "settings-page.png"
        await page.screenshot(path=str(path))
        print(f"  captured: settings-page.png (tall viewport)")
        # Restore normal viewport
        await page.set_viewport_size({"width": 1440, "height": 900})

        # ---------------------------------------------------------------
        # 12. Setup Wizard (last, since it requires removing setup_dismissed)
        # ---------------------------------------------------------------
        # ---------------------------------------------------------------
        # Done with main screenshots — close this context
        # ---------------------------------------------------------------
        await browser.close()

        # ---------------------------------------------------------------
        # 12. Setup Wizard — needs a fresh browser so the SPA re-checks
        #     /setup-status on mount (the old context cached dismissed=true)
        # ---------------------------------------------------------------
        print("\n--- Setup Wizard ---")
        async with aiosqlite.connect(str(db_path)) as db:
            await db.execute("DELETE FROM settings WHERE key = 'setup_dismissed'")
            await db.commit()

        browser = await p.chromium.launch()
        ctx2 = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            color_scheme="dark",
        )
        page2 = await ctx2.new_page()
        await page2.goto(f"{APP_URL}/")
        await page2.wait_for_timeout(2500)

        # Verify the wizard is visible before screenshotting
        try:
            await page2.wait_for_selector(".wizard-overlay", timeout=5000)
            print("  wizard overlay detected")
        except Exception:
            print("  WARNING: wizard overlay not found")

        path = GUIDE_IMG_DIR / "setup-wizard-overlay.png"
        await page2.screenshot(path=str(path))
        print(f"  captured: setup-wizard-overlay.png")

        await browser.close()

    print(f"\nAll screenshots saved to: {GUIDE_IMG_DIR}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def async_main() -> None:
    tmp_dir = tempfile.mkdtemp(prefix="talekeeper-screenshots-")
    tmp_path = Path(tmp_dir)
    # The DB is always at `data/db/talekeeper.db` relative to CWD,
    # so we create that structure inside our temp dir and set CWD for the server.
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_dir = data_dir / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "talekeeper.db"

    print(f"Temp dir: {tmp_dir}")

    # Set env before importing talekeeper modules
    os.environ["TALEKEEPER_DATA_DIR"] = str(data_dir)

    # Add src to path so we can import talekeeper
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

    # Monkey-patch the internal dir so init_db uses our temp path
    import talekeeper.paths as tp
    tp._INTERNAL_DIR = data_dir
    tp.set_user_data_dir(str(data_dir))

    # Initialize DB schema
    print("Initializing database...")
    await init_temp_db(db_path)

    # Seed mock data
    print("Seeding mock data...")
    ids = await seed_database(db_path, data_dir)
    print(f"  Campaign: {ids['campaign_id']}")
    print(f"  Sessions: {ids['session1_id']}, {ids['session2_id']}, {ids['session3_id']}")

    # Start server with CWD = tmp_dir so `data/db/talekeeper.db` resolves correctly
    print(f"Starting server on port {SERVER_PORT}...")
    server_proc = start_server(tmp_path)

    try:
        if not wait_for_server():
            stderr = server_proc.stderr.read().decode() if server_proc.stderr else ""
            print(f"Server failed to start!\n{stderr}")
            return

        print("Server is ready!")

        # Capture screenshots
        await capture_screenshots(ids, db_path)

    finally:
        print("Stopping server...")
        server_proc.send_signal(signal.SIGTERM)
        server_proc.wait(timeout=10)

        # Clean up temp dir
        print(f"Cleaning up {tmp_dir}")
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
