"""
agents/main/subagents.py — Sub-agent registry and runner.

Sub-agents are defined by two files under agents/<name>/:
  - CLAUDE.md       system prompt for this agent
  - config.json     description, allowed tools, MCP settings

Each sub-agent gets its own workspace at workspaces/<name>/.
Main spawns them synchronously inside its tool call — sdk.query() → result text.
Sub-agent calls are stateless (no session resume); each call is a fresh turn.
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


# ── Public API ─────────────────────────────────────────────────────────────────

def list_subagents() -> list[dict]:
    result = []
    for d in sorted(AGENTS_DIR.iterdir()):
        if d.name == "main" or not d.is_dir():
            continue
        claude_md = d / "CLAUDE.md"
        config_path = d / "config.json"
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

    setting_sources = ["user"] if cfg.get("inherit_user_mcp", True) else []

    options = sdk.ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(workspace),
        permission_mode="bypassPermissions",
        setting_sources=setting_sources,
        allowed_tools=cfg.get("tools"),  # None = all tools
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
