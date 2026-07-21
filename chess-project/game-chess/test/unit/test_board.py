from shared.model.board import Board

def make_board(rows):
    grid = [row.split() for row in rows]
    return Board(grid)

def test_get_piece():
    board = make_board(["wR . .", ". . ."])
    assert board.get_piece((0, 0)) == "wR"

def test_set_piece():
    board = make_board([". . .", ". . ."])
    board.set_piece((1, 1), "bN")
    assert board.get_piece((1, 1)) == "bN"

def test_is_inside_true_and_false():
    board = make_board([". .", ". ."])
    assert board.is_inside((1, 1)) is True
    assert board.is_inside((5, 5)) is False