import time

from client.network.app_bridge import AppBridge, BROADCAST
from client.network.game_bridge import apply_game_envelope
from client.network.remote_game_engine import RemoteGameEngine


def run_graphical_game(bridge: AppBridge, engine: RemoteGameEngine) -> bool:
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

        for event in bridge.poll_events():
            if event.kind == BROADCAST and event.envelope is not None:
                apply_game_envelope(engine, event.envelope)

        engine.advance_time(elapsed_ms)
        move_history.extend(engine.pop_newly_settled())
        running = renderer.render()

    return renderer.wants_menu
