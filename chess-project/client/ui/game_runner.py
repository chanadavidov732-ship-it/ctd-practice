"""Runs the existing (iteration 9) graphical game loop -- Controller + Renderer
built from a RemoteGameEngine -- so any wrapper screen that receives
"game_started" (Room in iteration 14, Matchmaking in iteration 15) can reuse
it without duplicating it.

Resurrects client/main.py's pre-iteration-12 `_run_graphical_game` (deleted
when main.py switched to the graphical Login/Home flow), adapted to pull
game_update/game_over/disconnect_countdown/*_rejected envelopes from
AppBridge.poll_events() each frame instead of a separate asyncio task reading
the connection directly -- AppBridge already owns the one continuous receive
loop on the network thread, so a second reader on the same connection isn't
an option here the way client/network/game_bridge.py's pump_game_messages was
for the CLI's GameBridge-based flow.
"""

import time

from client.network.app_bridge import AppBridge, BROADCAST
from client.network.game_bridge import apply_game_envelope
from client.network.remote_game_engine import RemoteGameEngine


def run_graphical_game(bridge: AppBridge, engine: RemoteGameEngine) -> None:
    # Imported lazily: only the graphical path needs cv2/Img, not every screen.
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
