import asyncio
import logging
import queue

from client.network.remote_game_engine import RemoteGameEngine
from shared.config import (
    MOVE_FROM_KEY,
    MOVE_TO_KEY,
    MSG_DISCONNECT_COUNTDOWN,
    MSG_GAME_OVER,
    MSG_GAME_UPDATE,
    MSG_JUMP,
    MSG_JUMP_REJECTED,
    MSG_MOVE,
    MSG_MOVE_REJECTED,
    POS_KEY,
    YOUR_COLOR_KEY,
)
from shared.protocol import Envelope

logger = logging.getLogger("client")


class GameBridge:
    def __init__(self):
        self._queue: "queue.Queue" = queue.Queue()

    def notify_game_started(self, engine: RemoteGameEngine) -> None:
        self._queue.put(engine)

    def notify_done(self) -> None:
        self._queue.put(None)

    def wait_for_game(self) -> RemoteGameEngine | None:
        return self._queue.get()


def build_remote_engine(connection, payload: dict, loop: asyncio.AbstractEventLoop | None = None) -> RemoteGameEngine:
    loop = loop or asyncio.get_running_loop()

    def send_move(from_pos, to_pos) -> None:
        envelope = Envelope(type=MSG_MOVE, payload={MOVE_FROM_KEY: list(from_pos), MOVE_TO_KEY: list(to_pos)})
        asyncio.run_coroutine_threadsafe(connection.send(envelope), loop)

    def send_jump(pos) -> None:
        envelope = Envelope(type=MSG_JUMP, payload={POS_KEY: list(pos)})
        asyncio.run_coroutine_threadsafe(connection.send(envelope), loop)

    return RemoteGameEngine(payload[YOUR_COLOR_KEY], payload, send_move, send_jump)


def apply_game_envelope(engine: RemoteGameEngine, envelope: Envelope) -> bool:
    if envelope.type == MSG_GAME_UPDATE:
        engine.apply_snapshot(envelope.payload)
    elif envelope.type == MSG_GAME_OVER:
        engine.mark_game_over(envelope.payload)
        return True
    elif envelope.type == MSG_DISCONNECT_COUNTDOWN:
        engine.set_disconnect_countdown(envelope.payload)
    elif envelope.type in (MSG_MOVE_REJECTED, MSG_JUMP_REJECTED):
        logger.info("%s: %s", envelope.type, envelope.payload)
    return False


async def pump_game_messages(connection, engine: RemoteGameEngine) -> None:
    while True:
        envelope = await connection.receive()
        if apply_game_envelope(engine, envelope):
            return
