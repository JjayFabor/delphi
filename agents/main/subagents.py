"""
agents/main/subagents.py — Sub-agent registry and runner.

Sub-agents are defined by two files under agents/<name>/:
  - CLAUDE.md       system prompt for this agent
  - config.json     description, allowed tools, MCP settings

Each sub-agent gets its own workspace at workspaces/<name>/.
Main spawns them synchronously inside its tool call — sdk.query() → result text.
Sub-agent calls are stateless (no session resume); each call is a fresh turn.

Each sub-agent receives an in-process MCP server with memory_search, wiki_write,
wiki_read, and wiki_list tools bound to its own workspace. This lets agents search
past lessons and write wiki pages without reading entire files every turn.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import claude_agent_sdk as sdk

logger = logging.getLogger("subagents")

ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = ROOT / "agents"
WORKSPACES_DIR = ROOT / "workspaces"

_DEFAULT_CONFIG = {
    "description": "",
    "tools": None,           # None = all tools; list = restricted set
    "inherit_user_mcp": True,  # inherit MCP servers from ~/.claude.json
}

# Memory tools injected into every subagent — added to allowed_tools automatically
_SUBAGENT_MEMORY_TOOLS = ["memory_search", "wiki_write", "wiki_read", "wiki_list"]


# ── Public API ─────────────────────────────────────────────────────────────────

def list_subagents() -> list[dict]:
    result = []
    for d in sorted(AGENTS_DIR.iterdir()):
        if d.name == "main" or not d.is_dir():
            continue
        claude_md = d / "CLAUDE.md"
        if not claude_md.exists():
            continue
        cfg = _load_config(d.name)
        result.append({
            "name": d.name,
            "description": cfg.get("description", ""),
            "tools": cfg.get("tools"),
            "workspace": str(WORKSPACES_DIR / d.name),
        })
    return result


def create_subagent(name: str, description: str, system_prompt: str, tools: Optional[list[str]]) -> str:
    """
    Create a new sub-agent. Returns the agent directory path.
    """
    safe_name = _safe(name)
    agent_dir = AGENTS_DIR / safe_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    (agent_dir / "CLAUDE.md").write_text(system_prompt.strip() + "\n", encoding="utf-8")

    config = {**_DEFAULT_CONFIG, "description": description, "tools": tools}
    (agent_dir / "config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    workspace = WORKSPACES_DIR / safe_name
    workspace.mkdir(parents=True, exist_ok=True)

    logger.info("Sub-agent created: %s", safe_name)
    return str(agent_dir)


_SUBAGENT_SAVE_SUFFIX = """

