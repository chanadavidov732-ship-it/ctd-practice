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
        self._loop = asyncio.get_running_loop()
        await asyncio.Event().wait()

    def connect(self, uri: str) -> None:
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
        if self._loop is None or self._connection is None:
            raise RuntimeError("AppBridge.run() must be started before send_request()")

        if envelope.request_id is None:
            envelope.request_id = uuid.uuid4().hex

        async def _send() -> None:
            self._pending_request_id = envelope.request_id
            await self._connection.send(envelope)

        asyncio.run_coroutine_threadsafe(_send(), self._loop)

    def build_remote_engine(self, payload: dict) -> RemoteGameEngine:
        if self._loop is None or self._connection is None:
            raise RuntimeError("AppBridge.run() must be started before build_remote_engine()")
        return build_remote_engine(self._connection, payload, loop=self._loop)

    def poll_events(self) -> list[AppEvent]:
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                break
        return events
