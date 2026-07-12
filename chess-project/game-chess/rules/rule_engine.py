from rules.piece_rules import is_legal_move

OK = "OK"
OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
ILLEGAL_SHAPE = "ILLEGAL_SHAPE"


def check_move(board, piece_type, from_pos, to_pos):
    """מחזיר קוד תוצאה ברור: OK / OUT_OF_BOUNDS / ILLEGAL_SHAPE.
    אינו מבצע שום שינוי בלוח."""
    if not board.is_inside(to_pos):
        return OUT_OF_BOUNDS

    if not is_legal_move(piece_type, from_pos, to_pos):
        return ILLEGAL_SHAPE

    return OK