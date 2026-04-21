"""
agents/main/connectors.py — Connector registry and installer.

Connectors are MCP servers that extend Main's capabilities.
add_connector() registers the server with claude CLI and writes credentials to .env.
"""

import json
import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger("connectors")

ROOT = Path(__file__).resolve().parent.parent.parent

# ── Registry ───────────────────────────────────────────────────────────────────

REGISTRY: dict[str, dict] = {
    "github": {
        "command": "npx -y @modelcontextprotocol/server-github",
        "env_vars": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": (
                "GitHub personal access token — go to github.com/settings/tokens, "
                "Generate new token (classic), tick the 'repo' scope, copy the token."
            ),
        },
        "description": "GitHub — issues, PRs, file contents, repo search",
    },
    "hubspot": {
        "command": "npx -y @hubspot/mcp --tools=all",
        "env_vars": {
            "HUBSPOT_ACCESS_TOKEN": (
                "HubSpot private app token — go to HubSpot → Settings → Integrations → "
                "Private Apps → Create app, grant scopes you need, copy the access token."
            ),
        },
        "description": "HubSpot — contacts, deals, companies, emails, pipelines",
    },
    "slack": {
        "command": "npx -y @modelcontextprotocol/server-slack",
        "env_vars": {
            "SLACK_BOT_TOKEN": (
                "Slack bot OAuth token — go to api.slack.com/apps, create an app, "
                "add scopes (channels:read, chat:write, users:read), install to workspace, "
                "copy the Bot User OAuth Token (starts with xoxb-)."
            ),
            "SLACK_TEAM_ID": (
                "Slack workspace ID — starts with T. "
                "Find it in your workspace URL: app.slack.com/client/TXXXXXXXX/..."
            ),
        },
        "description": "Slack — send messages, read channels, list users",
    },
    "linear": {
        "command": "npx -y @linear/mcp",
        "env_vars": {
            "LINEAR_API_KEY": (
                "Linear personal API key — go to linear.app → Settings → API → "
                "Personal API keys → Create key."
            ),
        },
        "description": "Linear — issues, projects, teams, cycles",
    },
    "notion": {
        "command": "npx -y @notionhq/mcp",
        "env_vars": {
            "NOTION_API_KEY": (
                "Notion integration secret — go to notion.so/my-integrations, "
                "create a new integration, copy the Internal Integration Token. "
                "Then share the pages you want access to with the integration."
            ),
        },
        "description": "Notion — read and write pages and databases",
    },
    "gdrive": {
        "command": "npx -y @modelcontextprotocol/server-gdrive",
        "env_vars": {},
        "description": "Google Drive — search and read files (OAuth on first use)",
    },
    "gmail": {
        "command": "npx -y @modelcontextprotocol/server-gmail",
        "env_vars": {},
        "description": "Gmail — read and send emails (OAuth on first use)",
    },
    "gcalendar": {
        "command": "npx -y @modelcontextprotocol/server-google-calendar",
        "env_vars": {},
        "description": "Google Calendar — read and create events (OAuth on first use)",
    },
    "postgres": {
        "command": "npx -y @modelcontextprotocol/server-postgres",
        "env_vars": {
            "POSTGRES_CONNECTION_STRING": (
                "PostgreSQL connection string — format: postgresql://user:password@host:5432/dbname"
            ),
        },
        "description": "PostgreSQL — query and inspect a Postgres database",
    },
    "sqlite": {
        "command": "npx -y @modelcontextprotocol/server-sqlite",
        "env_vars": {
            "SQLITE_DB_PATH": "Absolute path to the SQLite .db file",
        },
        "description": "SQLite — query and inspect a SQLite database",
    },
    "stripe": {
        "command": "npx -y @stripe/mcp --tools=all",
        "env_vars": {
            "STRIPE_SECRET_KEY": (
                "Stripe secret key — go to dashboard.stripe.com → Developers → API keys, "
                "copy the Secret key (starts with sk_)."
            ),
        },
        "description": "Stripe — customers, payments, subscriptions, invoices",
    },
    "jira": {
        "command": "npx -y @modelcontextprotocol/server-jira",
        "env_vars": {
            "JIRA_HOST": "Your Jira host, e.g. yourcompany.atlassian.net",
            "JIRA_EMAIL": "Your Jira account email",
            "JIRA_API_TOKEN": (
                "Jira API token — go to id.atlassian.com/manage-profile/security/api-tokens, "
                "create a token, copy it."
            ),
        },
        "description": "Jira — issues, projects, sprints, boards",
    },
}


