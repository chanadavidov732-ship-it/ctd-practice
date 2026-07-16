from model.board import Board
from input.board_mapper import BoardMapper
from rules.piece_rules import pawn_start_row
from ui.sprite_manager import SpriteManager
from ui.renderer import Renderer

# from model.game_state import GameState
# from realtime.realtime_arbiter import RealTimeArbiter
# from engine.game_engine import GameEngine
# from input.controller import Controller
# from io_options.board_parser import read_board, validate_board
# from text_test.script_runner import run_commands


BACK_RANK_ORDER = ["R", "N", "B", "Q", "K", "B", "N", "R"]


def main():
    grid = [["." for _ in range(8)] for _ in range(8)]
    height = len(grid)
    width = len(grid[0])
    for col in range(width):
        grid[pawn_start_row("b", height)][col] = "bP"
        grid[pawn_start_row("w", height)][col] = "wP"
        grid[0][col] = "b" + BACK_RANK_ORDER[col]
        grid[height - 1][col] = "w" + BACK_RANK_ORDER[col]

    square_size = 100

    board = Board(grid)
    board_mapper = BoardMapper(board, square_size)

    sprite_manager = SpriteManager(sprite_size=square_size)
    renderer = Renderer(sprite_manager, board_mapper, square_size=square_size)

    pieces = []
    for row in range(board.height):
        for col in range(board.width):
            token = board.get_piece((col, row))
            if token != ".":
                pieces.append({"token": token, "pos": (col, row)})

    renderer.render({"pieces": pieces})

    # error = validate_board(grid)
    # if error:
    #     print(error)
    #     return
    #
    # game_state = GameState()
    # arbiter = RealTimeArbiter(board, game_state)
    # game_engine = GameEngine(board, game_state, arbiter)
    # controller = Controller(board, board_mapper, game_engine)
    #
    # run_commands(controller, game_engine, board)


if __name__ == "__main__":
    main()
