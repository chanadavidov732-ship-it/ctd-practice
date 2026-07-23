"""Generalizes client.network.game_bridge.GameBridge's queue-based handoff
pattern to every graphical wrapper screen, not just the game-start handoff.

Threading model (same split as GameBridge): AppBridge.run() lives on the
background asyncio network thread and owns the ServerConnection; send_request
and poll_events are called from the main (OpenCV) thread. All cross-thread
handoff goes through queue.Queue (thread-safe) and
asyncio.run_coroutine_threadsafe (same mechanism client/network/game_bridge.py
already uses for send_move/send_jump).
"""

import asyncio
import queue
import uuid
from dataclasses import dataclass

import websockets

from client.network.connection import ServerConnection
from shared.protocol import Envelope

RESPONSE = "response"
BROADCAST = "broadcast"
CONNECTION_LOST = "connection_lost"


@dataclass
class AppEvent:
    kind: str
    envelope: Envelope | None = None


class AppBridge:
    def __init__(self):
        self._connection: ServerConnection | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pending_request_id: str | None = None
        self._events: queue.Queue = queue.Queue()

    async def run(self, connection: ServerConnection) -> None:
        """Runs on the network thread: owns `connection` and keeps receiving
        until the connection closes. One continuous loop replaces the
        scattered point-in-time connection.receive() calls that client/cli/*.py
        still use directly for their own (untouched) textual flow."""
        self._connection = connection
        self._loop = asyncio.get_running_loop()
        try:
            while True:
                envelope = await connection.receive()
                self._dispatch(envelope)
        except websockets.ConnectionClosed:
            self._events.put(AppEvent(kind=CONNECTION_LOST))

    def _dispatch(self, envelope: Envelope) -> None:
        if envelope.request_id is not None and envelope.request_id == self._pending_request_id:
            self._pending_request_id = None
            self._events.put(AppEvent(kind=RESPONSE, envelope=envelope))
        else:
            self._events.put(AppEvent(kind=BROADCAST, envelope=envelope))

    def send_request(self, envelope: Envelope) -> None:
        """Called from the main thread. Fire-and-forget: the correlated reply
        (if any) shows up later as a RESPONSE event from poll_events()."""
        if self._loop is None or self._connection is None:
            raise RuntimeError("AppBridge.run() must be started before send_request()")

        if envelope.request_id is None:
            envelope.request_id = uuid.uuid4().hex

        async def _send() -> None:
            self._pending_request_id = envelope.request_id
            await self._connection.send(envelope)

        asyncio.run_coroutine_threadsafe(_send(), self._loop)

    def poll_events(self) -> list[AppEvent]:
        """Called from the main thread, once per frame. Non-blocking: returns
        every event accumulated since the previous call."""
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                break
        return events
