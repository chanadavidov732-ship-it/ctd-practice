def _is_straight_line(dx, dy):
    return (dx == 0) != (dy == 0)


def _is_diagonal(dx, dy):
    return dx != 0 and abs(dx) == abs(dy)


def _validate_king(dx, dy):
    return max(abs(dx), abs(dy)) == 1


def _validate_rook(dx, dy):
    return _is_straight_line(dx, dy)


def _validate_bishop(dx, dy):
    return _is_diagonal(dx, dy)


def _validate_queen(dx, dy):
    return _is_straight_line(dx, dy) or _is_diagonal(dx, dy)


def _validate_knight(dx, dy):
    return (abs(dx), abs(dy)) in {(1, 2), (2, 1)}


def _validate_pawn(dx, dy):
    return True  # TODO: יטופל בשלב 8 (הוספת שאר הכלים) - כרגע כל תנועה מותרת


MOVEMENT_VALIDATORS = {
    "K": _validate_king,
    "Q": _validate_queen,
    "R": _validate_rook,
    "B": _validate_bishop,
    "N": _validate_knight,
    "P": _validate_pawn,
}


def is_legal_move(piece_type, from_pos, to_pos):
    """בודק אך ורק את חוקיות הצורה של המהלך עבור סוג הכלי הנתון."""
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    validator = MOVEMENT_VALIDATORS.get(piece_type)
    if validator is None:
        return False
    return validator(dx, dy)