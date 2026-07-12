from model.piece import token_color
from rules.piece_rules import is_legal_move, is_sliding_piece

OK = "OK"
OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
ILLEGAL_SHAPE = "ILLEGAL_SHAPE"
BLOCKED = "BLOCKED"
FRIENDLY_FIRE = "FRIENDLY_FIRE"


def _step(delta):
    if delta > 0:
        return 1
    if delta < 0:
        return -1
    return 0


def _squares_between(from_pos, to_pos):
    """מחזיר את המשבצות שבין from_pos ל-to_pos (לא כולל שני הקצוות)."""
    dx = _step(to_pos[0] - from_pos[0])
    dy = _step(to_pos[1] - from_pos[1])

    squares = []
    col, row = from_pos[0] + dx, from_pos[1] + dy
    while (col, row) != to_pos:
        squares.append((col, row))
        col += dx
        row += dy
    return squares


def check_move(board, piece_type, piece_color, from_pos, to_pos):
    """מחזיר קוד תוצאה ברור: OK / OUT_OF_BOUNDS / ILLEGAL_SHAPE / BLOCKED / FRIENDLY_FIRE.
    אינו מבצע שום שינוי בלוח."""
    if not board.is_inside(to_pos):
        return OUT_OF_BOUNDS

    if not is_legal_move(piece_type, from_pos, to_pos):
        return ILLEGAL_SHAPE

    if is_sliding_piece(piece_type):
        for pos in _squares_between(from_pos, to_pos):
            if board.get_piece(pos) != ".":
                return BLOCKED

    dest_token = board.get_piece(to_pos)
    if dest_token != "." and token_color(dest_token) == piece_color:
        return FRIENDLY_FIRE

    return OK