"""
agents/main/google_chat_bot.py — Google Chat channel for Delphi.

Subscribes to Google Cloud Pub/Sub to receive Chat app events (no public
URL required). Sends replies via the Google Chat REST API using a service
account.

Setup:
  1. Create a GCP project at console.cloud.google.com.
  2. Enable "Google Chat API" and "Cloud Pub/Sub API".
  3. Create a Pub/Sub topic (e.g. "delphi-chat") and a pull subscription
     (e.g. "delphi-chat-sub").
  4. Create a service account with two roles:
       - Pub/Sub Subscriber (on the subscription)
       - Chat app integration is handled via the Chat API scope
     Download the JSON key file.
  5. In Google Cloud Console → APIs & Services → Google Chat:
       - Configure a Chat app (App name, Avatar, Description)
       - Under "Connection settings" choose "Cloud Pub/Sub"
       - Enter your topic name (projects/PROJECT_ID/topics/TOPIC_NAME)
       - Enable "Message events" under "Slash commands & events" → event subscriptions
  6. Add the bot to your Google Chat space or DM it.
  7. Set these env vars in .env:
       GOOGLE_CHAT_CREDENTIALS_PATH   — absolute path to the service account JSON key
       GOOGLE_CLOUD_PROJECT_ID        — your GCP project ID
       GOOGLE_CHAT_SUBSCRIPTION_ID    — Pub/Sub subscription ID (not full path, just the name)
       GOOGLE_CHAT_ALLOWED_EMAILS     — comma-separated Google emails allowed to use the bot;
                                        leave empty to allow any user who can reach the app
"""
import asyncio
import json
import logging
import re
from typing import Awaitable, Callable

logger = logging.getLogger("google_chat_bot")

_CHAT_API_BASE = "https://chat.googleapis.com/v1"
_CHAT_SCOPES = ["https://www.googleapis.com/auth/chat.bot"]
_PUBSUB_SCOPES = ["https://www.googleapis.com/auth/pubsub"]
GC_MAX_CHARS = 4000


def _chunk(text: str, max_len: int = GC_MAX_CHARS) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        remaining = text[pos:]
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        slice_ = text[pos : pos + max_len]
        cut = slice_.rfind("\n\n")
        if cut == -1:
            cut = slice_.rfind("\n")
        if cut <= 0:
            cut = max_len
        else:
            cut += 1
        chunks.append(text[pos : pos + cut].strip())
        pos += cut
    return [c for c in chunks if c]


def _user_name_to_id(user_name: str) -> int:
    """Convert 'users/103712345678' to a stable positive int for session keying."""
    m = re.search(r"(\d+)$", user_name)
    if m:
        return int(m.group(1)) % (2**62)
    return abs(hash(user_name)) % (2**62)


async def _refresh_if_needed(credentials, loop: asyncio.AbstractEventLoop) -> None:
    if not credentials.valid:
        from google.auth.transport.requests import Request
        await loop.run_in_executor(None, credentials.refresh, Request())


async def _send_reply(
    chat_creds,
    space_name: str,
    text: str,
    loop: asyncio.AbstractEventLoop,
) -> None:
    try:
        import httpx
        await _refresh_if_needed(chat_creds, loop)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{_CHAT_API_BASE}/{space_name}/messages",
                headers={
                    "Authorization": f"Bearer {chat_creds.token}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
            )
        if resp.status_code not in (200, 201):
            logger.error("Chat API %d: %s", resp.status_code, resp.text[:300])
    except Exception as e:
        logger.exception("Failed to send reply to %s: %s", space_name, e)


async def _handle_event(
    event: dict,
    chat_creds,
    run_claude_fn: Callable[[str, int], Awaitable[str]],
    allowed_emails: set[str],
    loop: asyncio.AbstractEventLoop,
) -> None:
    event_type = event.get("type", "")

    if event_type == "ADDED_TO_SPACE":
        space_name = event.get("space", {}).get("name", "")
        logger.info("Added to space: %s", space_name)
        if space_name:
            await _send_reply(
                chat_creds,
                space_name,
                "Hello! I'm Delphi, your personal AI assistant. How can I help you?",
                loop,
            )
        return

    if event_type != "MESSAGE":
        return

    message = event.get("message", {})
    sender = message.get("sender", {})
    space_name = (
        event.get("space", {}).get("name", "")
        or message.get("space", {}).get("name", "")
    )
    sender_email = sender.get("email", "")
    sender_type = sender.get("type", "")
    sender_name = sender.get("name", "")
    text = message.get("text", "").strip()

    if sender_type != "HUMAN":
        return

    if allowed_emails and sender_email not in allowed_emails:
        logger.info("Rejected message from %s (not in allowlist)", sender_email)
        return

    if not text or not space_name:
        return

    # Strip bot @mentions (present in space messages, not DMs)
    text = re.sub(r"<users/\d+>", "", text).strip()
    if not text:
        return

    chat_id = _user_name_to_id(sender_name)
    logger.info(
        "Google Chat from %s (id=%d) in %s: %.80s",
        sender_email or sender_name,
        chat_id,
        space_name,
        text,
    )

    reply = await run_claude_fn(text, chat_id)
    for chunk in _chunk(reply):
        await _send_reply(chat_creds, space_name, chunk, loop)


async def start_google_chat(
    credentials_path: str,
    project_id: str,
    subscription_id: str,
    run_claude_fn: Callable[[str, int], Awaitable[str]],
    allowed_emails: set[str],
) -> None:
    """
    Start the Google Chat bot. Designed to run as an asyncio task alongside
    the Telegram bot. Exits silently if google-cloud-pubsub is not installed.
    """
    try:
        from google.cloud import pubsub_v1
        from google.oauth2 import service_account
    except ImportError:
        logger.warning(
            "google-cloud-pubsub not installed — Google Chat disabled. "
            "Run: pip install google-cloud-pubsub google-auth"
        )
        return

    try:
        chat_creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=_CHAT_SCOPES
        )
        pubsub_creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=_PUBSUB_SCOPES
        )
    except Exception as e:
        logger.error(
            "Failed to load Google service account key at %s: %s", credentials_path, e
        )
        return

    loop = asyncio.get_running_loop()

    try:
        subscriber = pubsub_v1.SubscriberClient(credentials=pubsub_creds)
    except Exception as e:
        logger.error("Failed to create Pub/Sub subscriber: %s", e)
        return

    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    def _on_pubsub_message(msg) -> None:
        try:
            event = json.loads(msg.data.decode("utf-8"))
        except Exception as e:
            logger.error("Malformed Pub/Sub message: %s", e)
            msg.ack()
            return

        fut = asyncio.run_coroutine_threadsafe(
            _handle_event(event, chat_creds, run_claude_fn, allowed_emails, loop),
            loop,
        )
        try:
            fut.result(timeout=300)
            msg.ack()
        except TimeoutError:
            logger.error("Claude response timed out — nacking for retry")
            msg.nack()
        except Exception as e:
            logger.exception("Error handling Chat message: %s", e)
            msg.ack()

    streaming_future = subscriber.subscribe(subscription_path, callback=_on_pubsub_message)
    logger.info("Google Chat bot listening on %s", subscription_path)

    try:
        await asyncio.Event().wait()  # keep alive until task is cancelled
    except asyncio.CancelledError:
        streaming_future.cancel()
        subscriber.close()
        logger.info("Google Chat subscriber stopped")
    except Exception as e:
        logger.exception("Google Chat subscriber crashed: %s", e)
        streaming_future.cancel()
        subscriber.close()
