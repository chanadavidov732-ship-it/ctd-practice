from game_chess.engine.game_engine import GameEngine

from shared.model.board import Board
from shared.model.game_state import GameState
from shared.model.standard_setup import STANDARD_START_GRID
from shared.realtime.realtime_arbiter import RealTimeArbiter


def create_engine():
    grid = [row[:] for row in STANDARD_START_GRID]
    board = Board(grid)
    game_state = GameState()
    arbiter = RealTimeArbiter(board, game_state)
    engine = GameEngine(board, game_state, arbiter)
    return board, game_state, arbiter, engine
