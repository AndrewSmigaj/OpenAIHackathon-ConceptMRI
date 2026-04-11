"""
Async WebSocket client for Evennia.

Speaks the same JSON protocol as the React frontend (useEvennia.ts):
  Send: ["text", ["command"], {}]
  Recv: ["text", ["..."], {}] / ["prompt", [">>>"], {}]

Handles auth, ANSI stripping, and message accumulation.
"""

import asyncio
import html
import json
import logging
import re

import websockets

logger = logging.getLogger(__name__)

# ANSI escape sequences (cursor control, colors, bell)
_ANSI_RE = re.compile(r'\033\[[0-9;]*[mKHJ]|\007')
# Evennia markup codes: |c, |n, |w, |[R, etc. (same pattern as frontend evenniaAnsi.ts)
_EVENNIA_MARKUP_RE = re.compile(r'\|\[[a-zA-Z]|\|[rgybmcwxRGYBMCWXnuis*^]')


_DBREF_RE = re.compile(r'\(#\d+\)')


def clean_evennia_text(text: str) -> str:
    """Clean Evennia WebSocket text for model consumption.

    Decodes HTML entities, strips Evennia color codes, strips ANSI escapes,
    strips Evennia dbrefs like (#20).
    """
    text = html.unescape(text)
    text = _EVENNIA_MARKUP_RE.sub('', text)
    text = _ANSI_RE.sub('', text)
    text = _DBREF_RE.sub('', text)
    return text


class EvenniaClient:
    """Async WebSocket client for Evennia, matching the frontend protocol."""

    def __init__(self, url: str = "ws://localhost:4002"):
        self.url = url
        self.ws = None
        self._text_buffer: asyncio.Queue = asyncio.Queue()
        self._reader_task = None

    async def connect(self):
        """Connect to Evennia and set raw mode."""
        self.ws = await websockets.connect(self.url)
        # Request raw ANSI mode (same as frontend)
        await self.ws.send(json.dumps(["client_options", [], {"raw": True}]))
        # Start background reader
        self._reader_task = asyncio.create_task(self._read_loop())
        logger.info(f"Connected to Evennia at {self.url}")

    async def _read_loop(self):
        """Read messages, route text to buffer, track special messages."""
        try:
            async for raw_msg in self.ws:
                try:
                    msg = json.loads(raw_msg)
                    cmdname, args, kwargs = msg[0], msg[1] if len(msg) > 1 else [], msg[2] if len(msg) > 2 else {}

                    if cmdname == "text":
                        text = "".join(str(a) for a in args)
                        await self._text_buffer.put(text)
                    elif cmdname == "prompt":
                        await self._text_buffer.put(None)  # sentinel for prompt
                    # OOB events (room_entered, room_left, logged_in, etc.) are silently ignored
                except (json.JSONDecodeError, IndexError):
                    # Non-JSON or malformed — treat as raw text
                    await self._text_buffer.put(str(raw_msg))
        except websockets.ConnectionClosed:
            logger.info("Evennia WebSocket connection closed")
        except asyncio.CancelledError:
            pass

    async def authenticate(self, username: str, password: str) -> str:
        """Log in to Evennia. Verifies the session is actually authenticated
        by sending a `look` probe and checking the response doesn't contain
        the unauthenticated welcome banner. Raises RuntimeError on failure.
        """
        await self.send_command(f"connect {username} {password}")
        welcome = await self.read_until_prompt(timeout=10.0)

        # Verify auth actually succeeded — the welcome banner is distinctive
        # and only shown to unauthenticated sessions. If we still see it
        # after a look-probe, auth did not complete.
        await self.send_command("look")
        probe = await self.read_until_prompt(timeout=5.0)

        if "Welcome to LLMud Institute" in probe or "connect <username>" in probe:
            raise RuntimeError(
                f"Evennia authentication failed for {username!r} — still on "
                "welcome screen after connect. If Evennia has an orphaned "
                "session for this account, run `evennia restart` (not reload) "
                "to clear it."
            )

        logger.info(f"Authenticated as {username}")
        return welcome

    async def send_command(self, text: str):
        """Send a text command to Evennia."""
        if self.ws:
            await self.ws.send(json.dumps(["text", [text], {}]))

    async def read_until_prompt(self, timeout: float = 30.0) -> str:
        """Read text messages until a prompt arrives or timeout.

        Evennia sends text fragments followed by a prompt message.
        Accumulates all text, returns concatenated result with ANSI stripped.
        """
        accumulated = []
        try:
            deadline = asyncio.get_event_loop().time() + timeout
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    logger.warning("read_until_prompt timed out")
                    break
                item = await asyncio.wait_for(self._text_buffer.get(), timeout=remaining)
                if item is None:  # prompt sentinel
                    break
                accumulated.append(item)
        except asyncio.TimeoutError:
            logger.warning("read_until_prompt timed out waiting for text")

        return clean_evennia_text("".join(accumulated))

    async def disconnect(self):
        """Send quit and close the WebSocket connection."""
        if self.ws:
            try:
                await self.send_command("quit")
                await asyncio.sleep(0.3)
            except Exception:
                pass
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None
        if self.ws:
            await self.ws.close()
            self.ws = None
        logger.info("Disconnected from Evennia")
