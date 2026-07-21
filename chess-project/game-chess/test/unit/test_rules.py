from shared.rules.piece_rules import is_legal_move
from shared.rules.piece_rules import is_legal_pawn_move, is_legal_pawn_capture

def test_king_one_step_legal():
    assert is_legal_move("K", (3, 3), (3, 4)) is True
    assert is_legal_move("K", (3, 3), (4, 4)) is True

def test_king_two_steps_illegal():
    assert is_legal_move("K", (3, 3), (3, 5)) is False

def test_rook_straight_line_legal():
    assert is_legal_move("R", (0, 0), (0, 5)) is True
    assert is_legal_move("R", (0, 0), (5, 0)) is True

def test_rook_diagonal_illegal():
    assert is_legal_move("R", (0, 0), (3, 3)) is False

def test_bishop_diagonal_legal():
    assert is_legal_move("B", (2, 2), (5, 5)) is True

def test_bishop_straight_line_illegal():
    assert is_legal_move("B", (2, 2), (2, 6)) is False

def test_queen_straight_and_diagonal_legal():
    assert is_legal_move("Q", (3, 3), (3, 0)) is True
    assert is_legal_move("Q", (3, 3), (6, 6)) is True

def test_queen_knight_shape_illegal():
    assert is_legal_move("Q", (3, 3), (4, 5)) is False

def test_knight_l_shape_legal():
    assert is_legal_move("N", (3, 3), (4, 5)) is True
    assert is_legal_move("N", (3, 3), (1, 4)) is True

def test_knight_straight_illegal():
    assert is_legal_move("N", (3, 3), (3, 5)) is False

def test_white_pawn_moves_upward():
    assert is_legal_pawn_move(0, -1, "w", 5, 8) is True

def test_black_pawn_moves_downward():
    assert is_legal_pawn_move(0, 1, "b", 3, 8) is True

def test_pawn_two_cells_only_from_start_row():
    assert is_legal_pawn_move(0, -2, "w", 6, 8) is True   
    assert is_legal_pawn_move(0, -2, "w", 5, 8) is False

def test_pawn_cannot_move_two_cells_diagonally():
    assert is_legal_pawn_move(1, -2, "w", 7, 8) is False

def test_pawn_capture_diagonal_only():
    assert is_legal_pawn_capture(1, -1, "w") is True
    assert is_legal_pawn_capture(-1, -1, "w") is True
    assert is_legal_pawn_capture(1, 1, "b") is True

def test_pawn_cannot_capture_forward():
    assert is_legal_pawn_capture(0, -1, "w") is False