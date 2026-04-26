"""
memory/index.py — BM25 index over memory Markdown files.

Maintains an in-memory BM25 index of:
  - workspaces/main/MEMORY.md
  - workspaces/main/memory/YYYY-MM-DD.md  (90-day lookback)

A watchdog file watcher triggers incremental re-indexing on any change
(debounced 5 seconds). Full rebuild runs on startup.

Thread-safe: index reads/writes protected by a threading.RLock.
"""

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

logger = logging.getLogger("memory.index")

CHUNK_TOKENS = 400
OVERLAP_TOKENS = 80
DAILY_LOOKBACK_DAYS = 90


@dataclass
class Chunk:
    text: str
    source: str      # relative path from workspace root, e.g. "MEMORY.md"
    line_start: int
    line_end: int
    tokens: list[str] = field(default_factory=list)


class MemoryIndex:
    """
    BM25 index over all memory Markdown files.
    Thread-safe — safe to read from async handlers while the watcher
    updates from a background thread.
    """

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self._lock = threading.RLock()
        self._chunks: list[Chunk] = []
        self._bm25: Optional[BM25Okapi] = None
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ── Public API ─────────────────────────────────────────────────────────────

    def build(self) -> None:
        """Full index rebuild. Called once at startup."""
        files = self._collect_files()
        chunks: list[Chunk] = []
        for path in files:
            chunks.extend(self._chunk_file(path))
        with self._lock:
            self._chunks = chunks
            self._bm25 = self._build_bm25(chunks)
        logger.info("Memory index built: %d chunks from %d files", len(chunks), len(files))

    def reindex_file(self, path: Path) -> None:
        """Replace chunks for a single file. Called by the file watcher."""
        rel = self._rel(path)
        new_chunks = self._chunk_file(path)
        with self._lock:
            self._chunks = [c for c in self._chunks if c.source != rel] + new_chunks
            self._bm25 = self._build_bm25(self._chunks)
        logger.info("Re-indexed %s: %d chunks", rel, len(new_chunks))

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """BM25 search. Returns list of {text, source, line_start, line_end, score}."""
        with self._lock:
            if not self._bm25 or not self._chunks:
                return []
            tokens = _tokenize(query)
            scores = self._bm25.get_scores(tokens)
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            # Filter: only return chunks that contain at least one query token.
            # BM25 can return negative scores with small corpora, so don't filter by score sign.
            query_tokens = set(tokens)
            results = []
            for idx, score in ranked[:limit]:
                c = self._chunks[idx]
                if not query_tokens.intersection(c.tokens):
                    continue
                results.append({
                    "text": c.text,
                    "source": c.source,
                    "line_start": c.line_start,
                    "line_end": c.line_end,
                    "score": round(float(score), 3),
                })
            return results

    def start_watcher(self) -> None:
        """Start background file watcher thread."""
        self._stop_event.clear()
        self._watcher_thread = threading.Thread(
            target=self._watch_loop, daemon=True, name="memory-watcher"
        )
        self._watcher_thread.start()
        logger.info("Memory file watcher started")

    def stop_watcher(self) -> None:
        self._stop_event.set()

    # ── Internals ──────────────────────────────────────────────────────────────

    def _collect_files(self) -> list[Path]:
        files: list[Path] = []
        memory_md = self.workspace / "MEMORY.md"
        if memory_md.exists():
            files.append(memory_md)

        cutoff = date.today() - timedelta(days=DAILY_LOOKBACK_DAYS)
        daily_dir = self.workspace / "memory"
        if daily_dir.exists():
            for f in sorted(daily_dir.glob("*.md")):
                try:
                    file_date = date.fromisoformat(f.stem)
                    if file_date >= cutoff:
                        files.append(f)
                except ValueError:
                    pass

        wiki_dir = self.workspace / "wiki"
        if wiki_dir.exists():
            for f in sorted(wiki_dir.rglob("*.md")):
                files.append(f)

        return files

    def _chunk_file(self, path: Path) -> list[Chunk]:
        if not path.exists() or path.stat().st_size == 0:
            return []
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Could not read %s: %s", path, e)
            return []

        rel = self._rel(path)
        lines = text.splitlines()
        chunks: list[Chunk] = []
        current_tokens: list[str] = []
        current_lines: list[str] = []
        line_start = 0

        for lineno, line in enumerate(lines):
            line_tokens = _tokenize(line)
            if len(current_tokens) + len(line_tokens) > CHUNK_TOKENS and current_tokens:
                chunk_text = "\n".join(current_lines).strip()
                if chunk_text:
                    c = Chunk(
                        text=chunk_text,
                        source=rel,
                        line_start=line_start,
                        line_end=lineno - 1,
                        tokens=current_tokens[:],
                    )
                    chunks.append(c)
                # Overlap: keep last OVERLAP_TOKENS worth of tokens
                overlap_lines = _trim_lines_to_tokens(current_lines, OVERLAP_TOKENS)
                current_lines = overlap_lines + [line]
                current_tokens = _tokenize("\n".join(current_lines))
                line_start = lineno - len(overlap_lines)
            else:
                current_lines.append(line)
                current_tokens.extend(line_tokens)

        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(Chunk(
                    text=chunk_text,
                    source=rel,
                    line_start=line_start,
                    line_end=len(lines) - 1,
                    tokens=current_tokens,
                ))
        return chunks

    def _build_bm25(self, chunks: list[Chunk]) -> Optional[BM25Okapi]:
        if not chunks:
            return None
        return BM25Okapi([c.tokens for c in chunks])

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.workspace))
        except ValueError:
            return path.name

    def _watch_loop(self) -> None:
        """Poll memory and wiki files for changes every 5 seconds."""
        mtimes: dict[Path, float] = {}

        while not self._stop_event.is_set():
            for path in self._collect_files():
                try:
                    mtime = path.stat().st_mtime
                    if mtimes.get(path) != mtime:
                        if path in mtimes:
                            logger.debug("Memory file changed: %s", path.name)
                        else:
                            logger.debug("New wiki file detected: %s", path.name)
                        self.reindex_file(path)
                        mtimes[path] = mtime
                except Exception as e:
                    logger.warning("Watcher error for %s: %s", path, e)
            self._stop_event.wait(5)


# ── Tokenizer ──────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer, lowercased."""
    return [t.lower() for t in re.findall(r"\b\w+\b", text) if len(t) > 1]


def _trim_lines_to_tokens(lines: list[str], max_tokens: int) -> list[str]:
    """Return the last lines that together contain at most max_tokens."""
    result: list[str] = []
    count = 0
    for line in reversed(lines):
        toks = len(_tokenize(line))
        if count + toks > max_tokens:
            break
        result.insert(0, line)
        count += toks
    return result
