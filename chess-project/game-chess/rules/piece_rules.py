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



# ADDED: שורת המוצא של רגלים לכל צבע, לצורך זיהוי "מהלך פתיחה כפול"
PAWN_START_ROW = {"w": 6, "b": 1}


# ADDED: כיוון התקדמות הרגלי לפי צבע (לבן = מעלה = row קטן יותר)
def _pawn_forward_direction(color):
    return -1 if color == "w" else 1


# ADDED: תבנית תנועה רגילה (ללא תפיסה) - עמודה קבועה, קדימה משבצת אחת, או שתיים משורת המוצא
def is_legal_pawn_move(dx, dy, color, from_row):
    forward = _pawn_forward_direction(color)
    if dx != 0:
        return False
    if dy == forward:
        return True
    if dy == forward * 2 and from_row == PAWN_START_ROW[color]:
        return True
    return False


# ADDED: תבנית תפיסה - אלכסון יחיד קדימה בלבד
def is_legal_pawn_capture(dx, dy, color):
    forward = _pawn_forward_direction(color)
    return abs(dx) == 1 and dy == forward