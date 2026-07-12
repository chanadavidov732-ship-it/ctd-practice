from model.board import Board
from rules import rule_engine


def make_board(rows):
    grid = [row.split() for row in rows]
    return Board(grid)


def test_legal_move_returns_ok():
    board = make_board([". . . .", ". . . ."])
    assert rule_engine.check_move(board, "R", (0, 0), (3, 0)) == rule_engine.OK


def test_illegal_shape_returns_illegal_shape():
    board = make_board([". . . .", ". . . ."])
    assert rule_engine.check_move(board, "K", (0, 0), (3, 0)) == rule_engine.ILLEGAL_SHAPE


def test_out_of_bounds_returns_out_of_bounds():
    board = make_board([". . . .", ". . . ."])
    assert rule_engine.check_move(board, "R", (0, 0), (10, 0)) == rule_engine.OUT_OF_BOUNDS