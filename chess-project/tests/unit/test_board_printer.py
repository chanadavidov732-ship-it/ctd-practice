from shared.model.board import Board
from client.io_options.board_printer import print_board

def test_print_board_outputs_rows(capsys):
    board = Board([["wR", "."], [".", "bN"]])
    print_board(board)
    captured = capsys.readouterr()
    assert captured.out == "wR .\n. bN\n"