import asyncio
import logging
import queue

from client.network.remote_game_engine import RemoteGameEngine
from shared.protocol import Envelope

logger = logging.getLogger("client")


class GameBridge:
    """Hands a started game off from the network (asyncio, background thread)
    to the graphical UI (OpenCV, main thread). The main thread blocks on
    wait_for_game() until either a game starts or the network side is done
    without one (e.g. the user quit from the CLI menus)."""

    def __init__(self):
        self._queue: "queue.Queue" = queue.Queue()

    def notify_game_started(self, engine: RemoteGameEngine) -> None:
        self._queue.put(engine)

    def notify_done(self) -> None:
        self._queue.put(None)

    def wait_for_game(self) -> RemoteGameEngine | None:
        return self._queue.get()


def build_remote_engine(connection, payload: dict, loop: asyncio.AbstractEventLoop | None = None) -> RemoteGameEngine:
    """`loop` defaults to the caller's own running loop (the CLI flow calls this
    from inside the network coroutine itself). client.network.app_bridge.AppBridge
    passes its own captured loop explicitly instead, since it builds the engine
    from the main (OpenCV) thread, where there is no running loop to detect."""
    loop = loop or asyncio.get_running_loop()

    def send_move(from_pos, to_pos) -> None:
        envelope = Envelope(type="move", payload={"from": list(from_pos), "to": list(to_pos)})
        asyncio.run_coroutine_threadsafe(connection.send(envelope), loop)

    def send_jump(pos) -> None:
        envelope = Envelope(type="jump", payload={"pos": list(pos)})
        asyncio.run_coroutine_threadsafe(connection.send(envelope), loop)

    return RemoteGameEngine(payload["your_color"], payload, send_move, send_jump)


def apply_game_envelope(engine: RemoteGameEngine, envelope: Envelope) -> bool:
    """Applies one game-related envelope to `engine`. Returns True if it was
    game_over (the signal both pump_game_messages and client.ui.game_runner use
    to know the game has ended)."""
    if envelope.type == "game_update":
        engine.apply_snapshot(envelope.payload)
    elif envelope.type == "game_over":
        engine.mark_game_over(envelope.payload)
        return True
    elif envelope.type == "disconnect_countdown":
        engine.set_disconnect_countdown(envelope.payload)
    elif envelope.type in ("move_rejected", "jump_rejected"):
        logger.info("%s: %s", envelope.type, envelope.payload)
    return False


async def pump_game_messages(connection, engine: RemoteGameEngine) -> None:
    """Keeps applying server broadcasts to `engine` until the game ends."""
    while True:
        envelope = await connection.receive()
        if apply_game_envelope(engine, envelope):
            return
