import pathlib
import sys
import time

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "game-chess"))

from game_setup import build_game
from io_options.board_parser import read_board, validate_board
from client.ui.renderer import Renderer

DEFAULT_GRID = [
    ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
    ["bP"] * 8,
    ["."] * 8,
    ["."] * 8,
    ["."] * 8,
    ["."] * 8,
    ["wP"] * 8,
    ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"],
]


def main():
    # No piped/redirected stdin (plain `python ui/app.py`) -> just start a
    # standard game instead of requiring the text board protocol on stdin.
    grid = DEFAULT_GRID if sys.stdin.isatty() else read_board()

    error = validate_board(grid)
    if error:
        print(error)
        return

    board, game_state, arbiter, game_engine, board_mapper, controller = build_game(grid)

    move_history = []
    renderer = Renderer(board, controller, game_engine, move_history)
    if not renderer.prompt_player_names():
        return

    last_time = time.perf_counter()
    running = True
    while running:
        now = time.perf_counter()
        elapsed_ms = (now - last_time) * 1000
        last_time = now

        settled = game_engine.advance_time(elapsed_ms)
        move_history.extend(settled)
        running = renderer.render()


if __name__ == "__main__":
    main()
