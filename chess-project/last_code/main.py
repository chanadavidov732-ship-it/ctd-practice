from game import Game, read_board, validate_board, run_commands


def main():
    board = read_board()

    error = validate_board(board)
    if error:
        print(error)
        return

    game = Game(board)
    run_commands(game)


if __name__ == "__main__":
    main()