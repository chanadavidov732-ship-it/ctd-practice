from shared.model.board import Board
from shared.model.game_state import GameState
from shared.realtime.realtime_arbiter import RealTimeArbiter
from engine.game_engine import GameEngine
from client.input.board_mapper import BoardMapper
from client.input.controller import Controller


def build_game(grid):
    board = Board(grid)
    game_state = GameState()
    arbiter = RealTimeArbiter(board, game_state)
    game_engine = GameEngine(board, game_state, arbiter)
    board_mapper = BoardMapper(board)
    controller = Controller(board, board_mapper, game_engine)
    return board, game_state, arbiter, game_engine, board_mapper, controller
