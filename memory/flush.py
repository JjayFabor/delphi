"""
memory/flush.py — Pre-compaction memory flush.

When a session's accumulated token count approaches the context window
limit, inject a silent flush turn that asks Main to write anything
worth remembering to disk before the CLI compacts the conversation.

Responses of exactly "NO_REPLY" are swallowed — invisible to the user.
"""

import logging
from typing import Optional

logger = logging.getLogger("memory.flush")

# Trigger flush when estimated tokens exceed this threshold.
# Conservative: better to flush too early than too late.
FLUSH_THRESHOLD_TOKENS = 60_000

# Estimated tokens per character (rough approximation)
CHARS_PER_TOKEN = 4

FLUSH_PROMPT = """\
Before this context window is summarized, do the following:

1. Save durable facts, preferences, and decisions:
   - Long-term facts → memory_write_long_term
   - Today's context and observations → memory_write_daily (date: {today})

2. Formalize any patterns or learnings from this conversation:
   - Did the user teach you something? ("remember", "always", "never", "from now on") → learn
   - Did you do the same multi-step thing more than once? → learn (category: skill)
   - Did you learn something about the user's preferences or style? → learn (category: preference)
   - Did you learn something about the business or project? → learn (category: context)

If there is nothing new worth saving and no patterns to formalize, \
respond with exactly: NO_REPLY
"""


class FlushManager:
    """Tracks cumulative session length and signals when a flush is needed."""

    def __init__(self) -> None:
        self._session_chars: dict[int, int] = {}  # chat_id → char count

    def record(self, chat_id: int, text: str) -> None:
        self._session_chars[chat_id] = self._session_chars.get(chat_id, 0) + len(text)

    def reset(self, chat_id: int) -> None:
        self._session_chars.pop(chat_id, None)

    def needs_flush(self, chat_id: int) -> bool:
        chars = self._session_chars.get(chat_id, 0)
        estimated_tokens = chars // CHARS_PER_TOKEN
        return estimated_tokens >= FLUSH_THRESHOLD_TOKENS

    def flush_prompt(self, today: str) -> str:
        return FLUSH_PROMPT.format(today=today)
