from shared.model.piece import token_color, token_type
from shared.rules import rule_engine

OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
NOT_YOUR_PIECE = "NOT_YOUR_PIECE"


def validate_move(board, color, from_pos, to_pos) -> str:
    if not (board.is_inside(from_pos) and board.is_inside(to_pos)):
        return OUT_OF_BOUNDS

    token = board.get_piece(from_pos)
    if token == "." or token_color(token) != color:
        return NOT_YOUR_PIECE

    return rule_engine.check_move(board, token_type(token), color, from_pos, to_pos)


def validate_jump(board, color, pos) -> str:
    if not board.is_inside(pos):
        return OUT_OF_BOUNDS

    token = board.get_piece(pos)
    if token == "." or token_color(token) != color:
        return NOT_YOUR_PIECE

    return rule_engine.OK
