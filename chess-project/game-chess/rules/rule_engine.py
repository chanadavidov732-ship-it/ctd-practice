from model.piece import token_color
from rules.piece_rules import is_legal_move, is_sliding_piece
from model.piece import token_color
from rules.piece_rules import is_legal_move, is_sliding_piece, is_legal_pawn_move, is_legal_pawn_capture  

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
    if not board.is_inside(to_pos):
        return OUT_OF_BOUNDS

    if piece_type == "P":
        return _check_pawn_move(board, piece_color, from_pos, to_pos)

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


def _check_pawn_move(board, piece_color, from_pos, to_pos):
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    from_row = from_pos[1]
    dest_token = board.get_piece(to_pos)

    if is_legal_pawn_move(dx, dy, piece_color, from_row):
        if dest_token != ".":
            return BLOCKED  

    if is_legal_pawn_capture(dx, dy, piece_color):
        if dest_token == ".":
            return ILLEGAL_SHAPE  
        if token_color(dest_token) == piece_color:
            return FRIENDLY_FIRE
        return OK

    return ILLEGAL_SHAPE