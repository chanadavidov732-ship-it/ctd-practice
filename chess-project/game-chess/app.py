from game_setup import build_game
from io_options.board_parser import read_board, validate_board
from text_test.script_runner import run_commands


def main():
    grid = read_board()

    error = validate_board(grid)
    if error:
        print(error)
        return

    board, game_state, arbiter, game_engine, board_mapper, controller = build_game(grid)

    run_commands(controller, game_engine, board)


if __name__ == "__main__":
    main()
