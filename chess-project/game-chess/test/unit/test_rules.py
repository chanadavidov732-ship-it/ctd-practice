from rules.piece_rules import is_legal_move


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


def test_pawn_always_legal():
    assert is_legal_move("P", (3, 3), (3, 4)) is True
    assert is_legal_move("P", (3, 3), (7, 0)) is True