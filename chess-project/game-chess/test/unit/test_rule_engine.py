from model.board import Board
from rules import rule_engine


def make_board(rows):
    grid = [row.split() for row in rows]
    return Board(grid)

def test_legal_move_returns_ok():
    board = make_board([". . . .", ". . . ."])
    assert rule_engine.check_move(board, "R", "w", (0, 0), (3, 0)) == rule_engine.OK

def test_illegal_shape_returns_illegal_shape():
    board = make_board([". . . .", ". . . ."])
    assert rule_engine.check_move(board, "K", "w", (0, 0), (3, 0)) == rule_engine.ILLEGAL_SHAPE


def test_out_of_bounds_returns_out_of_bounds():
    board = make_board([". . . .", ". . . ."])
    assert rule_engine.check_move(board, "R", "w", (0, 0), (10, 0)) == rule_engine.OUT_OF_BOUNDS

def test_blocked_by_piece_in_path():
    board = make_board(["wR wN . .", ". . . ."])
    assert rule_engine.check_move(board, "R", "w", (0, 0), (3, 0)) == rule_engine.BLOCKED

def test_friendly_fire_returns_friendly_fire():
    board = make_board(["wR wN . .", ". . . ."])
    assert rule_engine.check_move(board, "R", "w", (0, 0), (1, 0)) == rule_engine.FRIENDLY_FIRE


def test_capture_enemy_returns_ok():
    board = make_board(["wR bN . .", ". . . ."])
    assert rule_engine.check_move(board, "R", "w", (0, 0), (1, 0)) == rule_engine.OK

def test_pawn_straight_move_to_empty_is_ok():
    board = make_board([". . .", ". . .", "wP . ."])
    assert rule_engine.check_move(board, "P", "w", (0, 2), (0, 1)) == rule_engine.OK


def test_pawn_straight_move_blocked_by_any_piece():
    board = make_board([". . .", "bN . .", "wP . ."])
    assert rule_engine.check_move(board, "P", "w", (0, 2), (0, 1)) == rule_engine.BLOCKED


def test_pawn_diagonal_capture_enemy_is_ok():
    board = make_board([". . .", ". bN .", "wP . ."])
    assert rule_engine.check_move(board, "P", "w", (0, 2), (1, 1)) == rule_engine.OK


def test_pawn_diagonal_to_empty_is_illegal():
    board = make_board([". . .", ". . .", "wP . ."])
    assert rule_engine.check_move(board, "P", "w", (0, 2), (1, 1)) == rule_engine.ILLEGAL_SHAPE


def test_pawn_two_cells_move_illegal_not_from_start():
    board = make_board([". . .", ". . .", ". . .", "wP . ."])
    assert rule_engine.check_move(board, "P", "w", (0, 3), (0, 1)) == rule_engine.ILLEGAL_SHAPE