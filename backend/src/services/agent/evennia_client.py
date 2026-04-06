"""
Async WebSocket client for Evennia.

Speaks the same JSON protocol as the React frontend (useEvennia.ts):
  Send: ["text", ["command"], {}]
  Recv: ["text", ["..."], {}] / ["prompt", [">>>"], {}]

Handles auth, ANSI stripping, and message accumulation.
"""

import asyncio
import json
import logging
import re

import websockets

logger = logging.getLogger(__name__)

# Covers ANSI color codes, xterm256, cursor control, bell
_ANSI_RE = re.compile(r'\033\[[0-9;]*[mKHJ]|\007')


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub('', text)


class EvenniaClient:
    """Async WebSocket client for Evennia, matching the frontend protocol."""

    def __init__(self, url: str = "ws://localhost:4002"):
        self.url = url
        self.ws = None
        self._text_buffer: asyncio.Queue = asyncio.Queue()
        self._special_buffer: asyncio.Queue = asyncio.Queue()
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
                    elif cmdname == "logged_in":
                        await self._special_buffer.put("logged_in")
                    # OOB events (room_entered, room_left, etc.) are silently ignored
                except (json.JSONDecodeError, IndexError):
                    # Non-JSON or malformed — treat as raw text
                    await self._text_buffer.put(str(raw_msg))
        except websockets.ConnectionClosed:
            logger.info("Evennia WebSocket connection closed")
        except asyncio.CancelledError:
            pass

    async def authenticate(self, username: str, password: str) -> str:
        """Log in to Evennia. Returns accumulated welcome text."""
        await self.send_command(f"connect {username} {password}")

        # Wait for logged_in signal or timeout
        accumulated = []
        try:
            while True:
                # Check for logged_in signal
                try:
                    signal = self._special_buffer.get_nowait()
                    if signal == "logged_in":
                        break
                except asyncio.QueueEmpty:
                    pass

                # Accumulate text with timeout
                try:
                    item = await asyncio.wait_for(self._text_buffer.get(), timeout=10.0)
                    if item is None:  # prompt sentinel
                        continue
                    accumulated.append(item)
                except asyncio.TimeoutError:
                    logger.warning("Auth timeout — no logged_in signal received")
                    break
        except Exception as e:
            logger.error(f"Auth error: {e}")

        welcome = "".join(accumulated)
        logger.info(f"Authenticated as {username}")
        return strip_ansi(welcome)

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

        return strip_ansi("".join(accumulated))

    async def disconnect(self):
        """Close the WebSocket connection."""
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
