from client.io_options.board_parser import validate_board

def make_board(rows):
    return [row.split() for row in rows]

def test_validate_board_valid():
    board = make_board([". . .", ". . ."])
    assert validate_board(board) is None

def test_validate_board_empty():
    assert validate_board([]) == "ERROR EMPTY_BOARD"

def test_validate_board_row_width_mismatch():
    board = make_board([". . .", ". ."])
    assert validate_board(board) == "ERROR ROW_WIDTH_MISMATCH"

def test_validate_board_unknown_token():
    board = make_board([". X ."])
    assert validate_board(board) == "ERROR UNKNOWN_TOKEN"