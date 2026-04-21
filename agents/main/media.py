"""
agents/main/media.py — Media helpers: image saving, voice transcription, document handling.
"""
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("media")

WHISPER_PROVIDER = os.getenv("WHISPER_PROVIDER", "none").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# File extensions we can extract readable text from for Claude
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".env", ".sh", ".bash", ".html", ".htm", ".xml",
    ".css", ".sql", ".rs", ".go", ".java", ".c", ".cpp", ".h", ".csv", ".log",
}


async def save_photo(bot, file_id: str, dest_dir: Path) -> Path:
    """Download the highest-resolution Telegram photo and save to dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    tg_file = await bot.get_file(file_id)
    dest = dest_dir / f"photo_{file_id[:16]}.jpg"
    await tg_file.download_to_drive(str(dest))
    logger.info("Saved photo to %s", dest)
    return dest


async def save_document(bot, file_id: str, filename: str, dest_dir: Path) -> Path:
    """Download a Telegram document and save to dest_dir with its original filename."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    tg_file = await bot.get_file(file_id)
    # Sanitise filename — keep extension, replace unsafe chars
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    dest = dest_dir / safe_name
    # Avoid collisions
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        dest = dest_dir / f"{stem}_{file_id[:8]}{suffix}"
    await tg_file.download_to_drive(str(dest))
    logger.info("Saved document to %s", dest)
    return dest


def extract_text(path: Path, max_chars: int = 40_000) -> tuple[str, bool]:
    """
    Extract readable text from a saved file.

    Returns (text, is_extractable):
      - is_extractable=True  → text contains the file contents (truncated if large)
      - is_extractable=False → file is binary/unsupported; text is a brief description
    """
    suffix = path.suffix.lower()

    if suffix in _TEXT_EXTENSIONS:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
            if len(raw) > max_chars:
                raw = raw[:max_chars] + f"\n\n[... truncated at {max_chars:,} chars ...]"
            return raw, True
        except Exception as e:
            return f"(could not read file: {e})", False

    if suffix == ".pdf":
        return _extract_pdf(path, max_chars)

    return f"(binary file — {path.suffix} format not extractable as text)", False


def _extract_pdf(path: Path, max_chars: int) -> tuple[str, bool]:
    """Extract text from a PDF using pypdf (optional dependency)."""
    try:
        import pypdf
    except ImportError:
        return (
            "(PDF received — install pypdf to enable text extraction: pip install pypdf)",
            False,
        )
    try:
        reader = pypdf.PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
        combined = "\n\n".join(pages)
        if len(combined) > max_chars:
            combined = combined[:max_chars] + f"\n\n[... truncated at {max_chars:,} chars ...]"
        if not combined.strip():
            return "(PDF appears to be image-based — no extractable text)", False
        return combined, True
    except Exception as e:
        return f"(PDF extraction failed: {e})", False


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
