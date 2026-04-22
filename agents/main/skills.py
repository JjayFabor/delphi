"""
agents/main/skills.py — Prompt-injection skill system.

Skills are markdown files in agents/main/skills/.
Skills without frontmatter (or with always: true) are injected every turn.
Skills with triggers: [...] are injected only when a trigger word matches the message.
Main can create, update, read, list, and delete skills via SDK tools.

Frontmatter format (optional):
    ---
    always: false
    triggers: [backlog, report, schedule]
    description: Daily backlog report scheduling
    ---
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger("skills")

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def _parse_skill(path: Path) -> dict:
    """Return parsed metadata + content for a skill file."""
    text = path.read_text(encoding="utf-8").strip()
    meta = {"always": True, "triggers": [], "description": ""}
    content = text

    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm = text[3:end].strip()
            content = text[end + 3:].strip()
            for line in fm.splitlines():
                if ":" not in line:
                    continue
                key, _, val = line.partition(":")
                key, val = key.strip(), val.strip()
                if key == "always":
                    meta["always"] = val.lower() in ("true", "1", "yes")
                elif key == "triggers":
                    meta["triggers"] = [t.strip() for t in val.strip("[]").split(",") if t.strip()]
                elif key == "description":
                    meta["description"] = val

    return {"name": path.stem, "meta": meta, "content": content}


def load_relevant(message: str = "") -> str:
    """
    Return skills text for injection into the system prompt.

    Always-inject skills (no frontmatter, or always: true) are always included.
    Trigger-based skills are included if any trigger word appears in the message.
    A compact index of skipped skills is appended so Claude knows they exist.
    """
    SKILLS_DIR.mkdir(exist_ok=True)
    skills = []
    for f in sorted(SKILLS_DIR.glob("*.md")):
        try:
            skills.append(_parse_skill(f))
        except Exception as e:
            logger.warning("Could not load skill %s: %s", f.name, e)

    if not skills:
        return ""

    msg_lower = message.lower()
    loaded: list[str] = []
    skipped: list[str] = []

    for skill in skills:
        meta = skill["meta"]
        block = f"### Skill: {skill['name']}\n\n{skill['content']}"
        if meta["always"]:
            loaded.append(block)
        elif any(t.lower() in msg_lower for t in meta["triggers"]):
            loaded.append(block)
        else:
            triggers_str = ", ".join(meta["triggers"][:4]) or skill["name"]
            desc = meta["description"] or triggers_str
            skipped.append(f"- **{skill['name']}** — {desc}")

    if skipped:
        loaded.append("### Available Skills (not loaded this turn — mention a trigger word to activate)\n\n" + "\n".join(skipped))

    return "\n\n---\n\n".join(loaded)


# ── Kept for backward compat (used by load_all callers if any) ─────────────────
def load_all() -> str:
    return load_relevant("")


def list_skills() -> list[dict]:
    SKILLS_DIR.mkdir(exist_ok=True)
    result = []
    for f in sorted(SKILLS_DIR.glob("*.md")):
        try:
            skill = _parse_skill(f)
            preview = skill["content"].splitlines()[0][:120] if skill["content"] else ""
            result.append({
                "name": skill["name"],
                "preview": preview,
                "always": skill["meta"]["always"],
                "triggers": skill["meta"]["triggers"],
            })
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
    return re.sub(r"[^\w-]", "-", name.lower()).strip("-")
