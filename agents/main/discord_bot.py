"""
agents/main/discord_bot.py — Discord channel for claudhaus.

Runs as a discord.py client alongside the Telegram bot in the same event loop.
The run_claude_fn is passed in from agent.py to avoid circular imports.
"""
import logging
import os
from typing import Callable, Awaitable

logger = logging.getLogger("discord_bot")

_DISCORD_MAX_CHARS = 1900  # Discord hard limit is 2000; leave headroom


def _chunk(text: str, max_len: int = _DISCORD_MAX_CHARS) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        remaining = text[pos:]
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        slice_ = text[pos: pos + max_len]
        cut = slice_.rfind("\n\n")
        if cut == -1:
            cut = slice_.rfind("\n")
        if cut <= 0:
            cut = max_len
        else:
            cut += 1
        chunks.append(text[pos: pos + cut].strip())
        pos += cut
    return [c for c in chunks if c]


async def start_discord(
    token: str,
    run_claude_fn: Callable[[str, int], Awaitable[str]],
    allowed_user_ids: set[int],
    allowed_guild_ids: set[int],
) -> None:
    """
    Start the Discord bot. Designed to be run as an asyncio task alongside
    the Telegram bot. Exits silently if discord.py is not installed.
    """
    try:
        import discord
    except ImportError:
        logger.warning("discord.py not installed — Discord channel disabled. Run: pip install discord.py")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        logger.info("Discord bot ready: %s (ID %s)", client.user, client.user.id)

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

        # Guild allowlist — DMs always allowed if user is allowed
        if message.guild and allowed_guild_ids and message.guild.id not in allowed_guild_ids:
            return

        # User allowlist
        if allowed_user_ids and message.author.id not in allowed_user_ids:
            return

        # Ignore messages not directed at the bot in guild channels
        if message.guild and client.user not in message.mentions and not isinstance(message.channel, discord.DMChannel):
            return

        content = message.content
        # Strip the bot mention if present
        if client.user:
            content = content.replace(f"<@{client.user.id}>", "").replace(f"<@!{client.user.id}>", "").strip()

        if not content:
            return

        chat_id = message.author.id  # use Discord user ID as session key
        async with message.channel.typing():
            reply = await run_claude_fn(content, chat_id)

        for chunk in _chunk(reply):
            await message.channel.send(chunk)

    try:
        await client.start(token)
    except discord.LoginFailure:
        logger.error("Discord login failed — check DISCORD_BOT_TOKEN")
    except Exception as e:
        logger.exception("Discord bot crashed: %s", e)
