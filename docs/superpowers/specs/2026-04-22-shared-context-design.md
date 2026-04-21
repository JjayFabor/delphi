# Shared Context Feature — Design Spec

**Date:** 2026-04-22
**Status:** Approved

## Overview

Users of the Main bot can explicitly share specific context with other users. Shared context is opt-in, permission-controlled, and targeted — User A chooses what to share and with whom. User B receives it via push notification and can also pull it on demand. All shared content is injected into Claude's session so the AI can reference it naturally.

---

## Data Model

Two new SQLite tables added to the existing `data/agent.db`:

```sql
CREATE TABLE IF NOT EXISTS user_registry (
    chat_id   INTEGER PRIMARY KEY,
    user_id   INTEGER,
    username  TEXT,        -- Telegram @handle (nullable)
    full_name TEXT,        -- "First Last"
    last_seen TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shared_context (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    from_chat_id INTEGER NOT NULL,
    to_chat_id   INTEGER NOT NULL,
    content      TEXT NOT NULL,
    label        TEXT,                            -- optional tag e.g. "project X notes"
    shared_at    TEXT NOT NULL DEFAULT (datetime('now')),
    acknowledged INTEGER NOT NULL DEFAULT 0,      -- 0=unread, 1=seen
    revoked      INTEGER NOT NULL DEFAULT 0       -- soft delete
);
```

`user_registry` is auto-populated on every inbound message — no manual setup required. `shared_context` is append-only with soft deletes so revocation is possible without data loss.

---

## User Registry Population

Before every message handler, upsert the sender into `user_registry`:

```python
async def upsert_user(update: Update) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    db_upsert_user(chat_id, user.id, user.username, user.full_name)
```

Name resolution for sharing matches against `username` (without `@`), `full_name`, or case-insensitive partial `full_name`. If ambiguous, the bot asks User A to clarify. If the target has never messaged the bot, the share is rejected with an explanation.

---

## Share Flow (User A → User B)

**Trigger forms:**
```
/share @username <content>
/share Name: <content>
"share with John: here's what we decided about the API"
```

**Steps:**
1. Resolve target name/username to `to_chat_id` via `user_registry`
2. Insert row into `shared_context` with `acknowledged = 0`
3. Send push notification to User B's `chat_id`:
   > **📤 [User A name] shared something with you:**
   > *content here*
4. Inject into User B's next Claude turn as a system note (see Injection section)
5. Confirm to User A: *"Shared with [name]."*

---

## Pull Flow (User B on demand)

**Trigger forms:**
```
"what did Jay share with me?"
"show shared context"
"anything shared from the team?"
/shared
```

**Steps:**
1. Query `shared_context` where `to_chat_id = User B` and `revoked = 0`
2. Group results by `from_chat_id`, order by `shared_at DESC`
3. Display in chat:
   > **📥 Shared with you:**
   >
   > **From Jay** *(2 items)*
   > • *(Apr 21)* here's what we decided about the API
   > • *(Apr 22)* project X deadline moved to May 5
4. Inject all fetched items into the Claude session context (see Injection)
5. Mark all fetched items as `acknowledged = 1`

---

## Session Injection

Shared context is prepended to the Claude prompt as a system note — not logged to `conversations`, not shown as a user message:

```python
shared = db_get_unacknowledged_shared(chat_id)
if shared:
    note = format_shared_context_note(shared)
    prompt = f"[System: Shared context from other users]\n{note}\n\n{prompt}"
    db_mark_acknowledged(chat_id)
```

**Injected note format:**
```
[System: Shared context from other users]
From Jay (Apr 22): here's what we decided about the API — use REST not GraphQL
From Sarah (Apr 20): use the staging credentials I sent earlier
---
```

**Injection rules:**
- **Push:** injected the first time User B sends any message after the push notification (items sit as `acknowledged = 0` in the DB until then)
- **Pull:** injected every time the user explicitly requests shared context
- **No re-injection** on subsequent turns unless new items arrive or user pulls again — prevents context bloat

---

## Revocation (User A)

**Trigger forms:**
```
/revoke @username <content or label>
"revoke what I shared with John about the API"
```

**Steps:**
1. Match row(s) in `shared_context` by `from_chat_id` + `to_chat_id` + content/label fuzzy match
2. Set `revoked = 1` (soft delete)
3. Notify User B:
   > **🚫 [User A name] revoked shared context:** *content snippet*

**Scope:** Revocation prevents future injections and hides items from pulls. Context already injected into an active Claude session is not retroactively removed — Claude has already seen it.

---

## Components to Add/Modify

| File | Change |
|---|---|
| `agent.py` | Add `user_registry` + `shared_context` DB tables in `init_db()` |
| `agent.py` | Add `upsert_user()` called before every message handler |
| `agent.py` | Add `db_upsert_user`, `db_share_context`, `db_get_unacknowledged_shared`, `db_mark_acknowledged`, `db_revoke_shared`, `db_list_shared`, `db_resolve_user` DB helpers |
| `agent.py` | Add share/revoke/pull handlers (detect intent in `handle_message`) |
| `agent.py` | Modify `run_claude()` to prepend unacknowledged shared context |

All changes are in `agents/main/agent.py` — no new files needed.

---

## Out of Scope

- Group/broadcast sharing (one-to-many) — not in this version
- Expiry/TTL on shared context — can be added later
- User B accepting or rejecting a share — trust model is push-only for now
- End-to-end encryption of shared content
