"""
agents/main/media.py — Media helpers: image saving and voice transcription.
"""
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("media")

WHISPER_PROVIDER = os.getenv("WHISPER_PROVIDER", "none").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def save_photo(bot, file_id: str, dest_dir: Path) -> Path:
    """Download the highest-resolution Telegram photo and save to dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    tg_file = await bot.get_file(file_id)
    dest = dest_dir / f"photo_{file_id[:16]}.jpg"
    await tg_file.download_to_drive(str(dest))
    logger.info("Saved photo to %s", dest)
    return dest


async def transcribe_voice(bot, file_id: str) -> str:
    """Download voice/audio and return a transcript, or an explanatory string on failure."""
    if WHISPER_PROVIDER == "none":
        return "(voice transcription not configured — set WHISPER_PROVIDER=openai in .env)"
    try:
        tg_file = await bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        await tg_file.download_to_drive(str(tmp_path))
        transcript = await _transcribe(tmp_path)
        tmp_path.unlink(missing_ok=True)
        return transcript
    except Exception as e:
        logger.exception("Voice transcription failed: %s", e)
        return f"(transcription failed: {e})"


async def _transcribe(audio_path: Path) -> str:
    if WHISPER_PROVIDER == "openai":
        return await _transcribe_openai(audio_path)
    if WHISPER_PROVIDER == "local":
        return await _transcribe_local(audio_path)
    return "(unsupported WHISPER_PROVIDER value)"


async def _transcribe_openai(audio_path: Path) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    with open(audio_path, "rb") as f:
        result = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="text",
        )
    return str(result).strip()


async def _transcribe_local(audio_path: Path) -> str:
    import asyncio
    def _run() -> str:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path))
        return " ".join(s.text for s in segments).strip()
    return await asyncio.get_event_loop().run_in_executor(None, _run)
