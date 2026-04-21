"""
memory/dreaming.py — Nightly memory consolidation sweep.

Disabled by default (DREAMING_ENABLED=false).
When enabled, reads daily notes from the past DREAMING_LOOKBACK_DAYS days,
scores observations for likely long-term relevance, and writes candidates
above DREAMING_PROMOTION_THRESHOLD to DREAMS.md for human review.

Nothing reaches MEMORY.md automatically — DREAMS.md is the human checkpoint.
Run via the claude-memory-dreaming systemd timer, or manually:
    python memory/dreaming.py
"""

import logging
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspaces" / "main"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("memory.dreaming")


def _score_line(line: str) -> float:
    """
    Heuristic score for whether a daily-note line is worth promoting.
    Higher = more likely to be a durable fact worth remembering.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return 0.0

    score = 0.3  # baseline

    # Preference / decision markers
    if re.search(r"\b(prefer|decided|always|never|rule|policy|important)\b", line, re.I):
        score += 0.3
    # Tool / tech stack mentions
    if re.search(r"\b(use|using|stack|framework|library|tool|service)\b", line, re.I):
        score += 0.15
    # Concrete values (URLs, version numbers, identifiers)
    if re.search(r"https?://|v\d+\.\d+|\b[A-Z]{2,}\b", line):
        score += 0.1
    # Conversational / vague lines get penalised
    if re.search(r"\b(maybe|might|could|think|feel|seems)\b", line, re.I):
        score -= 0.15

    return min(max(score, 0.0), 1.0)


def _already_in_dreams(dreams_path: Path) -> set[str]:
    """
    Return the set of line bodies already written to DREAMS.md.
    Used to prevent the same candidate appearing in every nightly sweep.
    """
    if not dreams_path.exists():
        return set()
    seen: set[str] = set()
    for line in dreams_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("-"):
            seen.add(line)
    return seen


def run_sweep(
    lookback_days: int,
    threshold: float,
    workspace: Path = WORKSPACE,
) -> int:
    """
    Sweep daily notes and write new candidates to DREAMS.md.
    Returns the number of new candidates written.
    """
    daily_dir = workspace / "memory"
    dreams_path = workspace / "DREAMS.md"
    cutoff = date.today() - timedelta(days=lookback_days)

    already_seen = _already_in_dreams(dreams_path)
    candidates: list[str] = []

    for f in sorted(daily_dir.glob("*.md")):
        try:
            file_date = date.fromisoformat(f.stem)
        except ValueError:
            continue
        if file_date < cutoff:
            continue

        lines = f.read_text(encoding="utf-8").splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("-"):
                continue
            if stripped in already_seen:
                continue
            score = _score_line(stripped)
            if score >= threshold:
                candidates.append(f"<!-- score={score:.2f} source={f.name} -->\n{stripped}")

    if not candidates:
        logger.info("No new candidates above threshold %.2f", threshold)
        return 0

    # Append to DREAMS.md
    existing = dreams_path.read_text(encoding="utf-8") if dreams_path.exists() else ""
    block = f"\n\n## Sweep {date.today().isoformat()}\n\n" + "\n".join(candidates) + "\n"
    dreams_path.write_text(existing + block, encoding="utf-8")
    logger.info("Wrote %d new candidates to DREAMS.md", len(candidates))

    # Write a note to today's daily log so the bot surfaces it next session
    today = date.today().isoformat()
    daily_file = workspace / "memory" / f"{today}.md"
    daily_file.parent.mkdir(parents=True, exist_ok=True)
    if not daily_file.exists():
        daily_file.write_text(f"# {today}\n\n", encoding="utf-8")
    with daily_file.open("a", encoding="utf-8") as f:
        f.write(f"- [dreaming] {len(candidates)} new memory candidates written to DREAMS.md — review and promote what's worth keeping.\n")

    return len(candidates)


if __name__ == "__main__":
    # Load .env so the script works when run directly or via systemd
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    enabled = os.getenv("DREAMING_ENABLED", "false").lower() == "true"
    if not enabled:
        logger.info("DREAMING_ENABLED=false — nothing to do")
        sys.exit(0)

    lookback = int(os.getenv("DREAMING_LOOKBACK_DAYS", "30"))
    threshold = float(os.getenv("DREAMING_PROMOTION_THRESHOLD", "0.6"))
    count = run_sweep(lookback_days=lookback, threshold=threshold)
    logger.info("Sweep complete: %d new candidates", count)
