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



def pawn_promotion_row(color, board_height):
    """שורת ההכתרה - הקצה הנגדי לשורת המוצא."""
    return 0 if color == "w" else board_height - 1

MOVEMENT_VALIDATORS = {
    "K": _validate_king,
    "Q": _validate_queen,
    "R": _validate_rook,
    "B": _validate_bishop,
    "N": _validate_knight,
}


def is_legal_move(piece_type, from_pos, to_pos):
    """בודק אך ורק את חוקיות הצורה של המהלך עבור סוג הכלי הנתון."""
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    validator = MOVEMENT_VALIDATORS.get(piece_type)
    if validator is None:
        return False
    return validator(dx, dy)


SLIDING_PIECES = {"Q", "R", "B"}


def is_sliding_piece(piece_type):
    return piece_type in SLIDING_PIECES

def pawn_start_row(color, board_height):
    """שורת המוצא של רגלי - שורה אחת לפנים מהקצה של אותו צבע."""
    return board_height - 2 if color == "w" else 1

def _pawn_forward_direction(color):
    return -1 if color == "w" else 1


def is_legal_pawn_move(dx, dy, color, from_row, board_height):
    forward = _pawn_forward_direction(color)
    if dx != 0:
        return False
    if dy == forward:
        return True
    if dy == forward * 2 and from_row == pawn_start_row(color, board_height):
        return True
    return False


def is_legal_pawn_capture(dx, dy, color):
    forward = _pawn_forward_direction(color)
    return abs(dx) == 1 and dy == forward