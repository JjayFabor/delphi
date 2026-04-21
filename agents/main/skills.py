"""
agents/main/skills.py — Prompt-injection skill system.

Skills are markdown files in agents/main/skills/.
They are loaded into the system prompt on every turn — no restart needed.
Main can create, update, read, list, and delete skills via SDK tools.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger("skills")

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def load_all() -> str:
    """
    Return all skill contents joined for injection into the system prompt.
    Returns empty string if no skills exist.
    """
    SKILLS_DIR.mkdir(exist_ok=True)
    parts = []
    for f in sorted(SKILLS_DIR.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8").strip()
            if text:
                parts.append(f"### Skill: {f.stem}\n\n{text}")
        except Exception as e:
            logger.warning("Could not load skill %s: %s", f.name, e)
    return "\n\n---\n\n".join(parts)


def list_skills() -> list[dict]:
    SKILLS_DIR.mkdir(exist_ok=True)
    result = []
    for f in sorted(SKILLS_DIR.glob("*.md")):
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
            preview = next((l.strip() for l in lines if l.strip()), "")[:120]
            result.append({"name": f.stem, "preview": preview})
        except Exception:
            pass
    return result


def read_skill(name: str) -> str | None:
    path = SKILLS_DIR / f"{_safe(name)}.md"
    return path.read_text(encoding="utf-8") if path.exists() else None


def write_skill(name: str, content: str) -> str:
    """Create or overwrite a skill. Returns the filename written."""
    SKILLS_DIR.mkdir(exist_ok=True)
    path = SKILLS_DIR / f"{_safe(name)}.md"
    path.write_text(content.strip() + "\n", encoding="utf-8")
    logger.info("Skill written: %s", path.name)
    return path.name


def delete_skill(name: str) -> bool:
    path = SKILLS_DIR / f"{_safe(name)}.md"
    if path.exists():
        path.unlink()
        logger.info("Skill deleted: %s", path.name)
        return True
    return False


def _safe(name: str) -> str:
    """Convert a skill name to a safe filename stem."""
    return re.sub(r"[^\w-]", "-", name.lower()).strip("-")
