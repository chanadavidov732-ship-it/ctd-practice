from game_chess.engine.game_engine import GameEngine

from shared.model.board import Board
from shared.model.game_state import GameState
from shared.model.piece import token_color, token_type
from shared.realtime.realtime_arbiter import RealTimeArbiter
from shared.rules import rule_engine

STANDARD_START_GRID = [
    "bR bN bB bQ bK bB bN bR".split(),
    "bP bP bP bP bP bP bP bP".split(),
    ". . . . . . . .".split(),
    ". . . . . . . .".split(),
    ". . . . . . . .".split(),
    ". . . . . . . .".split(),
    "wP wP wP wP wP wP wP wP".split(),
    "wR wN wB wQ wK wB wN wR".split(),
]


def create_engine():
    grid = [row[:] for row in STANDARD_START_GRID]
    board = Board(grid)
    game_state = GameState()
    arbiter = RealTimeArbiter(board, game_state)
    engine = GameEngine(board, game_state, arbiter)
    return board, game_state, arbiter, engine


def check_move_reason(board, from_pos, to_pos) -> str:
    """Independently re-runs shared.rules validation for a from_pos whose
    piece/color are already known to be valid. GameEngine.request_move itself
    silently no-ops on an illegal move, so this exists purely to recover the
    rejection reason to report back to the client."""
    token = board.get_piece(from_pos)
    piece_type = token_type(token)
    piece_color = token_color(token)
    return rule_engine.check_move(board, piece_type, piece_color, from_pos, to_pos)
