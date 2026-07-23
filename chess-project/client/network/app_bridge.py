"""Generalizes client.network.game_bridge.GameBridge's queue-based handoff
pattern to every graphical wrapper screen, not just the game-start handoff.

Threading model (same split as GameBridge): AppBridge lives on the background
asyncio network thread (started via `asyncio.run(bridge.serve())`) and owns
the ServerConnection; connect(), send_request() and poll_events() are called
from the main (OpenCV) thread. All cross-thread handoff goes through
queue.Queue (thread-safe) and asyncio.run_coroutine_threadsafe (same
mechanism client/network/game_bridge.py already uses for send_move/send_jump).
"""

import asyncio
import queue
import uuid
from dataclasses import dataclass

import websockets

from client.network.connection import ServerConnection
from client.network.game_bridge import build_remote_engine
from client.network.remote_game_engine import RemoteGameEngine
from shared.protocol import Envelope

CONNECTED = "connected"
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

    async def serve(self) -> None:
        """The network thread's entry point (run via `asyncio.run(bridge.serve())`).
        Captures this thread's event loop -- so connect()/send_request(),
        called from the main thread, have somewhere to hand work off to via
        run_coroutine_threadsafe -- then idles for the rest of the process's
        life. The actual connection is established later by connect()."""
        self._loop = asyncio.get_running_loop()
        await asyncio.Event().wait()

    def connect(self, uri: str) -> None:
        """Called from the main thread to (re)establish the connection --
        once at startup and again each time a screen's "try again" is
        clicked after a drop. Success pushes CONNECTED and starts the receive
        loop (run()); failure pushes CONNECTION_LOST, exactly like a drop
        after a successful connection, so screens react to both the same way."""
        if self._loop is None:
            raise RuntimeError("AppBridge.serve() must be running before connect()")
        asyncio.run_coroutine_threadsafe(self._connect_and_run(uri), self._loop)

    async def _connect_and_run(self, uri: str) -> None:
        connection = ServerConnection(uri)
        try:
            await connection.connect()
        except (OSError, websockets.InvalidHandshake):
            self._events.put(AppEvent(kind=CONNECTION_LOST))
            return
        self._events.put(AppEvent(kind=CONNECTED))
        await self.run(connection)

    async def run(self, connection: ServerConnection) -> None:
        """Runs on the network thread: owns `connection` and keeps receiving
        until the connection closes. One continuous loop replaces the
        scattered point-in-time connection.receive() calls that client/cli/*.py
        still use directly for their own (untouched) textual flow."""
        self._connection = connection
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

    def build_remote_engine(self, payload: dict) -> RemoteGameEngine:
        """Called from the main thread once a "game_started" broadcast arrives
        on some screen. Reuses game_bridge.build_remote_engine's send_move/
        send_jump closures, but passes this bridge's own captured loop instead
        of letting it call asyncio.get_running_loop() -- there is no running
        loop on the main thread to detect."""
        if self._loop is None or self._connection is None:
            raise RuntimeError("AppBridge.run() must be started before build_remote_engine()")
        return build_remote_engine(self._connection, payload, loop=self._loop)

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
