"""Scene description and image generation pipeline service."""

import uuid

from talekeeper.db import get_db
from talekeeper.paths import get_session_images_dir
from talekeeper.services import llm_client, image_client

SCENE_DESCRIPTION_SYSTEM = """You are a visual scene describer for tabletop RPG sessions.
Your job is to read a session transcript or summary and craft a single vivid, concise
image generation prompt that captures the most dramatic or memorable moment from the session.

Guidelines:
- Write a single paragraph (2-4 sentences) describing a specific visual scene
- Use descriptive, painterly language: lighting, colors, composition, mood
- Include character appearances, setting details, and action if present
- Style: epic fantasy illustration, detailed, dramatic lighting
- Do NOT include text, speech bubbles, or written words in the scene
- Do NOT use meta-instructions like "generate an image of..." — just describe the scene directly
- Focus on one key moment, not the entire session"""

SCENE_DESCRIPTION_PROMPT = """Based on the following session content, write a vivid scene description
suitable for AI image generation. Pick the single most dramatic or memorable moment and describe
it visually.

SESSION CONTENT:
{content}

Write a concise, vivid scene description (2-4 sentences):"""


async def craft_scene_description(
    content: str,
    base_url: str,
    api_key: str | None,
    model: str,
) -> str:
    """Use the text LLM to craft an image generation prompt from session content."""
    prompt = SCENE_DESCRIPTION_PROMPT.format(content=content)
    return await llm_client.generate(base_url, api_key, model, prompt, system=SCENE_DESCRIPTION_SYSTEM)


async def generate_session_image(
    session_id: int,
    prompt: str,
    scene_description: str | None = None,
) -> dict:
    """Generate an image using the image provider and save it to disk + DB.

    Args:
        session_id: The session this image belongs to.
        prompt: The final prompt to send to the image generator.
        scene_description: The original LLM-crafted description (if prompt was edited).

    Returns:
        The image metadata dict from the database.
    """
    # Resolve image provider config
    config = await image_client.resolve_config()
    img_base_url, img_api_key, img_model = config["base_url"], config["api_key"], config["model"]

    # Generate image
    image_bytes = await image_client.generate_image(img_base_url, img_api_key, img_model, prompt)

    # Save to disk
    images_dir = get_session_images_dir(session_id)
    filename = f"{uuid.uuid4()}.png"
    file_path = images_dir / filename
    file_path.write_bytes(image_bytes)

    # Save metadata to DB
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO session_images (session_id, file_path, prompt, scene_description, model_used)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, str(file_path), prompt, scene_description, img_model),
        )
        rows = await db.execute_fetchall(
            "SELECT * FROM session_images WHERE id = ?", (cursor.lastrowid,)
        )
    return dict(rows[0])