# ── Public API ─────────────────────────────────────────────────────────────────

def get_installed_connectors() -> list[str]:
    return [name for name in REGISTRY if _is_installed(name)]


def list_connectors() -> str:
    lines = []
    for name, info in REGISTRY.items():
        installed = _is_installed(name)
        status = "✓" if installed else "○"
        lines.append(f"{status} {name} — {info['description']}")
    return "\n".join(lines)


def get_connector_info(name: str) -> dict | None:
    return REGISTRY.get(name.lower().strip())


def add_connector(name: str, credentials: dict[str, str]) -> tuple[bool, str]:
    """
    Register an MCP server with Claude Code and write credentials to .env.
    Returns (success, message).
    """
    name = name.lower().strip()
    if name not in REGISTRY:
        known = ", ".join(REGISTRY.keys())
        return False, f"Unknown connector '{name}'. Available: {known}"

    info = REGISTRY[name]

    # Validate required credentials are present
    missing = [k for k in info["env_vars"] if not credentials.get(k, "").strip()]
    if missing:
        details = "\n".join(f"  {k}" for k in missing)
        return False, f"Missing required credentials for {name}:\n{details}"

    # Run: claude mcp add <name> -s user -- <command>
    command_parts = info["command"].split()
    cli_cmd = ["claude", "mcp", "add", name, "-s", "user", "--"] + command_parts
    try:
        result = subprocess.run(cli_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            err = (result.stderr or result.stdout).strip()
            return False, f"`claude mcp add` failed: {err}"
    except FileNotFoundError:
        return False, "claude CLI not found in PATH."
    except subprocess.TimeoutExpired:
        return False, "`claude mcp add` timed out after 30s."
    except Exception as e:
        return False, f"Error: {e}"

    # Write credentials into .env
    env_path = ROOT / ".env"
    _upsert_env_vars(env_path, credentials)

    logger.info("Connector '%s' added successfully", name)
    return True, f"Connector '{name}' registered. Restart required to load it."


def remove_connector(name: str) -> tuple[bool, str]:
    name = name.lower().strip()
    if name not in REGISTRY:
        return False, f"Unknown connector '{name}'."
    cli_cmd = ["claude", "mcp", "remove", name, "-s", "user"]
    try:
        result = subprocess.run(cli_cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            err = (result.stderr or result.stdout).strip()
            return False, f"`claude mcp remove` failed: {err}"
    except Exception as e:
        return False, f"Error: {e}"
    logger.info("Connector '%s' removed", name)
    return True, f"Connector '{name}' removed. Restart to apply."


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_installed(name: str) -> bool:
    claude_json = Path.home() / ".claude.json"
    if not claude_json.exists():
        return False
    try:
        data = json.loads(claude_json.read_text())
        return name in data.get("mcpServers", {})
    except Exception:
        return False


def _upsert_env_vars(env_path: Path, vars_: dict[str, str]) -> None:
    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")
    content = env_path.read_text(encoding="utf-8")
    for key, value in vars_.items():
        if not value:
            continue
        pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
        new_line = f"{key}={value}"
        if pattern.search(content):
            content = pattern.sub(new_line, content)
        else:
            content = content.rstrip("\n") + f"\n{new_line}\n"
    env_path.write_text(content, encoding="utf-8")
