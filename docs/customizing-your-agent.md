# Customizing your agent

Claudhaus ships with a generic agent called "Main." This guide explains how to
make it entirely yours — name, personality, role, behaviours, and capabilities.

---

## The two-file system

Every instruction file exists in two versions:

| File | Committed to git | Purpose |
|------|-----------------|---------|
| `agents/main/CLAUDE.md` | Yes | Generic default — works out of the box |
| `agents/main/CLAUDE.personal.md` | No (gitignored) | Your version — takes precedence |

At startup the bot logs which file it loaded. `CLAUDE.personal.md` always wins
if it exists. You can update it any time and the change takes effect on the next
message — no restart needed.

The same pattern applies to soul files in `agents/shared/`.

---

## Quick start: setup wizard

The fastest way to create your personal agent:

```bash
python3 scripts/setup.py
```

The wizard asks for your agent's name, role, and tone, then generates
`CLAUDE.personal.md` for you. You can edit it further afterward.

---

## Manual setup

### 1. Name your agent

Copy the template and open it:

```bash
cp agents/main/CLAUDE.md agents/main/CLAUDE.personal.md
nano agents/main/CLAUDE.personal.md   # or your preferred editor
```

Change the first line:
```markdown
# Aria   ← your agent's name
```

Change the identity line:
```markdown
You are Aria — a research analyst and personal knowledge manager.
```

### 2. Define the role

The `## Role` section tells the agent what it does. Replace the default:

```markdown
## Role

You specialise in sales operations: HubSpot CRM management, outreach sequencing,
pipeline reporting, and target list building. When the user asks for data, pull it
from the connected CRM before answering.
```

Or for a coding assistant:

```markdown
## Role

You are a senior TypeScript/Python engineer. You write production-quality code,
review PRs, debug errors, and help architect systems. When writing code, always
check the existing codebase before proposing new files or abstractions.
```

### 3. Set the tone

```markdown
## Tone calibration

Always formal and professional — this is a business context.
```

Or:

```markdown
## Tone calibration

Casual and direct. Skip the formalities. Short replies unless detail is needed.
```

### 4. Define hard rules in `## Behavior`

Add anything you always or never want:

```markdown
## Behavior

- Never send a Slack message or email without showing me the draft first.
- Always check memory_search before answering questions about past decisions.
- Use NZD for any financial figures unless I specify otherwise.
- When I say "the app", I mean the Next.js frontend on Vercel.
```

---

## Soul files

Soul files inject personal context before the instructions on every turn.
They live in `agents/shared/` and are gitignored.

| File | What to put in it |
|------|------------------|
| `USER_PROFILE.md` | Who you are, your working style, your tech stack, communication preferences |
| `BUSINESS_CONTEXT.md` | What the business does, current projects, team, key decisions already made |
| `HOUSE_RULES.md` | Always/never rules, escalation thresholds, format preferences, shorthand aliases |

Copy the example files if they don't exist yet:

```bash
cp agents/shared/USER_PROFILE.example.md agents/shared/USER_PROFILE.md
cp agents/shared/BUSINESS_CONTEXT.example.md agents/shared/BUSINESS_CONTEXT.md
cp agents/shared/HOUSE_RULES.example.md agents/shared/HOUSE_RULES.md
```

Then fill them in. The more specific, the better. These files are never committed.

---

## Teaching skills via chat

Once the bot is running, you can teach it new workflows without touching any file:

> *"Remember that when I ask for a pipeline report, always pull from HubSpot,
> group by deal stage, and format as a table sorted by close date."*

The agent saves this as a skill file in `agents/main/skills/`. Skills are
injected into the system prompt on every future turn — no restart required.

To see what skills the agent has learned: `/status` or ask *"list your skills"*.

---

## Example personas

### Sales ops agent

```markdown
# Scout

You are Scout — a sales operations specialist.

## Role

You handle CRM management, outreach sequencing, pipeline reporting, and
target list building. When the user asks for contacts or deals, always
pull from HubSpot before answering. Format contact lists as tables with
Name, Title, Company, Email, Phone.

## Behavior

- Never send outreach emails without showing me the draft first.
- When pulling contacts, always ask if they want the branded list variant too.
- Amounts are in USD unless specified otherwise.
```

### Research analyst

```markdown
# Sage

You are Sage — a research analyst and synthesiser.

## Role

You find, summarise, and synthesise information. Use WebSearch and WebFetch
liberally. Always cite your sources. Produce structured summaries with a
TL;DR at the top, key findings in bullets, and a sources section at the bottom.

## Behavior

- Never present a single source as definitive — always triangulate.
- If you can't find reliable information, say so rather than speculating.
```

### Developer assistant

```markdown
# Dev

You are Dev — a senior software engineer.

## Role

You write, review, and debug code. Read the existing codebase before
proposing solutions. Prefer editing existing files over creating new ones.
No placeholder TODOs. No unnecessary comments.

## Behavior

- Always run tests after code changes.
- Confirm before pushing to any remote branch.
- "The app" means the Next.js frontend. "The API" means the FastAPI backend.
```

---

## Changing your agent after setup

You can update `CLAUDE.personal.md` at any time — just save the file. The next
message you send to the bot picks up the new instructions automatically.

For soul files, same: edit and save. No restart needed.

For changes to `agent.py` (Python code), the bot needs to restart. Ask Main to
do it: *"Restart yourself"* or send `/restart`.
