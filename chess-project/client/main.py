import asyncio
import logging
import threading
import time

from client.cli.home import run_home_menu
from client.cli.login import SERVER_URI, do_login
from client.network.connection import ServerConnection
from client.network.game_bridge import GameBridge
from client.network.remote_game_engine import RemoteGameEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def _async_client_flow(bridge: GameBridge) -> None:
    connection = ServerConnection(SERVER_URI)
    await connection.connect()
    try:
        if await do_login(connection):
            await run_home_menu(connection, bridge)
    finally:
        await connection.close()
        bridge.notify_done()


def _run_graphical_game(engine: RemoteGameEngine) -> None:
    # Imported lazily: only the graphical path needs cv2/Img, not the plain CLI flow.
    from client.input.board_mapper import BoardMapper
    from client.input.controller import Controller
    from client.ui.renderer import Renderer

    board_mapper = BoardMapper(engine.board)
    controller = Controller(engine.board, board_mapper, engine)
    move_history: list = []
    renderer = Renderer(engine.board, controller, engine, move_history)
    renderer.player_name_white = engine.white_username
    renderer.player_name_black = engine.black_username

    last_time = time.perf_counter()
    running = True
    while running:
        now = time.perf_counter()
        elapsed_ms = (now - last_time) * 1000
        last_time = now

        engine.advance_time(elapsed_ms)
        move_history.extend(engine.pop_newly_settled())
        running = renderer.render()


def main() -> None:
    bridge = GameBridge()
    network_thread = threading.Thread(target=lambda: asyncio.run(_async_client_flow(bridge)), daemon=True)
    network_thread.start()

    while True:
        engine = bridge.wait_for_game()
        if engine is None:
            break
        _run_graphical_game(engine)

    network_thread.join()


if __name__ == "__main__":
    main()
