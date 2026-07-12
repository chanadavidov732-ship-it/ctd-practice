from model.board import Board
from model.game_state import GameState
from realtime.realtime_arbiter import RealTimeArbiter
from engine.game_engine import GameEngine
from input.board_mapper import BoardMapper
from input.controller import Controller
from io_options.board_parser import read_board, validate_board
from text_test.script_runner import run_commands


def main():
    grid = read_board()

    error = validate_board(grid)
    if error:
        print(error)
        return

    board = Board(grid)
    game_state = GameState()
    arbiter = RealTimeArbiter(board, game_state)
    game_engine = GameEngine(board, game_state, arbiter)
    board_mapper = BoardMapper(board)
    controller = Controller(board, board_mapper, game_engine)

    run_commands(controller, game_engine, board)


if __name__ == "__main__":
    main()