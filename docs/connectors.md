# Connectors

Main inherits every MCP server configured in your Claude Code user settings
(`~/.claude.json`). Adding a connector is two steps:

1. Register the MCP server with Claude Code (`claude mcp add ...`)
2. Set any required API credentials in `.env`

That's it. Main picks up new servers on next restart.

---

## How it works

Main runs with `setting_sources=["user"]`, so it loads MCP servers from
`~/.claude.json` automatically. `MAIN_EXTRA_TOOLS=*` in `.env` (the default)
means there is no tool restriction — Claude can call any tool from any server.

---

## GitHub

```bash
claude mcp add github -s user -- \
  npx -y @modelcontextprotocol/server-github
```

Add to `.env`:
```
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
```

Available tools: `create_issue`, `list_issues`, `create_pull_request`,
`get_file_contents`, `search_repositories`, `push_files`, and more.

---

## HubSpot

```bash
claude mcp add hubspot -s user -- \
  npx -y @hubspot/mcp --tools=all
```

Add to `.env`:
```
HUBSPOT_ACCESS_TOKEN=pat-na1-...
```

Get a private app token: HubSpot → Settings → Integrations → Private Apps.
Scopes needed depend on what you want Main to do (contacts, deals, emails, etc.).

---

## Slack

```bash
claude mcp add slack -s user -- \
  npx -y @modelcontextprotocol/server-slack
```

Add to `.env`:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_TEAM_ID=T...
```

Create a Slack app at api.slack.com/apps with `channels:read`, `chat:write`,
`users:read` scopes, then install it to your workspace.

---

## Linear

```bash
claude mcp add linear -s user -- \
  npx -y @linear/mcp
```

Add to `.env`:
```
LINEAR_API_KEY=lin_api_...
```

Get an API key: Linear → Settings → API → Personal API keys.

---

## Google Workspace (Drive, Calendar, Gmail)

```bash
claude mcp add gdrive -s user -- \
  npx -y @modelcontextprotocol/server-gdrive

claude mcp add gcalendar -s user -- \
  npx -y @modelcontextprotocol/server-google-calendar

claude mcp add gmail -s user -- \
  npx -y @modelcontextprotocol/server-gmail
```

Each requires OAuth credentials. Follow the auth flow each server prompts on
first run. Credentials are cached in `~/.config/` or similar.

---

## Notion

```bash
claude mcp add notion -s user -- \
  npx -y @notionhq/mcp
```

Add to `.env`:
```
NOTION_API_KEY=secret_...
```

Create an integration at notion.so/my-integrations, then share the pages you
want Main to access with that integration.

---

## Adding any other MCP server

```bash
claude mcp add <name> -s user -- <command>
```

The `-s user` flag stores it in `~/.claude.json` so Main inherits it.
Restart Main after adding. The new server's tools are immediately available.

---

## Verifying a connector works

Ask Main directly in Telegram:
> "List my open GitHub issues"
> "What's in my HubSpot pipeline?"
> "Show me the last 5 messages in #general"

Or ask Main to list its available tools: "What tools do you have access to?"

---

## Restricting which tools Main can call

If you want Main to only use specific MCP tools, list them in `.env`:

```
MAIN_EXTRA_TOOLS=mcp__github__list_issues,mcp__github__create_issue
```

Set to `*` (the default) to allow everything.