---
After completing the task above:
1. If a bug was fixed or a mistake corrected → append to wiki/coding/lessons.md using wiki_write (Problem / Root cause / Fix / Watch for format).
2. If you discovered a useful pattern, gotcha, or architectural note → wiki_write to an appropriate page (e.g. "backend/schema", "docker/setup").
3. If nothing new was learned → skip silently.
"""


async def run_subagent(name: str, task: str) -> str:
    """
    Run a named sub-agent with the given task. Returns the result text.
    Raises ValueError if the agent doesn't exist.
    """
    safe_name = _safe(name)
    agent_dir = AGENTS_DIR / safe_name
    claude_md = agent_dir / "CLAUDE.md"

    if not claude_md.exists():
        available = [d.name for d in AGENTS_DIR.iterdir() if d.is_dir() and d.name != "main" and (d / "CLAUDE.md").exists()]
        raise ValueError(f"Sub-agent '{safe_name}' not found. Available: {available or ['none']}")

    system_prompt = claude_md.read_text(encoding="utf-8").strip()
    cfg = _load_config(safe_name)

    workspace = WORKSPACES_DIR / safe_name
    workspace.mkdir(parents=True, exist_ok=True)

    # Build per-workspace memory+wiki MCP server so the agent can search its
    # own lessons/memory instead of reading entire files on every turn.
    memory_mcp = _build_memory_mcp(workspace)

    # Auto-inject relevant memory/wiki context before the task so the agent
    # always has it without needing to call memory_search manually.
    from memory.index import MemoryIndex
    from memory.search import search as _mem_search
    _idx = MemoryIndex(workspace)
    _idx.build()
    mem_context = _mem_search(_idx, task, limit=3)
    if mem_context and mem_context.strip():
        task = (
            f"[Relevant memory/wiki context — apply automatically]\n"
            f"{mem_context}\n"
            f"---\n\n"
            f"{task}"
        )

    # Append save reminder so the agent writes lessons in the same turn.
    task = task + _SUBAGENT_SAVE_SUFFIX

    setting_sources = ["user"] if cfg.get("inherit_user_mcp", True) else []

    _tools = cfg.get("tools")  # None means unrestricted
    # When a tool list is specified, add the memory tools so they're always available.
    if _tools is not None:
        _tools = list(_tools) + [t for t in _SUBAGENT_MEMORY_TOOLS if t not in _tools]

    options = sdk.ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(workspace),
        permission_mode="bypassPermissions",
        setting_sources=setting_sources,
        mcp_servers={"memory": memory_mcp},
        **( {"allowed_tools": _tools} if _tools is not None else {} ),
    )

    logger.info("Running sub-agent '%s' for task: %s...", safe_name, task[:60])
    parts: list[str] = []
    async for event in sdk.query(prompt=task, options=options):
        if isinstance(event, sdk.AssistantMessage):
            for block in event.content:
                if isinstance(block, sdk.TextBlock):
                    parts.append(block.text)

    result = "".join(parts).strip()
    logger.info("Sub-agent '%s' returned %d chars", safe_name, len(result))
    return result or "(no response)"


# ── Per-workspace memory MCP server ───────────────────────────────────────────

def _build_memory_mcp(workspace: Path) -> object:
    """
    Build an in-process MCP server with memory_search, wiki_write, wiki_read,
    wiki_list tools bound to the given workspace.

    The BM25 index is built fresh per invocation (subagents are stateless).
    Covers: MEMORY.md, memory/*.md, wiki/**/*.md.
    """
    from memory.index import MemoryIndex
    from memory.search import search as _mem_search

    index = MemoryIndex(workspace)
    index.build()

    @sdk.tool(
        name="memory_search",
        description=(
            "Search this agent's memory and wiki (BM25) for past facts, lessons, "
            "and decisions. Call this before any coding task to find relevant lessons."
        ),
        input_schema={"query": str, "limit": int},
    )
    async def tool_search(args: dict) -> dict:
        query = args.get("query", "")
        limit = int(args.get("limit", 5))
        result = _mem_search(index, query, limit=limit)
        return {"content": [{"type": "text", "text": result}]}

    @sdk.tool(
        name="wiki_write",
        description=(
            "Create or update a wiki page. path is a slash-separated slug "
            "like 'coding/lessons' or 'architecture/overview'."
        ),
        input_schema={"path": str, "content": str},
    )
    async def tool_wiki_write(args: dict) -> dict:
        path_arg = args.get("path", "").strip().lstrip("/")
        content = args.get("content", "")
        if not path_arg:
            return {"content": [{"type": "text", "text": "path is required."}], "is_error": True}
        target = workspace / "wiki" / (path_arg if path_arg.endswith(".md") else f"{path_arg}.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        index.reindex_file(target)
        return {"content": [{"type": "text", "text": f"Wiki page written: wiki/{path_arg}.md"}]}

    @sdk.tool(
        name="wiki_read",
        description="Read a wiki page in full by its path slug (e.g. 'coding/lessons').",
        input_schema={"path": str},
    )
    async def tool_wiki_read(args: dict) -> dict:
        path_arg = args.get("path", "").strip().lstrip("/")
        target = workspace / "wiki" / (path_arg if path_arg.endswith(".md") else f"{path_arg}.md")
        if not target.exists():
            return {"content": [{"type": "text", "text": f"Wiki page not found: {path_arg}"}]}
        return {"content": [{"type": "text", "text": target.read_text(encoding="utf-8")}]}

    @sdk.tool(
        name="wiki_list",
        description="List all wiki pages. Returns a tree of topic paths.",
        input_schema={},
    )
    async def tool_wiki_list(_args: dict) -> dict:
        wiki_dir = workspace / "wiki"
        if not wiki_dir.exists() or not any(wiki_dir.rglob("*.md")):
            return {"content": [{"type": "text", "text": "Wiki is empty."}]}
        pages = sorted(str(p.relative_to(wiki_dir).with_suffix("")) for p in wiki_dir.rglob("*.md"))
        return {"content": [{"type": "text", "text": "\n".join(pages)}]}

    return sdk.create_sdk_mcp_server(
        name="memory",
        tools=[tool_search, tool_wiki_write, tool_wiki_read, tool_wiki_list],
    )


# ── Internals ──────────────────────────────────────────────────────────────────

def _load_config(name: str) -> dict:
    path = AGENTS_DIR / name / "config.json"
    if not path.exists():
        return dict(_DEFAULT_CONFIG)
    try:
        return {**_DEFAULT_CONFIG, **json.loads(path.read_text(encoding="utf-8"))}
    except Exception:
        return dict(_DEFAULT_CONFIG)


def _safe(name: str) -> str:
    return re.sub(r"[^\w-]", "-", name.lower()).strip("-")
