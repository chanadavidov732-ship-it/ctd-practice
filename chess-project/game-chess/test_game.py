import pytest

from game import (
    validate_board,
    is_legal_move,
    Game,
)


def make_board(rows):
    return [row.split() for row in rows]


# ---------- validate_board ----------

def test_validate_board_valid():
    board = make_board([
        ". . .",
        ". . .",
    ])
    assert validate_board(board) is None


def test_validate_board_empty():
    assert validate_board([]) == "ERROR EMPTY_BOARD"


def test_validate_board_row_width_mismatch():
    board = make_board([
        ". . .",
        ". .",
    ])
    assert validate_board(board) == "ERROR ROW_WIDTH_MISMATCH"


def test_validate_board_unknown_token():
    board = make_board([
        ". X .",
    ])
    assert validate_board(board) == "ERROR UNKNOWN_TOKEN"


# ---------- is_legal_move: King ----------

def test_king_one_step_legal():
    assert is_legal_move("K", (3, 3), (3, 4)) is True
    assert is_legal_move("K", (3, 3), (4, 4)) is True


def test_king_two_steps_illegal():
    assert is_legal_move("K", (3, 3), (3, 5)) is False


# ---------- is_legal_move: Rook ----------

def test_rook_straight_line_legal():
    assert is_legal_move("R", (0, 0), (0, 5)) is True
    assert is_legal_move("R", (0, 0), (5, 0)) is True


def test_rook_diagonal_illegal():
    assert is_legal_move("R", (0, 0), (3, 3)) is False


# ---------- is_legal_move: Bishop ----------

def test_bishop_diagonal_legal():
    assert is_legal_move("B", (2, 2), (5, 5)) is True


def test_bishop_straight_line_illegal():
    assert is_legal_move("B", (2, 2), (2, 6)) is False


# ---------- is_legal_move: Queen ----------

def test_queen_straight_and_diagonal_legal():
    assert is_legal_move("Q", (3, 3), (3, 0)) is True
    assert is_legal_move("Q", (3, 3), (6, 6)) is True


def test_queen_knight_shape_illegal():
    assert is_legal_move("Q", (3, 3), (4, 5)) is False


# ---------- is_legal_move: Knight ----------

def test_knight_l_shape_legal():
    assert is_legal_move("N", (3, 3), (4, 5)) is True
    assert is_legal_move("N", (3, 3), (1, 4)) is True


def test_knight_straight_illegal():
    assert is_legal_move("N", (3, 3), (3, 5)) is False


# ---------- is_legal_move: Pawn ----------

def test_pawn_always_legal():
    assert is_legal_move("P", (3, 3), (3, 4)) is True
    assert is_legal_move("P", (3, 3), (7, 0)) is True


# ---------- Game: pixel_to_cell ----------

def test_pixel_to_cell_top_left():
    board = make_board([". .", ". ."])
    game = Game(board)
    assert game.pixel_to_cell(50, 50) == (0, 0)


def test_pixel_to_cell_next_cell():
    board = make_board([". .", ". ."])
    game = Game(board)
    assert game.pixel_to_cell(150, 50) == (1, 0)


def test_pixel_to_cell_outside_board():
    board = make_board([". .", ". ."])
    game = Game(board)
    assert game.pixel_to_cell(500, 500) is None


# ---------- Game: calculate_duration ----------

def test_calculate_duration_straight_line():
    board = make_board([". .", ". ."])
    game = Game(board)
    duration = game.calculate_duration((0, 0), (0, 3))
    assert duration == pytest.approx(600)  # 3 squares * 200ms


# ---------- Game: handle_click + movement flow ----------

def test_legal_move_completes_after_wait():
    board = make_board([
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        "wR . . . . . . .",
    ])
    game = Game(board)

    game.handle_click(50, 750)   # select rook at (0,7)
    game.handle_click(350, 750)  # move to (3,7)

    assert game.get_piece((0, 7)) == "wR"
    assert game.get_piece((3, 7)) == "."

    game.handle_wait(600)  # 3 squares * 200ms

    assert game.get_piece((0, 7)) == "."
    assert game.get_piece((3, 7)) == "wR"


def test_illegal_move_is_ignored():
    board = make_board([
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        "wK . . . . . . .",
    ])
    game = Game(board)

    game.handle_click(50, 750)   # select king at (0,7)
    game.handle_click(350, 750)  # illegal: 3 squares straight

    game.handle_wait(1000)

    assert game.get_piece((0, 7)) == "wK"
    assert game.get_piece((3, 7)) == "."
    assert game.selected is None


def test_capture_enemy_piece():
    board = make_board([
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        "wR . . bN . . . .",
    ])
    game = Game(board)

    game.handle_click(50, 750)   # select rook at (0,7)
    game.handle_click(350, 750)  # move to (3,7), enemy knight there
    game.handle_wait(600)

    assert game.get_piece((3, 7)) == "wR"


def test_locked_piece_click_is_ignored():
    board = make_board([
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        "wR . . . . . . .",
    ])
    game = Game(board)

    game.handle_click(50, 750)   # select rook
    game.handle_click(350, 750)  # send move request, rook now locked

    game.handle_click(50, 750)   # click origin while mid-move: ignored
    assert game.selected is None


def test_reselect_friendly_piece():
    board = make_board([
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        ". . . . . . . .",
        "wR wN . . . . . .",
    ])
    game = Game(board)

    game.handle_click(50, 750)   # select rook at (0,7)
    game.handle_click(150, 750)  # click friendly knight: replace selection

    assert game.selected == {"pos": (1, 7), "color": "w"}